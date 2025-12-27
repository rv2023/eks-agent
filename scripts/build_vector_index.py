# scripts/build_vector_index.py

import json
import argparse
from eks_agent.rag.embeddings import BedrockEmbeddingProvider
from eks_agent.rag.vector_store import VectorStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--model-id", required=True)
    args = parser.parse_args()

    with open(args.docs) as f:
        docs = json.load(f)

    embedder = BedrockEmbeddingProvider(model_id=args.model_id)
    store = VectorStore(args.db)

    for d in docs:
        vec = embedder.embed_text(d["text"])
        store.upsert(
            doc_id=d["id"],
            title=d["title"],
            text=d["text"],
            vector=vec,
            meta=d.get("meta", {}),
        )

    print(f"Indexed {len(docs)} documents")


if __name__ == "__main__":
    main()