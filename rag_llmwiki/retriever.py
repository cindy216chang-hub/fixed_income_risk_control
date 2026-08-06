from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag_llmwiki.loader import load_knowledge_base


@dataclass
class SearchResult:
    document: str
    heading: str
    content: str
    file_path: str
    score: float


class KnowledgeRetriever:
    """使用 TF-IDF 檢索 Obsidian Markdown。"""

    def __init__(self) -> None:
        self.documents = load_knowledge_base()

        if not self.documents:
            raise ValueError("knowledge 資料夾中沒有可使用的 Markdown。")

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
        )

        self.document_texts = [
            self._build_search_text(doc)
            for doc in self.documents
        ]

        self.document_matrix = self.vectorizer.fit_transform(
            self.document_texts
        )

    @staticmethod
    def _build_search_text(document: dict) -> str:
        """
        將檔名、標題和內容一起加入搜尋。

        檔名通常是最重要的主題提示。
        """

        return "\n".join(
            [
                document["document"],
                document["document"],
                document["heading"],
                document["content"],
            ]
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        minimum_score: float = 0.0,
    ) -> list[SearchResult]:
        """搜尋最相關的知識區塊。"""

        query = query.strip()

        if not query:
            raise ValueError("查詢問題不可為空白。")

        query_vector = self.vectorizer.transform([query])

        scores = cosine_similarity(
            query_vector,
            self.document_matrix,
        )[0]

        ranked_indexes = scores.argsort()[::-1]

        results = []

        for index in ranked_indexes:
            score = float(scores[index])

            if score < minimum_score:
                continue

            document = self.documents[index]

            results.append(
                SearchResult(
                    document=document["document"],
                    heading=document["heading"],
                    content=document["content"],
                    file_path=document["file_path"],
                    score=score,
                )
            )

            if len(results) >= top_k:
                break

        return results


if __name__ == "__main__":
    retriever = KnowledgeRetriever()

    question = input("請輸入規章問題：").strip()
    results = retriever.search(question, top_k=5)

    for rank, result in enumerate(results, start=1):
        print("=" * 60)
        print(f"第 {rank} 名")
        print(f"文件：{result.document}")
        print(f"區塊：{result.heading}")
        print(f"分數：{result.score:.4f}")
        print(result.content)