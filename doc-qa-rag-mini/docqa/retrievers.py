"""Two local retrievers with the same interface: TF-IDF cosine and BM25. No API, no GPU."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Sequence, Tuple

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

_TOKEN = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")  # keeps tokens like 'tn-12' and 'vpn.fiktiva.example'


def stem(token: str) -> str:
    """Very small suffix stripper so 'days' ~ 'day', 'reimbursed' ~ 'reimburse'. Not a real stemmer."""
    for suffix, keep in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("ed", ""), ("s", "")):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3 and not (suffix == "s" and token.endswith("ss")):
            return token[: -len(suffix)] + keep
    return token


def tokenize(text: str) -> List[str]:
    return [stem(t) for t in _TOKEN.findall(text.lower()) if t not in ENGLISH_STOP_WORDS]


def analyzer(text: str) -> List[str]:
    """Unigrams + bigrams."""
    toks = tokenize(text)
    return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]


class TfidfRetriever:
    name = "tfidf"

    def __init__(self, texts: Sequence[str]):
        self.vec = TfidfVectorizer(analyzer=analyzer, sublinear_tf=True)
        self.matrix = self.vec.fit_transform(texts)

    def search(self, query: str, k: int = 3) -> List[Tuple[int, float]]:
        """Return [(chunk_index, cosine_similarity)] best first. Score is in [0, 1]."""
        scores = (self.matrix @ self.vec.transform([query]).T).toarray().ravel()
        order = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in order]


class BM25Retriever:
    """Okapi BM25 (k1=1.5, b=0.75), with scores normalised to [0, 1].

    Normalisation divides by the best score a chunk could get for this query, i.e.
    sum(idf(term) * (k1 + 1)) over all query terms; unseen terms count with the maximum idf.
    This makes 'terms missing from the corpus' lower the score, which is what we want for 'not found'.
    """

    name = "bm25"

    def __init__(self, texts: Sequence[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / len(self.lengths)
        self.n = len(self.docs)
        self.df = Counter(term for d in self.docs for term in d)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 3) -> List[Tuple[int, float]]:
        terms = set(tokenize(query))
        max_score = sum(self._idf(t) * (self.k1 + 1) for t in terms) or 1.0
        scores = []
        for doc, length in zip(self.docs, self.lengths):
            s = 0.0
            for t in terms:
                tf = doc.get(t, 0)
                if tf:
                    s += self._idf(t) * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            scores.append(s / max_score)
        order = sorted(range(self.n), key=lambda i: -scores[i])[:k]
        return [(i, scores[i]) for i in order]
