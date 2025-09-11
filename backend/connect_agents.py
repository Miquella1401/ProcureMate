# connect_agents.py
from __future__ import annotations
import re
import time
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------
# NEW: query normalization + retry
# ----------------------------

_STOP_WORDS = {"for", "by", "within", "before", "after", "new", "office", "setup"}
_PLURALS = {"chairs": "chair", "mice": "mouse", "keyboards": "keyboard", "laptops": "laptop"}

def _normalize_query(text: str) -> str:
    """
    Make a marketplace-friendly query:
    - remove numbers/quantities and punctuation
    - drop some stop words (keep product words)
    - singularize a few common plurals
    """
    t = (text or "").lower()
    # remove numbers like "50"
    t = re.sub(r"\b\d+\b", " ", t)
    # keep letters/spaces only
    t = re.sub(r"[^a-z\s]", " ", t)
    # collapse spaces
    toks = [w for w in t.split() if w]
    # drop stop words except when they are clearly part of item (we keep 'office' sometimes)
    cleaned = [w for w in toks if w not in _STOP_WORDS]
    # singularize a few common plural nouns
    norm = [_PLURALS.get(w, w[:-1] if w.endswith("s") and len(w) > 3 else w) for w in cleaned]
    q = " ".join(norm).strip()
    # guardrail: ensure at least 1 meaningful token
    return q or "chair"

def _retry_queries(base_query: str) -> List[str]:
    """
    Provide a small set of alternates to improve hit rate on marketplaces.
    """
    q = _normalize_query(base_query)
    alts = [q]
    # add a couple of semantic variants if relevant
    if "chair" in q and "ergonomic" in q and "office" not in q:
        alts.append("ergonomic office chair")
    if "chair" in q and "ergonomic" not in q:
        alts.append("ergonomic chair")
    if "chair" in q and "office" not in q:
        alts.append("office chair")
    # dedupe while preserving order
    seen, out = set(), []
    for s in alts:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# (unchanged) _parse_requirement() here ...


# ----------------------------
# Marketplace scraper import + RETRY logic
# ----------------------------

def _fetch_offers(query: str, max_items: int = 5, sources: Tuple[str, ...] = ("walmart",)) -> List[Dict[str, Any]]:
    """
    Try a few normalized/alternate queries until we get results (or exhaust the list).
    """
    try:
        from tools.scraper_tools import fetch_vendor_offers
    except Exception as e:
        ts = int(time.time())
        return [{
            "vendor_key": "internal", "vendor_name": "internal", "url": "",
            "title": None, "price": None, "currency": None, "availability": None,
            "timestamp": ts, "error": f"import_error: tools.scraper_tools: {e}",
        }]

    offers: List[Dict[str, Any]] = []
    candidates = _retry_queries(query)
    for idx, q in enumerate(candidates, start=1):
        try:
            batch = fetch_vendor_offers(q, max_vendors=max_items, sources=sources)
        except Exception as e:
            ts = int(time.time())
            batch = [{
                "vendor_key": "internal", "vendor_name": "internal", "url": "",
                "title": None, "price": None, "currency": None, "availability": None,
                "timestamp": ts, "error": f"runtime_error: fetch_vendor_offers({q}): {e}",
            }]
        # accept first non-empty set (ignore only-error rows)
        has_real = any(not r.get("error") for r in batch)
        offers = batch
        if has_real or idx == len(candidates):
            break
        # small pause between attempts to be polite
        time.sleep(0.6)
    return offers


# ----------------------------
# Public pipeline entrypoint
# ----------------------------

def run_procurement_pipeline(
    request_text: str,
    policy_text: str = "",
    buyer_info: Optional[Dict[str, Any]] = None,
    *,
    max_items: int = 5,
    sources: Tuple[str, ...] = ("walmart",),
) -> Dict[str, Any]:
    started = int(time.time())

    requirement = _parse_requirement(request_text or "")
    # use product words (not quantity) to search
    base_query = requirement.get("product_type") or (request_text or "product")
    search_query = _normalize_query(base_query)

    offers = _fetch_offers(query=search_query, max_items=max_items, sources=sources)
    comparison = _rank_offers_locally(offers, search_query)

    finished = int(time.time())
    return {
        "requirement": requirement,
        "offers": offers,
        "comparison": comparison,
        "meta": {
            "request_text": request_text,
            "policy_text": policy_text,
            "buyer_info": buyer_info or {},
            "query_used": search_query,
            "sources": list(sources),
            "t_started": started,
            "t_finished": finished,
            "duration_s": finished - started,
            "llm_used": False,
        },
    }
