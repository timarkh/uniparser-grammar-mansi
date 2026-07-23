try:
    from importlib.resources import files, as_file
except ImportError:
    from importlib_resources import files, as_file
from uniparser_morph import Analyzer
import re
import copy

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
        g = re.sub('([^.]+)\\.POSS', 'POSS.\\1', g)
        g = re.sub('\\.S\\b', '', g)
        g = re.sub('\\b(MOM|FREQ|INCH)\\b', 'ASP', g)
        glossNew += g
    return glossNew


class MansiAnalyzer(Analyzer):
    def __init__(self, mode='strict', verbose_grammar=False):
        """
        Initialize the analyzer by reading the grammar files.
        If mode=='strict' (default), load the data as is.
        If mode=='nodiacritics', load the data for (possibly) diacriticless texts.
        """
        super().__init__(verbose_grammar=verbose_grammar)
        self.mode = mode
        if mode not in ('strict', 'nodiacritics'):
            return
        self.dirName = 'data_' + mode

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
        # if disambiguate:
        #     with as_file(files(__package__) / self.dirName / 'mansi_disambiguation.cg3') as cgFile:
        #         cgFilePath = str(cgFile)
        #         return super().analyze_words(words, format=format, disambiguate=True,
        #                                      cgFile=cgFilePath, replacementsAllowed=replacementsAllowed)
        # There is no disambiguation yet!
        return super().analyze_words(words, format=format, disambiguate=False, replacementsAllowed=replacementsAllowed)

    def analyze_word_hint(self, word, parts, gloss_ru, gloss_en):
        """
        Take one word glossed using a potentially different annotation scheme.
        Return one analysis that conforms most to the morpheme segmentation or
        the gloss provided.
        """
        gloss = gloss_en
        if len(gloss) <= 0:
            gloss = gloss_ru
        simpleGloss = simplify_gloss(gloss)
        sortedGoodAnas = [[] for i in range(7)]
        anas = super().analyze_words(word, format=format, disambiguate=False, replacementsAllowed=0)
        for ana in anas:
            if (ana.wfGlossed == parts
                    and ana.gloss == gloss):
                sortedGoodAnas[0].append(ana)
            elif (ana.wfGlossed == parts
                  and simplify_gloss(ana.gloss) == simpleGloss):
                sortedGoodAnas[1].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  and ana.gloss == gloss):
                sortedGoodAnas[2].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  and simplify_gloss(ana.gloss) == simpleGloss):
                sortedGoodAnas[3].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  or simplify_gloss(rxStemGloss.sub('', ana.gloss)) == simplify_gloss(rxStemGloss.sub('', gloss))):
                sortedGoodAnas[5].append(ana)
            elif (simplify(ana.wfGlossed) == simplify(parts)
                  or ana.gloss == gloss):
                sortedGoodAnas[6].append(ana)

            # Search for glosses that have been corrected
            partsSplit = rxGloss.findall(parts)
            glossSplit = rxGloss.findall(gloss)
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
                if (simplify(ana.wfGlossed) == simplify(potentialParts[iPotent])
                        and simplify_gloss(ana.gloss) == simplify_gloss(potentialGloss[iPotent])):
                    # print('CORRECTED GLOSS:', ana.gloss, gloss)
                    sortedGoodAnas[4].append(ana)

        for i in range(len(sortedGoodAnas)):
            if len(sortedGoodAnas[i]) > 0:
                return sortedGoodAnas[i]
        return anas


if __name__ == '__main__':
    pass

