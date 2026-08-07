## Fixed Income AI Risk Control System

An AI-assisted risk control platform for fixed income trading.

Features:
• Daily P&L calculation
• Net DV01 monitoring
• Risk limit monitoring
• Rule-based risk engine
• RAG-based policy retrieval
• Streamlit dashboard
• Automated risk report generation




目前系統使用免費的TF-IDF搜尋，不使用OpenAI API，也不需要PyTorch。

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
