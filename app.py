import streamlit as st

import report
from rag_llmwiki.answer import answer_rule_question


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


# ============================================================
# 建立頁籤
# ============================================================

report_tab, rule_tab = st.tabs(
    [
        "📊 風控報告查詢",
        "📚 超限規章問答",
    ]
)


# ============================================================
# 初始化 Session State
# ============================================================

# 保存風控查詢結果
if "report_result" not in st.session_state:
    st.session_state.report_result = None

# 保存自動產生的超限規章建議
if "breach_rule_result" not in st.session_state:
    st.session_state.breach_rule_result = None

# 保存自動規章查詢的錯誤訊息
if "breach_rule_error" not in st.session_state:
    st.session_state.breach_rule_error = None

# 保存使用者主動詢問的規章結果
if "manual_rule_result" not in st.session_state:
    st.session_state.manual_rule_result = None


# ============================================================
# 頁籤一：風控報告查詢
# ============================================================

with report_tab:

    st.write(
        "輸入交易員代號與查詢日期，"
        "系統將計算損益、DV01及超限狀態。"
    )

    # ========================================================
    # 查詢表單
    # ========================================================

    with st.form("risk_query_form"):

        trader_id = st.text_input(
            "交易員代號",
            placeholder="例如：TRD001",
        )

        query_date = st.date_input(
            "查詢日期",
        )

        submitted = st.form_submit_button(
            "查詢風控資料",
            type="primary",
        )

    # ========================================================
    # 執行風控查詢
    # ========================================================

    if submitted:

        trader_id = trader_id.strip().upper()

        # 每次重新查詢時，清除上一次結果
        st.session_state.report_result = None
        st.session_state.breach_rule_result = None
        st.session_state.breach_rule_error = None

        if not trader_id:
            st.warning("請輸入交易員代號。")

        else:
            try:
                # 查詢損益
                pnl_result = report.get_total_pnl(
                    trader_id=trader_id,
                    query_date=query_date,
                )

                # 查詢 DV01
                dv01_result = report.get_dv01(
                    trader_id=trader_id,
                    query_date=query_date,
                )

                # 查詢整體風控狀態
                risk_result = report.get_risk_status(
                    trader_id=trader_id,
                    query_date=query_date,
                )

                # 保存查詢結果
                st.session_state.report_result = {
                    "trader_id": trader_id,
                    "query_date": query_date,
                    "pnl": pnl_result,
                    "dv01": dv01_result,
                    "risk": risk_result,
                }

                # =================================================
                # 如果發生超限，自動建立規章問題
                # =================================================

                if risk_result["overall_breach"]:

                    breach_names = []

                    if risk_result["dv01_breach"]:
                        breach_names.append("DV01超限")

                    if risk_result["monthly_stop_loss_breach"]:
                        breach_names.append("月停損超限")

                    if risk_result["yearly_stop_loss_breach"]:
                        breach_names.append("年停損超限")

                    rule_question = (
                        "交易員發生以下風控超限："
                        f"{'、'.join(breach_names)}。"
                        "請嚴格根據檢索到的規章內容，"
                        "說明制度依據、應辦事項、"
                        "通報對象與處理期限。"
                        "如果規章沒有提到某項資訊，"
                        "請明確回答規章未說明，不要自行推測。"
                    )

                    try:
                        with st.spinner(
                            "偵測到超限，正在檢索相關規章..."
                        ):
                            rule_result = answer_rule_question(
                                question=rule_question,
                                top_k=3,
                            )

                        st.session_state.breach_rule_result = (
                            rule_result
                        )

                    except Exception as api_error:
                        st.session_state.breach_rule_error = str(
                            api_error
                        )

            except FileNotFoundError as error:
                st.error(f"找不到資料檔案：{error}")

            except ValueError as error:
                st.error(f"查詢失敗：{error}")

            except KeyError as error:
                st.error(f"Excel缺少必要欄位：{error}")

            except Exception as error:
                st.error(f"執行查詢時發生錯誤：{error}")

    # ========================================================
    # 顯示查詢結果
    # ========================================================

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

        # ====================================================
        # 整體風控狀態
        # ====================================================

        if risk["overall_breach"]:
            st.error("⚠ 整體風控狀態：不合規")

        else:
            st.success("✓ 整體風控狀態：合規")

        # ====================================================
        # 損益資訊
        # ====================================================

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

        # ====================================================
        # DV01 資訊
        # ====================================================

        st.subheader("DV01概況")

        dv01_column_1, dv01_column_2, dv01_column_3 = (
            st.columns(3)
        )

        dv01_column_1.metric(
            "Net DV01",
            f"{dv01['net_dv01']:,.0f} USD/bp",
        )

        dv01_column_2.metric(
            "實際控管DV01",
            f"{dv01['actual_control_dv01']:,.0f} USD/bp",
        )

        dv01_column_3.metric(
            "DV01授權額度",
            f"{dv01['dv01_limit']:,.0f} USD/bp",
        )

        # ====================================================
        # 風控使用率
        # ====================================================

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

        # ====================================================
        # 超限警告及規章建議
        # ====================================================

        if risk["overall_breach"]:

            st.divider()
            st.header("⚠ 超限警告通知")

            active_breaches = []

            if risk["dv01_breach"]:
                active_breaches.append(
                    {
                        "name": "DV01超限",
                        "usage": risk["dv01_usage"],
                    }
                )

            if risk["monthly_stop_loss_breach"]:
                active_breaches.append(
                    {
                        "name": "月停損超限",
                        "usage": risk[
                            "monthly_stop_loss_usage"
                        ],
                    }
                )

            if risk["yearly_stop_loss_breach"]:
                active_breaches.append(
                    {
                        "name": "年停損超限",
                        "usage": risk[
                            "yearly_stop_loss_usage"
                        ],
                    }
                )

            # 顯示超限項目
            st.subheader("超限項目")

            for breach in active_breaches:
                st.error(
                    f"{breach['name']}："
                    f"{breach['usage']:.2%}"
                )

            # 顯示 RAG + Gemini 產生的規章建議
            breach_rule_result = (
                st.session_state.breach_rule_result
            )

            breach_rule_error = (
                st.session_state.breach_rule_error
            )

            if breach_rule_result is not None:

                st.subheader("AI規章處理建議")

                st.warning(
                    breach_rule_result["answer"]
                )

                sources = breach_rule_result.get(
                    "sources",
                    [],
                )

                if sources:

                    with st.expander("查看規章來源"):

                        for number, source in enumerate(
                            sources,
                            start=1,
                        ):
                            source_title = source.get(
                                "title",
                                "未命名規章",
                            )

                            source_score = source.get(
                                "score",
                                0,
                            )

                            source_path = source.get(
                                "path",
                                "未提供來源路徑",
                            )

                            st.markdown(
                                f"**{number}. "
                                f"{source_title}**"
                            )

                            st.write(
                                f"相似度："
                                f"{source_score:.3f}"
                            )

                            st.caption(
                                f"來源檔案：{source_path}"
                            )

            elif breach_rule_error is not None:

                st.warning(
                    "目前已偵測到風控超限，"
                    "但暫時無法取得規章處理建議，"
                    "請人工確認相關規章。"
                )

                st.caption(
                    f"錯誤資訊：{breach_rule_error}"
                )

        # ====================================================
        # Excel、PDF輸出及清除按鈕
        # ====================================================

        st.divider()

        (
            button_column_1,
            button_column_2,
            button_column_3,
        ) = st.columns(3)

        # 輸出 Excel
        if button_column_1.button(
            "輸出Excel報告",
            type="primary",
            use_container_width=True,
        ):
            try:
                archive_location = report.generate_report(
                    trader_id=result["trader_id"],
                    query_date=result["query_date"],
                    save_archive=True,
                )

                st.success(
                    "Excel報告已輸出："
                    f"{archive_location}"
                )

            except Exception as error:
                st.error(
                    f"輸出Excel時發生錯誤：{error}"
                )

        # 輸出 PDF
        if button_column_2.button(
            "輸出PDF報告",
            type="primary",
            use_container_width=True,
        ):
            try:
                pdf_location = (
                    report.generate_pdf_report(
                        trader_id=result["trader_id"],
                        query_date=result["query_date"],
                        save_archive=True,
                    )
                )

                st.success(
                    f"PDF報告已輸出：{pdf_location}"
                )

            except Exception as error:
                st.error(
                    f"輸出PDF時發生錯誤：{error}"
                )

        # 清除查詢結果
        if button_column_3.button(
            "清除查詢結果",
            use_container_width=True,
        ):
            st.session_state.report_result = None
            st.session_state.breach_rule_result = None
            st.session_state.breach_rule_error = None

            st.rerun()


# ============================================================
# 頁籤二：超限規章問答
# ============================================================

with rule_tab:

    st.subheader("超限規章問答")

    st.write(
        "可詢問DV01、停損、超限處理、"
        "通報流程及處理期限等規章問題。"
    )

    with st.form("rule_question_form"):

        rule_question = st.text_area(
            "規章問題",
            placeholder=(
                "例如：DV01超限後應該如何處理？"
            ),
            height=120,
        )

        ask_rule_button = st.form_submit_button(
            "查詢規章",
            type="primary",
        )

    # ========================================================
    # 執行規章問答
    # ========================================================

    if ask_rule_button:

        rule_question = rule_question.strip()

        if not rule_question:
            st.warning("請輸入規章問題。")

        else:
            try:
                with st.spinner(
                    "正在檢索規章並產生回答..."
                ):
                    manual_rule_result = (
                        answer_rule_question(
                            question=rule_question,
                            top_k=3,
                        )
                    )

                st.session_state.manual_rule_result = (
                    manual_rule_result
                )

            except Exception as error:
                st.session_state.manual_rule_result = None

                st.error(
                    f"規章查詢時發生錯誤：{error}"
                )

    # ========================================================
    # 顯示規章問答結果
    # ========================================================

    manual_rule_result = (
        st.session_state.manual_rule_result
    )

    if manual_rule_result is not None:

        st.divider()
        st.subheader("AI規章回答")

        st.write(
            manual_rule_result["answer"]
        )

        manual_sources = manual_rule_result.get(
            "sources",
            [],
        )

        if manual_sources:

            st.subheader("參考來源")

            for number, source in enumerate(
                manual_sources,
                start=1,
            ):
                source_title = source.get(
                    "title",
                    "未命名規章",
                )

                source_score = source.get(
                    "score",
                    0,
                )

                source_path = source.get(
                    "path",
                    "未提供來源路徑",
                )

                with st.expander(
                    f"{number}. {source_title}"
                ):
                    st.write(
                        f"相似度："
                        f"{source_score:.3f}"
                    )

                    st.caption(
                        f"來源檔案：{source_path}"
                    )

        else:
            st.warning(
                "沒有找到足夠相關的規章來源，"
                "請人工確認。"
            )