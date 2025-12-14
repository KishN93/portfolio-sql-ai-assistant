import re
import sqlite3
from typing import Optional, Set


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def extract_date(text: str) -> Optional[str]:
    m = _DATE_RE.search(text)
    return m.group(0) if m else None


def get_allowed_tickers(db_path: str = "portfolio.db") -> Set[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM securities;")
    rows = cur.fetchall()
    conn.close()
    return {r[0] for r in rows}


def extract_ticker(text: str, allowed: Set[str]) -> Optional[str]:
    words = re.findall(r"[A-Za-z]{1,5}", text.upper())
    for w in words:
        if w in allowed:
            return w
    return None
