import sqlite3
import pandas as pd

# Connect to SQLite (creates the database file)
conn = sqlite3.connect("portfolio.db")
cursor = conn.cursor()

# Enforce foreign key rules
cursor.execute("PRAGMA foreign_keys = ON;")

# Drop tables if re running
cursor.executescript("""
DROP TABLE IF EXISTS prices;
DROP TABLE IF EXISTS holdings;
DROP TABLE IF EXISTS cash;
DROP TABLE IF EXISTS securities;
""")

# Create tables with data quality rules
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

# Load Excel data
excel_file = "portfolio_data_extended.xlsx"

securities_df = pd.read_excel(excel_file, sheet_name="securities")
prices_df = pd.read_excel(excel_file, sheet_name="prices")
holdings_df = pd.read_excel(excel_file, sheet_name="holdings")
cash_df = pd.read_excel(excel_file, sheet_name="cash")

# Insert into database
securities_df.to_sql("securities", conn, if_exists="append", index=False)
prices_df.to_sql("prices", conn, if_exists="append", index=False)
holdings_df.to_sql("holdings", conn, if_exists="append", index=False)
cash_df.to_sql("cash", conn, if_exists="append", index=False)

conn.commit()
conn.close()

print("Database created and Excel data loaded successfully.")
