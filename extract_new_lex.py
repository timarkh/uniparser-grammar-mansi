import re
import os
from translit_mansi_lat import mansi_translit_cyr2lat
from pre_build import make_para, make_stem
import pymorphy2

def pymorphy2_311_hotfix():
    from inspect import getfullargspec
    from pymorphy2.units.base import BaseAnalyzerUnit

    def _get_param_names_311(klass):
        if klass.__init__ is object.__init__:
            return []
        args = getfullargspec(klass.__init__).args
        return sorted(args[1:])

    setattr(BaseAnalyzerUnit, '_get_param_names', _get_param_names_311)

pymorphy2_311_hotfix()
morphRu = pymorphy2.MorphAnalyzer(lang='ru')
rxPOSRus = re.compile('\\b[A-Z]+')

posCyr2Lat = {
    'гл': 'V',
    'межд': 'INTRJ',
    'нареч': 'ADV',
    'прил': 'ADJ',
    'сущ': 'N',
    'числит': 'NUM'
}


def clean_trans(s):
    s = re.sub('\\b([0-9]+[).]+|i+|ш\\b|п \\b) *', '', s)
    s = s.replace('́', '')
    s = re.sub('^[а-я]{2,5}\\. +', '', s)
    s = re.sub('  +', ' ', s)
    s = s.strip(' .,:;')
    return s


def trans2gloss(s):
    return re.sub('^((\\w\\w?\\w? )?[\\w̄]+( \\w\\w?\\b)?).*', '\\1', s)


def extract_lemmas(fnameIn, fnameOut):
    with open(fnameIn, 'r', encoding='utf-8') as fIn:
        text = fIn.read().replace('\t', ' ')
    lemmas = re.findall('(?<=\n)[0-9 ]*([а-яёӈӣӯ̄]+) +(гл\\.(?! прист\\.)|межд\\.|нареч\\.|прил\\.|сущ\\.|числит\\.) +([^;\n]+)',
                        text, flags=re.DOTALL)
    table = []
    for l in lemmas:
        lemma = mansi_translit_cyr2lat(l[0])
        pos = posCyr2Lat[l[1].strip('.')]
        trans_ru = clean_trans(l[2])
        gloss_ru = re.sub('[^\\w].*', '', trans_ru)
        if pos == 'V':
            lemma = re.sub('[au]ŋkwe?$', '', lemma)
        stem = make_stem(lemma, pos)
        paradigm = make_para(lemma, pos, stem)
        table.append([lemma, pos, '', stem, paradigm, gloss_ru, '', trans_ru, ''])

    with open(fnameOut, 'w', encoding='utf-8') as fOut:
        for line in table:
            fOut.write('\t'.join(line) + '\n')


def is_good_gramm(gramm):
    if 'pos' not in gramm:
        return False
    if gramm['pos'] == 'N':
        if ('case' in gramm and gramm['case'] == 'nom'
                and 'num' in gramm and gramm['num'] == 'sg'):
            return True
        if 'prop' in gramm:
            return True
        return False
    if gramm['pos'] == 'V':
        if 'mood_form' in gramm and gramm['mood_form'] == 'inf':
            return True
        if 'mood_form' in gramm and gramm['mood_form'] == 'ptcp':
            return True
        return False
    return True


def get_pos_from_rus(trans_ru):
    pos = set()
    for wTrans in re.findall('\\b[а-яё][а-яё-]+\\b', trans_ru.lower()):
        parses = morphRu.parse(wTrans)
        if len(parses) > 0 and all('Unkn' not in str(p)
                                   and 'Fake' not in str(p)
                                   for p in parses):
            for p in parses:
                curPos = rxPOSRus.findall(str(p.tag))
                for cp in curPos:
                    pos.add(cp)
    if 'ADVB' in pos:
        return 'ADV'
    if 'NOUN' in pos:
        return 'N'
    if 'ADJS' in pos or 'ADJF' in pos:
        return 'ADJ'
    if any (cp.startswith('NUM') for cp in pos):
        return 'NUM'
    if 'CONJ' in pos:
        return 'CONJ'
    if 'INTJ' in pos:
        return 'INTRJ'
    return 'X'


def process_rombandeeva():
    """
    Preliminary processing of the imperfectly OCRed Rombandeeva-Kuzakova
    Mansi-Russian dictionary.
    """
    rxWord = re.compile('\\b[а-яё̄́ӈӣӯ]{3,}', flags=re.DOTALL)
    rxEntry = re.compile('^([а-яё̄ӈӣӯ]{3,})((?:, *[а-яё̄ӈӣӯ]{3,})*)'
                         '[ IПШ]+[ .]*([^;]+)')
    with open('add_lex/rombandeeva/rombandeeva.txt', 'r', encoding='utf-8') as fIn:
        lines = [line.strip() for line in fIn if line.strip()]
    wordFreqs = {}
    # Count words, so that only those with a count of >= 2 are considered
    for line in lines:
        for w in rxWord.findall(line.lower()):
            try:
                wordFreqs[w] += 1
            except KeyError:
                wordFreqs[w] = 1

    from uniparser_mansi_lat import MansiAnalyzer
    aStrict = MansiAnalyzer(mode='strict')
    aStrict.alphabet = 'cyr'
    aLax = MansiAnalyzer(mode='nodiacritics')
    aLax.alphabet = 'cyr'

    linesOut = []

    for line in lines:
        if 'ПОСЛЕЛОГИ' in line:
            break   # Start of the Russian-Mansi part
        m = rxEntry.search(line.lower())
        if not m:
            # print('Bad enrty: ' + line)
            continue
        lemma = m.group(1)
        if lemma not in wordFreqs or wordFreqs[lemma] == 1:
            print('Hapax legomenon: ' + lemma)
            # continue
        trans_ru = m.group(3)
        trans_ru = clean_trans(trans_ru)
        transExist = ''
        transExistLax = ''
        for ana in aStrict.analyze_words(lemma, format='json'):
            print(ana)
            if ('lemma' in ana and ana['lemma']
                    and is_good_gramm(ana['gramm'])
                    and 'trans_ru' in ana):
                transExist += ana['trans_ru'] + ' // '
        transExist = transExist.strip(' /')
        if not transExist:
            for ana in aLax.analyze_words(lemma, format='json'):
                if ('lemma' in ana and ana['lemma']
                        and is_good_gramm(ana['gramm'])
                        and 'trans_ru' in ana):
                    transExistLax += ana['trans_ru'] + ' // '
            transExistLax = transExist.strip(' /')
        pos = ''
        if len(lemma) >= 7 and re.search('[ауяю]ӈкве$', lemma):
            pos = 'V'
        else:
            pos = get_pos_from_rus(trans_ru)
        linesOut.append((lemma, pos, trans_ru, trans2gloss(trans_ru), transExist, transExistLax))

    with open('add_lex/rombandeeva/rombandeeva_out.csv', 'w', encoding='utf-8') as fOut:
        for line in linesOut:
            fOut.write('\t'.join(line) + '\n')


if __name__ == '__main__':
    # extract_lemmas('lozva_dict.txt', 'lozva_dict.csv')
    process_rombandeeva()
