import sqlite3


DB_PATH = "portfolio.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# -----------------------------
# NAV on a specific date
# -----------------------------
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
    result = cursor.fetchone()
    conn.close()

    if result is None or result[0] is None:
        raise ValueError(f"No NAV data found for {date}")

    return result[0]


# -----------------------------
# Explain NAV change for a date
# -----------------------------
def explain_nav_change(date):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    WITH daily_nav AS (
        SELECT
            h.holding_date AS nav_date,
            SUM(h.quantity * p.close_price) + c.amount AS nav
        FROM holdings h
        JOIN prices p
            ON h.security_id = p.security_id
            AND h.holding_date = p.price_date
        JOIN cash c
            ON c.cash_date = h.holding_date
        GROUP BY h.holding_date
    )
    SELECT
        nav_date,
        nav,
        nav - LAG(nav) OVER (ORDER BY nav_date) AS nav_change
    FROM daily_nav
    WHERE nav_date = ?
    """

    cursor.execute(query, (date,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"No NAV data available for {date}")

    nav_date, nav, nav_change = row

    if nav_change is None:
        return f"NAV on {nav_date}: {nav:,.2f}. No prior day for comparison."

    pct_change = nav_change / (nav - nav_change)

    explanation = (
        f"**Buy Side Commentary — {nav_date}**\n\n"
        f"NAV declined to {nav:,.2f}.\n"
        f"Daily change was {nav_change:,.2f} ({pct_change:.2%})."
    )

    return explanation


# -----------------------------
# Big NAV moves
# -----------------------------
def get_big_nav_moves(threshold=0.03):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    WITH daily_nav AS (
        SELECT
            h.holding_date AS nav_date,
            SUM(h.quantity * p.close_price) + c.amount AS nav
        FROM holdings h
        JOIN prices p
            ON h.security_id = p.security_id
            AND h.holding_date = p.price_date
        JOIN cash c
            ON c.cash_date = h.holding_date
        GROUP BY h.holding_date
    ),
    nav_changes AS (
        SELECT
            nav_date,
            nav,
            nav - LAG(nav) OVER (ORDER BY nav_date) AS daily_change,
            (nav - LAG(nav) OVER (ORDER BY nav_date))
                / LAG(nav) OVER (ORDER BY nav_date) AS daily_return
        FROM daily_nav
    )
    SELECT nav_date, nav, daily_return, daily_change
    FROM nav_changes
    WHERE ABS(daily_return) >= ?
    """

    cursor.execute(query, (threshold,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "type": "BIG_NAV_MOVE",
            "nav_date": r[0],
            "nav": r[1],
            "daily_return": r[2],
            "daily_change": r[3],
        })

    return results


# -----------------------------
# Holdings on a specific date
# -----------------------------
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


# -----------------------------
# Cash on a specific date
# -----------------------------
def get_cash_on_date(date):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT amount
    FROM cash
    WHERE cash_date = ?
    """

    cursor.execute(query, (date,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"No cash data found for {date}")

    return row[0]
