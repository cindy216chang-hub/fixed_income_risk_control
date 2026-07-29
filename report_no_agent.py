import pandas as pd
from pathlib import Path

# ====================================================================
# Excel 檔案位置 、讀取
# ====================================================================
EXCEL_PATH = Path("data") / "債券交易員虛擬資料.xlsx"

trader_master = pd.read_excel(
    EXCEL_PATH,
    sheet_name="標準化債券交易員主檔",)

history = pd.read_excel(
    EXCEL_PATH,
    sheet_name="歷史資料集",)

# 統一交易員代號格式
trader_master["交易員代號"] = (
    trader_master["交易員代號"]
    .astype(str)
    .str.strip()
    .str.upper())

history["交易員代號"] = (
    history["交易員代號"]
    .astype(str)
    .str.strip()
    .str.upper())


# 統一交易日期格式
history["交易日期"] = pd.to_datetime(
    history["交易日期"]
).dt.normalize()

# ====================================================================
# 資料查詢
# ====================================================================
# 讓使用者輸入查詢條件
trader_id = input("請輸入交易員代號，例如 TRD001:").strip().upper()
query_date = input("請輸入報告日期，例如 2026-07-08:").strip()

query_date = pd.to_datetime(query_date).normalize()  # 將輸入的日期轉成 pandas 日期格式

# 從交易員主檔找到指定交易員
trader_result = trader_master.loc[
    trader_master["交易員代號"] == trader_id]

if trader_result.empty:
    raise ValueError(f"找不到交易員代號：{trader_id}")

trader_info = trader_result.iloc[0]


# 從歷史資料找出指定交易員與指定日期
report_data = history.loc[
    (history["交易員代號"] == trader_id) & (history["交易日期"] == query_date)].copy()

if report_data.empty:
    raise ValueError(
        f"{trader_id} 在 {query_date.date()} 沒有歷史資料")


# 把相關欄位轉成數字
numeric_columns = [
    "當日損益",
    "本月累計損益",
    "年累計損益",
    "持倉DV01",]

for column in numeric_columns:
    report_data[column] = pd.to_numeric(
        report_data[column],
        errors="coerce",
    )


# 計算交易員整體資料
# 加總指定交易員在報告日期的商品損益
total_daily_pnl = report_data["當日損益"].sum()
total_mtd_pnl = report_data["本月累計損益"].sum()
total_ytd_pnl = report_data["年累計損益"].sum()

# 加總指定交易員在報告日期的 Net DV01
net_dv01 = report_data["持倉DV01"].sum()

monthly_limit = float(trader_info["月停損上限"])
yearly_limit = float(trader_info["年停損上限"])
dv01_limit = float(trader_info["dv01授權額度"])


# 建立商品明細表
pnl_overview = report_data[
    [
        "商品名稱",
        "當日損益",
        "本月累計損益",
        "年累計損益",
    ]].copy()


# 數字加上千分位，方便閱讀
for column in [
    "當日損益",
    "本月累計損益",
    "年累計損益",
]:
    pnl_overview[column] = pnl_overview[column].map(
        lambda value: f"{value:,.0f}")


# 顯示第一部分報告
print("\n" + "=" * 60)
print("固定收益盤後風控監控報告")
print("=" * 60)

print(f"報告日期：{query_date.date()}")
print(
    f"交易員：{trader_info['交易員姓名']} "
    f"({trader_id})")


print("\n【損益概況】")
print(f"當日損益：{total_daily_pnl:,.0f}")
print(f"本月累計損益：{total_mtd_pnl:,.0f}")
print(f"年累計損益：{total_ytd_pnl:,.0f}")

print("\n【商品明細】")
print(pnl_overview.to_string(index=False))

# ====================================================================
# 取得交易員的停損上限
# ====================================================================
monthly_stop_loss_limit = float(trader_info["月停損上限"])

yearly_stop_loss_limit = float(trader_info["年停損上限"])

# 獲利時，停損使用率顯示為 0%
monthly_stop_loss_usage = max(
    0.0,
    -total_mtd_pnl / monthly_stop_loss_limit,)

yearly_stop_loss_usage = max(
    0.0,
    -total_ytd_pnl / yearly_stop_loss_limit,)


#顯示停損監控
print("\n【停損監控】")

print(
    f"月停損上限："
    f"{monthly_stop_loss_limit:,.0f} USD")

print(
    f"月停損使用率："
    f"{monthly_stop_loss_usage:.2%}")

print(
    f"年停損上限："
    f"{yearly_stop_loss_limit:,.0f} USD")

print(
    f"年停損使用率："
    f"{yearly_stop_loss_usage:.2%}")

# ====================================================================
# 壓力測試
# 利率上升情境的預估損益影響　＃前面已有net_dv01 = report_data["持倉DV01_USD"].sum()　
# 該交易員在報告日期，各商品DV01保留正負號後的總和
# ====================================================================
impact_up_10bp = -net_dv01 * 10
impact_up_50bp = -net_dv01 * 50
print("\n【壓力測試】")

print(
    f"總DV01:{net_dv01:,.0f} USD/bp")

print(
    f"利率上升10bps，預估影響:"
    f"{impact_up_10bp:,.0f} USD")

print(
    f"利率上升50bps，預估影響:"
    f"{impact_up_50bp:,.0f} USD")


# ====================================================================
# 計算風空指標
# 讀取交易員的 DV01 授權額度
# ====================================================================
dv01_limit = float(
    trader_info["dv01授權額度"]
)

# 第一版先以 Net DV01 的絕對值作為實際控管值
actual_control_dv01 = abs(net_dv01)

# 計算 DV01 額度使用率
dv01_usage = actual_control_dv01 / dv01_limit

# 使用率達到或超過 100%，第一版視為不合規
if dv01_usage >= 1.0:
    dv01_control_status = "不合規"
else:
    dv01_control_status = "合規"


if monthly_stop_loss_usage >= 1.0:
    monthly_stop_status = "不合規"
else:
    monthly_stop_status = "合規"


if yearly_stop_loss_usage >= 1.0:
    yearly_stop_status = "不合規"
else:
    yearly_stop_status = "合規"

# 綜合月、年停損狀態，決定整體停損控管狀態
if (
    monthly_stop_status == "合規"
    and yearly_stop_status == "合規"
):
    stop_loss_control_status = "合規"
else:
    stop_loss_control_status = "不合規"

if (
    dv01_control_status == "合規"
    and stop_loss_control_status == "合規"
):
    overall_risk_status = "合規"
else:
    overall_risk_status = "不合規"


#設定合規處置與審核狀態
if overall_risk_status == "合規":
    compliance_action = (
        "本日未發生異常，無須額外處置措施"
    )
    review_status = "免審核"
else:
    compliance_action = (
        "本日發生風控異常，應產生超限警告通知並送交審核"
    )
    review_status = "待審核"

# ====================================================================
# 模擬歸檔位置
# ====================================================================
from pathlib import Path

# 在桌面建立報告資料夾
archive_folder = Path(
    r"C:\Users\Sinopac\Desktop\固定收益盤後風控報告")
archive_folder.mkdir(parents=True, exist_ok=True)

# 設定報告檔案名稱與完整位置
archive_location = (
    archive_folder
    / f"{query_date:%Y-%m-%d}_{trader_id}_風控報告.xlsx"
)

# 顯示在報告中 
print("\n【風控指標】")

print(f"DV01控管:{dv01_control_status}")
print(f"DV01授權額度:{dv01_limit:,.0f} USD/bp")
print(
    f"實際控管DV01:"
    f"{actual_control_dv01:,.0f} USD/bp"
)
print(f"DV01使用率:{dv01_usage:.2%}")

print(f"停損控管:{stop_loss_control_status}")
print(f"月停損狀態:{monthly_stop_status}")
print(f"年停損狀態:{yearly_stop_status}")

print(f"\n【風控狀態:{overall_risk_status}")
print("\n【合規處置】")
print(compliance_action)

print("\n【審核狀態】")
print(review_status)

print("\n【歸檔位置】")
print(archive_location)