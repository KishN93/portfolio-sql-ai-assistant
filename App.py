import streamlit as st
import pandas as pd
import tempfile
import subprocess

from db_queries import (
    get_date_range,
    get_row_counts,
    get_available_holding_dates,
    get_available_tickers,
    get_nav_on_date,
    get_portfolio_breakdown,
    get_nav_timeseries,
    get_holding_on_date,
    get_cash_on_date,
    get_cash_timeseries,
    explain_cash_change,
    get_missing_prices,
    get_missing_holdings,
    get_missing_cash_dates,
    compute_top_holdings_table,
    compute_period_returns,
)


def _normalise_date_series(s):
    return pd.to_datetime(s, errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")


def _compute_nav_from_portfolio_workbook(xlsx_file_obj):
    xls = pd.ExcelFile(xlsx_file_obj)
    sheet_names_lower = [s.lower() for s in xls.sheet_names]

    required_sheets = ["prices", "holdings", "cash"]
    if not all(s in sheet_names_lower for s in required_sheets):
        raise ValueError(
            "This XLSX does not look like a portfolio workbook for NAV calc. "
            "Missing one of: prices, holdings, cash."
        )

    def _get_sheet(lower_name):
        for s in xls.sheet_names:
            if s.lower() == lower_name:
                return s
        return None

    prices = pd.read_excel(xlsx_file_obj, sheet_name=_get_sheet("prices"))
    holdings = pd.read_excel(xlsx_file_obj, sheet_name=_get_sheet("holdings"))
    cash = pd.read_excel(xlsx_file_obj, sheet_name=_get_sheet("cash"))

    prices.columns = [c.strip().lower() for c in prices.columns]
    holdings.columns = [c.strip().lower() for c in holdings.columns]
    cash.columns = [c.strip().lower() for c in cash.columns]

    for col in ["price_date", "security_id", "close_price"]:
        if col not in prices.columns:
            raise ValueError("Portfolio workbook prices sheet must include price_date, security_id, close_price.")

    for col in ["holding_date", "security_id", "quantity"]:
        if col not in holdings.columns:
            raise ValueError("Portfolio workbook holdings sheet must include holding_date, security_id, quantity.")

    for col in ["cash_date", "amount"]:
        if col not in cash.columns:
            raise ValueError("Portfolio workbook cash sheet must include cash_date and amount.")

    prices["price_date"] = _normalise_date_series(prices["price_date"])
    holdings["holding_date"] = _normalise_date_series(holdings["holding_date"])
    cash["cash_date"] = _normalise_date_series(cash["cash_date"])

    prices["security_id"] = pd.to_numeric(prices["security_id"], errors="coerce")
    holdings["security_id"] = pd.to_numeric(holdings["security_id"], errors="coerce")

    prices["close_price"] = pd.to_numeric(prices["close_price"], errors="coerce")
    holdings["quantity"] = pd.to_numeric(holdings["quantity"], errors="coerce")
    cash["amount"] = pd.to_numeric(cash["amount"], errors="coerce")

    prices = prices.dropna(subset=["price_date", "security_id", "close_price"])
    holdings = holdings.dropna(subset=["holding_date", "security_id", "quantity"])
    cash = cash.dropna(subset=["cash_date", "amount"])

    merged = holdings.merge(
        prices,
        left_on=["holding_date", "security_id"],
        right_on=["price_date", "security_id"],
        how="inner",
    )
    merged["mv"] = merged["quantity"] * merged["close_price"]

    sec_mv = merged.groupby("holding_date", as_index=False)["mv"].sum()
    sec_mv = sec_mv.rename(columns={"holding_date": "date", "mv": "securities_value"})

    cash_mv = cash.groupby("cash_date", as_index=False)["amount"].sum()
    cash_mv = cash_mv.rename(columns={"cash_date": "date", "amount": "cash_value"})

    nav = sec_mv.merge(cash_mv, on="date", how="left")
    nav["cash_value"] = nav["cash_value"].fillna(0.0)
    nav["external_nav"] = (nav["securities_value"] + nav["cash_value"]).round(2)

    nav = nav[["date", "external_nav"]].sort_values("date").dropna(subset=["date", "external_nav"])
    if nav.empty:
        raise ValueError("Could not compute NAV from the portfolio workbook. Check that dates and IDs align.")
    return nav


def _load_external_nav_file(uploaded):
    filename = uploaded.name.lower()

    if filename.endswith(".csv"):
        ext = pd.read_csv(uploaded)
        ext.columns = [c.strip().lower() for c in ext.columns]
        if "date" not in ext.columns or "nav" not in ext.columns:
            raise ValueError("External NAV CSV must include columns named date and nav.")
        ext["date"] = _normalise_date_series(ext["date"])
        ext["external_nav"] = pd.to_numeric(ext["nav"], errors="coerce")
        ext = ext.dropna(subset=["date", "external_nav"])
        ext = ext.drop_duplicates(subset=["date"], keep="last").sort_values("date")
        return ext[["date", "external_nav"]]

    if filename.endswith(".xlsx"):
        xls = pd.ExcelFile(uploaded)

        for sheet in xls.sheet_names:
            df = pd.read_excel(uploaded, sheet_name=sheet)
            df.columns = [c.strip().lower() for c in df.columns]
            if "date" in df.columns and "nav" in df.columns:
                df["date"] = _normalise_date_series(df["date"])
                df["external_nav"] = pd.to_numeric(df["nav"], errors="coerce")
                df = df.dropna(subset=["date", "external_nav"])
                df = df.drop_duplicates(subset=["date"], keep="last").sort_values("date")
                if not df.empty:
                    return df[["date", "external_nav"]]

        uploaded.seek(0)
        return _compute_nav_from_portfolio_workbook(uploaded)

    raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")


def _load_benchmark_file(uploaded):
    """
    Accept common formats:
    - date + level (preferred)
    - date + price, close, nav, value
    - date + return (daily return series)
    Adds a guard so uploading portfolio or securities data gives a clean message.
    """
    filename = uploaded.name.lower()

    if filename.endswith(".csv"):
        bench = pd.read_csv(uploaded)
    elif filename.endswith(".xlsx"):
        xls = pd.ExcelFile(uploaded)
        sheet_to_use = xls.sheet_names[0]
        bench = pd.read_excel(uploaded, sheet_name=sheet_to_use)
    else:
        raise ValueError("Unsupported benchmark file type. Upload CSV or XLSX.")

    bench.columns = [c.strip().lower() for c in bench.columns]
    cols = set(bench.columns)

    # Guard for common wrong uploads
    if {"security_id", "ticker", "security_name"}.issubset(cols):
        raise ValueError(
            "You uploaded a securities reference table or portfolio workbook sheet, not a benchmark file. "
            "Benchmark must have columns: date and level (or price, close, nav, value) or date and return."
        )

    if "date" not in cols:
        raise ValueError(
            f"Benchmark file must include a date column. Found columns: {list(bench.columns)}"
        )

    bench["date"] = pd.to_datetime(bench["date"], errors="coerce")
    bench = bench.dropna(subset=["date"]).sort_values("date")

    candidates_level = ["level", "price", "close", "nav", "value", "index"]
    candidates_return = ["return", "daily_return", "ret"]

    level_col = next((c for c in candidates_level if c in cols), None)
    return_col = next((c for c in candidates_return if c in cols), None)

    if level_col:
        bench[level_col] = pd.to_numeric(bench[level_col], errors="coerce")
        bench = bench.dropna(subset=[level_col])
        bench["benchmark_index"] = (bench[level_col] / bench[level_col].iloc[0]) * 100.0
    elif return_col:
        bench[return_col] = pd.to_numeric(bench[return_col], errors="coerce")
        bench = bench.dropna(subset=[return_col])
        bench["benchmark_index"] = (1.0 + bench[return_col]).cumprod() * 100.0
    else:
        raise ValueError(
            "Benchmark file must include either a level column (level, price, close, nav, value) "
            f"or a return column (return). Found columns: {list(bench.columns)}"
        )

    bench["date"] = bench["date"].dt.strftime("%Y-%m-%d")
    bench = bench.drop_duplicates(subset=["date"], keep="last")
    return bench[["date", "benchmark_index"]]


def _bp(x):
    return x * 10000.0


st.set_page_config(
    page_title="AVI Fund Data Controls and Analytics",
    layout="wide",
)

st.title("AVI Fund Data Controls and Analytics")
st.caption("Internal dashboard for fund data quality checks, NAV monitoring, benchmark comparison, and factsheet outputs.")

st.divider()

st.sidebar.header("Data Management")

uploaded_file = st.sidebar.file_uploader("Upload portfolio Excel file", type=["xlsx"])
if not uploaded_file:
    st.sidebar.info("Upload an Excel file to begin.")
    st.stop()

with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
    tmp.write(uploaded_file.read())
    temp_excel_path = tmp.name

try:
    subprocess.run(
        ["python", "load_excel_to_sqlite.py", temp_excel_path],
        capture_output=True,
        text=True,
        check=True,
    )
    st.sidebar.success("Portfolio data loaded successfully.")
except subprocess.CalledProcessError as e:
    st.sidebar.error("Data validation failed.")
    st.sidebar.text(e.stderr)
    st.stop()

min_date, max_date = get_date_range()
dates = get_available_holding_dates()
tickers = get_available_tickers()

if not dates:
    st.error("No valid portfolio data available after load.")
    st.stop()

st.sidebar.header("Navigation")
section = st.sidebar.radio(
    "Select section",
    [
        "Portfolio Overview",
        "Data Controls",
        "Benchmark Monitoring",
        "Factsheet Outputs",
        "Holdings",
        "Cash Analysis",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Data status")
st.sidebar.write(f"File loaded: {uploaded_file.name}")
st.sidebar.write(f"Date range: {min_date} to {max_date}")


if section == "Portfolio Overview":
    st.subheader("Portfolio Overview")
    date = st.selectbox("Select date", dates, index=len(dates) - 1)

    nav = get_nav_on_date(date)
    cash = get_cash_on_date(date)
    breakdown = get_portfolio_breakdown(date)

    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolio NAV", f"{nav:,.2f}")
    c2.metric("Cash balance", f"{cash:,.2f}")
    c3.metric("Number of holdings", f"{len(breakdown):,}")

    st.markdown("### Security breakdown")
    display_df = breakdown[["ticker", "security_name", "asset_class", "quantity", "close_price", "market_value", "weight"]]
    st.dataframe(
        display_df.style.format(
            {
                "quantity": "{:,}",
                "close_price": "{:,.2f}",
                "market_value": "{:,.2f}",
                "weight": "{:.2%}",
            }
        ),
        use_container_width=True,
    )


elif section == "Data Controls":
    st.subheader("Data Controls")

    st.markdown("### Table row counts")
    st.dataframe(get_row_counts(), use_container_width=True)

    missing_prices = get_missing_prices()
    missing_holdings = get_missing_holdings()
    missing_cash = get_missing_cash_dates()

    c1, c2, c3 = st.columns(3)
    c1.metric("Missing prices", f"{len(missing_prices):,}")
    c2.metric("Missing holdings", f"{len(missing_holdings):,}")
    c3.metric("Missing cash dates", f"{len(missing_cash):,}")

    st.markdown("### Missing prices by date and security")
    st.dataframe(missing_prices if not missing_prices.empty else pd.DataFrame({"status": ["No missing prices detected"]}), use_container_width=True)

    st.markdown("### Missing holdings by date and security")
    st.dataframe(missing_holdings if not missing_holdings.empty else pd.DataFrame({"status": ["No missing holdings detected"]}), use_container_width=True)

    st.markdown("### Missing cash dates")
    st.dataframe(missing_cash if not missing_cash.empty else pd.DataFrame({"status": ["No missing cash dates detected"]}), use_container_width=True)

    st.divider()

    st.markdown("### NAV reconciliation against an external source")
    st.caption("Upload external NAV to compare internal NAV versus a third party source. Accepted: CSV or XLSX with date and nav, or a full portfolio workbook.")

    external_file = st.file_uploader("Upload external NAV (CSV or XLSX)", type=["csv", "xlsx"], key="external_nav_file")

    if external_file:
        try:
            ext = _load_external_nav_file(external_file)
        except Exception as ex:
            st.error(str(ex))
            st.stop()

        internal = get_nav_timeseries().rename(columns={"nav": "internal_nav"})
        internal["date"] = internal["date"].astype(str)

        merged = internal.merge(ext, on="date", how="inner")
        if merged.empty:
            st.warning("No overlapping dates found between internal NAV and external NAV.")
        else:
            merged["difference"] = merged["internal_nav"] - merged["external_nav"]
            merged["difference_pct"] = merged["difference"] / merged["external_nav"]

            st.dataframe(
                merged.sort_values("date").style.format(
                    {
                        "internal_nav": "{:,.2f}",
                        "external_nav": "{:,.2f}",
                        "difference": "{:,.2f}",
                        "difference_pct": "{:.2%}",
                    }
                ),
                use_container_width=True,
            )

            breaks = merged[merged["difference_pct"].abs() > 0.002]
            if breaks.empty:
                st.success("No breaks above 20 bps threshold.")
            else:
                st.error("Breaks detected above 20 bps threshold.")
                st.dataframe(
                    breaks.style.format(
                        {
                            "internal_nav": "{:,.2f}",
                            "external_nav": "{:,.2f}",
                            "difference": "{:,.2f}",
                            "difference_pct": "{:.2%}",
                        }
                    ),
                    use_container_width=True,
                )


elif section == "Benchmark Monitoring":
    st.subheader("Benchmark Monitoring")
    st.caption("Compare NAV performance versus a benchmark using an indexed chart and excess return in basis points.")

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.selectbox("Start date", dates, index=0)
    with c2:
        end_date = st.selectbox("End date", dates, index=len(dates) - 1)

    nav_ts = get_nav_timeseries(start_date, end_date)
    if nav_ts.empty:
        st.error("No NAV data available for the selected range.")
        st.stop()

    nav_ts = nav_ts.copy()
    nav_ts["date"] = pd.to_datetime(nav_ts["date"])
    nav_ts = nav_ts.sort_values("date")
    nav_ts["fund_index"] = (nav_ts["nav"] / nav_ts["nav"].iloc[0]) * 100.0
    nav_ts["date_str"] = nav_ts["date"].dt.strftime("%Y-%m-%d")

    bench_file = st.file_uploader(
        "Upload benchmark (CSV or XLSX). Expected: date + level (or price, close, nav, value) or date + return.",
        type=["csv", "xlsx"],
        key="bench_file",
    )

    if bench_file:
        try:
            bench = _load_benchmark_file(bench_file)
        except Exception as ex:
            st.error(str(ex))
            st.stop()

        bench = bench[bench["date"].isin(nav_ts["date_str"])]

        if bench.empty:
            st.warning("Benchmark has no overlapping dates with the selected range. Showing fund only.")
            st.line_chart(nav_ts.set_index("date")[["fund_index"]], use_container_width=True)
        else:
            plot_df = nav_ts[["date_str", "fund_index"]].merge(bench, on="date", how="inner")
            plot_df["date"] = pd.to_datetime(plot_df["date"])
            plot_df = plot_df.set_index("date")[["fund_index", "benchmark_index"]]

            st.markdown("### Indexed performance")
            st.line_chart(plot_df, use_container_width=True)

            fund_return = (plot_df["fund_index"].iloc[-1] / plot_df["fund_index"].iloc[0]) - 1.0
            bench_return = (plot_df["benchmark_index"].iloc[-1] / plot_df["benchmark_index"].iloc[0]) - 1.0
            excess = fund_return - bench_return

            c1, c2, c3 = st.columns(3)
            c1.metric("Fund return (bps)", f"{_bp(fund_return):,.0f}")
            c2.metric("Benchmark return (bps)", f"{_bp(bench_return):,.0f}")
            c3.metric("Excess return (bps)", f"{_bp(excess):,.0f}")
    else:
        st.info("Upload a benchmark file to enable benchmark comparison.")
        st.line_chart(nav_ts.set_index("date")[["fund_index"]], use_container_width=True)


elif section == "Factsheet Outputs":
    st.subheader("Factsheet Outputs")
    st.caption("Generate factsheet ready tables for validated reporting and marketing outputs.")

    asof_date = st.selectbox("As of date", dates, index=len(dates) - 1)

    st.markdown("### Key period returns")
    pr = compute_period_returns(asof_date)

    if not pr:
        st.warning("Not enough data available to compute period returns.")
    else:
        pr_df = pd.DataFrame([{"period": k, "return": v} for k, v in pr.items()])
        st.dataframe(pr_df.style.format({"return": lambda x: "" if pd.isna(x) else f"{x:.2%}"}), use_container_width=True)

    st.divider()

    st.markdown("### Top holdings")
    top_n = st.selectbox("Number of holdings", [5, 10, 15, 20], index=1)
    top_df = compute_top_holdings_table(asof_date, top_n=top_n)
    top_df_display = top_df[["ticker", "security_name", "asset_class", "market_value", "weight"]]
    st.dataframe(top_df_display.style.format({"market_value": "{:,.2f}", "weight": "{:.2%}"}), use_container_width=True)


elif section == "Holdings":
    st.subheader("Holdings")
    c1, c2 = st.columns(2)
    with c1:
        ticker = st.selectbox("Select security", tickers)
    with c2:
        date = st.selectbox("Select date", dates)

    if st.button("Show holding"):
        qty = get_holding_on_date(ticker, date)
        st.metric(f"Holding in {ticker}", f"{qty:,} shares")


elif section == "Cash Analysis":
    st.subheader("Cash Analysis")

    cash_ts = get_cash_timeseries()
    if cash_ts.empty:
        st.warning("No cash data available.")
        st.stop()

    cash_ts = cash_ts.copy()
    cash_ts["date"] = pd.to_datetime(cash_ts["date"])

    st.markdown("### Cash balance over time")
    st.line_chart(cash_ts.set_index("date")["amount"], use_container_width=True)

    st.markdown("### Daily cash movements")
    st.dataframe(cash_ts.style.format({"amount": "{:,.2f}", "daily_change": "{:,.2f}"}), use_container_width=True)

    st.markdown("### Cash movement explanation")
    date = st.selectbox("Select date", cash_ts["date"].dt.strftime("%Y-%m-%d").tolist())
    st.text(explain_cash_change(date))
