from pathlib import Path
import re


# loader.py 位於 rag 資料夾
RAG_DIR = Path(__file__).resolve().parent

# 專案根目錄：盤後風控報告
BASE_DIR = RAG_DIR.parent

# Obsidian Vault
KNOWLEDGE_PATH = BASE_DIR / "knowledge"


def clean_markdown(text: str) -> str:
    """對 Markdown 做基本清理，但保留 Wiki Link 文字。"""

    # 移除 YAML Front Matter
    text = re.sub(
        r"^---\s*\n.*?\n---\s*\n",
        "",
        text,
        flags=re.DOTALL,
    )

    # 將 [[超限]] 轉為 超限
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)

    return text.strip()


def split_markdown_by_heading(
    text: str,
    file_title: str,
) -> list[dict]:
    """
    依 Markdown 的 ## 標題切段。

    每個區塊會保留：
    - 文件名稱
    - 區塊標題
    - 完整內容
    """

    lines = text.splitlines()

    chunks = []
    current_heading = "本文"
    current_lines = []

    def save_chunk() -> None:
        if not current_lines:
            return

        content = "\n".join(current_lines).strip()

        if not content:
            return

        chunks.append(
            {
                "document": file_title,
                "heading": current_heading,
                "content": content,
            }
        )

    for line in lines:
        if line.startswith("## "):
            save_chunk()

            current_heading = line.removeprefix("## ").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    save_chunk()

    return chunks


def load_knowledge_base() -> list[dict]:
    """讀取 knowledge 資料夾中所有 Markdown。"""

    if not KNOWLEDGE_PATH.exists():
        raise FileNotFoundError(
            f"找不到 knowledge 資料夾：{KNOWLEDGE_PATH}"
        )

    documents = []

    for file_path in sorted(KNOWLEDGE_PATH.rglob("*.md")):
        # 排除 Obsidian 系統資料夾
        if ".obsidian" in file_path.parts:
            continue

        raw_text = file_path.read_text(encoding="utf-8")
        cleaned_text = clean_markdown(raw_text)

        file_chunks = split_markdown_by_heading(
            text=cleaned_text,
            file_title=file_path.stem,
        )

        for chunk_index, chunk in enumerate(file_chunks):
            chunk["chunk_id"] = (
                f"{file_path.stem}::{chunk_index}"
            )
            chunk["file_path"] = str(file_path)

            documents.append(chunk)

    return documents


if __name__ == "__main__":
    docs = load_knowledge_base()

    print(f"共載入 {len(docs)} 個知識區塊")

    for doc in docs[:10]:
        print(
            doc["document"],
            "→",
            doc["heading"],
        )