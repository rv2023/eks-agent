from collections import Counter
import re
import math

_WORD_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str):
    return [w.lower() for w in _WORD_RE.findall(text)]


def build_index(docs):
    """
    Build a very small keyword index.
    """
    doc_terms = []
    df = Counter()

    for doc in docs:
        tokens = _tokenize(doc["text"])
        counts = Counter(tokens)
        doc_terms.append(counts)
        for t in counts:
            df[t] += 1

    return {
        "docs": docs,
        "doc_terms": doc_terms,
        "df": df,
        "n_docs": len(docs),
    }


def retrieve_top_k(index, query, k=3, min_score=5.0):
    tokens = _tokenize(query)
    if not tokens or index["n_docs"] == 0:
        return []

    scores = []

    for i, counts in enumerate(index["doc_terms"]):
        score = 0.0
        for t in tokens:
            if t in counts:
                idf = math.log((index["n_docs"] + 1) / (index["df"][t] + 1)) + 1
                score += counts[t] * idf
        if score >= min_score:
            scores.append((score, index["docs"][i]))

    scores.sort(reverse=True, key=lambda x: x[0])
    return [doc for _, doc in scores[:k]]