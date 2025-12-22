# app/state.py
from app.evidence.store import EvidenceStore

_SESSIONS = {}


def get_store(session_id: str) -> EvidenceStore:
    """
    Return a session-scoped EvidenceStore.
    Creates one if it does not exist.
    """
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = EvidenceStore()
    return _SESSIONS[session_id]


def get_session_meta(store: EvidenceStore) -> dict:
    """
    Initialize and return session metadata.
    Safe to call multiple times.
    """
    store.meta.setdefault("phase2_runs", 0)
    store.meta.setdefault("ask_loops", 0)
    return store.meta


def increment(store: EvidenceStore, key: str):
    """
    Increment a session counter safely.
    """
    meta = get_session_meta(store)
    meta[key] += 1