import re
from llm_explainer import extract_intent_with_llm


ALLOWED_INTENTS = {
    "NAV_QUERY",
    "EXPLAIN_DAY",
    "BIG_NAV_MOVES",
    "HOLDING_QUERY",
    "CASH_QUERY"
}


def parse_intent(question: str):
    q = question.lower()

    # -----------------------------
    # Rule based parsing (first)
    # -----------------------------

    # NAV
    if "nav" in q:
        date = extract_date(q)
        return {"intent": "NAV_QUERY", "date": date}

    # Explain day
    if q.startswith("explain"):
        date = extract_date(q)
        return {"intent": "EXPLAIN_DAY", "date": date}

    # Big moves
    if "big" in q and "move" in q:
        return {"intent": "BIG_NAV_MOVES"}

    # Cash queries
    if "cash" in q:
        date = extract_date(q)
        return {"intent": "CASH_QUERY", "date": date}

    # Holdings
    if "holding" in q or "position" in q or "shares" in q:
        ticker = extract_ticker(q)
        date = extract_date(q)
        return {
            "intent": "HOLDING_QUERY",
            "ticker": ticker,
            "date": date
        }

    # -----------------------------
    # Fallback to LLM intent parsing
    # -----------------------------
    llm_result = extract_intent_with_llm(question)

    if llm_result["intent"] not in ALLOWED_INTENTS:
        raise ValueError("Unsupported question")

    return llm_result


def extract_date(text):
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    return None


def extract_ticker(text):
    match = re.search(r"\b[A-Z]{2,5}\b", text.upper())
    if match:
        return match.group(0)
    return None
