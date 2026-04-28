import os, nltk
from typing import cast
from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import Synset

NLTK_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../model/nltk_data')
)

if NLTK_DATA_DIR not in nltk.data.path:
    nltk.data.path.append(NLTK_DATA_DIR)

def init_nltk():
    os.makedirs(NLTK_DATA_DIR, exist_ok=True)

    try:
        wn.synsets("dog")
    except LookupError:
        for pkg in ['wordnet', 'omw-1.4']:
            nltk.download(
                pkg,
                download_dir=NLTK_DATA_DIR,
                quiet=True
            )

init_nltk()

def get_wordnet_distractors(answer: str, count: int = 3) -> list[str]:
    results = []
    seen = set()

    answer_clean = answer.strip().lower()

    queries = [answer_clean.replace(' ', '_')]

    if ' ' in answer_clean:
        queries.append(answer_clean.split()[-1])

    for query in queries:

        synsets: list[Synset] = cast(list[Synset], wn.synsets(query))

        for synset in synsets[:3]:

            for hypernym in synset.hypernyms():

                for hyponym in hypernym.hyponyms():

                    if hyponym == synset:
                        continue

                    for lemma in hyponym.lemma_names():

                        word = lemma.replace('_', ' ')
                        word_l = word.lower()

                        if (
                            word_l == answer_clean
                            or word_l in seen
                            or not word.isascii()
                            or len(word) > 40
                        ):
                            continue

                        results.append(word.capitalize())
                        seen.add(word_l)

                        if len(results) >= count:
                            return results

    return results