#文件向量化

from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer #匯入文字向量工具
# 匯入原本寫好的 PDF 讀取與文字切段功能
from pdf_loader import PDF_PATH, load_pdf_text
from text_chunker import split_text


def load_all_chunks():
    records=[]
    pdf_files= list(Path(PDF_PATH).glob("*.pdf")) # 找出 PDF_PATH 裡面的所有 PDF
    # 逐一處理每份 PDF
    for pdf_file in pdf_files:
        text=load_pdf_text(pdf_file)
        chunks = split_text(
            text,
            chunk_size=500,
            overlap=100
        )
        # 逐一儲存段落及其來源檔案
        for chunk in chunks:
            records.append(
                {
                    "source": pdf_file.name,
                    "text":chunk
                }
            )
        
        print(f"{pdf_file.name}:{len(chunks)}段")
    return records


# 建立 TF-IDF 搜尋索引
def build_tfidf_index():

    # 讀取全部規章段落
    records = load_all_chunks()

    # 只取出每一段的文字
    chunk_texts = [
        record["text"]
        for record in records
    ]

    # 建立 TF-IDF 工具
    # analyzer="char"：按照中文字元分析
    # ngram_range=(2, 4)：比較連續2到4個字 ex:發生超限會拆成:發生、生超、超限、發生超、生超限、發生超限)
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5)
    )

    # 把所有規章段落轉成向量
    chunk_vectors = vectorizer.fit_transform(
        chunk_texts
    )

    # 回傳段落、TF-IDF工具及向量
    return records, vectorizer, chunk_vectors


# 直接執行 embedding.py 時進行測試
if __name__ == "__main__":

    # 建立TF-IDF索引
    records, vectorizer, chunk_vectors = (
        build_tfidf_index()
    )

    # 顯示處理結果
    print(f"\n總段落數:{len(records)}")
    print(f"向量形狀：{chunk_vectors.shape}")
    
