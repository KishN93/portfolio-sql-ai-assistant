import sqlite3
import pandas as pd

DB_PATH = "portfolio.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_nav_on_date(date):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT
        SUM(h.quantity * p.close_price) + c.amount AS nav
    FROM holdings h
    JOIN prices p
        ON h.security_id = p.security_id
        AND h.holding_date = p.price_date
    JOIN cash c
        ON c.cash_date = h.holding_date
    WHERE h.holding_date = ?
    """

    cursor.execute(query, (date,))
    row = cursor.fetchone()
    conn.close()

    if row is None or row[0] is None:
        raise ValueError(f"No NAV data found for {date}")

    return row[0]


def get_portfolio_breakdown(date):
    conn = get_connection()

    query = """
    SELECT
        s.ticker,
        s.security_name,
        h.quantity,
        p.close_price,
        h.quantity * p.close_price AS market_value
    FROM holdings h
    JOIN prices p
        ON h.security_id = p.security_id
        AND h.holding_date = p.price_date
    JOIN securities s
        ON s.security_id = h.security_id
    WHERE h.holding_date = ?
    ORDER BY market_value DESC
    """

    df = pd.read_sql(query, conn, params=(date,))
    conn.close()
    return df


def get_nav_between_dates(start_date, end_date):
    nav_start = get_nav_on_date(start_date)
    nav_end = get_nav_on_date(end_date)
    change = nav_end - nav_start
    return nav_start, nav_end, change


def get_nav_timeseries(start_date, end_date):
    conn = get_connection()

    query = """
    SELECT
        h.holding_date AS date,
        SUM(h.quantity * p.close_price) + c.amount AS nav
    FROM holdings h
    JOIN prices p
        ON h.security_id = p.security_id
        AND h.holding_date = p.price_date
    JOIN cash c
        ON c.cash_date = h.holding_date
    WHERE h.holding_date BETWEEN ? AND ?
    GROUP BY h.holding_date
    ORDER BY h.holding_date
    """

    df = pd.read_sql(query, conn, params=(start_date, end_date))
    conn.close()
    return df


def get_nav_daily_table(start_date, end_date):
    conn = get_connection()

    query = """
    WITH daily_nav AS (
        SELECT
            h.holding_date AS date,
            SUM(h.quantity * p.close_price) + c.amount AS nav
        FROM holdings h
        JOIN prices p
            ON h.security_id = p.security_id
            AND h.holding_date = p.price_date
        JOIN cash c
            ON c.cash_date = h.holding_date
        WHERE h.holding_date BETWEEN ? AND ?
        GROUP BY h.holding_date
    )
    SELECT
        date,
        nav,
        nav - LAG(nav) OVER (ORDER BY date) AS daily_change
    FROM daily_nav
    ORDER BY date
    """

    df = pd.read_sql(query, conn, params=(start_date, end_date))
    conn.close()
    return df


def get_holding_on_date(ticker, date):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT h.quantity
    FROM holdings h
    JOIN securities s
        ON h.security_id = s.security_id
    WHERE s.ticker = ?
      AND h.holding_date = ?
    """

    cursor.execute(query, (ticker, date))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"No holding found for {ticker} on {date}")

    return row[0]


def get_cash_on_date(date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT amount FROM cash WHERE cash_date = ?",
        (date,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"No cash data found for {date}")

    return row[0]


def get_cash_timeseries():
    conn = get_connection()

    query = """
    SELECT
        cash_date AS date,
        amount,
        amount - LAG(amount) OVER (ORDER BY cash_date) AS daily_change
    FROM cash
    ORDER BY cash_date
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df


def explain_cash_change(date):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT
        cash_date,
        amount,
        amount - LAG(amount) OVER (ORDER BY cash_date) AS cash_change
    FROM cash
    WHERE cash_date = ?
    """

    cursor.execute(query, (date,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"No cash data found for {date}")

    cash_date, amount, change = row

    if change is None:
        return f"Cash on {cash_date}: {amount:,.2f}. This is the first available date."

    direction = "decreased" if change < 0 else "increased"

    return (
        f"Cash {direction} on {cash_date}.\n"
        f"Ending balance: {amount:,.2f}\n"
        f"Daily change: {change:,.2f}"
    )
