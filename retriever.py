# 匯入餘弦相似度工具
# 用來比較「問題向量」和「規章段落向量」有多接近
from sklearn.metrics.pairwise import cosine_similarity

# 從 embedding.py 匯入建立搜尋索引的函式
from embedding import build_tfidf_index


# 建立規章搜尋函式
def search_rules(query, top_k=3):

    # 建立 TF-IDF 搜尋索引
    # records：原始段落及PDF來源
    # vectorizer：TF-IDF文字轉換工具
    # chunk_vectors：所有規章段落的向量

    records, vectorizer, chunk_vectors = (build_tfidf_index())

    # 將使用者問題轉成TF-IDF向量
    # 必須使用與規章相同的vectorizer
    query_vector = vectorizer.transform([query])

    # 比較問題與所有規章段落的相似度
    # 結果會是每個段落各自的相似分數
    similarities = cosine_similarity(
        query_vector,
        chunk_vectors)[0]

    # 依照相似度由大到小排列
    # [:top_k] 表示只取前top_k個結果
    top_indices = similarities.argsort()[::-1][:top_k]

    # 儲存搜尋結果
    results = []

    # 逐一整理最相關的段落
    for index in top_indices:

        results.append(
            {
                # 段落來自哪一份PDF
                "source": records[index]["source"],

                # 原始規章文字
                "text": records[index]["text"],

                # 問題與段落的相似度分數
                "score": similarities[index]
            }
        )

    # 回傳最相關的段落
    return results


# 只有直接執行retriever.py時才進入測試
if __name__ == "__main__":

    # 讓使用者輸入想查詢的問題
    query = input("請輸入規章問題：").strip()

    # 搜尋最相關的三段規章
    results = search_rules(
        query,
        top_k=3
    )

    # 顯示搜尋結果
    for rank, result in enumerate(
        results,
        start=1
    ):
        print(f"\n========== 第 {rank} 名 ==========")

        # 顯示來源檔案
        print(f"來源：{result['source']}")

        # 顯示相似度，保留小數點後四位
        print(f"相似度：{result['score']:.4f}")

        # 顯示規章內容
        print("規章內容：")
        print(result["text"])