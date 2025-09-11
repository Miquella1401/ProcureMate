# -*- coding: utf-8 -*-
"""
scraper_tools.py
Live marketplace scraping only (Walmart). No curated vendor fallbacks.

Backward-compat exports preserved so existing imports don't crash:
  - VENDOR_CONFIG: empty dict
  - scrape_vendor(): raises a clear runtime error if called

Public API you should use:
  - fetch_vendor_offers(query: str, max_vendors: int = 3, sources: Tuple[str,...]=("walmart",))

Output item shape:
  {
    "vendor_key": "walmart",
    "vendor_name": "Walmart",
    "url": str,
    "title": Optional[str],
    "price": Optional[float],
    "currency": Optional[str],
    "availability": Optional[str],  # "InStock"/"OutOfStock"/"PreOrder"/raw
    "timestamp": int,
    "error": Optional[str]
  }
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

# ---------- Back-compat stubs (so old imports don't crash) ----------
class VendorCfg:  # dummy placeholder for old type hints
    pass

VENDOR_CONFIG: Dict[str, VendorCfg] = {}  # no curated vendors anymore

def scrape_vendor(*args, **kwargs) -> Dict[str, Any]:
    raise RuntimeError(
        "scrape_vendor is deprecated: curated vendor scraping was removed. "
        "Use fetch_vendor_offers(query, max_vendors, sources) instead."
    )

# ---------- HTTP helpers ----------

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _fetch_static(url: str, timeout: int = 15) -> Optional[str]:
    try:
        resp = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return resp.text
        return None
    except Exception:
        return None

# ---------- Parsing helpers ----------

def _parse_json_ld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for tag in soup.select('script[type="application/ld+json"]'):
        raw = (tag.string or tag.text or "").strip()
        if not raw:
            continue
        try:
            loaded = json.loads(raw)
        except Exception:
            continue
        if isinstance(loaded, dict):
            data.append(loaded)
        elif isinstance(loaded, list):
            data.extend([it for it in loaded if isinstance(it, dict)])
    return data

def _from_json_ld(items: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """Extract (price, currency, availability) from JSON-LD Product.offers / AggregateOffer."""
    def to_float(x: Any) -> Optional[float]:
        try:
            return float(str(x).replace(",", "").strip())
        except Exception:
            return None

    for obj in items:
        typ = obj.get("@type")
        if isinstance(typ, list):
            typ = next((t for t in typ if t == "Product"), None)
        if typ == "Product":
            offers = obj.get("offers")
            if isinstance(offers, dict):
                return to_float(offers.get("price")), offers.get("priceCurrency"), offers.get("availability")
            if isinstance(offers, list):
                for off in offers:
                    if isinstance(off, dict):
                        price = to_float(off.get("price"))
                        curr = off.get("priceCurrency")
                        av = off.get("availability")
                        if price is not None or curr or av:
                            return price, curr, av
    return None, None, None

_PRICE_RE = re.compile(r'"?price"?\s*[:=]\s*"?(?P<price>\d+(?:\.\d{1,2})?)"?', re.I)
_CURR_RE  = re.compile(r'"?priceCurrency"?\s*[:=]\s*"?(?P<curr>[A-Z]{3})"?', re.I)

def _find_price_in_scripts(html: str) -> Tuple[Optional[float], Optional[str]]:
    price = None
    curr = None
    m = _PRICE_RE.search(html)
    if m:
        try:
            price = float(m.group("price"))
        except Exception:
            price = None
    m2 = _CURR_RE.search(html)
    if m2:
        curr = m2.group("curr")
    return price, curr

def _first_text(soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
    for sel in selectors:
        el = soup.select_one(sel)
        if not el:
            continue
        if el.name == "meta":
            content = el.get("content")
            if content and content.strip():
                return content.strip()
        txt = el.get_text(strip=True)
        if txt:
            return txt
    return None

def _norm_availability(av: Optional[str]) -> Optional[str]:
    if not av:
        return None
    av = av.lower()
    if "instock" in av:
        return "InStock"
    if "outofstock" in av:
        return "OutOfStock"
    if "preorder" in av:
        return "PreOrder"
    return av

# ---------- Walmart adapter (HTML) ----------

def walmart_search(query: str, max_items: int = 10) -> List[Dict[str, Any]]:
    """Scrape Walmart search results (best-effort; markup can change)."""
    url = f"https://www.walmart.com/search?q={quote_plus(query)}"
    html = _fetch_static(url)
    results: List[Dict[str, Any]] = []
    if not html:
        return results

    soup = BeautifulSoup(html, "html.parser")

    # Try several card selectors (Walmart updates often)
    cards = soup.select('[data-automation-id="productTile"]') \
         or soup.select("div.mb0.ph0-xl.pr0-xl") \
         or soup.select("div.search-result-gridview-item")

    for card in cards:
        a = (card.select_one('a[href][data-automation-id="product-title"]')
             or card.select_one("a[href].absolute")
             or card.select_one("a[href]"))
        if not a:
            continue
        href = a.get("href")
        if not href:
            continue
        prod_url = href if href.startswith("http") else urljoin("https://www.walmart.com", href)
        title = (a.get_text() or "").strip() or (a.get("aria-label") or a.get("title") or "").strip()
        if not title:
            continue
        results.append({"title": title, "url": prod_url})
        if len(results) >= max_items:
            break
    return results

def walmart_product_details(url: str) -> Dict[str, Any]:
    """Open Walmart PDP and extract details via JSON-LD with fallbacks."""
    html = _fetch_static(url)
    if not html:
        return {
            "vendor_key": "walmart",
            "vendor_name": "Walmart",
            "url": url,
            "title": None, "price": None, "currency": None, "availability": None,
            "timestamp": int(time.time()), "error": "fetch_failed",
        }

    soup = BeautifulSoup(html, "html.parser")
    price, currency, availability = _from_json_ld(_parse_json_ld(soup))
    if price is None or currency is None:
        p2, c2 = _find_price_in_scripts(html)
        price = price or p2
        currency = currency or c2
    title = _first_text(soup, ["meta[property='og:title']", "h1", "title"]) or None

    return {
        "vendor_key": "walmart",
        "vendor_name": "Walmart",
        "url": url,
        "title": title,
        "price": price,
        "currency": currency,
        "availability": _norm_availability(availability),
        "timestamp": int(time.time()),
        "error": None,
    }

def _safe_sleep(sec: float) -> None:
    try:
        time.sleep(sec)
    except Exception:
        pass

def fetch_marketplace_offers(query: str, max_items: int = 5, sources: Tuple[str, ...] = ("walmart",)) -> List[Dict[str, Any]]:
    """Return live offers from supported marketplaces."""
    offers: List[Dict[str, Any]] = []
    if "walmart" in sources:
        try:
            hits = walmart_search(query, max_items=max_items)
            for h in hits:
                try:
                    offers.append(walmart_product_details(h["url"]))
                    _safe_sleep(0.8)  # be polite
                except Exception as e:
                    offers.append({
                        "vendor_key": "walmart", "vendor_name": "Walmart",
                        "url": h.get("url"), "title": h.get("title"),
                        "price": None, "currency": None, "availability": None,
                        "timestamp": int(time.time()),
                        "error": f"detail_error: {e}",
                    })
        except Exception as e:
            offers.append({
                "vendor_key": "walmart", "vendor_name": "Walmart",
                "url": "", "title": None, "price": None, "currency": None, "availability": None,
                "timestamp": int(time.time()),
                "error": f"search_error: {e}",
            })
    return offers

# ---------- Public API (compat with old callers) ----------

def fetch_vendor_offers(query: str, max_vendors: int = 3, sources: Tuple[str, ...] = ("walmart",)) -> List[Dict[str, Any]]:
    """
    Backward-compatible signature (old code passes max_vendors).
    Returns ONLY live scraped marketplace results.
    """
    print(f">>> fetch_vendor_offers: query='{query}', max_vendors={max_vendors}, sources={sources}")
    offers = fetch_marketplace_offers(query=query, max_items=max_vendors, sources=sources)
    print(f">>> fetch_vendor_offers: got {len(offers)} offers")
    return offers

__all__ = [
    "fetch_vendor_offers",
    "fetch_marketplace_offers",
    "walmart_search",
    "walmart_product_details",
    "VENDOR_CONFIG",     # back-compat
    "scrape_vendor",     # back-compat (raises)
    "VendorCfg",         # back-compat (dummy)
]
