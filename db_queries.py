import sqlite3
import pandas as pd

DB_PATH = "portfolio.db"


def _read_sql(query, params=None):
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(query, conn, params=params or [])
    finally:
        conn.close()
    return df


def get_date_range():
    df = _read_sql(
        """
        SELECT
            MIN(holding_date) AS min_date,
            MAX(holding_date) AS max_date
        FROM holdings;
        """
    )
    if df.empty:
        return None, None
    return df.loc[0, "min_date"], df.loc[0, "max_date"]


def get_row_counts():
    df = _read_sql(
        """
        SELECT 'securities' AS table_name, COUNT(*) AS row_count FROM securities
        UNION ALL
        SELECT 'prices' AS table_name, COUNT(*) AS row_count FROM prices
        UNION ALL
        SELECT 'holdings' AS table_name, COUNT(*) AS row_count FROM holdings
        UNION ALL
        SELECT 'cash' AS table_name, COUNT(*) AS row_count FROM cash;
        """
    )
    return df


def get_available_holding_dates():
    df = _read_sql(
        """
        SELECT DISTINCT holding_date AS date
        FROM holdings
        ORDER BY holding_date;
        """
    )
    return df["date"].tolist()


def get_available_tickers():
    df = _read_sql(
        """
        SELECT ticker
        FROM securities
        ORDER BY ticker;
        """
    )
    return df["ticker"].tolist()


def get_nav_timeseries(start_date=None, end_date=None):
    filters_h = []
    filters_c = []
    params = []

    if start_date:
        filters_h.append("h.holding_date >= ?")
        filters_c.append("c.cash_date >= ?")
        params.append(start_date)

    if end_date:
        filters_h.append("h.holding_date <= ?")
        filters_c.append("c.cash_date <= ?")
        params.append(end_date)

    where_h = ""
    where_c = ""
    if filters_h:
        where_h = "WHERE " + " AND ".join(filters_h)
    if filters_c:
        where_c = "WHERE " + " AND ".join(filters_c)

    # IMPORTANT:
    # If we filter both holdings and cash, the SQL has placeholders twice.
    # So we must provide params twice: holdings params + cash params
    params_all = params + params

    df = _read_sql(
        f"""
        WITH sec_mv AS (
            SELECT
                h.holding_date AS date,
                SUM(h.quantity * p.close_price) AS securities_value
            FROM holdings h
            JOIN prices p
                ON p.security_id = h.security_id
               AND p.price_date = h.holding_date
            {where_h}
            GROUP BY h.holding_date
        ),
        cash_mv AS (
            SELECT
                c.cash_date AS date,
                c.amount AS cash_value
            FROM cash c
            {where_c}
        )
        SELECT
            s.date AS date,
            ROUND(s.securities_value + COALESCE(c.cash_value, 0), 2) AS nav
        FROM sec_mv s
        LEFT JOIN cash_mv c
            ON c.date = s.date
        ORDER BY s.date;
        """,
        params=params_all,
    )

    return df


def get_nav_on_date(date):
    df = get_nav_timeseries(date, date)
    if df.empty:
        raise ValueError(f"No NAV data found for {date}")
    return float(df.loc[0, "nav"])


def get_nav_between_dates(start_date, end_date):
    ts = get_nav_timeseries(start_date, end_date)
    if ts.empty:
        raise ValueError("No NAV data found for the selected range")

    nav_start = float(ts.iloc[0]["nav"])
    nav_end = float(ts.iloc[-1]["nav"])
    change = nav_end - nav_start
    return nav_start, nav_end, change


def get_nav_daily_table(start_date=None, end_date=None):
    ts = get_nav_timeseries(start_date, end_date)
    if ts.empty:
        return pd.DataFrame(columns=["date", "nav", "daily_change"])

    ts = ts.copy()
    ts["daily_change"] = ts["nav"].diff().fillna(0.0)
    ts["nav"] = ts["nav"].astype(float)
    ts["daily_change"] = ts["daily_change"].astype(float)
    return ts


def get_portfolio_breakdown(date):
    df = _read_sql(
        """
        SELECT
            s.ticker AS ticker,
            s.security_name AS security_name,
            s.asset_class AS asset_class,
            h.quantity AS quantity,
            p.close_price AS close_price,
            ROUND(h.quantity * p.close_price, 2) AS market_value
        FROM holdings h
        JOIN securities s
            ON s.security_id = h.security_id
        JOIN prices p
            ON p.security_id = h.security_id
           AND p.price_date = h.holding_date
        WHERE h.holding_date = ?
        ORDER BY market_value DESC;
        """,
        params=[date],
    )
    if df.empty:
        raise ValueError(f"No holdings or prices found for {date}")
    df["market_value"] = df["market_value"].astype(float)
    total = float(df["market_value"].sum())
    df["weight"] = df["market_value"] / total if total != 0 else 0.0
    return df


def get_holding_on_date(ticker, date):
    df = _read_sql(
        """
        SELECT
            h.quantity AS quantity
        FROM holdings h
        JOIN securities s
            ON s.security_id = h.security_id
        WHERE s.ticker = ?
          AND h.holding_date = ?;
        """,
        params=[ticker, date],
    )
    if df.empty:
        raise ValueError(f"No holding found for {ticker} on {date}")
    return int(df.loc[0, "quantity"])


def get_cash_on_date(date):
    df = _read_sql(
        """
        SELECT amount
        FROM cash
        WHERE cash_date = ?;
        """,
        params=[date],
    )
    if df.empty:
        raise ValueError(f"No cash found for {date}")
    return float(df.loc[0, "amount"])


def get_cash_timeseries():
    df = _read_sql(
        """
        SELECT
            cash_date AS date,
            amount
        FROM cash
        ORDER BY cash_date;
        """
    )
    if df.empty:
        return pd.DataFrame(columns=["date", "amount", "daily_change"])
    df["amount"] = df["amount"].astype(float)
    df["daily_change"] = df["amount"].diff().fillna(0.0)
    return df


def explain_cash_change(date):
    cash_ts = get_cash_timeseries()
    if cash_ts.empty:
        return "No cash data available."

    row = cash_ts[cash_ts["date"] == date]
    if row.empty:
        return f"No cash data found for {date}"

    amount = float(row.iloc[0]["amount"])
    change = float(row.iloc[0]["daily_change"])

    if change > 0:
        direction = "increased"
    elif change < 0:
        direction = "decreased"
    else:
        direction = "was unchanged"

    return f"Cash on {date} was {amount:,.2f} and {direction} by {change:,.2f} versus the prior day."


def get_missing_prices():
    df = _read_sql(
        """
        SELECT
            h.holding_date AS date,
            s.ticker AS ticker
        FROM holdings h
        JOIN securities s
            ON s.security_id = h.security_id
        LEFT JOIN prices p
            ON p.security_id = h.security_id
           AND p.price_date = h.holding_date
        WHERE p.close_price IS NULL
        ORDER BY h.holding_date, s.ticker;
        """
    )
    return df


def get_missing_holdings():
    df = _read_sql(
        """
        SELECT
            p.price_date AS date,
            s.ticker AS ticker
        FROM prices p
        JOIN securities s
            ON s.security_id = p.security_id
        LEFT JOIN holdings h
            ON h.security_id = p.security_id
           AND h.holding_date = p.price_date
        WHERE h.quantity IS NULL
        ORDER BY p.price_date, s.ticker;
        """
    )
    return df


def get_missing_cash_dates():
    df = _read_sql(
        """
        SELECT
            d.date AS date
        FROM (
            SELECT DISTINCT holding_date AS date
            FROM holdings
        ) d
        LEFT JOIN cash c
            ON c.cash_date = d.date
        WHERE c.cash_date IS NULL
        ORDER BY d.date;
        """
    )
    return df


def get_nav_returns_series(start_date=None, end_date=None):
    ts = get_nav_timeseries(start_date, end_date)
    if ts.empty:
        return pd.DataFrame(columns=["date", "nav", "return"])
    ts = ts.copy()
    ts["return"] = ts["nav"].pct_change().fillna(0.0)
    return ts


def compute_top_holdings_table(date, top_n=10):
    df = get_portfolio_breakdown(date).copy()
    df = df.sort_values("weight", ascending=False).head(top_n)
    return df


def compute_period_returns(asof_date):
    ts = get_nav_timeseries()
    if ts.empty:
        return {}

    ts = ts.copy()
    ts["date"] = pd.to_datetime(ts["date"])
    ts = ts.sort_values("date").set_index("date")

    asof = pd.to_datetime(asof_date)
    if asof not in ts.index:
        return {}

    nav_asof = float(ts.loc[asof, "nav"])

    def _closest_on_or_before(target_date):
        eligible = ts.loc[:target_date]
        if eligible.empty:
            return None
        return eligible.index[-1]

    results = {}

    start_of_month = asof.replace(day=1)
    start_of_year = asof.replace(month=1, day=1)

    anchors = {
        "MTD": _closest_on_or_before(start_of_month),
        "YTD": _closest_on_or_before(start_of_year),
        "1W": _closest_on_or_before(asof - pd.Timedelta(days=7)),
        "1M": _closest_on_or_before(asof - pd.Timedelta(days=30)),
        "3M": _closest_on_or_before(asof - pd.Timedelta(days=90)),
    }

    for label, anchor_date in anchors.items():
        if anchor_date is None or anchor_date == asof:
            results[label] = None
            continue
        nav_anchor = float(ts.loc[anchor_date, "nav"])
        results[label] = (nav_asof / nav_anchor) - 1.0

    return results
