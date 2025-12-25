# Simple in-memory store
# session_id -> list of messages

_MEMORY = {}


def add_message(session_id: str, role: str, text: str):
    if session_id not in _MEMORY:
        _MEMORY[session_id] = []

    _MEMORY[session_id].append({
        "role": role,
        "text": text,
    })

    # keep only last 6 messages
    _MEMORY[session_id] = _MEMORY[session_id][-6:]


def get_messages(session_id: str):
    return _MEMORY.get(session_id, [])