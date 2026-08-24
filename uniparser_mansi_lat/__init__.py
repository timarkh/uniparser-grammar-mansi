try:
    from importlib.resources import files, as_file
except ImportError:
    from importlib_resources import files, as_file
from uniparser_morph import Analyzer
from uniparser_morph.wordform import Wordform
from .translit_mansi_lat import mansi_translit_cyr2lat
import re
import copy
from itertools import combinations

simplifyChars = {
        'ā': 'a',
        'ā': 'a',
        'ō': 'o',
        'ō': 'o',
        'ē': 'e',
        'ē': 'e',
        'ī': 'i',
        'ī': 'i',
        'ū': 'u',
        'ū': 'u',
        'γ': 'ɣ',
        'é': 'e',
        'è': 'e',
        'á': 'a',
        'ȯ': 'o',
        'ó': 'o',
        'ž': 'ɕ',
        'š': 'ɕ',
        '̊': ''
    }
oversimplifyChars = copy.deepcopy(simplifyChars)
oversimplifyChars.update({
    'ə': 'i',
    "'": '',
    'w': 'u',
    'ŋ': 'n',
    'jī': 'i',
    'ji': 'i'
})
rxGloss = re.compile('[-=<>]|[^-=<>]+')
rxStemGloss = re.compile('\\b[^-=<>]*[a-zа-яё][^-=<>]*\\b')
rxHyphens = re.compile('[\\-<>]+')
rxYI = re.compile("(?<!')ə|'?i|.")
iySwap = {
    "'i": "'ə",
    "i": "ə",
    "ə": "i"
}


def simplify(s, over=False):
    """
    Remove diacritics.
    """
    chars = simplifyChars
    if over:
        chars = oversimplifyChars
    for c in chars:
        s = s.replace(c, chars[c])
        s = s.replace(c.upper(), chars[c].upper())
    return s


def simplify_gloss(s):
    """
    Remove distinctions that might have been absent in the glosses
    earlier.
    """
    glossNew = ''
    for g in rxGloss.findall(s):
        g = re.sub('\\.?\\[([^\\[\\]]+)\\]', '\\1', g)
        g = g.replace('PRS', 'NPST')
        g = g.replace('NMLZ', 'PTCP')
        g = g.replace('NMZ', 'PTCP')
        g = g.replace('VBLZ', 'VBZ')
        g = g.replace('INSTR', 'INS')
        g = g.replace('SOL', 'EMPH')
        g = re.sub('([^.]+)\\.POSS', 'POSS.\\1', g)
        g = re.sub('\\.S\\b', '', g)
        g = re.sub('\\b(MOM|FREQ|INCH)\\b', 'ASP', g)
        g = re.sub('2(DU|PL)(?!/)', '2DU/PL', g)
        glossNew += g
    return glossNew


def iy_vars(s):
    """
    Return all variants of the string with one or more I/Y swapped.
    """
    phonemes = rxYI.findall(s)
    positions = [i for i, c in enumerate(phonemes) if c in iySwap]
    variants = set()
    for r in range(1, len(positions) + 1):
        for changed in combinations(positions, r):
            changed = set(changed)
            var = ''
            for i, c in enumerate(phonemes):
                if i in changed:
                    var += iySwap[c]
                else:
                    var += c
            variants.add(var)
    return variants


class MansiAnalyzer(Analyzer):
    rxGlossBracket = re.compile('\\b(N?PST|IRR|PASS)\\.(3SG|NPST)$')

    def __init__(self, mode='strict', verbose_grammar=False):
        """
        Initialize the analyzer by reading the grammar files.
        If mode=='strict' (default), load the data as is.
        If mode=='nodiacritics', load the data for (possibly) diacriticless texts.
        If mode=='nopalatal', load the data for (possibly) diacriticless texts
        that also may have palatalization marks at the wrong places inside stems.
        """
        super().__init__(verbose_grammar=verbose_grammar)
        self.mode = mode
        if mode not in ('strict', 'nodiacritics', 'nopalatal'):
            return
        self.dirName = 'data_' + mode
        self.alphabet = 'lat'
        self.glossBrackets = False

        # Equivalents of glosses that have been removed
        self.eqEn = {}
        self.eqRu = {}
        self.eqEnRu = {}
        self.load_gloss_equiv()

        # Load grammar
        with as_file(files(__package__) / self.dirName / 'paradigms.txt') as self.paradigmFile,\
             as_file(files(__package__) / self.dirName / 'lexemes.txt') as self.lexFile,\
             as_file(files(__package__) / self.dirName / 'lex_rules.txt') as self.lexRulesFile,\
             as_file(files(__package__) / self.dirName / 'derivations.txt') as self.derivFile,\
             as_file(files(__package__) / self.dirName / 'stem_conversions.txt') as self.conversionFile,\
             as_file(files(__package__) / self.dirName / 'clitics.txt') as self.cliticFile,\
             as_file(files(__package__) / self.dirName / 'bad_analyses.txt') as self.delAnaFile,\
             as_file(files(__package__) / self.dirName / 'char_equiv.txt') as self.charEquivFile:
            self.load_grammar()
        self.initialize_parser()
        self.m.MIN_REPLACEMENT_WORD_LEN = 8
        self.m.MIN_REPLACEMENT_STEM_LEN = 6

    def load_gloss_equiv(self, mode='strict'):
        """
        Load equivalences for glosses that have been removed
        but occur in the manual analyses.
        """
        self.eqEn = {}
        self.eqRu = {}
        self.eqEnRu = {}
        with as_file(files(__package__) / self.dirName / 'gloss_replacements.csv') as fnameIn:
            with open(fnameIn, 'r', encoding='utf-8') as fIn:
                for line in fIn:
                    if len(line) <= 5 or '\t' not in line:
                        continue
                    lexOld, enOld, ruOld,\
                        lexNew, enNew, ruNew = line.strip('\r\n').split('\t')
                    if lexNew == 'NONE' or len(lexNew) <= 0:
                        continue
                    if enOld not in self.eqEn:
                        self.eqEn[enOld] = set()
                    if ruOld not in self.eqRu:
                        self.eqRu[ruOld] = set()
                    if (enOld, ruOld) not in self.eqEnRu:
                        self.eqEnRu[(enOld, ruOld)] = set()
                    v = (lexOld, lexNew, enNew, ruNew)
                    self.eqEn[enOld].add(v)
                    self.eqRu[ruOld].add(v)
                    self.eqEnRu[(enOld, ruOld)].add(v)

    def bracket_gloss(self, gloss):
        """
        Put in brackets those glosses that do not correspond to any overt marker.
        """
        glossSegs = rxGloss.findall(gloss)
        for i in range(len(glossSegs)):
            glossSegs[i] = self.rxGlossBracket.sub('\\1[\\2]', glossSegs[i])
        return ''.join(glossSegs)


    def analyze_words(self, words, format=None, disambiguate=False, replacementsAllowed=0):
        """
        Analyze a single word or a (possibly nested) list of words. Return either a list of
        analyses (all possible analyses of the word) or a nested list of lists
        of analyses with the same depth as the original list.
        If format is None, the analyses are Wordform objects.
        If format == 'xml', the analyses for each word are united into an XML string.
        If format == 'json', the analyses are JSON objects (dictionaries).
        Perform CG3 disambiguation if disambiguate == True and CG3 is installed.
        """
        if disambiguate:
            with as_file(files(__package__) / self.dirName / 'mansi_disambiguation.cg3') as cgFile:
                cgFilePath = str(cgFile)
                return super().analyze_words(words, format=format, disambiguate=True,
                                             cgFile=cgFilePath, replacementsAllowed=replacementsAllowed)
        return super().analyze_words(words, format=format, disambiguate=False, replacementsAllowed=replacementsAllowed)

    def __analyze_word__(self, word, replacementsAllowed=0):
        """
        Analyze a single word. Return either a list of its analyses
        or a list with a single Wordform object that has only the wf
        property filled. Assume the parser has already been initialized.
        If glossBrackets == True, put in brackets those glosses that
        do not correspond to any overt marker.
        """
        if self.alphabet == 'lat':
            analyses = super().__analyze_word__(word, replacementsAllowed=replacementsAllowed)
            if self.glossBrackets:
                for ana in analyses:
                    ana.gloss = self.bracket_gloss(ana.gloss)
                    for lang in ana.glossByLang:
                        ana.glossByLang[lang] = self.bracket_gloss(ana.glossByLang[lang])
            return analyses

        # For Cyrillic alphabet, there may be several transliteration options, try them all
        wordTrans = mansi_translit_cyr2lat(word)
        words = [wordTrans] + [var for var in sorted(iy_vars(wordTrans))]
        self.g.COMPLEX_WF_AS_BAGS = self.flattenSubwords
        analyses = []
        for var in words:
            # print(var)
            analyses += self.m.parse(var.lower(), replacementsAllowed=replacementsAllowed)
        if len(analyses) <= 0:
            analyses = [Wordform(self.g, wf=word)]
        else:
            for ana in analyses:
                ana.wf = word  # Reverse lowering if needed.
                if self.glossBrackets:
                    ana.gloss = self.bracket_gloss(ana.gloss)
                    for lang in ana.glossByLang:
                        ana.glossByLang[lang] = self.bracket_gloss(ana.glossByLang[lang])
        if format == 'xml':
            analyses = '<w>' + ''.join(ana.to_xml(glossing=self.glossing)
                                       for ana in analyses) + \
                       html.escape(word) + '</w>'
        if format == 'json':
            analyses = [ana.to_json() for ana in analyses]
        return analyses


    def analyze_word_hint(self, word, parts, glossRu, glossEn, defaultIfNotFound=True):
        """
        Take one word glossed using a potentially different annotation scheme.
        Return one analysis that conforms most to the morpheme segmentation or
        the gloss provided.
        """
        simpleGlossEn = simplify_gloss(glossEn)
        simpleGlossRu = simplify_gloss(glossRu)
        sortedGoodAnas = [[] for _ in range(13)]

        anas = super().analyze_words(word, format=format, disambiguate=False, replacementsAllowed=0)
        for ana in anas:
            if (ana.wfGlossed == parts
                    and ana.gloss == glossEn):
                sortedGoodAnas[0].append(ana)
            elif (ana.wfGlossed == parts
                    and 'ru' in ana.glossByLang and ana.glossByLang['ru'] == glossRu):
                sortedGoodAnas[1].append(ana)
            elif (ana.wfGlossed == parts
                  and simplify_gloss(ana.gloss) == simpleGlossEn):
                sortedGoodAnas[2].append(ana)
            elif (ana.wfGlossed == parts
                  and 'ru' in ana.glossByLang and simplify_gloss(ana.glossByLang['ru']) == simpleGlossRu):
                sortedGoodAnas[3].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  and ana.gloss == glossEn):
                sortedGoodAnas[4].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  and 'ru' in ana.glossByLang and ana.glossByLang['ru'] == glossRu):
                sortedGoodAnas[5].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  and simplify_gloss(ana.gloss) == simpleGlossEn):
                sortedGoodAnas[6].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  and 'ru' in ana.glossByLang and simplify_gloss(ana.glossByLang['ru']) == simpleGlossRu):
                sortedGoodAnas[7].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  or simplify_gloss(rxStemGloss.sub('', ana.gloss)) == simplify_gloss(rxStemGloss.sub('', glossEn))):
                sortedGoodAnas[11].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  or ana.gloss == glossEn):
                sortedGoodAnas[12].append(ana)

            # Search for glosses that have been corrected
            partsSplit = rxGloss.findall(parts)
            glossSplit = rxGloss.findall(glossEn)
            if len(partsSplit) != len(glossSplit):
                continue
            potentialParts = ['']
            potentialGloss = ['']
            for i in range(len(glossSplit)):
                curEnGl = glossSplit[i]
                curPart = partsSplit[i]
                if curEnGl not in self.eqEn:
                    for iPotent in range(len(potentialParts)):
                        potentialParts[iPotent] += curPart
                        potentialGloss[iPotent] += curEnGl
                    continue
                additionsParts = []
                additionsGloss = []
                for lexOld, lexNew, enNew, ruNew in self.eqEn[curEnGl]:
                    if lexOld != curPart:
                        lexNew = curPart
                    for iPotent in range(len(potentialParts)):
                        additionsParts.append(potentialParts[iPotent] + lexNew)
                        additionsGloss.append(potentialGloss[iPotent] + enNew)
                potentialParts = additionsParts
                potentialGloss = additionsGloss
            for iPotent in range(len(potentialParts)):
                if (ana.wfGlossed == potentialParts[iPotent]
                        and simplify_gloss(ana.gloss) == simplify_gloss(potentialGloss[iPotent])):
                    # print('CORRECTED GLOSS:', ana.gloss, gloss)
                    sortedGoodAnas[8].append(ana)
                elif (rxHyphens.sub('', ana.wfGlossed) == word
                        and simplify_gloss(ana.gloss) == simplify_gloss(potentialGloss[iPotent])):
                    # print('CORRECTED GLOSS:', ana.gloss, gloss)
                    sortedGoodAnas[9].append(ana)
                elif (simplify(ana.wfGlossed) == simplify(potentialParts[iPotent])
                        and simplify_gloss(ana.gloss) == simplify_gloss(potentialGloss[iPotent])):
                    # print('CORRECTED GLOSS:', ana.gloss, gloss)
                    sortedGoodAnas[10].append(ana)

        for i in range(len(sortedGoodAnas)):
            if len(sortedGoodAnas[i]) > 0:
                if any(rxHyphens.sub('', ana.wfGlossed) == rxHyphens.sub('', word) for ana in sortedGoodAnas[i]):
                    sortedGoodAnas[i] = [ana for ana in sortedGoodAnas[i]
                                         if rxHyphens.sub('', ana.wfGlossed) == rxHyphens.sub('', word)]
                return sortedGoodAnas[i]
        if any(rxHyphens.sub('', ana.wfGlossed) == rxHyphens.sub('', word) for ana in anas):
            anas = [ana for ana in anas
                    if rxHyphens.sub('', ana.wfGlossed) == rxHyphens.sub('', word)]
        if not defaultIfNotFound:
            anas = []
        return anas


if __name__ == '__main__':
    pass

