from datetime import datetime
import report
from rag_llmwiki.answer import (answer_rule_question, generate_breach_warning)

def get_trader_id():
    """
    要求使用者輸入交易員代號。
    只有交易員代號存在時，才會進入日期輸入。
    """

    while True:
        trader_id = input(
            "請輸入交易員代號，例如 TRD003："
        ).strip()

        if trader_id.lower() == "exit":
            return None

        try:
            # 直接使用 report.py 的檢查函式
            trader_id, trader_info = report.get_trader_info(trader_id)

            if "交易員姓名" in trader_info.index:
                print(f"交易員姓名：{trader_info['交易員姓名']}")

            print()
            return trader_id

        except ValueError as error:
            print(f"{error}")
            print("請重新輸入。\n")

def get_query_date():
    while True:
        date_text = input("請輸入查詢日期，例如 2026-07-08：").strip()

        try:
            datetime.strptime(date_text, "%Y-%m-%d")
            return date_text
        except ValueError:
            print("日期格式錯誤，請輸入 YYYY-MM-DD，例如 2026-07-08。")


def run_agent():

    # 確認目前載入的是哪一份 report.py
    print("目前載入的 report.py：")
    print(report.__file__)

    # 確認 report.py 的必要函式都存在
    required_functions = [
        "get_total_pnl",
        "get_dv01",
        "get_risk_status",
        "generate_report",]

    missing_functions = [
        function_name
        for function_name in required_functions
        if not hasattr(report, function_name)
    ]

    if missing_functions:
        print("report.py 缺少以下函式：" + ", ".join(missing_functions))
        return

    print("=" * 50)
    print("Fixed Income Risk Agent")
    print("=" * 50)

    trader_id = get_trader_id()
    if trader_id is None:
         print("已離開風控查詢系統。")
         return
    query_date = get_query_date()

    print()
    print(f"目前交易員：{trader_id}")
    print(f"目前查詢日期：{query_date}")

    try:
            # 產生完整報告
            report_result = report.generate_report(
                    trader_id=trader_id,
                    query_date=query_date,
                )

            print("\n報告已成功產生並歸檔:")
            print(report_result)

    except Exception as error:
        print(f"\n產生風控報告時發生錯誤:{error}")

# ========================================================
# 報告完成後開放查詢
# ========================================================
    while True:
            question = input("\n請輸入問題（輸入 exit 離開）：").strip()

            if question.lower() == "exit":
                print("Agent 已結束。")
                break

            if not question:
                print("請輸入問題。")
                continue

            question_upper = question.upper()
            rule_keywords = [
                "規章",
                "規定",
                "依據",
                "流程",
                "程序",
                "處理",
                "通報",
                "通知",
                "期限",
                "負責",
                "應該怎麼",
                "應該如何",
                "需要做什麼",
            ]

            is_rule_question = any(
                keyword in question
                for keyword in rule_keywords
            )

            
            try:
                # 1. 查詢規章、超限處理流程或通報規定
                if is_rule_question:
                    result = answer_rule_question(
                        question=question,
                        top_k=3,
                    )

                    print("\n【規章知識庫回答】")
                    print(result["answer"])

                    if result["sources"]:
                        print("\n【檢索來源】")

                        for number, source in enumerate(
                            result["sources"],
                            start=1,
                        ):
                            print(
                                f'{number}. {source["title"]} '
                                f'（相似度：{source["score"]:.3f}）'
                            )
                            print(f'   檔案：{source["path"]}')

                # 2. 查詢交易員實際超限狀態
                elif (
                    "超限" in question
                    or "預警" in question
                    or "合規" in question
                    or "風控狀態" in question
                ):
                    result = report.get_risk_status(
                        trader_id=trader_id,
                        query_date=query_date,
                    )

                    print("\n【風控超限查詢結果】")
                    print(
                        f"交易員：{result['trader_name']} "
                        f"({result['trader_id']})"
                    )

                    print(
                        f"DV01 使用率：{result['dv01_usage']:.2%} "
                        f"（{'超限' if result['dv01_breach'] else '正常'}）"
                    )

                    print(
                        f"月停損使用率："
                        f"{result['monthly_stop_loss_usage']:.2%} "
                        f"（{'超限' if result['monthly_stop_loss_breach'] else '正常'}）"
                    )

                    print(
                        f"年停損使用率："
                        f"{result['yearly_stop_loss_usage']:.2%} "
                        f"（{'超限' if result['yearly_stop_loss_breach'] else '正常'}）"
                    )

                    if result["overall_breach"]:
                        try:
                            warning_text = generate_breach_warning(result)

                            print("\n【AI 風控警告】")
                            print(warning_text)

                        except Exception as api_error:
                            print("\n⚠ 風控狀態：超限預警")
                            print("至少一項使用率超過 100%。")
                            print(f"AI 警告暫時無法生成：{api_error}")

                    else:
                        print("\n風控狀態：正常")
                        print("目前沒有任何指標超過 100%。")

                # 3. 查詢 DV01
                elif "DV01" in question_upper:
                    result = report.get_dv01(
                        trader_id=trader_id,
                        query_date=query_date,
                    )

                    print("\n【DV01 查詢結果】")
                    print(f"Net DV01：{result['net_dv01']:,.0f} USD/bp")
                    print(
                        f"實際控管 DV01："
                        f"{result['actual_control_dv01']:,.0f} USD/bp"
                    )
                    print(
                        f"DV01 授權額度："
                        f"{result['dv01_limit']:,.0f} USD/bp"
                    )
                    print(f"DV01 使用率：{result['dv01_usage']:.2%}")
                    print(f"DV01 控管狀態：{result['dv01_control_status']}")

                # 4. 查詢損益
                elif (
                    "總損益" in question
                    or "損益" in question
                    or "PNL" in question_upper
                    or "P&L" in question_upper
                ):
                    result = report.get_total_pnl(
                        trader_id=trader_id,
                        query_date=query_date,
                    )

                    print("\n【損益查詢結果】")
                    print(
                        f"交易員：{result['trader_name']} "
                        f"({result['trader_id']})"
                    )
                    print(
                        f"當日損益："
                        f"{result['total_daily_pnl']:,.0f} USD"
                    )
                    print(
                        f"本月累計損益："
                        f"{result['total_mtd_pnl']:,.0f} USD"
                    )
                    print(
                        f"年累計損益："
                        f"{result['total_ytd_pnl']:,.0f} USD"
                    )

                else:
                    print(
                        "目前支援：\n"
                        "1. 損益查詢\n"
                        "2. DV01 查詢\n"
                        "3. 超限狀態查詢\n"
                        "4. 規章與處理流程查詢"
                    )


            except FileNotFoundError as error:
                print(f"找不到資料檔案：{error}")

            except ValueError as error:
                print(f"查詢失敗：{error}")

            except KeyError as error:
                print(f"Excel 缺少必要欄位：{error}")

            except Exception as error:
                print(f"執行查詢時發生錯誤：{error}")


    if __name__ == "__main__":
            run_agent()