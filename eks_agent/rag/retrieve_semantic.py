# eks_agent/rag/retrieve_semantic.py

from typing import List
from eks_agent.rag.embeddings import BedrockEmbeddingProvider
from eks_agent.rag.vector_store import VectorStore


def retrieve_semantic(
    query: str,
    vector_store: VectorStore,
    embedder: BedrockEmbeddingProvider,
    top_k: int = 5,
) -> List[dict]:
    query_vec = embedder.embed_text(query)
    results = vector_store.search(query_vec, top_k=top_k)

    refs = []
    for doc, score in results:
        refs.append({
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "snippet": doc["text"][:300],
            "score": round(score, 3),
            "source": "semantic",
        })
    return refs
