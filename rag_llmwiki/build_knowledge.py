import argparse
import json
import re
from pathlib import Path
from pypdf import PdfReader
from rag_llmwiki.llm_client import GeminiClient


# ============================================================
# 路徑設定
# ============================================================

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 原始 PDF 放置位置
PDF_PATH = PROJECT_ROOT / "input_pdfs"

# Markdown 輸出位置
GENERATED_PATH = PROJECT_ROOT / "knowledge" / "generated"

# 每次傳給 SPADE 的文字上限
# 避免整份 PDF 太長而超過模型限制
MAX_CHARS_PER_REQUEST = 12000


# ============================================================
# SPADE 整理規則
# ============================================================

SYSTEM_PROMPT = """
你是金融機構的固定收益規章知識整理助理。

你的工作是將規章原文整理成可供 Obsidian 與 RAG 使用的
Markdown 知識卡。

整理原則：

1. 每張知識卡只能處理一個明確主題。
2. 不得自行增加原文沒有的規定。
3. 不得捏造條號、門檻、期限、單位或處理程序。
4. 必須保留數字、期限、條件、例外及負責單位。
5. 若原文沒有相關資訊，使用空字串或空陣列。
6. related_topics 只放相關主題名稱，不要加入中括號。
7. source_pages 必須根據文字中的「PDF第X頁」標記填寫。
8. 回傳內容只能是有效 JSON，不要加入 Markdown code block。
9. 最外層必須是物件，並包含 notes 陣列。

每個 note 必須使用以下欄位：

{
  "title": "知識卡名稱",
  "category": "分類",
  "aliases": ["可能的查詢用語"],
  "summary": "簡短摘要",
  "definition": "定義",
  "scope": "適用範圍",
  "trigger": "啟動條件、門檻或判斷標準",
  "workflow": ["處理步驟一", "處理步驟二"],
  "deadlines": ["期限或頻率"],
  "responsible_roles": ["負責單位或角色"],
  "important_rules": ["重要規定"],
  "related_topics": ["相關主題"],
  "source_pages": [1, 2]
}
""".strip()


def build_user_prompt(
    document_name: str,
    document_text: str,
) -> str:
    """建立傳給 SPADE 的使用者 Prompt。"""

    return f"""
請整理以下金融規章內容。

【文件名稱】

{document_name}

【規章原文】

{document_text}

【輸出要求】

請辨識這段原文中所有具有獨立意義的主題，
每個主題建立一張知識卡。

例如：

- DV01 定義
- DV01 使用率
- DV01 超限處理
- 月停損
- 年停損
- 異常通報
- 超限回覆期限

若同一段原文涉及多個主題，應建立多個 note。

只回傳以下格式的有效 JSON：

{{
  "notes": [
    {{
      "title": "主題名稱",
      "category": "風險管理",
      "aliases": [],
      "summary": "",
      "definition": "",
      "scope": "",
      "trigger": "",
      "workflow": [],
      "deadlines": [],
      "responsible_roles": [],
      "important_rules": [],
      "related_topics": [],
      "source_pages": []
    }}
  ]
}}
""".strip()


# ============================================================
# PDF 文字擷取
# ============================================================

def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    """逐頁擷取 PDF 文字。"""

    reader = PdfReader(str(pdf_path))
    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""
        text = text.strip()

        if not text:
            print(
                f"警告：{pdf_path.name} 第 {page_number} 頁"
                "沒有擷取到文字。"
            )
            continue

        pages.append(
            {
                "page_number": page_number,
                "text": text,
            }
        )

    if not pages:
        raise ValueError(
            f"{pdf_path.name} 沒有擷取到任何文字。\n"
            "如果是掃描型 PDF，需要先進行 OCR。"
        )

    return pages


def split_large_page(
    page_number: int,
    text: str,
) -> list[dict]:
    """如果單頁文字過長，將單頁再切成多段。"""

    units = []

    for start in range(
        0,
        len(text),
        MAX_CHARS_PER_REQUEST,
    ):
        part = text[
            start:start + MAX_CHARS_PER_REQUEST
        ]

        units.append(
            {
                "page_numbers": [page_number],
                "text": (
                    f"[PDF第{page_number}頁]\n"
                    f"{part}"
                ),
            }
        )

    return units


def build_pdf_chunks(
    pages: list[dict],
) -> list[dict]:
    """將 PDF 頁面組合成適合傳給 SPADE 的文字區塊。"""

    page_units = []

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        if len(text) > MAX_CHARS_PER_REQUEST:
            page_units.extend(
                split_large_page(
                    page_number=page_number,
                    text=text,
                )
            )
        else:
            page_units.append(
                {
                    "page_numbers": [page_number],
                    "text": (
                        f"[PDF第{page_number}頁]\n"
                        f"{text}"
                    ),
                }
            )

    chunks = []
    current_texts = []
    current_pages = []
    current_length = 0

    for unit in page_units:
        unit_text = unit["text"]
        unit_length = len(unit_text)

        if (
            current_texts
            and current_length + unit_length
            > MAX_CHARS_PER_REQUEST
        ):
            chunks.append(
                {
                    "page_numbers": list(
                        dict.fromkeys(current_pages)
                    ),
                    "text": "\n\n".join(current_texts),
                }
            )

            current_texts = []
            current_pages = []
            current_length = 0

        current_texts.append(unit_text)
        current_pages.extend(
            unit["page_numbers"]
        )
        current_length += unit_length

    if current_texts:
        chunks.append(
            {
                "page_numbers": list(
                    dict.fromkeys(current_pages)
                ),
                "text": "\n\n".join(current_texts),
            }
        )

    return chunks


# ============================================================
# 資料清理
# ============================================================

def normalize_list(value) -> list[str]:
    """確保欄位是乾淨的字串陣列。"""

    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    result = []

    for item in value:
        item = str(item).strip()

        if item and item not in result:
            result.append(item)

    return result


def normalize_page_numbers(
    value,
    default_pages: list[int],
) -> list[int]:
    """整理 SPADE 回傳的頁碼。"""

    if not isinstance(value, list):
        return default_pages

    pages = []

    for item in value:
        try:
            page_number = int(item)
        except (TypeError, ValueError):
            continue

        if page_number not in pages:
            pages.append(page_number)

    return sorted(pages) if pages else default_pages


def normalize_note(
    note: dict,
    document_name: str,
    default_pages: list[int],
) -> dict:
    """統一 SPADE 回傳的 note 格式。"""

    return {
        "title": str(
            note.get("title", "")
        ).strip(),
        "category": str(
            note.get("category", "風險管理")
        ).strip() or "風險管理",
        "aliases": normalize_list(
            note.get("aliases")
        ),
        "summary": str(
            note.get("summary", "")
        ).strip(),
        "definition": str(
            note.get("definition", "")
        ).strip(),
        "scope": str(
            note.get("scope", "")
        ).strip(),
        "trigger": str(
            note.get("trigger", "")
        ).strip(),
        "workflow": normalize_list(
            note.get("workflow")
        ),
        "deadlines": normalize_list(
            note.get("deadlines")
        ),
        "responsible_roles": normalize_list(
            note.get("responsible_roles")
        ),
        "important_rules": normalize_list(
            note.get("important_rules")
        ),
        "related_topics": normalize_list(
            note.get("related_topics")
        ),
        "source_document": document_name,
        "source_pages": normalize_page_numbers(
            note.get("source_pages"),
            default_pages=default_pages,
        ),
    }


# ============================================================
# 合併重複知識卡
# ============================================================

TEXT_FIELDS = [
    "summary",
    "definition",
    "scope",
    "trigger",
]

LIST_FIELDS = [
    "aliases",
    "workflow",
    "deadlines",
    "responsible_roles",
    "important_rules",
    "related_topics",
    "source_pages",
]


def merge_unique_items(
    first_list: list,
    second_list: list,
) -> list:
    """合併兩個陣列並移除重複值。"""

    merged = []

    for item in first_list + second_list:
        if item not in merged:
            merged.append(item)

    return merged


def merge_notes(notes: list[dict]) -> list[dict]:
    """將不同 PDF 區塊中相同標題的知識卡合併。"""

    merged_notes = {}

    for note in notes:
        title = note["title"].strip()

        if not title:
            continue

        key = re.sub(
            r"\s+",
            "",
            title,
        ).lower()

        if key not in merged_notes:
            merged_notes[key] = note.copy()
            continue

        existing = merged_notes[key]

        for field in TEXT_FIELDS:
            new_text = note.get(field, "")
            old_text = existing.get(field, "")

            if new_text and new_text not in old_text:
                if old_text:
                    existing[field] = (
                        old_text + "\n\n" + new_text
                    )
                else:
                    existing[field] = new_text

        for field in LIST_FIELDS:
            existing[field] = merge_unique_items(
                existing.get(field, []),
                note.get(field, []),
            )

        if (
            note["source_document"]
            != existing["source_document"]
        ):
            existing["source_document"] = (
                existing["source_document"]
                + "；"
                + note["source_document"]
            )

    return list(merged_notes.values())


# ============================================================
# Markdown 產生
# ============================================================

def safe_filename(title: str) -> str:
    """將主題名稱轉成 Windows 可使用的檔名。"""

    filename = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        title,
    )

    filename = filename.strip().rstrip(".")

    return filename or "未命名知識卡"


def format_list(
    heading: str,
    items: list,
    wiki_links: bool = False,
) -> str:
    """產生 Markdown 清單區塊。"""

    if not items:
        return f"## {heading}\n\n無明確規定。"

    if wiki_links:
        lines = [
            f"- [[{item}]]"
            for item in items
        ]
    else:
        lines = [
            f"- {item}"
            for item in items
        ]

    return (
        f"## {heading}\n\n"
        + "\n".join(lines)
    )


def note_to_markdown(note: dict) -> str:
    """將知識卡資料轉成 Markdown。"""

    title = note["title"]
    category = note["category"]
    aliases = note["aliases"]

    frontmatter = [
        "---",
        (
            "title: "
            + json.dumps(
                title,
                ensure_ascii=False,
            )
        ),
        (
            "category: "
            + json.dumps(
                category,
                ensure_ascii=False,
            )
        ),
    ]

    if aliases:
        frontmatter.append("aliases:")

        for alias in aliases:
            frontmatter.append(
                "  - "
                + json.dumps(
                    alias,
                    ensure_ascii=False,
                )
            )
    else:
        frontmatter.append("aliases: []")

    frontmatter.extend(
        [
            "tags:",
            "  - LLM-Wiki",
            "  - 固定收益",
            "  - 風險管理",
            "---",
        ]
    )

    pages = "、".join(
        f"第{page}頁"
        for page in note["source_pages"]
    )

    source_text = (
        f"- {note['source_document']}"
    )

    if pages:
        source_text += f"｜{pages}"

    sections = [
        "\n".join(frontmatter),
        f"# {title}",
        (
            "## 摘要\n\n"
            + (
                note["summary"]
                or "無明確摘要。"
            )
        ),
        (
            "## 定義\n\n"
            + (
                note["definition"]
                or "無明確規定。"
            )
        ),
        (
            "## 適用範圍\n\n"
            + (
                note["scope"]
                or "無明確規定。"
            )
        ),
        (
            "## 啟動條件與門檻\n\n"
            + (
                note["trigger"]
                or "無明確規定。"
            )
        ),
        format_list(
            "處理流程",
            note["workflow"],
        ),
        format_list(
            "期限與頻率",
            note["deadlines"],
        ),
        format_list(
            "負責單位",
            note["responsible_roles"],
        ),
        format_list(
            "重要規定",
            note["important_rules"],
        ),
        format_list(
            "相關主題",
            note["related_topics"],
            wiki_links=True,
        ),
        "## 來源\n\n" + source_text,
        (
            "> [!warning] 人工覆核\n"
            "> 本知識卡由 Gemini 協助整理；"
            "正式作業仍應以原始規章及最新核定版本為準。"
        ),
    ]

    return "\n\n".join(sections).strip() + "\n"


# ============================================================
# 主程式
# ============================================================

def generate_knowledge(
    overwrite: bool = False,
) -> None:
    """讀取 PDF、呼叫 SPADE 並產生 Markdown。"""

    pdf_files = sorted(
        PDF_PATH.glob("*.pdf")
    )

    if not pdf_files:
        raise FileNotFoundError(
            f"在以下位置找不到 PDF：\n{PDF_PATH}"
        )

    GENERATED_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = GeminiClient()
    all_notes = []

    for pdf_path in pdf_files:
        print()
        print(f"正在讀取：{pdf_path.name}")

        pages = extract_pdf_pages(pdf_path)
        chunks = build_pdf_chunks(pages)

        print(
            f"共 {len(pages)} 頁，"
            f"分成 {len(chunks)} 個 SPADE 請求。"
        )

        for chunk_number, chunk in enumerate(
            chunks,
            start=1,
        ):
            page_text = "、".join(
                str(page)
                for page in chunk["page_numbers"]
            )

            print(
                f"正在整理第 {chunk_number}/"
                f"{len(chunks)} 段，"
                f"頁碼：{page_text}"
            )

            result = client.chat_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(
                    document_name=pdf_path.name,
                    document_text=chunk["text"],
                ),
                temperature=0.1,
            )

            notes = result.get("notes")

            if not isinstance(notes, list):
                raise RuntimeError(
                    f"{pdf_path.name} 第 {chunk_number} 段"
                    "回傳結果缺少 notes 陣列。"
                )

            for note in notes:
                if not isinstance(note, dict):
                    continue

                normalized_note = normalize_note(
                    note=note,
                    document_name=pdf_path.name,
                    default_pages=chunk[
                        "page_numbers"
                    ],
                )

                if normalized_note["title"]:
                    all_notes.append(
                        normalized_note
                    )

    merged_notes = merge_notes(all_notes)

    created_count = 0
    skipped_count = 0

    for note in merged_notes:
        output_path = (
            GENERATED_PATH
            / f"{safe_filename(note['title'])}.md"
        )

        if output_path.exists() and not overwrite:
            print(
                f"略過既有檔案："
                f"{output_path.name}"
            )
            skipped_count += 1
            continue

        markdown = note_to_markdown(note)

        output_path.write_text(
            markdown,
            encoding="utf-8",
        )

        print(
            f"已建立：{output_path.name}"
        )
        created_count += 1

    print()
    print("=" * 50)
    print(f"完成，共建立 {created_count} 份 Markdown。")
    print(f"略過 {skipped_count} 份既有 Markdown。")
    print(f"輸出位置：{GENERATED_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="使用 SPADE 將 PDF 整理成 Markdown。"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆蓋名稱相同的既有 Markdown。",
    )

    arguments = parser.parse_args()

    generate_knowledge(
        overwrite=arguments.overwrite,
    )