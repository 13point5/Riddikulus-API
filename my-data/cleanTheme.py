# For tokenizing corpus into sentences
from nltk import sent_tokenize

# For tokenizing the sentences into words, lowercase them and remove punctuation marks
from gensim.utils import simple_preprocess

# For removing stopwords
# from gensim.parsing.preprocessing import remove_stopwords

filePath = "hp-1.txt"

# For storing tokenized words
story = []

# Opens each book at each iteration
f = open(filePath)

# Read each book at each iteration
# 1 - Lowercasing of all the letters
corpus = f.read().lower()

# 2 - Tokenization of corpus into sentences
raw_sent = sent_tokenize(corpus)

for sent in raw_sent:
    # 3 - Removal of stopwords
    # sent = remove_stopwords(sent)

    # 4 - Removal of punctuation marks
    # 5 - Tokenization of sentences to words
    story.append(simple_preprocess(sent))

# Removing empty lists
story = [x for x in story if x]
story = [" ".join(line) for line in story]
story = "\n".join(story)

with open("hp-1-clean.txt", "w") as cleanedFile:
    cleanedFile.write(story)
