import re
import sqlite3
from llm_explainer import extract_intent_with_llm


ALLOWED_INTENTS = {
    "NAV_QUERY",
    "EXPLAIN_DAY",
    "BIG_NAV_MOVES",
    "HOLDING_QUERY",
    "CASH_QUERY",
    "CASH_CHANGE_EXPLAIN",
}


# -----------------------------
# Helpers
# -----------------------------
def get_known_tickers():
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ticker FROM securities")
    tickers = {row[0] for row in cursor.fetchall()}
    conn.close()
    return tickers


KNOWN_TICKERS = get_known_tickers()


def extract_date(text):
    # YYYY-MM-DD
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)

    # YYYY MM DD
    match = re.search(r"(\d{4})\s+(\d{2})\s+(\d{2})", text)
    if match:
        y, m, d = match.groups()
        return f"{y}-{m}-{d}"

    return None


def extract_ticker(text):
    words = re.findall(r"\b[A-Z]{2,5}\b", text.upper())
    for word in words:
        if word in KNOWN_TICKERS:
            return word
    return None


# -----------------------------
# Intent parsing
# -----------------------------
def parse_intent(question: str):
    q = question.lower()

    # Why did cash change
    if "cash" in q and ("why" in q or "drop" in q or "increase" in q or "change" in q):
        return {
            "intent": "CASH_CHANGE_EXPLAIN",
            "date": extract_date(q),
        }

    # Cash level
    if "cash" in q:
        return {
            "intent": "CASH_QUERY",
            "date": extract_date(q),
        }

    # NAV
    if "nav" in q:
        return {
            "intent": "NAV_QUERY",
            "date": extract_date(q),
        }

    # Explain NAV
    if q.startswith("explain"):
        return {
            "intent": "EXPLAIN_DAY",
            "date": extract_date(q),
        }

    # Big moves
    if "big" in q and "move" in q:
        return {"intent": "BIG_NAV_MOVES"}

    # Holdings
    if "holding" in q or "shares" in q or "position" in q:
        return {
            "intent": "HOLDING_QUERY",
            "ticker": extract_ticker(question),
            "date": extract_date(q),
        }

    # -----------------------------
    # LLM fallback
    # -----------------------------
    llm_result = extract_intent_with_llm(question)

    if llm_result.get("intent") not in ALLOWED_INTENTS:
        raise ValueError("Unsupported question")

    return llm_result
