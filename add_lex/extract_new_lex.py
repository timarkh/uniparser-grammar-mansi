import re
import os
from translit_mansi_lat import mansi_translit_cyr2lat
from pre_build import make_para, make_stem
posCyr2Lat = {
    'гл': 'V',
    'межд': 'INTRJ',
    'нареч': 'ADV',
    'прил': 'ADJ',
    'сущ': 'N',
    'числит': 'NUM'
}


def clean_trans(s):
    s = re.sub('[0-1][).]+ *', '', s)
    s = re.sub('  +', ' ', s)
    s = s.strip(' .,:;')
    return s


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


if __name__ == '__main__':
    extract_lemmas('lozva_dict.txt', 'lozva_dict.csv')
