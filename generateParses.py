import stanza
from stanza.pipeline.core import DownloadMethod
import json

nlp = stanza.Pipeline(
    lang="en",
    processors="tokenize,mwt,pos,lemma,depparse,constituency,ner",
    download_method=DownloadMethod.REUSE_RESOURCES,
)

f = open("./externalData/scriptbase/traindev_flat/2.txt")
data = f.read()
doc = nlp(data)

# print(doc)
with open("bla.json", "w") as file:
    file.write(json.dumps(doc.to_dict()))  # use `json.loads` to do the reverse
