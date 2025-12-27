# scripts/md_to_internal_docs.py

import os
import json
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    docs = []

    for fname in sorted(os.listdir(args.input_dir)):
        if not fname.endswith(".md"):
            continue

        path = os.path.join(args.input_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        doc_id = os.path.splitext(fname)[0]
        title = doc_id.replace("_", " ").title()

        docs.append({
            "id": doc_id,
            "title": title,
            "text": text,
            "meta": {
                "source": "internal_md",
                "filename": fname
            }
        })

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)

    print(f"Wrote {len(docs)} docs to {args.output}")


if __name__ == "__main__":
    main()