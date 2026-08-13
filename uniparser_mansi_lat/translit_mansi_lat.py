import re

dic2cyr = {
    'a': 'а', 'b': 'б', 'v': 'в',
    'g': 'г', 'ɣ': 'г', 'd': 'д', 'e': 'э',
    'ž': 'ж', 'š': 'ш',
    'ə': 'ы', 'č': 'ч',
    'z': 'з', 'i': 'ы', 'j': 'й', 'k': 'к',
    'l': 'л', 'm': 'м', 'n': 'н',
    'o': 'о', 'p': 'п', 'r': 'р',
    's': 'с', 'ɕ': "с'", 't': 'т', 'u': 'у',
    'c': 'ц', 'w': 'в', 'x': 'х',
    'y': 'ы', 'f': 'ф',
    'ā': 'а̄',
    'ō': 'о̄',
    'ē': 'э̄',
    'ī': 'ы̄',
    'ū': 'ӯ',
    'ŋ': 'ӈ'
}

cyr2dic = {
    'а': 'a', 'б': 'b', 'в': 'w',
    'г': 'ɣ', 'д': 'd', 'э': 'e',
    'ж': 'ž', 'ш': 'š',
    'ы': 'ə', 'ч': 'č',
    'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k',
    'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r',
    'с': 's', 'щ': 'ɕ', 'т': 't', 'у': 'u',
    'ц': 'c', 'х': 'x',
    'ф': 'f',
    'а̄': 'ā',
    'о̄': 'ō',
    'э̄': 'ē',
    'ӣ': 'ī',
    'ӣ': 'ī',
    'ы̄': 'ī',
    'ӯ': 'ū',
    'ӯ': 'ū',
    'ӈ': 'ŋ',
    'ь': "'",
    'ъ': 'j'
}

cyrHard2Soft = {
    'а': 'я', 'а̄': 'я̄',
    'э': 'е', 'э̄': 'е̄',
    'ы': 'и', 'ы̄': 'ӣ',
    'о': 'ё', 'о̄': 'ё̄',
    'у': 'ю', 'ӯ': 'ю̄'
}

cyrSoft2Hard = {
    'я': 'а', 'я̄': 'а̄',
    'е': 'э', 'е̄': 'э̄', 'ē': 'э̄',
    'и': 'ы', 'ӣ': 'ы̄',
    'ё': 'о', 'ё̄': 'о̄',
    'ю': 'у', 'ю̄': 'ӯ'
}

badChars = {
    'ā': 'ā',
    'ō': 'ō',
    'ē': 'ē',
    'ī': 'ī',
    'ū': 'ū'
}

rxCyrLetter = re.compile('\\w̄?|[^\\w]')
rxSoften = re.compile('\'([аэыоуӯ])', flags=re.I)
rxCyrSoften = re.compile('([яеёю]̄?)', flags=re.I)
rxCyrSoftenI = re.compile('(?<!^)([иӣ]̄?)', flags=re.I)
rxCyrMultSoften = re.compile('\'{2,}')
rxNeutral1 = re.compile('(?<=[бвгджзкмпрфхцчшщй\'])([эы])', re.I)
rxNeutral2 = re.compile('(\\b)(ы)', re.I)
rxCJV = re.compile('(?<=[бвгджзклмнӈпрстфхцчшщ])й([аяэеоёуӯюыиӣ])', re.I)
rxVJV = re.compile('(?<=[аеёиӣоуӯыэюя̄\'])й([аэыоуӯ])', flags=re.I)
rxJV = re.compile('\\bй([аэыоуӯ])')
rxJVCapital = re.compile('\\bЙ([аэыоуӯАЭЫОУӮ])')
rxExtraSoft = re.compile('([лнст])ь\\1(?=[ьяеёиӣю])')
rxSoftYLab = re.compile("['ь]ы([мпб])")
rxSoftYLabCapital = re.compile("['Ь]Ы([МПБ])")
rxYLab = re.compile('ы([мпб])')
rxYLabCapital = re.compile('Ы([МПБ])')
rxCyrVowelSoft = re.compile('([ ,."()\\[\\]<>!?:;=-]|^|[ьаеёиӣоуӯыэюя̄])\'')
rxCyrNeutralConsSoftY = re.compile('([бвгджзкмӈпрсфхцчшщйБВГДЖЗКМӇПРСФХЦЧШЩЙ]|^)[\'ь]ы')
rxCyrNeutralConsSoftYCap = re.compile('([бвгджзкмӈпрсфхцчшщйБВГДЖЗКМӇПРСФХЦЧШЩЙ]|^)[\'ь]Ы')
rxCyrNeutralConsSoft = re.compile('([бвгджзкмӈпрсфхцчшщйБВГДЖЗКМӇПРСФХЦЧШЩЙ])[\'ь]')

rxCyrillic = re.compile('^[а-яёӟӥӧўөА-ЯЁӞӤӦЎӨ.,;:!?\\-()\\[\\]{}<>]*$')

cyrReplacements = {}
srcReplacements = {}


def mansi_clean(s):
    for c in badChars:
        s = s.replace(c, badChars[c])
        s = s.replace(c.upper(), badChars[c].upper())
    return s


def mansi_translit_cyrillic(text):
    """
    Transliterate Mansi text from Dasha's Latin script to Cyrillics.
    """
    if rxCyrillic.search(text) is not None:
        return text

    letters = []
    for letter in text:
        if letter.lower() in dic2cyr:
            if letter.islower():
                letters.append(dic2cyr[letter.lower()])
            else:
                letters.append(dic2cyr[letter.lower()].upper())
        else:
            letters.append(letter)
    res = ''.join(letters)
    res = res.replace('h', 'х')
    res = res.replace('H', 'Х')
    res = rxSoftYLab.sub('ю\\1', res)
    res = rxSoftYLabCapital.sub('Ю\\1', res)
    res = rxYLab.sub('у\\1', res)
    res = rxYLabCapital.sub('У\\1', res)
    res = rxSoften.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxVJV.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxVJV.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxJV.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxJVCapital.sub(lambda m: cyrHard2Soft[m.group(1).lower()].upper(), res)
    res = rxNeutral1.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxNeutral2.sub('\\1и', res)
    res = rxCJV.sub(lambda m: 'ъ' + cyrHard2Soft[m.group(1).lower()], res)
    res = res.replace("'", 'ь')
    res = rxExtraSoft.sub('\\1\\1', res)
    res = res.replace('ӣ', 'ӣ')
    res = res.replace('ӣ'.upper(), 'ӣ'.upper())
    res = res.replace('ӯ', 'ӯ')
    res = res.replace('ӯ'.upper(), 'ӯ'.upper())
    res = res.replace('иг', 'ыг')
    res = res.replace('иг'.upper(), 'ыг'.upper())
    res = res.replace('ӣг', 'ы̄г')
    res = res.replace('ӣг'.upper(), 'ы̄г'.upper())

    if res in cyrReplacements:
        res = cyrReplacements[res]
    return res


def mansi_translit_cyr2lat(text):
    """
    Transliterate Mansi text from Cyrillics to Dasha's Latin script.
    """
    text = rxCyrSoften.sub(lambda m: "'" + cyrSoft2Hard[m.group(1).lower()], text)
    text = rxCyrSoftenI.sub(lambda m: "'" + cyrSoft2Hard[m.group(1).lower()], text)
    text = text.replace("''", "'й")
    text = text.replace("ъ'", "й")
    text = text.replace("Ъ'", "Й")
    text = text.replace("с'", 'щ')
    text = text.replace("сь", 'щ')
    text = text.replace("С'", 'Щ')
    text = text.replace("СЬ", 'Щ')
    text = text.replace("Сь", 'Щ')
    text = rxCyrVowelSoft.sub('\\1й', text)
    text = rxCyrNeutralConsSoftY.sub('\\1и', text)
    text = rxCyrNeutralConsSoftYCap.sub('\\1И', text)
    text = rxCyrNeutralConsSoft.sub('\\1', text)
    letters = []
    for letter in rxCyrLetter.findall(text):
        if letter.lower() in cyr2dic:
            if letter.islower():
                letters.append(cyr2dic[letter.lower()])
            else:
                letters.append(cyr2dic[letter.lower()].upper())
        else:
            letters.append(letter)
    res = ''.join(letters)
    return res


def mansi_translit_ipa(text):
    text = mansi_clean(text)
    text = text.replace('č', 'č')
    text = text.replace('Č', 'Č')
    text = text.replace('š', 'š')
    text = text.replace('Š', 'Š')
    text = text.replace('ž', 'ž')
    text = text.replace('Ž', 'Ž')
    text = text.replace('ǯ', 'ǯ')
    text = text.replace('Ǯ', 'Ǯ')
    text = text.replace("'", 'ʼ')
    text = text.replace('ə', 'ʌ')
    text = text.replace('Ə', 'Ʌ')
    text = text.replace('ɤ', 'ɘ')
    text = text.replace('ü', 'ʉ')
    # text = text.replace('ɨ', 'i̮')
    # text = text.replace('Ɨ', 'I̮')
    text = text.replace('čʼ', 't͡ɕ')
    text = text.replace('Čʼ', 'T͡ɕ')
    text = text.replace('ǯʼ', 'd͡ʑ')
    text = text.replace('Ǯʼ', 'D͡ʑ')
    text = text.replace('šʼ', 'ɕ')
    text = text.replace('Šʼ', 'ɕ')
    text = text.replace('žʼ', 'ʑ')
    text = text.replace('Žʼ', 'ʑ')
    text = text.replace('č', 't͡ʂ')
    text = text.replace('Č', 'T͡ʂ')
    text = text.replace('ǯ', 'd͡ʐ')
    text = text.replace('Ǯ', 'D͡ʐ')
    text = text.replace('š', 'ʂ')
    text = text.replace('Š', 'ʂ')
    text = text.replace('ž', 'ʐ')
    text = text.replace('Ž', 'ʐ')
    text = text.replace('ʼ', 'ʲ')
    text = text.replace('c', 't͡s')
    text = text.replace('C', 'T͡s')
    text = text.replace('ā', 'aː')
    text = text.replace('ā'.upper(), 'aː'.upper())
    text = text.replace('ō', 'oː')
    text = text.replace('ō'.upper(), 'oː'.upper())
    text = text.replace('ū', 'uː')
    text = text.replace('ū'.upper(), 'uː'.upper())
    text = text.replace('ī', 'iː')
    text = text.replace('ī'.upper(), 'iː'.upper())
    text = text.replace('ē', 'eː')
    text = text.replace('ē'.upper(), 'eː'.upper())
    return text


def mansi_translit_upa(text):
    text = mansi_clean(text)
    text = text.replace("'", 'ʼ')
    text = text.replace('ɕ', 'ś')
    text = text.replace('žʼ', 'ź')
    text = text.replace('Žʼ', 'Ź')
    text = text.replace('nʼ', 'ń')
    text = text.replace('Nʼ', 'Ń')
    # text = text.replace('ʼ', '̓')
    return text


if __name__ == '__main__':
    print(mansi_translit_cyr2lat('вотъялаӈкв; Āмп о̄с вотьялаӈкв э̄ри; Ам таве ёт во̄вуӈкв патыслум; Во̄ль хосыт ха̄пыл на̄тылтаӈкв'))
    print(mansi_translit_cyr2lat('Āквум Мēӈкв-я̄ па̄вылт ōлыс; Ам таве а̄ла-а̄ла ат хо̄йылтаслум'))
    print(mansi_translit_cyr2lat('Ам апщирищанум тувыл ейрищанум пуссын а̄нумныл ма̄нит'))
    print(mansi_translit_cyr2lat('Янгый ēмтапаӈкв'))
    print(mansi_translit_cyr2lat('Кēрнялил нёхыс пувуӈкв'))