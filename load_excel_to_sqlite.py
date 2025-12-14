import sqlite3
import pandas as pd


# -----------------------------
# Configuration thresholds
# -----------------------------
MAX_PRICE_MOVE_PCT = 0.30     # 30 percent day-on-day move
MAX_POSITION_SIZE = 10000     # Max shares per security per day


def normalise_date_column(df, column_name):
    """
    Parse and normalise date columns to ISO format (YYYY-MM-DD).
    Handles Excel dates, ISO strings, and locale-specific strings.
    Fails fast on invalid dates.
    """
    df[column_name] = pd.to_datetime(
        df[column_name],
        format="mixed",
        dayfirst=True,
        errors="raise"
    )
    df[column_name] = df[column_name].dt.strftime("%Y-%m-%d")
    return df


def validate_prices(df):
    if (df["close_price"] <= 0).any():
        raise ValueError("Invalid price detected: prices must be > 0")

    df = df.sort_values(["security_id", "price_date"])
    df["prev_price"] = df.groupby("security_id")["close_price"].shift(1)

    df["price_move_pct"] = (df["close_price"] - df["prev_price"]) / df["prev_price"]

    extreme_moves = df[df["price_move_pct"].abs() > MAX_PRICE_MOVE_PCT]

    if not extreme_moves.empty:
        raise ValueError(
            "Price fat finger detected. Extreme price moves:\n"
            + extreme_moves[
                ["security_id", "price_date", "close_price", "prev_price", "price_move_pct"]
            ].to_string(index=False)
        )

    return df.drop(columns=["prev_price", "price_move_pct"])


def validate_holdings(df):
    if (df["quantity"] <= 0).any():
        raise ValueError("Invalid quantity detected: quantity must be > 0")

    if (df["quantity"] > MAX_POSITION_SIZE).any():
        raise ValueError(
            f"Position size exceeds maximum allowed ({MAX_POSITION_SIZE})"
        )

    if df.duplicated(subset=["holding_date", "security_id"]).any():
        raise ValueError("Duplicate holdings detected for same date and security")

    return df


def validate_cash(df):
    if (df["amount"] < 0).any():
        raise ValueError("Invalid cash amount detected: cash cannot be negative")

    if df.duplicated(subset=["cash_date"]).any():
        raise ValueError("Duplicate cash rows detected for the same date")

    return df


# -----------------------------
# Database setup
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
# Load Excel
# -----------------------------
excel_file = "portfolio_data_extended.xlsx"

securities_df = pd.read_excel(excel_file, sheet_name="securities")

prices_df = pd.read_excel(excel_file, sheet_name="prices")
prices_df = normalise_date_column(prices_df, "price_date")

holdings_df = pd.read_excel(excel_file, sheet_name="holdings")
holdings_df = normalise_date_column(holdings_df, "holding_date")

cash_df = pd.read_excel(excel_file, sheet_name="cash")
cash_df = normalise_date_column(cash_df, "cash_date")

# -----------------------------
# Validation guardrails
# -----------------------------
prices_df = validate_prices(prices_df)
holdings_df = validate_holdings(holdings_df)
cash_df = validate_cash(cash_df)

# -----------------------------
# Insert into database
# -----------------------------
securities_df.to_sql("securities", conn, if_exists="append", index=False)
prices_df.to_sql("prices", conn, if_exists="append", index=False)
holdings_df.to_sql("holdings", conn, if_exists="append", index=False)
cash_df.to_sql("cash", conn, if_exists="append", index=False)

conn.commit()
conn.close()

print("Database created and Excel data loaded successfully with full data quality guardrails.")
