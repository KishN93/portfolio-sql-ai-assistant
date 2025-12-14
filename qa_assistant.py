from db_queries import (
    get_nav_row_for_date,
    get_price_pnl_contributions,
    get_cash_change,
    get_nav_series,
    get_holding_for_date,
)
from rule_engine import detect_big_nav_moves
from guardrails import extract_date, extract_ticker, get_allowed_tickers
from llm_explainer import explain_nav_move


def main():
    allowed = get_allowed_tickers()
    print("Portfolio assistant ready.")
    print("Examples:")
    print("NAV on 2025-01-13")
    print("Explain 2025-01-20")
    print("What is my holding in NVDA on 2025-01-13")
    print("Show big moves")
    print("Type quit to exit")

    while True:
        q = input("\nQuestion: ").strip()
        if q.lower() in {"quit", "exit"}:
            break

        q_lower = q.lower()
        date = extract_date(q)
        ticker = extract_ticker(q, allowed)

        if "holding" in q_lower or "shares" in q_lower or "exposure" in q_lower:
            if not date or not ticker:
                print("Please specify both a valid ticker and date.")
                continue
            row = get_holding_for_date(ticker, date)
            if row["quantity"] is None:
                print(f"No holding found for {ticker} on {date}.")
                continue
            print(
                f"On {date}, you held {row['quantity']:.0f} shares of {ticker} "
                f"at {row['price']:.2f} with a market value of {row['market_value']:,.2f}."
            )
            continue

        if "nav" in q_lower:
            if not date:
                print("Please specify a date.")
                continue
            row = get_nav_row_for_date(date)
            print(f"NAV on {date} was {row['nav']:,.2f}.")
            continue

        if "explain" in q_lower or "why" in q_lower:
            if not date:
                print("Please specify a date.")
                continue
            nav = get_nav_row_for_date(date)
            contribs = get_price_pnl_contributions(date)
            cash = get_cash_change(date)
            print(explain_nav_move(nav, contribs, cash))
            continue

        if "big" in q_lower:
            navs = get_nav_series()
            alerts = detect_big_nav_moves(navs)
            for a in alerts:
                print(
                    f"{a['nav_date']} NAV change {a['daily_change']:,.2f}"
                )
            continue

        print("I did not understand. Try again.")


if __name__ == "__main__":
    main()
