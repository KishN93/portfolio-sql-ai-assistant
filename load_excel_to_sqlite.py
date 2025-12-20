import sqlite3
import pandas as pd
import sys


def normalise_date_column(df, column_name):
    df[column_name] = pd.to_datetime(
        df[column_name],
        errors="raise",
        format="mixed"
    ).dt.strftime("%Y-%m-%d")
    return df


def validate_prices(prices_df):
    df = prices_df.sort_values(["security_id", "price_date"]).copy()

    df["prev_price"] = df.groupby("security_id")["close_price"].shift(1)
    df["price_move_pct"] = (
        (df["close_price"] - df["prev_price"]) / df["prev_price"]
    )

    extreme_moves = df[df["price_move_pct"].abs() > 0.5]

    if not extreme_moves.empty:
        raise ValueError(
            "Price fat finger detected. Extreme price moves:\n"
            + extreme_moves[
                ["security_id", "price_date", "close_price", "prev_price", "price_move_pct"]
            ].to_string(index=False)
        )

    # Return ONLY valid columns
    return prices_df[["price_date", "security_id", "close_price"]]


# -----------------------------
# Read Excel path from argument
# -----------------------------
if len(sys.argv) < 2:
    raise ValueError("No Excel file path provided.")

excel_file = sys.argv[1]

# -----------------------------
# Connect to SQLite
# -----------------------------
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

# -----------------------------
# Load Excel sheets
# -----------------------------
securities_df = pd.read_excel(excel_file, sheet_name="securities")
prices_df = pd.read_excel(excel_file, sheet_name="prices")
holdings_df = pd.read_excel(excel_file, sheet_name="holdings")
cash_df = pd.read_excel(excel_file, sheet_name="cash")

prices_df = normalise_date_column(prices_df, "price_date")
holdings_df = normalise_date_column(holdings_df, "holding_date")
cash_df = normalise_date_column(cash_df, "cash_date")

prices_df = validate_prices(prices_df)

# -----------------------------
# Write to database
# -----------------------------
securities_df.to_sql("securities", conn, if_exists="append", index=False)
prices_df.to_sql("prices", conn, if_exists="append", index=False)
holdings_df.to_sql("holdings", conn, if_exists="append", index=False)
cash_df.to_sql("cash", conn, if_exists="append", index=False)

conn.commit()
conn.close()

print("Database created and Excel data loaded successfully.")
