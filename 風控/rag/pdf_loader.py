#讀取pdf
from pathlib import Path
import fitz # 匯入 PyMuPDF 套件

PDF_PATH = Path(__file__).parent / "data"

# 定義一個讀取單一 PDF 的函式 # -> str 表示這個函式最後會回傳文字字串

def load_pdf_text(pdf_path: Path) -> str:
    document = fitz.open(pdf_path)

    pages_text = []

    # 逐頁讀取 PDF
    # enumerate 可以同時取得頁碼與頁面內容
    # start=1 表示頁碼從 1 開始，而不是從 0 開始
    for page_number, page in enumerate(document, start=1):
        text = page.get_text("text")

        pages_text.append(
            f"\n--- {pdf_path.name}／第 {page_number} 頁 ---\n{text}"
        )

    document.close()

    return "".join(pages_text)


if __name__ == "__main__":
    # 找出 data 資料夾裡所有副檔名為 .pdf 的檔案 # list 將搜尋結果轉成串列
    pdf_files = list(PDF_PATH.glob("*.pdf"))  

    if not pdf_files:
        raise FileNotFoundError(f"資料夾內找不到 PDF:{PDF_PATH}")

    for pdf_file in pdf_files:
        print(f"\n正在讀取:{pdf_file.name}")

        pdf_text = load_pdf_text(pdf_file)

        print("PDF 讀取成功")
        print(f"總文字數：{len(pdf_text)}")
        print("前 500 個字：")
        print(pdf_text[:2000])