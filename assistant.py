from db_queries import (
    get_nav_series,
    get_nav_row_for_date,
    get_price_pnl_contributions,
    get_cash_change,
)
from rule_engine import detect_big_nav_moves
from llm_explainer import explain_nav_move


def main():
    nav_series = get_nav_series()
    alerts = detect_big_nav_moves(nav_series)

    if not alerts:
        print("No big NAV moves detected.")
        return

    alert = sorted(alerts, key=lambda x: abs(x["daily_return"]), reverse=True)[0]
    date = alert["nav_date"]

    print("=" * 80)
    print(f"Explaining date: {date}")

    nav_row = get_nav_row_for_date(date)
    contribs = get_price_pnl_contributions(date)
    cash = get_cash_change(date)

    text = explain_nav_move(nav_row, contribs, cash)
    print(text)


if __name__ == "__main__":
    main()
