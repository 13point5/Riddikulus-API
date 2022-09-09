import requests


def getQuestionAnnotations(question):
    return requests.post(
        'http://[::]:9000/?properties={"annotators":"tokenize,pos,lemma,ner,parse","outputFormat":"json"}',
        data=question,
    ).json()
