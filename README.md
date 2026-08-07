## 固定收益盤後 AI 風控系統
Fixed Income AI Risk Control System

本專案整合兩項功能：

盤後風控報告：查詢交易員損益、DV01、停損使用率與超限狀態，並輸出 Excel／PDF 報告。

規章 RAG 問答：檢索 Markdown 規章知識庫，再由 Gemini 根據檢索內容回答問題；發生超限時，也會自動產生規章處理建議。

## 每天開啟VS Code後的操作

### 開啟VS Code終端機
```text
Terminal → New Terminal
```
### 切換到專案資料夾
```powershell
cd "C:\Users\xxxxx\xxxxxx\xxxxxx\fixed_income_risk_control"
```
### 建立虛擬環境：
```powershell
py -3.12 -m venv .venv
```

啟用虛擬環境：
```powershell
.venv\Scripts\Activate.ps1
```
## 第一次使用需要安裝的套件
以下套件只需要安裝一次，不需要每天重新安裝。
在VS Code終端機輸入：
```powershell
py -m pip install -r requirements.txt
```

### 設定 Gemini API Key
在專案最外層建立 .env：
GEMINI_API_KEY=你的_Gemini_API_Key
請確認 .gitignore 包含：

.env
.venv/
__pycache__/
*.pyc



### 第一次建立規章知識庫

只有在以下情況需要執行 build_knowledge.py：

第一次建立規章 Markdown 知識庫。

新增或修改原始規章。

想重新產生 knowledge/generated 中的 Markdown。

請在專案最外層執行：

py -m rag_llmwiki.build_knowledge

執行後，確認產生的 Markdown 位於：

rag_llmwiki/knowledge/generated/

如果 Markdown 已經建立完成，而且規章沒有更新，就不需要每天重新執行這一步。

### 開啟streamlit
```powershell
py -m streamlit run app.py
```

每天正常使用時，不需要逐一執行其他Python檔案。

---
