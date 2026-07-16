import re
import os

rxLexeme = re.compile('(-lexeme\n lex: ([^\r\n]+)\n(?: [^\r\n]*\n)*?'
                      ' gramm: ([^\r\n,]+)[^\r\n]*\n(?: [^\r\n]*\n)*)', flags=re.DOTALL)


badChars = {
        'ā': 'ā',
        'ō': 'ō',
        'ē': 'ē',
        'ī': 'ī',
        'ū': 'ū',
        'γ': 'ɣ',
        'é': 'e',
        'á': 'a',
        'ȯ': 'o'
    }


def sort_key(s):
    # s = s.replace('a', 'a2')
    s = s.replace('ā', 'a')
    # s = s.replace('e', 'e2')
    s = s.replace('ē', 'e')
    # s = s.replace('i', 'i2')
    s = s.replace('ī', 'i')
    # s = s.replace('o', 'o2')
    s = s.replace('ō', 'o')
    # s = s.replace('u', 'u2')
    s = s.replace('ū', 'u')
    s = s.replace('ɣ', 'g')
    s = s.replace('n', 'n1')
    s = s.replace("n1'", 'n2')
    s = s.replace('l', 'l1')
    s = s.replace("l1'", 'l2')
    return s


def split_fields(lex):
    lemma = ''
    pos = ''
    grdic = ''
    stem = ''
    paradigm = ''
    gloss_ru = ''
    gloss = ''
    lemma = ' / '.join(re.findall(' lex: *([^\r\n]*?) *\n', lex, flags=re.DOTALL))
    m = re.search(' gramm: *([^\r\n ]*)', lex, flags=re.DOTALL)
    if m is not None:
        pos = m.group(1)
    m = re.search(' stem: *([^\r\n]*)', lex, flags=re.DOTALL)
    if m is not None:
        stem = m.group(1).strip()
    paradigm = ' / '.join(re.findall(' paradigm: *([^\r\n]*?) *\n', lex, flags=re.DOTALL))
    gloss_ru = ' / '.join(re.findall(' gloss_ru: *([^\r\n]*?) *\n', lex, flags=re.DOTALL))
    gloss = ' / '.join(re.findall(' gloss: *([^\r\n]*?) *\n', lex, flags=re.DOTALL))
    return lemma, pos, grdic, stem, paradigm, gloss_ru, gloss


def load_tabulate_lexemes(fnameDict):
    curDict = {}
    table = []
    usedLexemes = set()
    with open(fnameDict, 'r', encoding='utf-8') as fIn:
        text = fIn.read()
        lexemesFound = rxLexeme.findall(text)
        print(len(lexemesFound), 'lexemes found.')
        for lexeme, lemma, pos in lexemesFound:
            lexeme = re.sub('(gramm: *[A-Z]+)\\?', '\\1', lexeme)
            if lexeme in usedLexemes:
                print('Duplicate', lexeme)
                continue    # remove complete duplicates
            if (lemma, pos) not in curDict:
                curDict[(lemma, pos)] = []
            curDict[(lemma, pos)].append(lexeme)
    lexNew = set()
    for lemma, pos in curDict:
        for lexeme in curDict[(lemma, pos)]:
            lemma, pos, grdic, stem, paradigm, gloss_ru, gloss = split_fields(lexeme)
            if lexeme in lexNew:
                print('Duplicate', lexeme)
            else:
                table.append([lemma, pos, grdic, stem, paradigm, gloss_ru, gloss, ''])
                lexNew.add(lexeme)
    return lexNew, table


def yaml2csv(fnameYaml, fnameCsv, fnameExistingCsv=''):
    lex, table = load_tabulate_lexemes(fnameYaml)
    wfFreqs = {}
    lemmaFreqs = {}
    rxLemma = re.compile('\\bl(?:ex)?="([^\r\n"<>]+)"')
    rxWf = re.compile('>([^\r\n<>]+)</w>')
    # with open('wordlists/wordlist.csv', 'r', encoding='utf-8-sig') as fWordlist:
    #     for line in fWordlist:
    #         if '\t' not in line:
    #             continue
    #         wf, freq = line.strip('\r\n').split('\t')
    #         wfFreqs[wf] = int(freq)
    # with open('wordlists/wordlist_analyzed.txt', 'r', encoding='utf-8-sig') as fAnalyzed:
    #     for line in fAnalyzed:
    #         mWf = rxWf.search(line)
    #         if mWf is None:
    #             continue
    #         wf = mWf.group(1)
    #         if wf not in wfFreqs:
    #             print(wf, 'not in frequency list')
    #             continue
    #         freq = wfFreqs[wf]
    #         for lemma in rxLemma.findall(line):
    #             if lemma not in lemmaFreqs:
    #                 lemmaFreqs[lemma] = freq
    #             else:
    #                 lemmaFreqs[lemma] += freq
    for i in range(len(table)):
        lemma = table[i][0]
        if lemma not in lemmaFreqs:
            table[i].append(0)
        else:
            table[i].append(lemmaFreqs[lemma])
    with open('cur-lexemes.txt', 'w', encoding='utf-8') as fOut:
        fOut.write('\n'.join(l for l in sorted(lex)))
    # Sort by POS, then by frequency, then by lemma
    with open(fnameCsv, 'w', encoding='utf-8') as fOut:
        fOut.write('\n'.join('\t'.join(str(field) for field in line)
                             for line in table))
                             # for line in sorted(table, key=lambda l: (l[1], -l[-1], l[0]))))

def clean(s):
    for c in badChars:
        s = s.replace(c, badChars[c])
        s = s.replace(c.upper(), badChars[c].upper())
    return s


def csv2yaml(fnameCsv, fnameYaml, fnameDel):
    """
    Load manually edited data from a CSV.
    """
    lexemesOut = []
    lexDel = []
    with open(fnameCsv, 'r', encoding='utf-8') as fIn:
        lexemes = fIn.readlines()
    for lex in sorted(l.strip('\r\n') for l in lexemes if len(l) > 5 and '\t' in l):
        lex = clean(lex)
        lex += '\t' * (7 - lex.count('\t'))
        lemma, pos, stem, para, trans_ru, trans_en, remove, rest = lex.split('\t', 8)
        if len(remove.strip()) > 0 or len(lemma) <= 0:
            lexDel.append(lex)
            continue
        if 'PN' not in pos and re.search('\\b(topn|famn|persn|patrn)\\b', pos) is not None:
            pos += ',PN'
        if 'PN' not in pos and (lemma[0].lower() != lemma[0]
                                or (len(trans_en) > 0 and trans_en[0].lower() != trans_en[0] and trans_en.upper() != trans_en)):
            pos += ',PN'
        if 'anim' not in pos and re.search('\\b(hum)\\b', pos) is not None:
            pos += ',anim'
        gramm = pos.replace(' ', '')
        gramm = gramm.strip('.,')
        if re.search(',(persn|topn|famn|patrn|PN)\\b', gramm) is not None:
            lemma = lemma[0].upper() + lemma[1:]
        if para.startswith('ADV'):
            para = 'ADV'
        elif len(para) <= 0 or re.search('^(N|V|ADJ|NUM|ADV|POSTP)', para) is None:
            para = 'unchangeable'
        elif '|' in stem:
            if re.search('^\\w\\w\\.\\|\\w\\w\\w\\.', stem) is not None:
                para = 'V_odd_short'
            elif re.search('^([\\w\']+)[aeiouāēīōūə]([^aeiouāēīōūə]*)\\|\\1\\2', stem) is not None:
                para += '-syncop'
            elif re.search('^([\\w\']+)[nŋ]\'?([^aeiouāēīōūə]+)\\|\\1\\2', stem) is not None:
                para += '-n'
            elif stem == 'xum.|xumi.':
                para = 'N_xum'
            else:
                print(stem, para)
        para = para.replace(' ', '').split('/')
        lexOut = ('\n-lexeme\n lex: ' + lemma + '\n stem: ' + stem.strip().replace(' /', '/').replace(' |', '|')
                  + '\n gramm: ' + gramm + ''.join('\n paradigm: ' + p for p in sorted(para))
                  + '\n gloss: ' + trans_en.strip() + '\n gloss_ru: ' + trans_ru.strip() + '\n')
        lexemesOut.append([re.sub(',.*', '', gramm), lemma, lexOut])
    lexemesOutStr = ''.join(l[2] for l in sorted(lexemesOut, key=lambda x: sort_key(x[1])))

    with open(fnameYaml, 'w', encoding='utf-8') as fOut:
        fOut.write(lexemesOutStr.strip())
    with open(fnameDel, 'w', encoding='utf-8') as fOut:
        fOut.write('\n'.join(lexDel))


if __name__ == '__main__':
    # yaml2csv('lexemes.txt', 'lexemes.csv')
    # yaml2csv('lexemes_update_2026.07.14.txt', 'lexemes_update_2026.07.14.csv')
    # yaml2csv('udm_lexemes_V.txt', 'add_lex/udm_lexemes_V.csv')
    # yaml2csv('udm_lexemes_N_persn.txt', 'add_lex/udm_lexemes_N_persn.csv')
    # yaml2csv('udm_lexemes_ADJ.txt', 'add_lex/udm_lexemes_ADJ.csv')
    # yaml2csv('udm_lexemes_unchangeable.txt', 'add_lex/udm_lexemes_unchangeable.csv')
    csv2yaml('lexemes_update_2026.07.14.csv', 'lexemes_update_2026.07.14.txt', 'lex_deleted_2026.07.14.csv')
    # csv2yaml('lexemes-mansi-lat.csv', 'lexemes.txt', 'lex_deleted.csv')
