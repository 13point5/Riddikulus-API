import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import infer
from themeResnik import makeTheme
from getThematifiedQuestion import getThematifiedQuestion

w2vf = infer.Embeddings.load("./my-data/deps-vecs.npy")

themes = ["iron-man", "hp1", "ad3g"]
themeConfigs = {}

for theme in themes:

    themeFileName = theme + ".txt"
    if themeFileName not in os.listdir("themes/"):
        raise Exception("Theme not found")

    currThemeConfig = {
        "N": 1000,
        "dir": "themes",
        "new": themeFileName,
        "parse": themeFileName + ".json",
    }

    newTheme = makeTheme(currThemeConfig["new"], currThemeConfig)
    newTheme.loadPos()
    newTheme.w2vf = w2vf

    themeConfigs[theme] = newTheme

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/thematifyQuestion")
def thematifyQuestion(question, theme):
    return {"result": getThematifiedQuestion(question, themeConfigs[theme])}


@app.get("/themes")
def getThemes():
    return {"result": themes}
