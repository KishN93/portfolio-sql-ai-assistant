import streamlit as st
import sqlite3
import pandas as pd

from db_queries import (
    get_nav_on_date,
    get_portfolio_breakdown,
    get_nav_between_dates,
    get_nav_timeseries,
    get_nav_daily_table,
    get_holding_on_date,
    get_cash_on_date,
    get_cash_timeseries,
    explain_cash_change,
)

DB_PATH = "portfolio.db"


def get_available_dates():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT DISTINCT holding_date FROM holdings ORDER BY holding_date", conn
    )
    conn.close()
    return df["holding_date"].tolist()


def get_tickers():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT ticker FROM securities ORDER BY ticker", conn)
    conn.close()
    return df["ticker"].tolist()


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="AVI Portfolio Analytics Dashboard",
    layout="wide",
)

st.title("AVI Portfolio Analytics Dashboard")
st.caption(
    "Internal portfolio analytics and monitoring tool designed to support "
    "investment and operations teams with transparent, auditable insights."
)

st.divider()

# -----------------------------
# Load core data safely
# -----------------------------
dates = get_available_dates()
tickers = get_tickers()

if not dates:
    st.error(
        "No portfolio data available. Please ensure the database is loaded successfully."
    )
    st.stop()

# -----------------------------
# Sidebar navigation
# -----------------------------
st.sidebar.header("Navigation")

section = st.sidebar.radio(
    "Select analysis",
    [
        "Portfolio Overview",
        "NAV Analysis",
        "Holdings",
        "Cash Analysis",
    ],
)

# -----------------------------
# Portfolio Overview
# -----------------------------
if section == "Portfolio Overview":
    st.subheader("Portfolio Overview")

    date = st.selectbox("Select date", dates, index=len(dates) - 1)

    if date is None:
        st.warning("Please select a valid date.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        nav = get_nav_on_date(date)
        st.metric("Portfolio NAV", f"{nav:,.2f}")

    with col2:
        cash = get_cash_on_date(date)
        st.metric("Cash Balance", f"{cash:,.2f}")

    st.markdown("### Portfolio Breakdown")

    breakdown = get_portfolio_breakdown(date)
    breakdown["Contribution (%)"] = (
        breakdown["market_value"] / breakdown["market_value"].sum()
    )

    st.dataframe(
        breakdown.style.format(
            {
                "close_price": "{:,.2f}",
                "market_value": "{:,.2f}",
                "Contribution (%)": "{:.2%}",
            }
        ),
        use_container_width=True,
    )

# -----------------------------
# NAV Analysis
# -----------------------------
elif section == "NAV Analysis":
    st.subheader("NAV Analysis")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.selectbox("Start date", dates, index=0)

    with col2:
        end_date = st.selectbox("End date", dates, index=len(dates) - 1)

    if start_date is None or end_date is None:
        st.warning("Please select both a start and end date.")
        st.stop()

    if st.button("Analyse NAV"):
        nav_start, nav_end, change = get_nav_between_dates(start_date, end_date)

        st.metric("NAV Change", f"{change:,.2f}")

        nav_ts = get_nav_timeseries(start_date, end_date)
        nav_ts["date"] = pd.to_datetime(nav_ts["date"])

        st.markdown("### NAV Over Time")
        st.line_chart(nav_ts.set_index("date")["nav"], use_container_width=True)

        st.markdown("### Daily NAV Detail")
        nav_table = get_nav_daily_table(start_date, end_date)

        st.dataframe(
            nav_table.style.format(
                {
                    "nav": "{:,.2f}",
                    "daily_change": "{:,.2f}",
                }
            ),
            use_container_width=True,
        )

# -----------------------------
# Holdings
# -----------------------------
elif section == "Holdings":
    st.subheader("Holdings Analysis")

    col1, col2 = st.columns(2)

    with col1:
        ticker = st.selectbox("Select security", tickers)

    with col2:
        date = st.selectbox("Select date", dates)

    if ticker is None or date is None:
        st.warning("Please select both a security and a date.")
        st.stop()

    if st.button("Show Holding"):
        quantity = get_holding_on_date(ticker, date)
        st.metric(f"Holding in {ticker}", f"{quantity:,} shares")

# -----------------------------
# Cash Analysis
# -----------------------------
elif section == "Cash Analysis":
    st.subheader("Cash Analysis")

    cash_ts = get_cash_timeseries()
    cash_ts["date"] = pd.to_datetime(cash_ts["date"])

    st.markdown("### Cash Balance Over Time")
    st.line_chart(cash_ts.set_index("date")["amount"], use_container_width=True)

    st.markdown("### Daily Cash Movements")
    st.dataframe(
        cash_ts.style.format(
            {
                "amount": "{:,.2f}",
                "daily_change": "{:,.2f}",
            }
        ),
        use_container_width=True,
    )

    st.markdown("### Explain Cash Change")

    date = st.selectbox(
        "Select date", cash_ts["date"].dt.strftime("%Y-%m-%d").tolist()
    )

    if date is None:
        st.warning("Please select a valid date.")
        st.stop()

    explanation = explain_cash_change(date)
    st.text(explanation)
