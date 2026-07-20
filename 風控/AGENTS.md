# AGENTS

## Purpose
This file helps AI coding agents understand the current workspace and be immediately productive.

## Project overview
- Single Python script: `main.py`
- Reads Excel data from `data/債券交易員虛擬資料.xlsx`
- Uses `pandas` and `pathlib`
- No frontend, UI, or styling code is present in this workspace

## Key behavior
- `main.py` prompts for:
  - 交易員代號 (trader ID)
  - 報告日期 (report date)
- It reads two sheets from the Excel file:
  - `標準化債券交易員主檔`
  - `歷史資料集`
- It computes risk status based on:
  - monthly stop-loss limit (`月停損上限`)
  - yearly stop-loss limit (`年停損上限`)
  - net DV01 (`dv01授權額度`)

## What an agent should know
- Do not invent frontend or font-family behavior; there is no CSS/HTML/UI in this repository.
- Keep changes limited to Python code and data handling unless the user adds new files or explicitly requests UI work.
- The script assumes `data/債券交易員虛擬資料.xlsx` exists and must not be deleted.

## Run command
- `python main.py`

## Notes for future enhancements
- If the user requests anything about styling, fonts, or frontend presentation, clarify that this repository currently contains only backend/reporting logic.
