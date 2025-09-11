# tools/ranking.py
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple

def simple_rank_offers(offers: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """
    LLM-free baseline ranking.
    score = 60% price + 20% availability + 20% title relevance
    Lower price -> higher score. Unknown price = neutral (0.5).
    """
    # --- normalize price range ---
    prices = [o.get("price") for o in offers if isinstance(o.get("price"), (int, float))]
    pmin, pmax = (min(prices), max(prices)) if prices else (None, None)

    def price_score(p: Optional[float]) -> float:
        if not isinstance(p, (int, float)) or pmin is None or pmax is None or pmax == pmin:
            return 0.5  # neutral if unknown
        # invert: lower price better
        norm = 1.0 - ((p - pmin) / (pmax - pmin))
        return max(0.0, min(1.0, norm))

    def availability_score(av: Optional[str]) -> float:
        if not av:
            return 0.5
        a = str(av).lower()
        if "instock" in a or "in stock" in a or "available" in a:
            return 1.0
        if "pre" in a or "back" in a:
            return 0.6
        if "out" in a:
            return 0.2
        return 0.5

    q = (query or "").lower()
    words = [w for w in re.split(r"\W+", q) if w]

    def relevance_score(title: Optional[str]) -> float:
        t = (title or "").lower()
        if not t or not q:
            return 0.5
        if q in t:
            return 1.0
        if any(w in t for w in words):
            return 0.6
        return 0.4

    ranked: List[Dict[str, Any]] = []
    for o in offers:
        ps = price_score(o.get("price"))
        avs = availability_score(o.get("availability"))
        rs = relevance_score(o.get("title"))
        score = 100.0 * (0.6 * ps + 0.2 * avs + 0.2 * rs)
        ranked.append({
            "vendor_name": o.get("vendor_name"),
            "url": o.get("url"),
            "price": o.get("price"),
            "currency": o.get("currency"),
            "availability": o.get("availability"),
            "score": round(score, 2),
            "reason": f"price={round(ps,2)}, availability={round(avs,2)}, relevance={round(rs,2)}"
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return {
        "ranking": ranked,
        "notes": "LLM-free heuristic used for price comparison."
    }
