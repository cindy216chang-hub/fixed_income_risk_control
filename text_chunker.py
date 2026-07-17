# 從 pdf_loader.py 匯入：
# 1. PDF 資料夾的位置
# 2. 讀取單一 PDF 的函式
from pdf_loader import PDF_PATH, load_pdf_text


# 定義文字切段函式
def split_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100
) -> list[str]:
    """
    將長文字切成多個小段。

    chunk_size:
        每一段最多保留多少個字元。

    overlap:
        前後兩段重複保留多少個字元，
        避免重要句子剛好被切斷。
    """

    # chunk_size 必須大於 0
    if chunk_size <= 0:
        raise ValueError("chunk_size 必須大於 0")

    # overlap 不能小於 0
    if overlap < 0:
        raise ValueError("overlap 不能小於 0")

    # 重疊字數必須小於每段長度
    if overlap >= chunk_size:
        raise ValueError("overlap 必須小於 chunk_size")

    # 用來保存切好的文字段落
    chunks = []

    # 從文字的第 0 個位置開始
    start = 0

    # 只要還沒有讀完整份文字，就繼續切段
    while start < len(text):

        # 計算這一段的結束位置
        end = start + chunk_size

        # 擷取目前這一段文字
        chunk = text[start:end].strip()

        # 避免加入空白段落
        if chunk:
            chunks.append(chunk)

        # 如果已經切到全文最後，就停止
        if end >= len(text):
            break

        # 下一段往回保留 overlap 個字元
        # 例如：
        # 第一段是 0～500
        # 下一段會從 400 開始
        # 因此前後會重複 100 個字
        start = end - overlap

    # 回傳所有切好的段落
    return chunks


# 只有直接執行 text_chunker.py 時，
# 才會執行下面的測試程式
if __name__ == "__main__":

    # 找出 data 資料夾中所有 PDF
    pdf_files = sorted(PDF_PATH.glob("*.pdf"))

    # 如果沒有找到 PDF，就顯示錯誤
    if not pdf_files:
        raise FileNotFoundError(
            f"資料夾內找不到 PDF:{PDF_PATH}"
        )

    # 用來保存所有 PDF 的切段結果
    all_chunks = []

    # 依序處理每一份 PDF
    for pdf_file in pdf_files:

        # 讀取整份 PDF 的文字
        pdf_text = load_pdf_text(pdf_file)

        # 將整份文字切成多個小段
        chunks = split_text(
            text=pdf_text,
            chunk_size=500,
            overlap=100
        )

        # 將每一段文字與來源檔名保存起來
        for chunk_number, chunk in enumerate(chunks, start=1):

            all_chunks.append({
                "source": pdf_file.name,
                "chunk_number": chunk_number,
                "text": chunk
            })

        # 顯示目前 PDF 被切成幾段
        print(
            f"{pdf_file.name}：共切成 {len(chunks)} 段"
        )

    # 顯示所有 PDF 合計的段落數量
    print(f"\n全部文件共 {len(all_chunks)} 段")

    # 顯示前兩段，確認切段結果
    print("\n前兩段內容:")

    for chunk in all_chunks[:2]:

        print("\n" + "=" * 50)
        print(f"來源：{chunk['source']}")
        print(f"段落編號：{chunk['chunk_number']}")
        print(chunk["text"])