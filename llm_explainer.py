import os
from openai import OpenAI


def _fmt_money(x):
    return "None" if x is None else f"{x:,.2f}"


def explain_nav_move(nav_row, contributions, cash_info):
    if not os.getenv("OPENAI_API_KEY"):
        return "OPENAI_API_KEY not set."

    total_sec_pnl = sum(c["pnl"] for c in contributions if c["pnl"] is not None)
    cash_chg = cash_info.get("cash_change")
    nav_chg = nav_row.get("daily_change")

    residual = None
    if nav_chg is not None and cash_chg is not None:
        residual = nav_chg - (total_sec_pnl + cash_chg)

    positives = [c for c in contributions if c["pnl"] and c["pnl"] > 0][:3]
    negatives = [c for c in contributions if c["pnl"] and c["pnl"] < 0][:3]

    facts = {
        "date": nav_row["nav_date"],
        "nav": _fmt_money(nav_row["nav"]),
        "nav_change": _fmt_money(nav_chg),
        "securities_pnl": _fmt_money(total_sec_pnl),
        "cash_change": _fmt_money(cash_chg),
        "residual": _fmt_money(residual),
        "positives": [
            f"{c['ticker']} ({_fmt_money(c['pnl'])})" for c in positives
        ],
        "negatives": [
            f"{c['ticker']} ({_fmt_money(c['pnl'])})" for c in negatives
        ],
    }

    prompt = f"""
You are a portfolio operations assistant.

Write a concise buy side style commentary.
Use only absolute numbers.
Do not use percentages.
Do not guess.
Use short sentences.
No hyphens.

Facts:
{facts}
"""

    client = OpenAI()
    resp = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    return resp.output_text
