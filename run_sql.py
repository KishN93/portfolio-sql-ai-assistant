import sqlite3

conn = sqlite3.connect("portfolio.db")
cursor = conn.cursor()

query = """
WITH daily_prices AS (
    SELECT
        p.security_id,
        p.price_date,
        p.close_price,
        LAG(p.close_price) OVER (
            PARTITION BY p.security_id
            ORDER BY p.price_date
        ) AS prev_close_price
    FROM prices p
),
daily_holdings AS (
    SELECT
        h.security_id,
        h.holding_date,
        h.quantity
    FROM holdings h
)
SELECT
    s.ticker,
    h.holding_date AS pnl_date,
    h.quantity,
    dp.prev_close_price,
    dp.close_price,
    h.quantity * (dp.close_price - dp.prev_close_price) AS pnl_contribution
FROM daily_holdings h
JOIN daily_prices dp
    ON h.security_id = dp.security_id
    AND h.holding_date = dp.price_date
JOIN securities s
    ON h.security_id = s.security_id
WHERE h.holding_date = '2025-01-13'
ORDER BY pnl_contribution DESC;
"""







cursor.execute(query)

rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
