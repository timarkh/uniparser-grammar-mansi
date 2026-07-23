import re
import os
import shutil
import json
from rapidfuzz.distance import DamerauLevenshtein
from rapidfuzz.fuzz import ratio
from uniparser_mansi_lat import simplify
from sklearn.metrics.pairwise import cosine_similarity
import math
from itertools import combinations

badChars = {
        'ā': 'ā',
        'ō': 'ō',
        'ē': 'ē',
        'ī': 'ī',
        'ū': 'ū',
        'γ': 'ɣ',
        'é': 'e',
        'á': 'a',
        'ȯ': 'o',
        '̊': ''
    }

rxStem = re.compile('( stem: *)([^\r\n]+)')
rxStemVariants = re.compile('[^|/]+')
rxPhon = re.compile("[lnt]'?|.")
palatCons = {
    "t": "t'",
    "n": "n'",
    "l": "l'",
    "t'": "t",
    "n'": "n",
    "l'": "l"
}

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


def palat_var(s):
    """
    Return all variants of `s` with one or more palatalizations swapped.
    """
    phonemes = rxPhon.findall(s)
    positions = [i for i, c in enumerate(phonemes) if c in palatCons]
    variants = set()
    for r in range(1, len(positions) + 1):
        for changed in combinations(positions, r):
            changed = set(changed)
            var = ''
            for i, c in enumerate(phonemes):
                if i in changed:
                    var += palatCons[c]
                else:
                    var += c
            variants.add(var)
    return variants


def add_palatal_var_stem(s):
    s = s.group(0)
    # if "'" not in s:
    #     return s
    vars = '//'.join(palat_var(s))
    if vars:
        return s + '//' + vars
    return s


def add_palatal_vars_stem(m):
    morphEnhanced = rxStemVariants.sub(add_palatal_var_stem, m.group(2).strip())
    return m.group(1) + morphEnhanced + '\n std: ' + re.sub('//[^|]*', '', m.group(2))


def add_palatal_vars(lemmata):
    """
    Add non-palatalized variants for palatalized phonemes and vice versa.
    """
    return rxStem.sub(add_palatal_vars_stem, lemmata)


def prepare_files():
    """
    Put all grammar files to ../uniparser_mansi_lat/data_strict/.
    """
    lemmata, lexrules = collect_lemmata('.')
    with open('uniparser_mansi_lat/data_strict/lexemes.txt', 'w', encoding='utf-8') as fOutLemmata:
        fOutLemmata.write(lemmata)
    with open('uniparser_mansi_lat/data_nodiacritics/lexemes.txt', 'w', encoding='utf-8') as fOutLemmata:
        fOutLemmata.write(lemmata)
    with open('uniparser_mansi_lat/data_nopalatal/lexemes.txt', 'w', encoding='utf-8') as fOutLemmata:
        fOutLemmata.write(add_palatal_vars(lemmata))

    with open('paradigms.txt', 'r', encoding='utf-8-sig') as fInParadigms:
        paradigms = fInParadigms.read()
    with open('uniparser_mansi_lat/data_strict/paradigms.txt', 'w', encoding='utf-8') as fOutParadigms:
        fOutParadigms.write(paradigms)
    with open('uniparser_mansi_lat/data_nodiacritics/paradigms.txt', 'w', encoding='utf-8') as fOutParadigms:
        fOutParadigms.write(paradigms)
    with open('uniparser_mansi_lat/data_nopalatal/paradigms.txt', 'w', encoding='utf-8') as fOutParadigms:
        fOutParadigms.write(paradigms)

    # with open('uniparser_mansi_lat/data_strict/lex_rules.txt', 'w', encoding='utf-8') as fOutLexrules:
    #     fOutLexrules.write(lexrules)
    if os.path.exists('bad_analyses.txt'):
        shutil.copy2('bad_analyses.txt', 'uniparser_mansi_lat/data_strict/')
        shutil.copy2('bad_analyses.txt', 'uniparser_mansi_lat/data_nodiacritics/')
        shutil.copy2('bad_analyses.txt', 'uniparser_mansi_lat/data_nopalatal/')
    if os.path.exists('mansi_disambiguation.cg3'):
        shutil.copy2('mansi_disambiguation.cg3', 'uniparser_mansi_lat/data_strict/')
        shutil.copy2('mansi_disambiguation.cg3', 'uniparser_mansi_lat/data_nodiacritics/')
        shutil.copy2('mansi_disambiguation.cg3', 'uniparser_mansi_lat/data_nopalatal/')

    if os.path.exists('char_equiv.txt'):
        shutil.copy2('char_equiv.txt', 'uniparser_mansi_lat/data_nodiacritics/')
        shutil.copy2('char_equiv.txt', 'uniparser_mansi_lat/data_nopalatal/')
    if os.path.exists('gloss_replacements.csv'):
        shutil.copy2('gloss_replacements.csv', 'uniparser_mansi_lat/data_strict/')
        shutil.copy2('gloss_replacements.csv', 'uniparser_mansi_lat/data_nodiacritics/')
        shutil.copy2('gloss_replacements.csv', 'uniparser_mansi_lat/data_nopalatal/')


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


def filter_lexemes(lexemes, fnameProcessed=''):
    """
    Filter short stems for which there are long stems
    """
    lexProcessed = set()
    if len(fnameProcessed) > 0:
        with open(fnameProcessed, 'r', encoding='utf-8') as fIn:
            for line in fIn:
                if '\t' not in line:
                    continue
                fields = line.strip(' \r\n').split('\t')
                lexProcessed.add((simplify(fields[0]), fields[4], fields[5]))

    filtered = []
    for iLex in range(len(lexemes)):
        lex = lexemes[iLex]
        m = re.search(' lex: ([^\r\n]+)\n.*? stem: ([^/\r\n]+)\n.*?(gloss: ([^\r\n]*)\n gloss_ru: ([^\r\n]*))', lex, flags=re.DOTALL)
        if m is None:
            filtered.append(lex)
            print(' Weird lexeme: ', lex)
        else:
            # print((simplify(m.group(1)), m.group(5), m.group(4)))
            if any (iLexOther != iLex
                    and ('//' + m.group(2) in lexemes[iLexOther]
                         or 'lex: ' + m.group(1) in lexemes[iLexOther])
                    and m.group(3) in lexemes[iLexOther]
                    for iLexOther in range(len(lexemes))):
                continue
            elif (simplify(m.group(1)), m.group(5), m.group(4)) in lexProcessed:
                print('Processed lexeme: ' + lex)
                continue
            elif any(m.group(5) == l[1]
                     and m.group(4) == l[2]
                     and DamerauLevenshtein.distance(m.group(1), l[0], score_cutoff=1) <= 1
                     for l in lexProcessed):
                print('Processed lexeme (Damerau-Levenshtein): ' + lex)
                continue
            filtered.append(lex)
    return filtered


def clean(s):
    for c in badChars:
        s = s.replace(c, badChars[c])
        s = s.replace(c.upper(), badChars[c].upper())
    return s


def convert_lexemes(fnameIn='lexemes.json',
                    fnameOut='lexemes.txt',
                    fnameProcessed=''):
    with open(fnameIn, 'r', encoding='utf-8') as fIn:
        lexJson = json.load(fIn)
    lexemes = []
    lexJson = {clean(k): v for k, v in lexJson.items()}
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
    lexemes = filter_lexemes(lexemes, fnameProcessed=fnameProcessed)
    with open(fnameOut, 'w', encoding='utf-8') as fOut:
        fOut.write('\n'.join(lexemes))

def cos_sim(lex1, lex2):
    """
    Cosine similarity of the embeddings of the two glosses.
    """
    if ((len(lex1[3]) <= 0 or len(lex2[3]) <= 0)
            and (len(lex1[4]) <= 0 or len(lex2[4]) <= 0)):
        return 0.0
    if len(lex1[3]) <= 0 or len(lex2[3]) <= 0:
        return cosine_similarity([lex1[4]], [lex2[4]])[0][0]
    elif len(lex1[4]) <= 0 or len(lex2[4]) <= 0:
        return cosine_similarity([lex1[3]], [lex2[3]])[0][0]
    # English similarities are more reliable
    return 0.7 * cosine_similarity([lex1[3]], [lex2[3]])[0][0] \
        + 0.3 * cosine_similarity([lex1[4]], [lex2[4]])[0][0]

def find_best_alt(lex, existingLex):
    """
    Find the best alternative for a deleted lexeme among the
    existing lexemes.
    """
    candidates = []
    simpleLemma = simplify(lex[0], over=True)
    oversimpleLemma = simplify(lex[0], over=True)
    for exLex in existingLex:
        if exLex[1] == lex[1] and simplify(exLex[0], over=True) == simpleLemma:
            candidates.append(exLex)
    if len(candidates) <= 0:
        for exLex in existingLex:
            if exLex[2] == lex[2] and simplify(exLex[0], over=True) == simpleLemma:
                candidates.append(exLex)

    if len(candidates) <= 0:
        for exLex in existingLex:
            if ((exLex[1] == lex[1] or exLex[2] == lex[2] or cos_sim(exLex, lex) > 0.58)
                    and simpleLemma[0] == simplify(exLex[0])[0]  # it's improbable that the first letter is different
                    and DamerauLevenshtein.distance(simpleLemma,
                                                    simplify(exLex[0]),
                                                    score_cutoff=1) <= 1
                    and ratio(simpleLemma, simplify(exLex[0]),
                              score_cutoff=70) >= 70):
                candidates.append(exLex)
    if len(candidates) <= 0:
        for exLex in existingLex:
            if ((exLex[1] == lex[1] or exLex[2] == lex[2] or cos_sim(exLex, lex) > 0.58)
                    and oversimpleLemma[0] == simplify(exLex[0], over=True)[0]  # it's improbable that the first letter is different
                    and DamerauLevenshtein.distance(oversimpleLemma,
                                                    simplify(exLex[0], over=True),
                                                    score_cutoff=2) <= min(2, len(oversimpleLemma) - 1, len(exLex[0]) - 1)
                    and ratio(oversimpleLemma, simplify(exLex[0], over=True),
                              score_cutoff=60) >= 60):
                candidates.append(exLex)
    if len(candidates) > 1:
        candidates.sort(key=lambda x: (-math.floor(cos_sim(x, lex) * 6),
                                       -ratio(simplify(x[0], over=True),
                                              oversimpleLemma,
                                              score_cutoff=60)))
        print(lex[:3], [c[:3] + [-math.floor(cos_sim(c, lex) * 6),
                                 -ratio(simplify(c[0], over=True),
                                        oversimpleLemma,
                                        score_cutoff=60)]
                        for c in candidates])
    if len(candidates) > 0:
        return candidates[0]
    return None

def generate_replacements():
    """
    Prepare a list of deleted lexemes indicating what they
    have to be replaced with.
    """
    from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer('all-MiniLM-L6-v2')
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    existingLex = []     # (lemma, gloss_en, gloss_ru, embedding_en, embedding_ru)
    deletedLex = []
    with open('lexemes.txt', 'r', encoding='utf-8') as fIn:
        text = fIn.read()
        existingLex = [l for l in re.findall(' lex: +([^\r\n]+)\n(?: [^\r\n]*\n)*'
                                             ' gloss: +([^\r\n]+)\n(?: [^\r\n]*\n)*'
                                             ' gloss_ru: +([^\r\n]+)', text,
                                             flags=re.DOTALL)]
    embeddingsEn = model.encode([l[1].replace('.', ' ') for l in existingLex])
    embeddingsRu = model.encode([l[2].replace('.', ' ') for l in existingLex])
    existingLex = [list(existingLex[i]) + [embeddingsEn[i], embeddingsRu[i]]
                   for i in range(len(existingLex))]

    with open('lex_deleted.csv', 'r', encoding='utf-8') as fIn:
        for line in fIn:
            if len(line) <= 5 or '\t' not in line:
                continue
            line = line.strip('\r\n ').split('\t')
            if line[-2] != 'x':
                continue    # words that need checking; maybe they are alright
            deletedLex.append((line[0], line[5], line[4]))
    embeddingsEn = model.encode([l[1].replace('.', ' ') for l in deletedLex])
    embeddingsRu = model.encode([l[2].replace('.', ' ') for l in deletedLex])
    deletedLex = [list(deletedLex[i]) + [embeddingsEn[i], embeddingsRu[i]]
                  for i in range(len(deletedLex))]

    with open('gloss_replacements.csv', 'w', encoding='utf-8'):
        pass
    for lex in deletedLex:
        bestAlt = find_best_alt(lex, existingLex)
        with open('gloss_replacements.csv', 'a', encoding='utf-8') as fOut:
            if bestAlt is not None:
                fOut.write('\t'.join(lex[:3]) + '\t' + '\t'.join(bestAlt[:3]) + '\n')
            else:
                fOut.write('\t'.join(lex[:3]) + '\t' + '\t'.join(['NONE', '', '']) + '\n')


if __name__ == '__main__':
    # convert_lexemes('lexemes_update.json',
    #                 'lexemes_update_2026.07.14.txt',
    #                 'lexemes-mansi-lat.csv')
    prepare_files()
    parse_wordlists()
    # generate_replacements()

    from uniparser_mansi_lat import MansiAnalyzer
    a = MansiAnalyzer(mode='strict')
    for wf in a.analyze_words([
        'ōjka',
        'minas',
        'minasmēn',
        'minasasmēn',
        'xumil',
        'uretəl'
    ], format='xml'):
        print(wf)

    # Test no-diacritics analyses
    a = MansiAnalyzer(mode='nopalatal')
    for wf in a.analyze_words([
        'ojka',
        'minas',
        'minās',
        'mināsmen',
        'minasāsmēn',
        'xumil',
        'urētəl',
        'lēw'
    ], format='xml'):
        print(wf)

    # Test alignment with manual glosses
    testTuples = [
        ('susne', 'sus-ne', 'смотреть-PTCP.NPST', 'look-NMLZ.NPST'),
        ('lēw', 'lēw', 'лев', 'lion'),
        ('totēɣn', 'tot-ē-ɣ-n', 'нести-NPST-DU.O-2SG.S', 'carry-NPST-DU.O-2SG.S'), # should not match
        ]

    for t in testTuples:
        anas = a.analyze_word_hint(*t)
        print(t, len(anas), 'conforming analyses found:')
        for ana in anas:
            print(ana.wfGlossed, ana.gloss)
