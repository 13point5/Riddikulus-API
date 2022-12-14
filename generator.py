import time

sT = time.clock()

import json
import os
import infer
import parseInflection
import kenlm

# import stanza
import requests

# from themer import makeTheme
from themeResnik import makeTheme
from nltk.corpus import stopwords

# posProp = "upos"
posProp = "pos"


def getQuestionAnnotations(question):
    return requests.post(
        'http://[::]:9000/?properties={"annotators":"tokenize,pos,lemma,ner,parse","outputFormat":"json"}',
        data=question,
    ).json()


# questionAnnotator = stanza.Pipeline("en", processors="tokenize,pos,ner,lemma")

themeConfig = {
    "N": 1000,
    "questions": "data/SW_Dev/",
    "dir": "themes",
    "old": "math",
    "new": "Iron-Man.txt",
    "out": "film.txt",
    "parse": "Iron-Man.txt.json",
}

# setup some clocks and configurtions
eT = time.clock()
print("Imports and configs Loaded in " + str(eT - sT))

print("Loading Dependency Language Model...")
sT = time.clock()
LM = kenlm.Model(
    "/media/bharath/4C0EEFBE0EEF9EE8/Users/13point5/Documents/wiki-lm/wiki_en-mine-2.binary"
)
eT = time.clock()
print("Loaded in " + str(eT - sT))

# load Word Embeddings
print("Loading w2v...")
sT = time.clock()
w2vf = infer.Embeddings.load("./my-data/deps-vecs.npy")
eT = time.clock()
print("Loaded in " + str(eT - sT))

global aW
global dW
global sW
global tW
global tLMW
beamSize = 100

# function Words, pronouns, and math keywords
en = list(stopwords.words("english"))
for fn in os.listdir("data/fnWords"):
    en.extend(
        [
            x.strip()
            for x in open("data/fnWords/" + fn, errors="replace").readlines()
            if x[0] != "/"
        ]
    )
en.extend(
    [
        "he",
        "she",
        "it",
        "they",
        "them",
        "their",
        "her",
        "his",
        "its",
        "you",
        "your",
        "our",
        "us",
        "we",
        "i",
        "my",
        "mine",
        "him",
    ]
)
en.extend([x.strip() for x in open("data/commonWords50k.txt").readlines()[:1000]])
specialMathWords = "plus minus sum difference total change added to taken from (take away) in all have left more than less than (less) gain of loss of additional remaining all together save (archaic) combined dropped how many all together how many left (how many more) how many in all how many remain (how many fewer) how much all together how much less (how much more) increase of decrease (or decrease of) increased by decreased by how much more (how much less) product quotient times goes into of (with fractions, decimals, & percents) per twice (or double) ??? (multiply by two) half (half of) (divide by two) triple (multiply by three) third (divide by three)  divided by (divided into, equally) evenly total left cost costs amount leave number numbers spend spent tall taller money".split()


def getSynConstraints(parse):
    shift = -1
    constraints = []
    for s in parse["sentences"]:
        # print(s)
        for d in s["basicDependencies"]:
            if d["dep"] in ["ROOT", "PUNCT"]:
                continue
            constraints.append(
                (int(d["governor"]) + shift, d["dep"], int(d["dependent"]) + shift)
            )
        shift += len(s["tokens"])
    return constraints


def printLemma(
    allToks,
    b,
    newTheme,
    deleted=[],
):
    bdict = dict([x.split(":") for x in b.split(";")])
    tmp = []
    for i, t in enumerate(allToks):
        if i in deleted:
            continue
        if t["lemma"] + "_" + t[posProp][0] in bdict:
            tmp.append(
                parseInflection.get(bdict[t["lemma"] + "_" + t[posProp][0]], t[posProp])
            )
        elif t["lemma"] + "_NER" in bdict:
            ner = bdict[t["lemma"] + "_NER"]
            if ner in newTheme.bigNERD[t["ner"]]:
                tmp.append(newTheme.bigNERD[t["ner"]][ner])
            else:
                tmp.append(ner)

        else:
            tmp.append(t["word"])
    return " ".join(tmp)


if __name__ == "__main__":

    print("Creating Theme")
    newTheme = makeTheme(themeConfig["new"], themeConfig)
    newTheme.loadPos()
    newTheme.w2vf = w2vf

    aW, dW, sW = (1, 5, 0.1)
    tW = 1

    # This is a language model built from theme text.
    # it didn't work well so it's set to 0, but play w/ it and see what happens
    tLMW = 0

    questions = [
        "Kaleen filled a bucket with 0.75 of a gallon of water. A few minutes later, she realized only 0.5 of a gallon of water remained. How much water had leaked out of the bucket?",
        "Sally earns $12.50 an hour cleaning houses. If she works for 12 hours, how much money will she make ?",
    ]

    for i in range(len(questions)):
        print("Rewriting Problem # " + str(i))

        problem = questions[i]

        parse = getQuestionAnnotations(problem)

        allToks = [tok for s in parse["sentences"] for tok in s["tokens"]]
        reduced = []

        # Get Nouns from original and candidates

        eNouns = [
            i
            for i, x in enumerate(allToks)
            if x[posProp][0] == "N"
            and x["ner"] == "O"
            and x["word"] not in specialMathWords
            and i not in reduced
        ]
        eLemmas = set([t["lemma"] for i, t in enumerate(allToks) if i in eNouns])
        eCands = {}
        for o in eLemmas:
            opts = newTheme.bestIC(o, "n")
            if opts == -1:
                continue
            if opts == 0:
                opts = newTheme.commonPOS("N", N=25)

            eCands[o] = sorted(
                ((tW * tsc) + (sW * w2vf.similarity(o, x)), x) for tsc, x in opts
            )
            eCands[o].reverse()

        # Get Verbs and candidates
        verbs = [
            i
            for i, x in enumerate(allToks)
            if x[posProp][0] == "V"
            and x["lemma"] not in en
            and x["word"] not in specialMathWords
            and i not in reduced
        ]
        vLemmas = set([t["lemma"] for i, t in enumerate(allToks) if i in verbs])
        vCands = {}
        for v in vLemmas:
            infl = v
            opts = newTheme.bestIC(v, "v")
            if opts == -1:
                continue
            if opts == 0:
                opts = newTheme.commonPOS("V", N=25)

            vCands[v] = sorted(
                ((tW * tsc) + (sW * w2vf.similarity(infl, x)), x) for tsc, x in opts
            )
            vCands[v].reverse()

        # Do Adjectives
        adj = [
            i
            for i, x in enumerate(allToks)
            if x[posProp][0] == "J"
            and x["lemma"] not in en
            and x["word"] not in specialMathWords
            and i not in reduced
        ]
        aLemmas = set([t["lemma"] for i, t in enumerate(allToks) if i in adj])
        # pick new lemmas:
        aCands = {}
        for a in aLemmas:
            opts = newTheme.commonPOS("J", N=25)
            aCands[a] = sorted(
                ((tW * tsc) + (sW * w2vf.similarity(a, x)), x) for tsc, x in opts
            )
            aCands[a].reverse()

        # Do named entities
        ner = [
            i
            for i, x in enumerate(allToks)
            if x[posProp][0] == "N"
            and x["lemma"] not in en
            and x["word"] not in specialMathWords
            and i not in reduced
            and x["ner"] in "PERSON LOCATION"
            and x["lemma"] not in eCands
        ]
        nerLemmas = set(
            [(t["lemma"], t["ner"]) for i, t in enumerate(allToks) if i in ner]
        )
        nerCands = {}
        for n, l in nerLemmas:
            opts = newTheme.topNER(l)
            nerCands[n] = [
                (
                    (tW * (1 - (1 / y))) + (sW * w2vf.similarity(n.lower(), x.lower())),
                    x,
                )
                for x, y in opts
            ]

        todo = (
            [x + "_N" for x in eCands]
            + [y + "_V" for y in vCands]
            + [z + "_J" for z in aCands]
            + [a + "_NER" for a in nerCands]
        )
        # construct beam

        beam = (
            [(x[0], n + "_N:" + x[1]) for n in eCands for x in eCands[n]]
            + [(x[0], n + "_V:" + x[1]) for n in vCands for x in vCands[n]]
            + [(x[0], n + "_NER:" + x[1]) for n in nerCands for x in nerCands[n]]
        )
        beam.sort()
        beam.reverse()
        beam = beam[:100]

        iters = len(todo) - 1
        syn = getSynConstraints(parse)
        lem2idx = {}
        for td in todo:
            l, p = td.split("_")
            # if p == "NER": p="N"
            lem2idx[td] = [
                i
                for i, t in enumerate(allToks)
                if t["lemma"] == l and t[posProp][0] == p
            ]

        for ctr in range(iters):
            newbeam = []
            for sc, b in beam:
                bdict = dict([x.split(":") for x in b.split(";")])
                for t in todo:
                    if t in bdict:
                        continue
                    o, p = t.split("_")
                    if p == "V":
                        opts = vCands[o]
                    elif p == "N":
                        opts = eCands[o]
                    elif p == "NER":
                        opts = nerCands[o]
                    else:
                        opts = aCands[o]
                    undone = [x for y in todo if y not in bdict for x in lem2idx[y]]
                    tSyn = [x for x in syn if x[0] in lem2idx[t] and x[2] not in undone]
                    tSyn = tSyn + [
                        x for x in syn if x[2] in lem2idx[t] and x[0] not in undone
                    ]
                    tSyn = [
                        x for x in tSyn if x[0] not in reduced and x[2] not in reduced
                    ]

                    for oscore, opt in opts:
                        if opt in bdict.values():
                            continue
                        dScore = 0
                        for i, l, j in tSyn:
                            if i in lem2idx[t]:
                                wi = opt
                            elif (
                                allToks[i]["lemma"] + "_" + allToks[i][posProp][0]
                                in bdict
                            ):
                                wi = bdict[
                                    allToks[i]["lemma"] + "_" + allToks[i][posProp][0]
                                ]
                            else:
                                wi = allToks[i]["word"]

                            if j in lem2idx[t]:
                                wj = opt
                            elif (
                                allToks[j]["lemma"] + "_" + allToks[j][posProp][0]
                                in bdict
                            ):
                                wj = bdict[
                                    allToks[j]["lemma"] + "_" + allToks[j][posProp][0]
                                ]
                            else:
                                wj = allToks[j]["word"]
                            dScore += LM.score(wi + " " + l + " " + wj)

                        if dScore == 0:
                            dScore = -99

                        theseAnalogies = 0
                        for w in bdict:
                            wi, wiPOS = w.split("_")
                            score1 = w2vf.scoreAnalogy(wi, o, bdict[w], opt)

                            theseAnalogies += score1

                            # if wiPOS == p:

                            score2 = w2vf.similarity(wi, o) * w2vf.similarity(
                                bdict[w], opt
                            )

                            theseAnalogies += score2

                        newbeam.append(
                            (
                                (aW * theseAnalogies) + (dW * dScore) + sc + oscore,
                                b + ";" + t + ":" + opt,
                            )
                        )
            if not newbeam:
                newbeam = beam

            newbeam.sort()
            newbeam.reverse()
            beam = newbeam[:100]

        tLMscores = []
        for sc, b in beam:
            text = printLemma(
                allToks,
                b,
                newTheme,
                deleted=reduced,
            )
            # tLMscores.append((sc + (tLMW * tLM.score(text)), text)) # when using a model trained on the theme
            tLMscores.append((sc, text))
        tLMscores.sort(reverse=True)

        if tLMscores:
            print(
                "Original problem: \n------------\n" + problem + "\n\n"
                "Generated problem: \n------------\n" + str(tLMscores[0][1]) + "\n\n\n"
            )
        else:
            print("FAILED \n")
