import streamlit as st
import report
from rag.rule_mapping import get_breach_rule #匯入超限規章對照表


# ============================================================
# 網頁基本設定
# ============================================================

st.set_page_config(
    page_title="固定收益盤後風控系統",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# 網頁標題
# ============================================================

st.title("固定收益盤後風控系統")

st.write(
    "輸入交易員代號與查詢日期，"
    "系統將計算損益、DV01及超限狀態。"
)


# ============================================================
# 初始化網頁查詢結果
# ============================================================

# session_state可以在網頁重新執行時保留查詢結果
if "report_result" not in st.session_state:
    st.session_state.report_result = None


# ============================================================
# 查詢表單
# ============================================================

with st.form("risk_query_form"):

    # 輸入交易員代號
    trader_id = st.text_input(
        "交易員代號",
        placeholder="例如：TRD001",
    )

    # 選擇查詢日期
    query_date = st.date_input(
        "查詢日期",
    )

    # 送出查詢
    submitted = st.form_submit_button(
        "查詢風控資料",
        type="primary",
    )


# ============================================================
# 執行查詢
# ============================================================

if submitted:

    # 整理交易員代號
    trader_id = trader_id.strip().upper()

    # 沒有輸入交易員代號
    if not trader_id:
        st.warning("請輸入交易員代號。")

    else:
        try:
            # 查詢損益
            pnl_result = report.get_total_pnl(
                trader_id=trader_id,
                query_date=query_date,
            )

            # 查詢DV01
            dv01_result = report.get_dv01(
                trader_id=trader_id,
                query_date=query_date,
            )

            # 查詢整體風控狀態
            risk_result = report.get_risk_status(
                trader_id=trader_id,
                query_date=query_date,
            )

            # 將查詢結果保存到session_state
            # 這裡只查詢，不會輸出Excel
            st.session_state.report_result = {
                "trader_id": trader_id,
                "query_date": query_date,
                "pnl": pnl_result,
                "dv01": dv01_result,
                "risk": risk_result,
            }

        except FileNotFoundError as error:
            st.error(f"找不到資料檔案：{error}")

        except ValueError as error:
            st.error(f"查詢失敗：{error}")

        except KeyError as error:
            st.error(f"Excel缺少必要欄位：{error}")

        except Exception as error:
            st.error(f"執行查詢時發生錯誤：{error}")


# ============================================================
# 顯示查詢結果
# ============================================================

result = st.session_state.report_result

if result is not None:

    pnl = result["pnl"]
    dv01 = result["dv01"]
    risk = result["risk"]

    st.divider()

    st.subheader(
        f"{pnl['trader_name']} "
        f"({pnl['trader_id']})"
    )

    st.write(
        f"查詢日期：{result['query_date']}"
    )

    # ========================================================
    # 整體風控狀態
    # ========================================================

    if risk["overall_breach"]:
        st.error(
            "⚠ 整體風控狀態：不合規"
        )

    else:
        st.success(
            "✓ 整體風控狀態：合規"
        )

    # ========================================================
    # 損益資訊
    # ========================================================

    st.subheader("損益概況")

    pnl_column_1, pnl_column_2, pnl_column_3 = (
        st.columns(3)
    )

    pnl_column_1.metric(
        "當日損益",
        f"{pnl['total_daily_pnl']:,.0f} USD",
    )

    pnl_column_2.metric(
        "本月累計損益",
        f"{pnl['total_mtd_pnl']:,.0f} USD",
    )

    pnl_column_3.metric(
        "年累計損益",
        f"{pnl['total_ytd_pnl']:,.0f} USD",
    )

    # ========================================================
    # 風控使用率
    # ========================================================

    st.subheader("風控指標")

    risk_column_1, risk_column_2, risk_column_3 = (
        st.columns(3)
    )

    risk_column_1.metric(
        "DV01使用率",
        f"{risk['dv01_usage']:.2%}",
    )

    risk_column_2.metric(
        "月停損使用率",
        f"{risk['monthly_stop_loss_usage']:.2%}",
    )

    risk_column_3.metric(
        "年停損使用率",
        f"{risk['yearly_stop_loss_usage']:.2%}",
    )

    # ========================================================
    # 超限警告通知
    # ========================================================

    if risk["overall_breach"]:

        st.divider()
        st.header("⚠ 超限警告通知")

        # 儲存所有超限項目
        active_breaches = []

        # DV01超限
        if risk["dv01_breach"]:
            active_breaches.append(
                {
                    "type": "dv01_breach",
                    "name": "DV01超限",
                    "usage": risk["dv01_usage"],
                }
            )

        # 月停損超限
        if risk["monthly_stop_loss_breach"]:
            active_breaches.append(
                {
                    "type": (
                        "monthly_stop_loss_breach"
                    ),
                    "name": "月停損超限",
                    "usage": risk[
                        "monthly_stop_loss_usage"
                    ],
                }
            )

        # 年停損超限
        if risk["yearly_stop_loss_breach"]:
            active_breaches.append(
                {
                    "type": (
                        "yearly_stop_loss_breach"
                    ),
                    "name": "年停損超限",
                    "usage": risk[
                        "yearly_stop_loss_usage"
                    ],
                }
            )

        # 顯示所有超限項目
        st.subheader("超限項目")

        for breach in active_breaches:
            st.write(
                f"- {breach['name']}："
                f"{breach['usage']:.2%}"
            )

        # 取得規章對照內容
        first_breach_type = (
            active_breaches[0]["type"]
        )

        rule = get_breach_rule(
            first_breach_type
        )

        # 顯示規章內容
        if rule is not None:

            st.subheader("制度依據")

            st.caption(
                f"來源：{rule['basis']['source']}｜"
                f"條次：{rule['basis']['section']}"
            )

            st.write(
                rule["basis"]["text"]
            )

            st.subheader("應辦事項")

            st.caption(
                f"來源："
                f"{rule['required_actions']['source']}｜"
                f"條次："
                f"{rule['required_actions']['section']}"
            )

            st.write(
                rule["required_actions"]["text"]
            )

            st.subheader("處理期限")

            st.caption(
                f"來源：{rule['deadline']['source']}｜"
                f"條次：{rule['deadline']['section']}"
            )

            st.write(
                rule["deadline"]["text"]
            )

        else:
            st.warning(
                "找不到對應規章，請人工確認。"
            )

    # ========================================================
    # Excel輸出及重新查詢按鈕
    # ========================================================

    st.divider()

    button_column_1, button_column_2 = st.columns(2)

    # 只有按這個按鈕，才會呼叫generate_report()
    if button_column_1.button(
        "輸出Excel報告",
        type="primary",
        use_container_width=True,
    ):
        try:
            archive_location = report.generate_report(
                trader_id=result["trader_id"],
                query_date=result["query_date"],
            )

            st.success(
                f"Excel報告已輸出："
                f"{archive_location}"
            )

        except Exception as error:
            st.error(
                f"輸出Excel時發生錯誤：{error}"
            )

    # 清除目前顯示的查詢結果
    if button_column_2.button(
        "清除查詢結果",
        use_container_width=True,
    ):
        st.session_state.report_result = None
        st.rerun()