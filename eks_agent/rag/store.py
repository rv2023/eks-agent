import os

def load_internal_docs(path: str):
    docs = []

    if not os.path.isdir(path):
        print(f"[warn] internal docs path not found: {path}")
        return docs

    for file in os.listdir(path):
        if file.endswith(".md"):
            full_path = os.path.join(path, file)
            with open(full_path, "r") as f:
                docs.append({
                    "source": file,
                    "text": f.read(),
                })

    return docs