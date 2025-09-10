# tools/scraper_tools.py
import re
import time
import json
from typing import List, Dict, Any, Optional, Tuple
import requests
from bs4 import BeautifulSoup

# Optional Playwright fallback for JS-heavy pages
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# --------------------------------------------------------------------
# Vendor configuration
#   - Add/adjust selectors per site as needed
#   - Keep URLs to specific, high-signal product/PLP pages
# --------------------------------------------------------------------
VENDOR_CONFIG: Dict[str, Dict[str, Any]] = {
    # ----- Chairs -----
    "autonomous_ergochair_pro": {
        "name": "Autonomous ErgoChair Pro",
        "url": "https://www.autonomous.ai/office-chairs/ergonomic-chair",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": [
                "meta[itemprop='price']",
                "meta[property='product:price:amount']",
                "span.price",
                "span[class*='Price']",
                "[data-test='product-price']",
            ],
            "currency": [
                "meta[property='product:price:currency']",
                "meta[itemprop='priceCurrency']",
            ],
            "availability": [
                "link[itemprop='availability']",
                "div.stock",
                "span.availability",
                "div[data-test='availability']",
            ],
        },
    },
    "steelcase_gesture": {
        "name": "Steelcase Gesture",
        "url": "https://store.steelcase.com/seating/gesture",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": [
                "meta[itemprop='price']",
                "meta[property='product:price:amount']",
                "[data-test='product-price']",
                "span[data-test='product-price']",
                "span[data-testid='product-price']",
                "span[class*='price']",
                "div[class*='Price']",
            ],
            "currency": [
                "meta[property='product:price:currency']",
                "meta[itemprop='priceCurrency']",
            ],
            "availability": ["div.stock", "span.availability"],
        },
    },
    "hermanmiller_aeron": {
        "name": "Herman Miller Aeron (Size B)",
        "url": "https://store.hermanmiller.com/office-chairs/aeron-chair/2294.html",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": [
                "meta[itemprop='price']",
                "meta[property='product:price:amount']",
                "span.price",
                "span[class*='Price']",
            ],
            "currency": [
                "meta[property='product:price:currency']",
                "meta[itemprop='priceCurrency']",
            ],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- Laptops -----
    "lenovo_thinkpad_t_series": {
        "name": "Lenovo ThinkPad T Series",
        "url": "https://www.lenovo.com/us/en/laptops/thinkpad/thinkpad-t-series/",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']", "div[class*='price']"],
            "currency": ["meta[itemprop='priceCurrency']", "meta[property='product:price:currency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },
    "dell_xps_13": {
        "name": "Dell XPS 13",
        "url": "https://www.dell.com/en-us/shop/dell-laptops/xps-13-laptop/spd/xps-13-9340-laptop",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']", "div[class*='price']"],
            "currency": ["meta[itemprop='priceCurrency']", "meta[property='product:price:currency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- Monitors -----
    "lg_ultragear_monitor": {
        "name": "LG UltraGear Monitor",
        "url": "https://www.lg.com/us/monitors/gaming-monitors",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']", "div[class*='price']"],
            "currency": ["meta[itemprop='priceCurrency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- Keyboards -----
    "logitech_mx_keys": {
        "name": "Logitech MX Keys",
        "url": "https://www.logitech.com/en-us/products/keyboards/mx-keys",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']", "div[class*='price']"],
            "currency": ["meta[itemprop='priceCurrency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- Phones -----
    "apple_iphone": {
        "name": "Apple iPhone",
        "url": "https://www.apple.com/iphone/",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']", "div[class*='price']"],
            "currency": ["meta[itemprop='priceCurrency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- SSDs -----
    "samsung_970_evo_plus": {
        "name": "Samsung 970 EVO Plus",
        "url": "https://www.samsung.com/semiconductor/minisite/ssd/product/consumer/970evoplus/",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']"],
            "currency": ["meta[itemprop='priceCurrency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- Webcams -----
    "logitech_brio": {
        "name": "Logitech Brio",
        "url": "https://www.logitech.com/en-us/products/webcams/brio-4k-hdr-webcam",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']"],
            "currency": ["meta[itemprop='priceCurrency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- Printers -----
    "hp_laserjet_pro": {
        "name": "HP LaserJet Pro",
        "url": "https://www.hp.com/us-en/shop/cv/laserjet-printers",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']"],
            "currency": ["meta[itemprop='priceCurrency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },

    # ----- Desks -----
    "uplift_standing_desk": {
        "name": "UPLIFT Standing Desk",
        "url": "https://www.upliftdesk.com/standing-desks/",
        "selectors": {
            "title": ["meta[property='og:title']", "h1"],
            "price": ["span.price", "meta[itemprop='price']"],
            "currency": ["meta[itemprop='priceCurrency']"],
            "availability": ["div.stock", "span.availability"],
        },
    },
}

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def _first_text(soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
    for sel in selectors:
        el = soup.select_one(sel)
        if not el:
            continue
        if el.name == "meta" and el.get("content"):
            return el["content"].strip()
        txt = (el.get_text() or "").strip()
        if txt:
            return txt
    return None

def _fetch_static(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None

def _fetch_dynamic(url: str, price_selector_hint: Optional[str] = None) -> Optional[str]:
    if not HAS_PLAYWRIGHT:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(25000)
            page.goto(url)
            # wait for a likely price selector and network to settle
            try:
                page.wait_for_selector(
                    price_selector_hint or "meta[itemprop='price'], [data-test='product-price']",
                    timeout=8000
                )
            except Exception:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            time.sleep(2.0)  # small buffer for late rendering
            html = page.content()
            browser.close()
            return html
    except Exception:
        return None

def _parse_price(raw: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    if not raw:
        return None, None
    # Currency hint by symbol if present
    currency = "EUR" if "€" in raw else ("USD" if "$" in raw else None)

    # Match numbers like 1,299.99 or 1.299,99 or 1299.99 etc.
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*|[0-9]+)([.,][0-9]{2})?", raw)
    if not m:
        return None, currency
    num = m.group(0)

    # Normalize thousand/decimal separators
    if num.count(",") and num.count("."):
        # Decide which is decimal by last occurrence
        if num.rfind(",") > num.rfind("."):  # decimal is comma
            num = num.replace(".", "").replace(",", ".")
        else:  # decimal is dot
            num = num.replace(",", "")
    else:
        if num.endswith(",00"):
            num = num.replace(",", ".")
        elif "," in num and not num.endswith(",00"):
            num = num.replace(",", "")

    try:
        return float(num), currency
    except Exception:
        return None, currency

def _safe_float(x) -> Optional[float]:
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None

def _parse_json_ld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    blocks = soup.find_all("script", type="application/ld+json")
    items: List[Dict[str, Any]] = []
    for b in blocks:
        try:
            data = json.loads(b.string or "")
            if isinstance(data, dict):
                items.append(data)
            elif isinstance(data, list):
                items.extend([d for d in data if isinstance(d, dict)])
        except Exception:
            pass
    return items

def _from_json_ld(items: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Try to pull price, currency, availability from JSON-LD 'offers'.
    Returns (price, currency, availability)
    """
    price, currency, availability = None, None, None
    for it in items:
        offers = it.get("offers")
        if not offers:
            continue
        if isinstance(offers, dict):
            offers = [offers]
        for off in offers:
            price = price or _safe_float(off.get("price"))
            currency = currency or (off.get("priceCurrency") or off.get("price_currency"))
            availability = availability or off.get("availability")
            if price and currency and availability:
                return price, currency, availability
    return price, currency, availability

def _norm_availability(avail_raw: Optional[str]) -> Optional[str]:
    if not avail_raw:
        return None
    a = str(avail_raw).lower()
    if "instock" in a or "in stock" in a:
        return "In stock"
    if "outofstock" in a or "out of stock" in a:
        return "Out of stock"
    if "backorder" in a or "backordered" in a:
        return "Backorder"
    if "preorder" in a:
        return "Preorder"
    return avail_raw.strip()

def _find_price_in_scripts(html: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Last-resort: scan raw HTML/scripts for common JSON fields with price/currency.
    """
    curr = None
    curr_m = re.search(r'"(?:priceCurrency|currency)"\s*:\s*"([A-Z]{3})"', html, re.I)
    if curr_m:
        curr = curr_m.group(1).upper()

    price_patterns = [
        r'"price"\s*:\s*"(?P<p>\d[\d,\.]+)"',
        r'"price"\s*:\s*(?P<p>\d[\d,\.]+)',
        r'"amount"\s*:\s*"(?P<p>\d[\d,\.]+)"',
        r'"amount"\s*:\s*(?P<p>\d[\d,\.]+)',
        r'"unit_price"\s*:\s*"(?P<p>\d[\d,\.]+)"',
        r'"unit_price"\s*:\s*(?P<p>\d[\d,\.]+)',
    ]
    for pat in price_patterns:
        m = re.search(pat, html, re.I)
        if m:
            val = _safe_float(m.group("p").replace(",", ""))
            if val is not None:
                return val, curr
    return None, curr

# --------------------------------------------------------------------
# Core scraping functions
# --------------------------------------------------------------------
def scrape_vendor(vendor_key: str) -> Dict[str, Any]:
    cfg = VENDOR_CONFIG[vendor_key]
    url = cfg["url"]

    # Try static first, then dynamic
    html = _fetch_static(url)
    if not html:
        price_hint = (cfg["selectors"]["price"][0] if cfg["selectors"].get("price") else None)
        html = _fetch_dynamic(url, price_selector_hint=price_hint)

    out: Dict[str, Any] = {
        "vendor_key": vendor_key,
        "vendor_name": cfg["name"],
        "url": url,
        "title": None,
        "price": None,
        "currency": None,
        "availability": None,
        "timestamp": int(time.time()),
        "error": None,
    }
    if not html:
        out["error"] = "Failed to fetch (static+dynamic)"
        return out

    soup = BeautifulSoup(html, "html.parser")

    # Primary extraction via DOM/meta
    title_raw = _first_text(soup, cfg["selectors"]["title"])
    price_raw = _first_text(soup, cfg["selectors"]["price"])
    avail_raw = _first_text(soup, cfg["selectors"]["availability"])
    curr_meta = _first_text(soup, cfg["selectors"].get("currency", []))
    price_val, curr = _parse_price(price_raw)
    curr = curr or curr_meta

    # JSON-LD fallback if anything missing
    if price_val is None or curr is None or not avail_raw:
        items = _parse_json_ld(soup)
        j_price, j_curr, j_avail = _from_json_ld(items)
        price_val = price_val if price_val is not None else j_price
        curr = curr or j_curr
        avail_raw = avail_raw or j_avail

    # Raw script scan as last resort
    if price_val is None:
        s_price, s_curr = _find_price_in_scripts(html)
        if s_price is not None:
            price_val = s_price
            curr = curr or s_curr

    out["title"] = title_raw
    out["price"] = price_val
    out["currency"] = curr
    out["availability"] = _norm_availability(avail_raw)

    return out

# --------------------------------------------------------------------
# Routing by product keywords → vendor key lists
#   - Expand categories as needed
#   - Keep results small (top 3–5) for speed and rate limits
# --------------------------------------------------------------------
CATEGORY_ROUTING: List[Tuple[List[str], List[str]]] = [
    # Chairs / seating
    (["chair", "seating", "ergonomic", "office chair"],
     ["autonomous_ergochair_pro", "steelcase_gesture", "hermanmiller_aeron"]),

    # Laptops / notebooks
    (["laptop", "notebook", "ultrabook"],
     ["lenovo_thinkpad_t_series", "dell_xps_13"]),

    # Monitors / displays
    (["monitor", "display", "screen"],
     ["lg_ultragear_monitor"]),

    # Keyboards
    (["keyboard", "mx keys", "mechanical keyboard"],
     ["logitech_mx_keys"]),

    # Phones
    (["phone", "iphone", "smartphone", "mobile phone"],
     ["apple_iphone"]),

    # SSD / storage
    (["ssd", "solid state drive", "nvme", "970 evo"],
     ["samsung_970_evo_plus"]),

    # Webcams
    (["webcam", "camera", "video conference"],
      ["logitech_brio"]),

    # Printers
    (["printer", "laserjet", "laser printer"],
      ["hp_laserjet_pro"]),

    # Desks
    (["standing desk", "desk", "workstation"],
      ["uplift_standing_desk"]),
]

def _route_vendor_keys(query: str, max_vendors: int) -> List[str]:
    q = (query or "").lower()
    for keywords, keys in CATEGORY_ROUTING:
        if any(k in q for k in keywords):
            return keys[:max_vendors]

    # Generic fallback: first N known vendors (acts as a baseline)
    # You can reorder to prefer broader, evergreen vendors
    all_keys = list(VENDOR_CONFIG.keys())
    return all_keys[:max_vendors]

def fetch_vendor_offers(query: str, max_vendors: int = 3) -> List[Dict[str, Any]]:
    """
    Map queries to a curated list of vendor keys, then scrape each.
    Extend this logic to route different products to different vendors.
    """
    keys = _route_vendor_keys(query, max_vendors=max_vendors)
    results: List[Dict[str, Any]] = []
    for k in keys:
        try:
            results.append(scrape_vendor(k))
            time.sleep(1.0)  # be polite
        except Exception as e:
            cfg = VENDOR_CONFIG.get(k, {"name": k, "url": ""})
            results.append({
                "vendor_key": k,
                "vendor_name": cfg.get("name", k),
                "url": cfg.get("url", ""),
                "title": None,
                "price": None,
                "currency": None,
                "availability": None,
                "timestamp": int(time.time()),
                "error": str(e),
            })
    return results
