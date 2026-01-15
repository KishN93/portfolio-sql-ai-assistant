import sqlite3
import pandas as pd


# ==============================
# Configuration
# ==============================
MAX_POSITION_SIZE = 100000  # sanity limit


# ==============================
# Helper functions
# ==============================
def normalise_date_column(df, column_name):
    df[column_name] = pd.to_datetime(
        df[column_name],
        format="mixed",
        dayfirst=True,
        errors="raise"
    ).dt.strftime("%Y-%m-%d")
    return df


def validate_holdings(df):
    errors = []

    for idx, row in df.iterrows():
        date = row.get("holding_date")
        sec = row.get("security_id")
        qty = row.get("quantity")

        if pd.isna(qty):
            errors.append(
                f"Missing quantity for security_id {sec} on {date}"
            )
        elif qty <= 0:
            errors.append(
                f"Invalid quantity ({qty}) for security_id {sec} on {date}"
            )
        elif qty > MAX_POSITION_SIZE:
            errors.append(
                f"Unusually large quantity ({qty}) for security_id {sec} on {date}"
            )

    if errors:
        msg = (
            "Holdings validation failed.\n\n"
            "The following issues were found:\n"
            + "\n".join(f"• {e}" for e in errors)
            + "\n\nPlease correct the Excel file and re-upload."
        )
        raise ValueError(msg)


def validate_prices(df):
    if (df["close_price"] <= 0).any():
        raise ValueError(
            "Prices validation failed.\n\n"
            "Close prices must be greater than zero.\n"
            "Please correct the Excel file and re-upload."
        )


def validate_cash(df):
    if (df["amount"] < 0).any():
        raise ValueError(
            "Cash validation failed.\n\n"
            "Cash balances cannot be negative.\n"
            "Please correct the Excel file and re-upload."
        )


# ==============================
# Main load process
# ==============================
def main(excel_file="portfolio_data_extended.xlsx"):
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.executescript("""
    DROP TABLE IF EXISTS prices;
    DROP TABLE IF EXISTS holdings;
    DROP TABLE IF EXISTS cash;
    DROP TABLE IF EXISTS securities;
    """)

    cursor.executescript("""
    CREATE TABLE securities (
        security_id INTEGER PRIMARY KEY,
        ticker TEXT NOT NULL UNIQUE,
        security_name TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        currency TEXT NOT NULL
    );

    CREATE TABLE prices (
        price_date TEXT NOT NULL,
        security_id INTEGER NOT NULL,
        close_price REAL NOT NULL CHECK (close_price > 0),
        PRIMARY KEY (price_date, security_id),
        FOREIGN KEY (security_id) REFERENCES securities(security_id)
    );

    CREATE TABLE holdings (
        holding_date TEXT NOT NULL,
        security_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        PRIMARY KEY (holding_date, security_id),
        FOREIGN KEY (security_id) REFERENCES securities(security_id)
    );

    CREATE TABLE cash (
        cash_date TEXT PRIMARY KEY,
        currency TEXT NOT NULL,
        amount REAL NOT NULL CHECK (amount >= 0)
    );
    """)

    securities_df = pd.read_excel(excel_file, sheet_name="securities")
    prices_df = pd.read_excel(excel_file, sheet_name="prices")
    holdings_df = pd.read_excel(excel_file, sheet_name="holdings")
    cash_df = pd.read_excel(excel_file, sheet_name="cash")

    prices_df = normalise_date_column(prices_df, "price_date")
    holdings_df = normalise_date_column(holdings_df, "holding_date")
    cash_df = normalise_date_column(cash_df, "cash_date")

    validate_prices(prices_df)
    validate_holdings(holdings_df)
    validate_cash(cash_df)

    securities_df.to_sql("securities", conn, if_exists="append", index=False)
    prices_df.to_sql("prices", conn, if_exists="append", index=False)
    holdings_df.to_sql("holdings", conn, if_exists="append", index=False)
    cash_df.to_sql("cash", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
