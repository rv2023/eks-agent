def extract_bullets(text: str) -> list[str]:
    bullets = []

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            bullets.append(line[2:].strip())

    if not bullets:
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                bullets.append(line)
            if len(bullets) >= 3:
                break

    return bullets


def format_internal_refs(docs):
    lines = []
    lines.append("Internal experience (reference only):")
    lines.append("<internal_experience_refs>")

    for d in docs:
        lines.append(f"- Source: {d['source']}")
        for bullet in extract_bullets(d["text"]):
            lines.append(f"  - {bullet}")

    lines.append("</internal_experience_refs>")
    return "\n".join(lines)