from datetime import datetime
import report

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
        "generate_report",
    ]

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

    trader_id = input("請輸入交易員代號，例如 TRD001：").strip().upper()
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

            question_upper = question.upper()

            
            try:
                    # 查詢超限狀態
                    if ("超限" in question
                        or "預警" in question
                        or "合規" in question
                        or "風控狀態" in question):
                        result = report.get_risk_status(
                            trader_id=trader_id,
                            query_date=query_date,)

                        print("\n【風控超限查詢結果】")
                        print(f"交易員：{result['trader_name']} ({result['trader_id']})")

                        print(
                            f"DV01 使用率：{result['dv01_usage']:.2%} "
                            f"（{'超限' if result['dv01_breach'] else '正常'}）"
                        )

                        print(
                            f"月停損使用率：{result['monthly_stop_loss_usage']:.2%} "
                            f"（{'超限' if result['monthly_stop_loss_breach'] else '正常'}）"
                        )

                        print(
                            f"年停損使用率：{result['yearly_stop_loss_usage']:.2%} "
                            f"（{'超限' if result['yearly_stop_loss_breach'] else '正常'}）"
                        )

                        if result["overall_breach"]:
                            print("\n⚠ 風控狀態：超限預警")
                            print("至少一項使用率超過 100%。")
                        else:
                            print("\n風控狀態：正常")
                            print("目前沒有任何指標超過 100%。")

                    # 查詢 DV01
                    elif "DV01" in question_upper:
                        result = report.get_dv01(
                            trader_id=trader_id,
                            query_date=query_date,)

                        print("\n【DV01 查詢結果】")
                        print(f"Net DV01：{result['net_dv01']:,.0f} USD/bp")
                        print(f"實際控管 DV01：{result['actual_control_dv01']:,.0f} USD/bp")
                        print(f"DV01 授權額度：{result['dv01_limit']:,.0f} USD/bp")
                        print(f"DV01 使用率：{result['dv01_usage']:.2%}")
                        print(f"DV01 控管狀態：{result['dv01_control_status']}")

                    # 查詢損益
                    elif "總損益" in question or "損益" in question or "PNL" in question_upper:
                        result = report.get_total_pnl(
                            trader_id=trader_id,
                            query_date=query_date,
                        )

                        print("\n【損益查詢結果】")
                        print(f"交易員：{result['trader_name']} ({result['trader_id']})")
                        print(f"當日損益：{result['total_daily_pnl']:,.0f} USD")
                        print(f"本月累計損益：{result['total_mtd_pnl']:,.0f} USD")
                        print(f"年累計損益：{result['total_ytd_pnl']:,.0f} USD")

                    else:
                        print(
                            "目前支援：\n"
                            "1. 損益\n"
                            "2. DV01\n"
                            "3. 超限\n"
                            "4. 產生完整風控報告"
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