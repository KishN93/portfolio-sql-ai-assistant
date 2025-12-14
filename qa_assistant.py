import sys
from assistant import parse_intent
from db_queries import (
    get_nav_on_date,
    explain_nav_change,
    get_big_nav_moves,
    get_holding_on_date,
    get_cash_on_date,
)


def main():
    print("Portfolio assistant ready.")
    print("Examples:")
    print("NAV on 2025-01-13")
    print("Explain 2025-01-20")
    print("What is my holding in NVDA on 2025-01-13")
    print("What was cash position on 2025-01-30")
    print("Show big moves")
    print("Type quit to exit\n")

    while True:
        question = input("Question: ").strip()

        if question.lower() == "quit":
            sys.exit(0)

        try:
            intent_data = parse_intent(question)
            intent = intent_data["intent"]

            # -----------------------------
            # NAV
            # -----------------------------
            if intent == "NAV_QUERY":
                date = intent_data.get("date")
                nav = get_nav_on_date(date)
                print(f"NAV on {date}: {nav:,.2f}\n")

            # -----------------------------
            # Explain NAV move
            # -----------------------------
            elif intent == "EXPLAIN_DAY":
                date = intent_data.get("date")
                explanation = explain_nav_change(date)
                print(explanation + "\n")

            # -----------------------------
            # Big NAV moves
            # -----------------------------
            elif intent == "BIG_NAV_MOVES":
                moves = get_big_nav_moves()
                for m in moves:
                    print(m)
                print()

            # -----------------------------
            # Holdings
            # -----------------------------
            elif intent == "HOLDING_QUERY":
                ticker = intent_data.get("ticker")
                date = intent_data.get("date")
                holding = get_holding_on_date(ticker, date)
                print(
                    f"Holding in {ticker} on {date}: {holding}\n"
                )

            # -----------------------------
            # Cash
            # -----------------------------
            elif intent == "CASH_QUERY":
                date = intent_data.get("date")
                cash = get_cash_on_date(date)
                print(
                    f"Cash position on {date}: {cash:,.2f}\n"
                )

            else:
                print("I did not understand. Try again.\n")

        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
