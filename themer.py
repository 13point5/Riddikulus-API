import sys
import os
import pickle
import json
from random import shuffle
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import wordnet as wn
from nltk.corpus import wordnet_ic

bic = wordnet_ic.ic("ic-brown.dat")
hyper = lambda s: s.hypernyms()

filters = [
    y.strip().lower()
    for x in os.listdir("data/filters")
    for y in open("data/filters/" + x, errors="replace").readlines()
]
common = [x.strip() for x in open("data/commonWords50k.txt").readlines()]


class makeTheme:
    def __init__(self, title, themeConfig):

        print("Loading " + title + " theme information...")
        self.themeConfig = themeConfig
        self.title = title
        indexes = os.listdir(themeConfig["dir"])
        indexes.sort()
        print("indexes", indexes)
        data = [
            open(themeConfig["dir"] + "/" + x, errors="replace").read() for x in indexes
        ]
        self.idx = indexes.index(title)
        self.text = data[self.idx]
        print("Calculating tfidf")
        self.m = TfidfVectorizer(max_df=0.99, stop_words="english")

        # print("\n\ndata\n\n", data)

        rows = self.m.fit_transform(data)
        print(rows.shape)
        self.tfidfScores = rows.toarray()[
            self.idx,
        ]
        self.w2vf = None

    # print("Done!")

    def loadPos(self):
        # load pos and lemma data
        print(self.themeConfig["parse"])
        if self.themeConfig["parse"] not in os.listdir("themeFiles"):
            print("parse Theme and put in themeFiles dir first!")
            exit()
        themeJson = json.load(open("themeFiles/" + self.themeConfig["parse"]))

        posD = defaultdict(list)
        self.nerD = defaultdict(list)

        print("Reading json")
        last = defaultdict(list)
        print(len(themeJson["sentences"]))
        j = 0
        self.lemmaD = defaultdict(list)
        for s in themeJson["sentences"]:
            j += 1
            if j % 1000 == 0:
                print(j)
            for t in s["tokens"]:
                wrd = t["word"].lower()
                if wrd in filters:
                    continue
                if t["ner"] != "O":
                    if "\n" in t["after"]:
                        self.nerD[t["ner"]].append(t["word"])
                    else:
                        last[t["ner"]].append(wrd)
                else:
                    if last:
                        for ner in last:
                            self.nerD[ner].append(" ".join(last[ner]))
                        last = defaultdict(list)
                    posD[t["pos"]].append(wrd)
                    self.lemmaD[wrd].append(t["lemma"])

        print("Done reading json")

        self.bestPosD = {}
        for pos in posD:
            candidates = list(set(posD[pos]))
            candidates = [x for x in candidates if x not in filters]
            candidates2 = [x for x in candidates if x in self.m.vocabulary_]
            self.bestPosD[pos] = sorted(
                [(self.tfidfScores[self.m.vocabulary_[w]], w) for w in candidates2],
                reverse=True,
            )[: int(self.themeConfig["N"])]
            if len(self.bestPosD[pos]) < int(self.themeConfig["N"]):
                diff = int(self.themeConfig["N"]) - len(self.bestPosD[pos])
                candidates = [x for x in candidates if x not in candidates2]
                shuffle(candidates)
                self.bestPosD[pos].extend([(0, x) for x in candidates[:diff]])

        nerList = set([x.lower() for y in self.nerD for x in self.nerD[y]])
        self.commonD = {}
        for k in self.bestPosD.keys():
            self.commonD[k] = [
                x for x in self.bestPosD[k] if x[1] in common and x[1] not in nerList
            ]

        for x in self.nerD:
            self.nerD[x] = [y.lower() for y in self.nerD[x]]

        self.bigNERD = {x: {} for x in self.nerD}
        for x in self.nerD:
            for y in self.topNER(x):
                for z in self.topNER(x, N=50):
                    if z[1] < 2:
                        continue
                    if y[0] != z[0] and y[0] in z[0]:
                        self.bigNERD[x][y[0]] = z[0]

    def bestIC(self, w, pos):
        posses = [x for x in self.commonD if x[0].lower() == pos]
        try:
            posses.remove("NNP")
        except:
            pass
        vals = []
        for p in posses:
            vals.extend([x for x in self.commonPOS(p, N=100) if x[0] > 0])

        vals = list(set(vals))
        icVals = []
        oov = []
        wSyns = wn.synsets(w, pos)
        if not wSyns:
            return 0

        ok = False
        # things that are definite_quantities are math specific
        for s in wSyns:
            if wn.synset("definite_quantity.n.01") in list(s.closure(hyper)):
                return -1

        # pick the first synset that is a physical_entity, or else the first synset
        for s in wSyns:
            if wn.synset("physical_entity.n.01") in list(s.closure(hyper)):
                wSyn = s
                ok = True
                break
        if not ok:
            wSyn = wSyns[0]

        for sc, v in vals:
            vSyns = wn.synsets(v, pos)
            if vSyns:
                sim = wSyn.res_similarity(vSyns[0], bic)
                icVals.append((sim, v))
            else:
                oov.append(v)

        icVals.sort()
        icVals.reverse()
        # print("icVals", icVals)
        if len(icVals) == 0:
            return 0
        high = icVals[0][0]
        if high == 0:
            return 0
        return icVals[:25]

    def commonPOS(self, pos, N=100):
        if "NNP" in self.commonD:
            del self.commonD["NNP"]
        if pos not in self.bestPosD:
            posses = [x for x in self.commonD if x[0] == pos[0]]
            vals = []
            for pos in posses:
                vals.extend(self.commonD[pos][:N])
            vals = list(set(vals))
            vals.sort(reverse=True)
            return vals[:N]
        else:
            return self.commonD[pos][:N]

    def topNER(self, ner, N=10):
        return Counter(self.nerD[ner]).most_common(N)


if __name__ == "__main__":
    import configparser

    config = configparser.ConfigParser()
    config.read(sys.argv[2])
    themeConfig = config["theme"]
    newTheme = makeTheme(sys.argv[1], themeConfig)
    newTheme.loadPos()
    print(newTheme.bestPOS("NN"))
    print(newTheme.topNER("PERSON"))
    print(newTheme.topNER("LOCATION"))
