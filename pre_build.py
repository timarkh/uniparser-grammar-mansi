import re
import os
import shutil
import json


def collect_lemmata(dirName):
    lemmata = ''
    lexrules = ''
    for fname in os.listdir(dirName):
        if fname.endswith('.txt') and fname.startswith('lexemes'):
            f = open(os.path.join(dirName, fname), 'r', encoding='utf-8-sig')
            lemmata += f.read() + '\n'
            f.close()
        elif fname.endswith('.txt') and fname.startswith('lexrules'):
            f = open(os.path.join(dirName, fname), 'r', encoding='utf-8-sig')
            lexrules += f.read() + '\n'
            f.close()
    lemmataSet = set(re.findall('-lexeme\n(?: [^\r\n]*\n)+', lemmata, flags=re.DOTALL))
    lemmata = '\n'.join(sorted(list(lemmataSet)))
    return lemmata, lexrules


def prepare_files():
    """
    Put all grammar files to ../uniparser_mansi_lat/data_strict/.
    """
    lemmata, lexrules = collect_lemmata('.')
    with open('uniparser_mansi_lat/data_strict/lexemes.txt', 'w', encoding='utf-8') as fOutLemmata:
        fOutLemmata.write(lemmata)

    with open('paradigms.txt', 'r', encoding='utf-8-sig') as fInParadigms:
        paradigms = fInParadigms.read()
    with open('uniparser_mansi_lat/data_strict/paradigms.txt', 'w', encoding='utf-8') as fOutParadigms:
        fOutParadigms.write(paradigms)

    # with open('uniparser_mansi_lat/data_strict/lex_rules.txt', 'w', encoding='utf-8') as fOutLexrules:
    #     fOutLexrules.write(lexrules)
    if os.path.exists('bad_analyses.txt'):
        shutil.copy2('bad_analyses.txt', 'uniparser_mansi_lat/data_strict/')
    if os.path.exists('mansi_disambiguation.cg3'):
        shutil.copy2('mansi_disambiguation.cg3', 'uniparser_mansi_lat/data_strict/')


def parse_wordlists():
    """
    Analyze wordlists/wordlist.csv.
    """
    from uniparser_mansi_lat import MansiAnalyzer
    a = MansiAnalyzer(mode='strict')
    a.analyze_wordlist(freqListFile='wordlists/wordlist.csv',
                       parsedFile='wordlists/wordlist_analyzed.txt',
                       unparsedFile='wordlists/wordlist_unanalyzed.txt',
                       verbose=True,
                       replacementsAllowed=0)


rxVowels = re.compile('[aāeēiīoōuūə]')
# rxLastVowel = re.compile('([aāeēiīoōuūə])([^aāeēiīoōuūə]*)$')
rxLastVowel = re.compile('(ə)([^aāeēiīoōuūə]+)$')
vowelRepl = {
    # 'a': '',
    # 'ā': 'a',
    # 'e': '',
    # 'ē': 'e',
    # 'i': '',
    # 'ī': 'i',
    # 'o': '',
    # 'ō': 'o',
    # 'u': '',
    # 'ū': 'u',
    'ə': ''
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


def make_stem(lex, pos):
    stemVars = [lex]
    nVowels = len(rxVowels.findall(lex))
    if nVowels % 2 == 0:
        stemVars.append(rxLastVowel.sub(lambda m: vowelRepl[m.group(1)] + m.group(2), lex))
    return '|'.join(var + '.' for var in sorted(set(stemVars), key=lambda x: (-len(x), x)))


def make_para(lex, pos):
    if pos == 'unknown':
        pos = 'unchangeable_'
    else:
        pos += '_'
    nVowels = len(rxVowels.findall(lex))
    if nVowels % 2 == 0:
        pos += 'even'
    else:
        pos += 'odd'
    return pos


def make_lexeme(lemma, glossRu, glossEn, pos):
    if pos == '':
        pos = 'unknown'
    pos = re.sub('_guess', '', pos)
    lex = '-lexeme\n'
    lex += ' lex: ' + lemma + '\n'
    lex += ' stem: ' + make_stem(lemma, pos) + '\n'
    lex += ' gramm: ' + pos + '\n'
    lex += ' paradigm: ' + make_para(lemma, pos) + '\n'
    lex += ' gloss: ' + glossEn + '\n'
    # lex += ' trans_en: ' + glossEn + '\n'
    lex += ' gloss_ru: ' + glossRu + '\n'
    return lex


def filter_lexemes(lexemes):
    """
    Filter short stems for which there are long stems
    """
    filtered = []
    for lex in lexemes:
        m = re.search(' stem: ([^/\r\n]+\n).*?(trans_en: [^\r\n]*\n trans_ru: [^\r\n]*)', lex, flags=re.DOTALL)
        if m is None:
            filtered.append(lex)
        else:
            if any ('//' + m.group(1) in l and m.group(2) in l for l in lexemes):
                continue
            filtered.append(lex)
    return filtered


def convert_lexemes():
    with open('lexemes.json', 'r', encoding='utf-8') as fIn:
        lexJson = json.load(fIn)
    lexemes = []
    for lex in sorted(lexJson, key=sort_key):
        freqs = lexJson[lex]
        vars = {}
        for var in freqs:
            freq = freqs[var]
            glossRu, glossEn, pos = var.split('\t')
            if len(glossRu) <= 0 and len(glossEn) <= 0:
                continue
            if pos == '':
                if (glossRu, glossEn, 'N') in vars or (glossRu, glossEn, 'V') in vars:
                    continue
                if re.search('[a-z]', glossRu) is not None:
                    continue
                if glossRu.endswith(('ий', 'ый', 'ой')):
                    pos = 'ADJ_guess'
                elif glossRu.endswith(('ать', 'аться', 'ить', 'иться', 'ыть', 'ыться', 'уть', 'уться', 'тись', 'сти', 'йти')):
                    pos = 'V_guess'
                else:
                    pos = 'N_guess'
                vars[(glossRu, glossEn, pos)] = freq
            else:
                if pos == 'N' and (glossRu, glossEn, 'V') in vars and vars[(glossRu, glossEn, 'V')] > freq:
                    continue
                if pos == 'V' and (glossRu, glossEn, 'N') in vars and vars[(glossRu, glossEn, 'N')] > freq:
                    continue
                vars = {v: vars[v] for v in vars if v != (glossRu, glossEn, '')}
                vars[(glossRu, glossEn, pos)] = freq
        for var in vars:
            lexemes.append(make_lexeme(lex, var[0], var[1], var[2]))
    lexemes = filter_lexemes(lexemes)
    with open('lexemes.txt', 'w', encoding='utf-8') as fOut:
        fOut.write('\n'.join(lexemes))


if __name__ == '__main__':
    # convert_lexemes()
    prepare_files()
    parse_wordlists()
    from uniparser_mansi_lat import MansiAnalyzer
    a = MansiAnalyzer(mode='strict')
    for wf in a.analyze_words(['ōjka'], format='xml'):
        print(wf)
