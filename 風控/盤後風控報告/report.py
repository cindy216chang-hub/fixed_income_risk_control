from pathlib import Path
import pandas as pd
from rag.rule_mapping import get_breach_rule

# ============================================================
# 1. 路徑設定
# ============================================================

# report.py 所在的專案資料夾
BASE_DIR = Path(__file__).resolve().parent

# Excel 資料位置
EXCEL_PATH = BASE_DIR / "data" / "債券交易員虛擬資料.xlsx"

# 報告歸檔位置
ARCHIVE_FOLDER = Path.home() / "Desktop" / "固定收益盤後風控報告"


# ============================================================
# 2. 讀取與整理資料
# ============================================================

def _load_data():
    """讀取交易員主檔與歷史資料。"""

    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"找不到 Excel 檔案：{EXCEL_PATH}")

    trader_master = pd.read_excel(EXCEL_PATH, sheet_name="標準化債券交易員主檔")
    history = pd.read_excel(EXCEL_PATH, sheet_name="歷史資料集")

    # 統一交易員代號格式
    trader_master["交易員代號"] = (
        trader_master["交易員代號"].astype(str).str.strip().str.upper()
    )
    history["交易員代號"] = (
        history["交易員代號"].astype(str).str.strip().str.upper()
    )

    # 統一交易日期格式
    history["交易日期"] = pd.to_datetime(history["交易日期"], errors="coerce").dt.normalize()

    return trader_master, history


# ============================================================
# 3. 查詢指定交易員與日期的資料
# ============================================================

def _get_query_data(trader_id, query_date):
    """取得指定交易員的主檔資料，以及指定日期的歷史資料。"""

    trader_master, history = _load_data()

    trader_id = str(trader_id).strip().upper()

    try:
        query_date = pd.to_datetime(query_date).normalize()
    except (ValueError, TypeError):
        raise ValueError("日期格式錯誤，請使用 YYYY-MM-DD，例如 2026-07-08。")

    # 查詢交易員主檔
    trader_result = trader_master.loc[trader_master["交易員代號"] == trader_id]

    if trader_result.empty:
        raise ValueError(f"找不到交易員代號：{trader_id}")

    trader_info = trader_result.iloc[0]

    # 查詢指定日期的歷史資料
    report_data = history.loc[
        (history["交易員代號"] == trader_id) & (history["交易日期"] == query_date)
    ].copy()

    if report_data.empty:
        raise ValueError(f"{trader_id} 在 {query_date.date()} 沒有歷史資料")

    # 將計算欄位轉成數字
    numeric_columns = ["當日損益", "本月累計損益", "年累計損益", "持倉DV01"]

    for column in numeric_columns:
        report_data[column] = pd.to_numeric(report_data[column], errors="coerce")

    # 有無法轉換的數值時直接警告
    if report_data[numeric_columns].isna().any().any():
        raise ValueError("歷史資料中存在無法轉換成數字的損益或 DV01 資料。")

    return trader_id, query_date, trader_info, report_data


# ============================================================
# 4. 計算共用風控指標
# ============================================================

def _calculate_metrics(trader_info, report_data):
    """計算損益、DV01、停損使用率及超限狀態。"""

    total_daily_pnl = report_data["當日損益"].sum()
    total_mtd_pnl = report_data["本月累計損益"].sum()
    total_ytd_pnl = report_data["年累計損益"].sum()

    # 各商品 DV01 保留正負號後加總
    net_dv01 = report_data["持倉DV01"].sum()

    # 取得授權限額
    monthly_stop_loss_limit = float(trader_info["月停損上限"])
    yearly_stop_loss_limit = float(trader_info["年停損上限"])
    dv01_limit = float(trader_info["dv01授權額度"])

    if monthly_stop_loss_limit <= 0:
        raise ValueError("月停損上限必須大於 0。")
    if yearly_stop_loss_limit <= 0:
        raise ValueError("年停損上限必須大於 0。")
    if dv01_limit <= 0:
        raise ValueError("DV01 授權額度必須大於 0。")

    # 獲利時，停損使用率顯示為 0%
    monthly_stop_loss_usage = max(0.0, -total_mtd_pnl / monthly_stop_loss_limit)
    yearly_stop_loss_usage = max(0.0, -total_ytd_pnl / yearly_stop_loss_limit)

    # 第一版以 Net DV01 絕對值作為控管值
    actual_control_dv01 = abs(net_dv01)
    dv01_usage = actual_control_dv01 / dv01_limit

    # 超過 100% 才是超限，剛好 100% 不算超限
    dv01_breach = dv01_usage > 1.0
    monthly_stop_loss_breach = monthly_stop_loss_usage > 1.0
    yearly_stop_loss_breach = yearly_stop_loss_usage > 1.0

    # 任一項超過 100% 就啟動預警
    overall_breach = dv01_breach or monthly_stop_loss_breach or yearly_stop_loss_breach

    dv01_control_status = "不合規" if dv01_breach else "合規"
    monthly_stop_status = "不合規" if monthly_stop_loss_breach else "合規"
    yearly_stop_status = "不合規" if yearly_stop_loss_breach else "合規"

    stop_loss_control_status = (
        "不合規" if (monthly_stop_loss_breach or yearly_stop_loss_breach) else "合規"
    )

    overall_risk_status = "不合規" if overall_breach else "合規"

    if overall_breach:
        compliance_action = "本日發生風控異常，應產生超限警告通知並送交審核。"
        review_status = "待審核"
    else:
        compliance_action = "本日未發生異常，無須額外處置措施。"
        review_status = "免審核"

    # 壓力測試
    impact_up_10bp = -net_dv01 * 10
    impact_up_50bp = -net_dv01 * 50

    return {
        "total_daily_pnl": total_daily_pnl,
        "total_mtd_pnl": total_mtd_pnl,
        "total_ytd_pnl": total_ytd_pnl,
        "net_dv01": net_dv01,
        "actual_control_dv01": actual_control_dv01,
        "dv01_limit": dv01_limit,
        "dv01_usage": dv01_usage,
        "monthly_stop_loss_limit": monthly_stop_loss_limit,
        "monthly_stop_loss_usage": monthly_stop_loss_usage,
        "yearly_stop_loss_limit": yearly_stop_loss_limit,
        "yearly_stop_loss_usage": yearly_stop_loss_usage,
        "dv01_breach": dv01_breach,
        "monthly_stop_loss_breach": monthly_stop_loss_breach,
        "yearly_stop_loss_breach": yearly_stop_loss_breach,
        "overall_breach": overall_breach,
        "dv01_control_status": dv01_control_status,
        "monthly_stop_status": monthly_stop_status,
        "yearly_stop_status": yearly_stop_status,
        "stop_loss_control_status": stop_loss_control_status,
        "overall_risk_status": overall_risk_status,
        "compliance_action": compliance_action,
        "review_status": review_status,
        "impact_up_10bp": impact_up_10bp,
        "impact_up_50bp": impact_up_50bp,
    }


# ============================================================
# 5. Agent 功能：查詢損益
# ============================================================

def get_total_pnl(trader_id, query_date):
    trader_id, query_date, trader_info, report_data = _get_query_data(trader_id, query_date)
    metrics = _calculate_metrics(trader_info, report_data)

    return {
        "trader_id": trader_id,
        "trader_name": trader_info["交易員姓名"],
        "query_date": query_date,
        "total_daily_pnl": metrics["total_daily_pnl"],
        "total_mtd_pnl": metrics["total_mtd_pnl"],
        "total_ytd_pnl": metrics["total_ytd_pnl"],
    }


# ============================================================
# 6. Agent 功能：查詢 DV01
# ============================================================

def get_dv01(trader_id, query_date):
    trader_id, query_date, trader_info, report_data = _get_query_data(trader_id, query_date)
    metrics = _calculate_metrics(trader_info, report_data)

    return {
        "trader_id": trader_id,
        "trader_name": trader_info["交易員姓名"],
        "query_date": query_date,
        "net_dv01": metrics["net_dv01"],
        "actual_control_dv01": metrics["actual_control_dv01"],
        "dv01_limit": metrics["dv01_limit"],
        "dv01_usage": metrics["dv01_usage"],
        "dv01_breach": metrics["dv01_breach"],
        "dv01_control_status": metrics["dv01_control_status"],
    }


# ============================================================
# 7. Agent 功能：查詢超限狀態
# ============================================================

def get_risk_status(trader_id, query_date):
    trader_id, query_date, trader_info, report_data = _get_query_data(trader_id, query_date)
    metrics = _calculate_metrics(trader_info, report_data)

    return {
        "trader_id": trader_id,
        "trader_name": trader_info["交易員姓名"],
        "query_date": query_date,
        "dv01_usage": metrics["dv01_usage"],
        "monthly_stop_loss_usage": metrics["monthly_stop_loss_usage"],
        "yearly_stop_loss_usage": metrics["yearly_stop_loss_usage"],
        "dv01_breach": metrics["dv01_breach"],
        "monthly_stop_loss_breach": metrics["monthly_stop_loss_breach"],
        "yearly_stop_loss_breach": metrics["yearly_stop_loss_breach"],
        "overall_breach": metrics["overall_breach"],
        "overall_risk_status": metrics["overall_risk_status"],
        "compliance_action": metrics["compliance_action"],
        "review_status": metrics["review_status"],
    }



# ============================================================
# 8. Agent 功能：產生完整報告
# ============================================================

def generate_report(trader_id, query_date):
    trader_id, query_date, trader_info, report_data = _get_query_data(trader_id, query_date)
    metrics = _calculate_metrics(trader_info, report_data)

    # 商品明細
    pnl_overview = report_data[
        ["商品名稱", "當日損益", "本月累計損益", "年累計損益", "持倉DV01"]
    ].copy()

    # 終端機顯示用版本
    display_overview = pnl_overview.copy()

    for column in ["當日損益", "本月累計損益", "年累計損益", "持倉DV01"]:
        display_overview[column] = display_overview[column].map(lambda value: f"{value:,.0f}")

    # 顯示完整報告
    print("\n" + "=" * 60)
    print("固定收益盤後風控監控報告")
    print("=" * 60)

    print(f"報告日期：{query_date.date()}")
    print(f"交易員：{trader_info['交易員姓名']} ({trader_id})")

    print("\n【損益概況】")
    print(f"當日損益：{metrics['total_daily_pnl']:,.0f} USD")
    print(f"本月累計損益：{metrics['total_mtd_pnl']:,.0f} USD")
    print(f"年累計損益：{metrics['total_ytd_pnl']:,.0f} USD")

    print("\n【商品明細】")
    print(display_overview.to_string(index=False))

    print("\n【停損監控】")
    print(f"月停損上限：{metrics['monthly_stop_loss_limit']:,.0f} USD")
    print(f"月停損使用率：{metrics['monthly_stop_loss_usage']:.2%}")
    print(f"月停損狀態：{metrics['monthly_stop_status']}")
    print(f"年停損上限：{metrics['yearly_stop_loss_limit']:,.0f} USD")
    print(f"年停損使用率：{metrics['yearly_stop_loss_usage']:.2%}")
    print(f"年停損狀態：{metrics['yearly_stop_status']}")

    print("\n【壓力測試】")
    print(f"總 DV01：{metrics['net_dv01']:,.0f} USD/bp")
    print(f"利率上升 10bps，預估影響：{metrics['impact_up_10bp']:,.0f} USD")
    print(f"利率上升 50bps，預估影響：{metrics['impact_up_50bp']:,.0f} USD")

    print("\n【風控指標】")
    print(f"DV01 控管：{metrics['dv01_control_status']}")
    print(f"DV01 授權額度：{metrics['dv01_limit']:,.0f} USD/bp")
    print(f"實際控管 DV01：{metrics['actual_control_dv01']:,.0f} USD/bp")
    print(f"DV01 使用率：{metrics['dv01_usage']:.2%}")
    print(f"停損控管：{metrics['stop_loss_control_status']}")

    print(f"\n【風控狀態】{metrics['overall_risk_status']}")

    print("\n【合規處置】")
    print(metrics["compliance_action"])

    print("\n【審核狀態】")
    print(metrics["review_status"])

# ============================================================
# 產生超限警告通知
# ============================================================

# 預設沒有超限通知
    breach_notice = None

    # 只有overall_breach為True時才建立通知
    if metrics["overall_breach"]:

        # 儲存本次發生的所有超限項目
        active_breaches = []

        # 檢查DV01超限
        if metrics["dv01_breach"]:
            active_breaches.append(
                {
                    "type": "dv01_breach",
                    "name": "DV01超限",
                    "usage": metrics["dv01_usage"],
                }
            )

        # 檢查月停損超限
        if metrics["monthly_stop_loss_breach"]:
            active_breaches.append(
                {
                    "type": "monthly_stop_loss_breach",
                    "name": "月停損超限",
                    "usage": metrics[
                        "monthly_stop_loss_usage"
                    ],
                }
            )

        # 檢查年停損超限
        if metrics["yearly_stop_loss_breach"]:
            active_breaches.append(
                {
                    "type": "yearly_stop_loss_breach",
                    "name": "年停損超限",
                    "usage": metrics[
                        "yearly_stop_loss_usage"
                    ],
                }
            )

        # 使用第一個超限項目取得共用規章
        first_breach_type = active_breaches[0]["type"]

        # 從rule_mapping.py取得規章
        rule = get_breach_rule(first_breach_type)

        # 整理超限項目文字
        breach_items = []

        for breach in active_breaches:
            breach_items.append(
                f"{breach['name']}："
                f"{breach['usage']:.2%}"
            )

        # 將多個超限項目合併成多行文字
        breach_items_text = "\n".join(
            breach_items
        )

        # 如果成功找到規章
        if rule is not None:
            breach_notice = {
                "breach_items": breach_items_text,
                "basis": rule["basis"],
                "required_actions": (
                    rule["required_actions"]
                ),
                "deadline": rule["deadline"],
            }

        # 如果沒有找到規章設定
        else:
            breach_notice = {
                "breach_items": breach_items_text,
                "basis": {
                    "source": "未設定",
                    "section": "未設定",
                    "text": "找不到制度依據，請人工確認。",
                },
                "required_actions": {
                    "source": "未設定",
                    "section": "未設定",
                    "text": "找不到應辦事項，請人工確認。",
                },
                "deadline": {
                    "source": "未設定",
                    "section": "未設定",
                    "text": "找不到處理期限，請人工確認。",
                },
            }
# ========================================================
# 終端機顯示超限警告通知
# ========================================================

    if breach_notice is not None:

        print("\n" + "!" * 60)
        print("超限警告通知")
        print("!" * 60)

        print("\n【超限項目】")
        print(breach_notice["breach_items"])

        print("\n【制度依據】")
        print(
            f"來源："
            f"{breach_notice['basis']['source']}")
        print(
            f"條次："
            f"{breach_notice['basis']['section']}")
        print(breach_notice["basis"]["text"])
        print("\n【應辦事項】")
        print(
            f"來源："
            f"{breach_notice['required_actions']['source']}")
        print(
            f"條次："
            f"{breach_notice['required_actions']['section']}")
        print(
            breach_notice["required_actions"]["text"])
        print("\n【處理期限】")
        print(
            f"來源："
            f"{breach_notice['deadline']['source']}")
        print(
            f"條次："
            f"{breach_notice['deadline']['section']}")
        print(breach_notice["deadline"]["text"])

        print("\n【審核狀態】")
        print(metrics["review_status"])

    # 建立歸檔資料夾
    ARCHIVE_FOLDER.mkdir(parents=True, exist_ok=True)

    archive_location = ARCHIVE_FOLDER / f"{query_date:%Y-%m-%d}_{trader_id}_風控報告.xlsx"

    # ========================================================
    # 建立風控摘要
    # ========================================================
    summary = pd.DataFrame(
        [
            ["報告日期", str(query_date.date())],
            ["交易員代號", trader_id],
            ["交易員姓名", trader_info["交易員姓名"]],
            ["當日損益", metrics["total_daily_pnl"]],
            ["本月累計損益", metrics["total_mtd_pnl"]],
            ["年累計損益", metrics["total_ytd_pnl"]],
            ["Net DV01", metrics["net_dv01"]],
            ["實際控管 DV01", metrics["actual_control_dv01"]],
            ["DV01 授權額度", metrics["dv01_limit"]],
            ["DV01 使用率", metrics["dv01_usage"]],
            ["月停損使用率", metrics["monthly_stop_loss_usage"]],
            ["年停損使用率", metrics["yearly_stop_loss_usage"]],
            ["整體風控狀態", metrics["overall_risk_status"]],
            ["合規處置", metrics["compliance_action"]],
            ["審核狀態", metrics["review_status"]],
        ],
        columns=["項目", "數值"],)

    # ========================================================
    # 建立超限警告通知工作表
    # ========================================================

    # 預設沒有超限警告通知工作表
    breach_notice_df = None

    # 只有產生breach_notice時才建立
    if breach_notice is not None:

        breach_notice_df = pd.DataFrame(
            [
                ["通知狀態",
                "超限預警",],
                ["報告日期",
                    str(query_date.date()),],
                ["交易員代號",
                    trader_id,],
                ["交易員姓名",
                    trader_info["交易員姓名"],],
                ["超限項目",
                    breach_notice["breach_items"],],
                ["整體風控狀態",
                    metrics["overall_risk_status"],],

                # 制度依據
                ["制度依據來源",
                    breach_notice["basis"]["source"],],
                ["制度依據條次",
                    breach_notice["basis"]["section"],],
                ["制度依據原文",
                    breach_notice["basis"]["text"],],

                # 應辦事項
                ["應辦事項來源",
                    breach_notice[
                        "required_actions"
                    ]["source"],],
                ["應辦事項條次",
                    breach_notice[
                        "required_actions"
                    ]["section"],],
                ["應辦事項原文",
                    breach_notice[
                        "required_actions"
                    ]["text"],],

                # 處理期限
                ["處理期限來源",
                    breach_notice["deadline"]["source"],],
                ["處理期限條次",
                    breach_notice["deadline"]["section"],],
                ["處理期限原文",
                    breach_notice["deadline"]["text"],],

                # 審核狀態
                ["審核狀態",
                    metrics["review_status"],],
            ],columns=["項目", "內容"],)

    # 寫入 Excel
        # ========================================================
    # 寫入Excel
    # ========================================================

    with pd.ExcelWriter(archive_location) as writer:

        # 一般風控摘要
        summary.to_excel(
            writer,
            sheet_name="風控摘要",
            index=False,
        )

        # 商品明細
        pnl_overview.to_excel(
            writer,
            sheet_name="商品明細",
            index=False,
        )

        # 只有不合規時才新增超限警告通知
        if breach_notice_df is not None:
            breach_notice_df.to_excel(
                writer,
                sheet_name="超限警告通知",
                index=False,
            )

    print("\n【歸檔位置】")
    print(archive_location)

    return archive_location