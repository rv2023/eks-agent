# eks_agent/rag/vector_store.py

import sqlite3
import json
import math
from typing import List, Tuple


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS docs (
                doc_id TEXT PRIMARY KEY,
                title TEXT,
                text TEXT,
                meta TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                doc_id TEXT PRIMARY KEY,
                vector TEXT
            )
        """)
        conn.commit()
        conn.close()

    def upsert(self, doc_id: str, title: str, text: str, vector: List[float], meta: dict):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "REPLACE INTO docs VALUES (?, ?, ?, ?)",
            (doc_id, title, text, json.dumps(meta)),
        )
        cur.execute(
            "REPLACE INTO vectors VALUES (?, ?)",
            (doc_id, json.dumps(vector)),
        )
        conn.commit()
        conn.close()

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[dict, float]]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT d.doc_id, d.title, d.text, d.meta, v.vector
            FROM docs d JOIN vectors v ON d.doc_id = v.doc_id
        """)
        rows = cur.fetchall()
        conn.close()

        scored = []
        for doc_id, title, text, meta_json, vec_json in rows:
            vec = json.loads(vec_json)
            score = cosine_similarity(query_vector, vec)
            scored.append((
                {
                    "doc_id": doc_id,
                    "title": title,
                    "text": text,
                    "meta": json.loads(meta_json),
                },
                score
            ))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]