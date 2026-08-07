from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag_llmwiki.loader import load_knowledge_base


class KnowledgeRetriever:
    def __init__(self) -> None:
        self.documents = load_knowledge_base()

        if not self.documents:
            raise ValueError("knowledge/generated 裡找不到 Markdown。")

        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            lowercase=False,
        )

        self.document_matrix = self.vectorizer.fit_transform(
            document["content"] for document in self.documents
        )

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        query = query.strip()

        if not query:
            return []

        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(
            query_vector,
            self.document_matrix,
        )[0]

        ranked_indexes = scores.argsort()[::-1][:top_k]

        results = []

        for index in ranked_indexes:
            document = self.documents[index]

            results.append({
                **document,
                "score": float(scores[index]),
            })

        return results


if __name__ == "__main__":
    retriever = KnowledgeRetriever()
    question = input("請輸入規章問題：")

    for result in retriever.search(question):
        print(
            f'\n{result["title"]} '
            f'（相似度：{result["score"]:.3f}）'
        )