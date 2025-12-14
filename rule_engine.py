from typing import List, Dict, Any


def detect_big_nav_moves(nav_series: List[Dict[str, Any]], threshold: float = 0.03) -> List[Dict[str, Any]]:
    alerts = []
    for r in nav_series:
        ret = r.get("daily_return")
        if ret is not None and abs(ret) >= threshold:
            alerts.append({
                "type": "BIG_NAV_MOVE",
                "nav_date": r["nav_date"],
                "daily_return": ret,
                "daily_change": r["daily_change"],
            })
    return alerts
