Fixed Income AI Risk Control System

An AI-assisted risk control platform for fixed income trading.

Features:
• Daily P&L calculation
• Net DV01 monitoring
• Risk limit monitoring
• Rule-based risk engine
• RAG-based policy retrieval
• Streamlit dashboard
• Automated risk report generation

---

## 第一次使用需要安裝的套件

以下套件只需要安裝一次，不需要每天重新安裝。
在VS Code終端機輸入：
```powershell
pip install pandas openpyxl pypdf scikit-learn streamlit
```
各套件用途：
| 套件 | 用途 |
| pandas | 讀取、處理及輸出Excel資料 |
| openpyxl | 讓pandas讀寫`.xlsx`檔案 |
| pypdf | 讀取PDF中的規章文字 |
| scikit-learn | 使用TF-IDF及餘弦相似度搜尋規章 |

目前系統使用免費的TF-IDF搜尋，不使用OpenAI API，也不需要PyTorch。

---

## 每天開啟VS Code後的操作

### 1. 開啟VS Code終端機

在VS Code上方選單點選：
```text
Terminal → New Terminal
```
### 切換到專案資料夾
```powershell
cd "C:\Users\Sinopac\Desktop\風控\盤後風控報告"
```
正常應顯示：
```text
C:\Users\Sinopac\Desktop\風控\盤後風控報告
```
### 啟動固定收益風控Agent
```powershell
py agent.py
```
每天正常使用時，只需要執行這個指令，不需要逐一執行其他Python檔案。

---

開啟streamlit
py -m streamlit run app.py
