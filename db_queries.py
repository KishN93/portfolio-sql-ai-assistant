import sqlite3
from typing import List, Dict, Any, Tuple


def _fetch_all(conn: sqlite3.Connection, query: str, params: Tuple = ()) -> List[tuple]:
    cur = conn.cursor()
    cur.execute(query, params)
    return cur.fetchall()


def get_nav_series(db_path: str = "portfolio.db") -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)

    query = """
    WITH nav_series AS (
        SELECT
            h.holding_date AS nav_date,
            SUM(h.quantity * p.close_price) + c.amount AS nav
        FROM holdings h
        JOIN prices p
            ON h.security_id = p.security_id
            AND h.holding_date = p.price_date
        JOIN cash c
            ON h.holding_date = c.cash_date
        GROUP BY h.holding_date, c.amount
    )
    SELECT
        nav_date,
        nav,
        nav - LAG(nav) OVER (ORDER BY nav_date) AS daily_change,
        (nav / LAG(nav) OVER (ORDER BY nav_date) - 1) AS daily_return
    FROM nav_series
    ORDER BY nav_date;
    """

    rows = _fetch_all(conn, query)
    conn.close()

    out = []
    for d, nav, chg, ret in rows:
        out.append({
            "nav_date": d,
            "nav": float(nav),
            "daily_change": None if chg is None else float(chg),
            "daily_return": None if ret is None else float(ret),
        })
    return out


def get_nav_row_for_date(nav_date: str, db_path: str = "portfolio.db") -> Dict[str, Any]:
    rows = get_nav_series(db_path)
    for r in rows:
        if r["nav_date"] == nav_date:
            return r
    return {"nav_date": nav_date, "nav": None, "daily_change": None, "daily_return": None}


def get_price_pnl_contributions(nav_date: str, db_path: str = "portfolio.db") -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)

    query = """
    WITH prices_lag AS (
        SELECT
            security_id,
            price_date,
            close_price,
            LAG(close_price) OVER (
                PARTITION BY security_id
                ORDER BY price_date
            ) AS prev_close
        FROM prices
    )
    SELECT
        s.ticker,
        h.quantity,
        p.prev_close,
        p.close_price,
        h.quantity * (p.close_price - p.prev_close) AS pnl
    FROM holdings h
    JOIN prices_lag p
        ON h.security_id = p.security_id
        AND h.holding_date = p.price_date
    JOIN securities s
        ON h.security_id = s.security_id
    WHERE h.holding_date = ?
    ORDER BY pnl DESC;
    """

    rows = _fetch_all(conn, query, (nav_date,))
    conn.close()

    out = []
    for t, q, prev, px, pnl in rows:
        out.append({
            "ticker": t,
            "quantity": q,
            "prev_close": prev,
            "close": px,
            "pnl": None if pnl is None else float(pnl),
        })
    return out


def get_cash_change(nav_date: str, db_path: str = "portfolio.db") -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)

    query = """
    WITH cash_lag AS (
        SELECT
            cash_date,
            amount,
            LAG(amount) OVER (ORDER BY cash_date) AS prev_amount
        FROM cash
    )
    SELECT
        amount,
        prev_amount,
        amount - prev_amount AS change
    FROM cash_lag
    WHERE cash_date = ?;
    """

    rows = _fetch_all(conn, query, (nav_date,))
    conn.close()

    if not rows:
        return {"amount": None, "prev_amount": None, "cash_change": None}

    amt, prev, chg = rows[0]
    return {
        "amount": amt,
        "prev_amount": prev,
        "cash_change": None if chg is None else float(chg),
    }


def get_holding_for_date(ticker: str, nav_date: str, db_path: str = "portfolio.db") -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)

    query = """
    SELECT
        s.ticker,
        h.quantity,
        p.close_price,
        h.quantity * p.close_price AS market_value
    FROM holdings h
    JOIN securities s
        ON h.security_id = s.security_id
    JOIN prices p
        ON h.security_id = p.security_id
        AND h.holding_date = p.price_date
    WHERE
        s.ticker = ?
        AND h.holding_date = ?;
    """

    rows = _fetch_all(conn, query, (ticker, nav_date))
    conn.close()

    if not rows:
        return {
            "ticker": ticker,
            "date": nav_date,
            "quantity": None,
            "price": None,
            "market_value": None,
        }

    t, q, px, mv = rows[0]
    return {
        "ticker": t,
        "date": nav_date,
        "quantity": float(q),
        "price": float(px),
        "market_value": float(mv),
    }
