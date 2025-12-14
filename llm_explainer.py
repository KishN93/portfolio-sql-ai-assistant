import os
import json
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ALLOWED_INTENTS = [
    "NAV_QUERY",
    "EXPLAIN_DAY",
    "BIG_NAV_MOVES",
    "HOLDING_QUERY",
    "CASH_QUERY"
]


def extract_intent_with_llm(question: str) -> dict:
    """
    Uses ChatGPT ONLY to classify intent and extract parameters.
    Never performs calculations.
    Never touches SQL.
    Returns structured JSON.
    """

    system_prompt = (
        "You are an intent classification engine for a portfolio analytics system.\n"
        "Your job is to classify the user's question into one of the allowed intents\n"
        "and extract parameters if present.\n\n"
        "Allowed intents:\n"
        "- NAV_QUERY (date)\n"
        "- EXPLAIN_DAY (date)\n"
        "- BIG_NAV_MOVES\n"
        "- HOLDING_QUERY (ticker, date)\n"
        "- CASH_QUERY (date)\n\n"
        "Rules:\n"
        "- Return ONLY valid JSON\n"
        "- Do NOT explain\n"
        "- Do NOT calculate\n"
        "- If the question cannot be classified, return intent = UNKNOWN\n"
    )

    user_prompt = f"Question: {question}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return {"intent": "UNKNOWN"}

    intent = parsed.get("intent")

    if intent not in ALLOWED_INTENTS:
        return {"intent": "UNKNOWN"}

    return parsed
