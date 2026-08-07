from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_FOLDER = PROJECT_ROOT / "knowledge" / "generated"


def load_knowledge_base() -> list[dict]:
    documents = []

    for file_path in KNOWLEDGE_FOLDER.rglob("*.md"):
        text = file_path.read_text(encoding="utf-8")

        if not text.strip():
            continue

        documents.append({
            "title": file_path.stem,
            "path": str(file_path),
            "content": text,
        })

    return documents


if __name__ == "__main__":
    documents = load_knowledge_base()

    print(f"成功載入 {len(documents)} 份 Markdown。")

    for document in documents[:5]:
        print(document["title"])