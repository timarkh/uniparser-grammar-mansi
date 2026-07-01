import re
import os
import html


rxWords = re.compile('\\b\\w[\\w-]*\\w\\b|\\b\\w\\b')
rxCleanTags = re.compile('</?(?:a|img|span|div|p|body)(?: [^<>]+)?>|[\0⌐-♯]+' , flags=re.DOTALL)
rxBadFolder = re.compile('_uncleaned\\b')


def process_file(fpath, fname, wordlist):
    f = open(os.path.join(fpath, fname), 'r', encoding='utf-8-sig')
    text = f.read()
    text = html.unescape(text)
    text = rxCleanTags.sub('', text)
    # text = text.replace('é', 'ë')
    # text = text.replace('ё', 'ë')
    f.close()
    words = rxWords.findall(text)
    for word in words:
        word = word.lower()
        try:
            wordlist[word] += 1
        except KeyError:
            wordlist[word] = 1
        if '-' in word:
            parts = word.split('-')
            for iPart in range(len(parts)):
                part = parts[iPart]
                if iPart != len(parts) - 1:
                    part += '-'
                else:
                    part = '-' + part
                try:
                    wordlist[part] += 1
                except KeyError:
                    wordlist[part] = 1


def write_conc(dictConc, fname):
    f = open(fname, 'w', encoding='utf-8-sig')
    for word in sorted(dictConc, key=lambda w: -dictConc[w]):
        f.write(word + '\t' + str(dictConc[word]) + '\n')
    f.close()


wordlist = {}
for root, dirs, files in os.walk('.'):
    if rxBadFolder.search(root) is not None:
        continue
    print(root)
    for fname in files:
        if not fname.lower().endswith('.txt') or 'meta' in fname or 'concordance' in fname:
            continue
        process_file(root, fname, wordlist)
write_conc(wordlist, 'wordlist.csv')
