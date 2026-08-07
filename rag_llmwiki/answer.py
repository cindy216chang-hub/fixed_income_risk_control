from rag_llmwiki.llm_client import GeminiClient
from rag_llmwiki.retriever import KnowledgeRetriever


SYSTEM_PROMPT = """
你是固定收益風險管理規章問答助理。

請嚴格遵守以下規則：

1. 只能根據系統提供的「檢索內容」回答。
2. 不可以使用外部知識補充規章內容。
3. 不可以自行推測或創造流程、期限、數字、職責或規定。
4. 如果檢索內容不足以回答，請明確回答：
   「目前檢索到的規章內容不足以回答此問題，請查閱原始規章或洽詢相關單位。」
5. 回答時使用清楚、自然且容易理解的繁體中文。
6. 若內容包含流程，請依照正確順序列點說明。
7. 若內容包含期限、負責人員或控管標準，必須明確列出。
8. 回答最後列出引用來源，但只能引用檢索內容中實際出現的來源資訊。
"""


def build_context(search_results: list[dict]) -> str:
    """把檢索結果整理成提供給 Gemini 的規章內容。"""

    context_sections = []

    for number, result in enumerate(search_results, start=1):
        title = result.get("title", "未知標題")
        path = result.get("path", "未知路徑")
        content = result.get("content", "")
        score = result.get("score", 0.0)

        section = (
            f"===== 檢索文件 {number} =====\n"
            f"標題：{title}\n"
            f"檔案：{path}\n"
            f"檢索相似度：{score:.4f}\n\n"
            f"{content}"
        )

        context_sections.append(section)

    return "\n\n".join(context_sections)


def build_user_prompt(question: str, context: str) -> str:
    """建立傳給 Gemini 的使用者 Prompt。"""

    return f"""
請根據下方檢索到的規章內容回答問題。

【使用者問題】
{question}

【檢索內容】
{context}

【回答格式】
回答：
請直接回答問題，必要時使用條列方式。

依據：
說明回答所依據的規章重點。

來源：
列出使用到的知識卡標題、原始規章名稱及來源頁碼。
如果檢索內容沒有記載原始規章名稱或頁碼，不可自行編造。
""".strip()


class RAGAnswerService:
    """整合 Markdown 檢索與 Gemini 回答。"""

    def __init__(self) -> None:
        self.retriever = KnowledgeRetriever()
        self.client = GeminiClient()

    def answer(
        self,
        question: str,
        top_k: int = 3,
        minimum_score: float = 0.01,
    ) -> dict:
        """檢索知識庫並使用 Gemini 產生回答。"""

        question = question.strip()

        if not question:
            raise ValueError("問題不能是空白。")

        if top_k < 1:
            raise ValueError("top_k 必須大於或等於 1。")

        search_results = self.retriever.search(
            query=question,
            top_k=top_k,
        )

        # 排除幾乎完全不相關的結果。
        relevant_results = [
            result
            for result in search_results
            if result.get("score", 0.0) >= minimum_score
        ]

        if not relevant_results:
            return {
                "question": question,
                "answer": (
                    "目前檢索到的規章內容不足以回答此問題，"
                    "請查閱原始規章或洽詢相關單位。"
                ),
                "sources": [],
            }

        context = build_context(relevant_results)

        answer_text = self.client.chat(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(
                question=question,
                context=context,
            ),
            temperature=0.1,
        )

        sources = []

        for result in relevant_results:
            sources.append({
                "title": result.get("title", "未知標題"),
                "path": result.get("path", "未知路徑"),
                "score": result.get("score", 0.0),
            })

        return {
            "question": question,
            "answer": answer_text,
            "sources": sources,
        }

def answer_rule_question(
    question: str,
    top_k: int = 3,
) -> dict:
    """提供給 agent.py 或 app.py 使用的規章問答函式。"""

    service = RAGAnswerService()

    return service.answer(
        question=question,
        top_k=top_k,
    )

def generate_breach_warning(risk_result: dict) -> str:
    """將程式計算完成的風控結果整理成自然語言警告。"""

    client = GeminiClient()

    prompt = f"""
你是固定收益風險管理助理。

以下數值已由風控程式完成計算與判斷。
你不可以重新計算、修改數值或改變超限結果。

請用正式、清楚、簡潔的繁體中文產生超限警告。

【風控結果】
交易員：{risk_result['trader_name']}
交易員代號：{risk_result['trader_id']}

DV01 使用率：{risk_result['dv01_usage']:.2%}
DV01 是否超限：{'是' if risk_result['dv01_breach'] else '否'}

月停損使用率：{risk_result['monthly_stop_loss_usage']:.2%}
月停損是否超限：
{'是' if risk_result['monthly_stop_loss_breach'] else '否'}

年停損使用率：{risk_result['yearly_stop_loss_usage']:.2%}
年停損是否超限：
{'是' if risk_result['yearly_stop_loss_breach'] else '否'}

整體是否超限：
{'是' if risk_result['overall_breach'] else '否'}

【輸出要求】
1. 先說明整體風控狀態。
2. 只列出超限的指標。
3. 不得自行補充規章、處理流程、期限或通報對象。
4. 若沒有超限，簡短說明目前狀態正常。
""".strip()

    return client.chat(
        system_prompt=(
            "你只能整理系統提供的風控結果，"
            "不得修改數值、重新判斷或虛構資訊。"
        ),
        user_prompt=prompt,
        temperature=0.1,
    )
 
def run_chat() -> None:
    """在 Terminal 中執行連續問答。"""

    print("LLM Wiki 規章問答系統")
    print("輸入 exit、quit 或 q 可以結束。\n")

    service = RAGAnswerService()

    while True:
        question = input("請輸入問題：").strip()

        if question.lower() in {"exit", "quit", "q"}:
            print("問答結束。")
            break

        if not question:
            print("問題不能是空白。\n")
            continue

        try:
            result = service.answer(
                question=question,
                top_k=3,
            )

            print(result["answer"])

            if result["sources"]:
                print("\n檢索來源：")

                for number, source in enumerate(
                    result["sources"],
                    start=1,
                ):
                    print(
                        f'{number}. {source["title"]} '
                        f'（相似度：{source["score"]:.3f}）'
                    )

            print()

        except Exception as error:
            print(f"\n產生回答時發生錯誤：{error}\n")


if __name__ == "__main__":
    run_chat()