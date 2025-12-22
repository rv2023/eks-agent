from app.evidence.store import EvidenceStore

_SESSIONS = {}

def get_store(session_id: str) -> EvidenceStore:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = EvidenceStore()
    return _SESSIONS[session_id]
