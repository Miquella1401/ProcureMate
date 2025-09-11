# app.py
import os
import re
import json
import time
import traceback
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

# Optional CORS; won't crash if not installed
try:
    from flask_cors import CORS
    CORS(app)
except Exception:
    pass


# -----------------------------
# Basic routes
# -----------------------------

@app.route("/")
def home():
    return jsonify({"message": "ProcureMate Flask backend is running!"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


# -----------------------------
# Helpers (lazy imports, consistent JSON)
# -----------------------------

def _json_response(payload, status=200):
    """Ensure a proper JSON response (never empty body)."""
    return app.response_class(
        response=json.dumps(payload, ensure_ascii=False),
        status=status,
        mimetype="application/json",
    )


def _fetch_vendor_offers_safe(query: str, max_vendors: int):
    """Import scraper lazily and catch errors so we never crash the server."""
    try:
        import tools.scraper_tools as st
        # Debug prints help confirm the right module is loaded
        print(">>> scraper_tools path:", st.__file__)
        print(">>> has walmart_search:", hasattr(st, "walmart_search"))
        print(">>> has fetch_vendor_offers:", hasattr(st, "fetch_vendor_offers"))
    except Exception as e:
        tb = traceback.format_exc()
        print(">>> IMPORT ERROR in tools.scraper_tools\n", tb)
        return None, f"Failed to import tools.scraper_tools: {e}"

    try:
        data = st.fetch_vendor_offers(query, max_vendors=max_vendors)
        return data, None
    except Exception as e:
        tb = traceback.format_exc()
        print(">>> RUNTIME ERROR in fetch_vendor_offers\n", tb)
        return None, f"{e}\nTRACEBACK:\n{tb}"


def _run_procurement_pipeline_safe(**kwargs):
    """Import pipeline lazily; return (payload, http_status)."""
    try:
        from connect_agents import run_procurement_pipeline
    except Exception as e:
        tb = traceback.format_exc()
        print(">>> IMPORT ERROR connect_agents.run_procurement_pipeline\n", tb)
        return {
            "status": "error",
            "message": "Failed to import connect_agents.run_procurement_pipeline",
            "details": str(e),
        }, 500
    try:
        result = run_procurement_pipeline(**kwargs)
        return result, 200
    except Exception as e:
        tb = traceback.format_exc()
        print(">>> PIPELINE ERROR\n", tb)
        return {
            "status": "error",
            "message": "Pipeline execution failed",
            "details": str(e),
        }, 500


def _extract_retry_after_seconds(err_text: str, default_secs: int = 30) -> int:
    """Pull Retry-After hint from Vertex/Gemini error details if present."""
    # try to parse embedded JSON
    try:
        pos = err_text.find("{")
        j = json.loads(err_text[pos:] if pos != -1 else "{}")
        details = j.get("error", {}).get("details", [])
        for d in details:
            if d.get("@type", "").endswith("RetryInfo"):
                retry = d.get("retryDelay")
                if retry and retry.endswith("s"):
                    return int(retry[:-1])
    except Exception:
        pass
    # fallback: crude regex
    m = re.search(r'retryDelay[^0-9]*"(\d+)s"', err_text)
    return int(m.group(1)) if m else default_secs


# -----------------------------
# Vendors endpoints (Walmart-only scraper behind tools.scraper_tools)
# -----------------------------

# Debug endpoint to verify scraper wiring & search hits without doing full PDP parsing
@app.get("/api/vendors/debug")
def vendors_debug():
    try:
        import tools.scraper_tools as st
        info = {
            "module_path": st.__file__,
            "has_walmart_search": hasattr(st, "walmart_search"),
            "has_fetch_vendor_offers": hasattr(st, "fetch_vendor_offers"),
        }
        q = request.args.get("q", "wireless mouse")
        try:
            hits = st.walmart_search(q, max_items=3)
        except Exception as e:
            hits = []
            info["walmart_search_error"] = str(e)
        info["query"] = q
        info["walmart_search_hits"] = hits
        return _json_response(info, 200)
    except Exception as e:
        return _json_response(
            {"error": "debug failed", "details": str(e), "trace": traceback.format_exc()}, 500
        )


# GET style: /api/vendors?query=...&max_vendors=3
@app.get("/api/vendors")
def get_vendors():
    query = request.args.get("query", "").strip()
    if not query:
        return _json_response({"error": "query is required"}, 400)
    try:
        max_vendors = int(request.args.get("max_vendors", "3"))
    except ValueError:
        return _json_response({"error": "max_vendors must be an integer"}, 400)

    data, err = _fetch_vendor_offers_safe(query, max_vendors)
    if err:
        print(">>> /api/vendors ERROR:", err)
        return _json_response({"status": "error", "message": err}, 500)

    if data is None:
        data = []
    print(f">>> /api/vendors sending {len(data) if hasattr(data,'__len__') else 'unknown'} items")
    return _json_response(data, 200)


# POST style: JSON { "query": "...", "max_vendors": 3 }
@app.post("/api/vendors")
def post_vendors():
    payload = request.get_json(force=True) or {}
    query = (payload.get("query") or "").strip()
    if not query:
        return _json_response({"error": "query is required"}, 400)
    try:
        max_vendors = int(payload.get("max_vendors", 3))
    except (TypeError, ValueError):
        return _json_response({"error": "max_vendors must be an integer"}, 400)

    data, err = _fetch_vendor_offers_safe(query, max_vendors)
    if err:
        print(">>> /api/vendors (POST) ERROR:", err)
        return _json_response({"status": "error", "message": err}, 500)

    if data is None:
        data = []
    print(f">>> /api/vendors (POST) sending {len(data) if hasattr(data,'__len__') else 'unknown'} items")
    return _json_response(data, 200)


# -----------------------------
# Pipeline endpoint (with retry/backoff and clean 429/503 responses)
# -----------------------------

@app.post("/api/run")
def run_pipeline():
    data = request.get_json(force=True) or {}
    request_text = data.get("request_text", "")
    policy_text  = data.get("policy_text", "")
    buyer_info   = data.get("buyer_info")

    attempts = 0
    last_payload = None
    last_err_text = None

    while attempts < 3:
        payload, code = _run_procurement_pipeline_safe(
            request_text=request_text,
            policy_text=policy_text,
            buyer_info=buyer_info,
        )
        if code == 200:
            return _json_response(payload, 200)

        # Check for transient LLM issues
        err_text = ""
        if isinstance(payload, dict):
            err_text = str(payload.get("details", "")) or str(payload.get("message", ""))
        last_payload = payload
        last_err_text = err_text

        # Treat 429/503 and similar as transient
        transient_markers = ("429", "RESOURCE_EXHAUSTED", "RateLimit", "rate", "503", "UNAVAILABLE", "overloaded")
        if any(m in err_text for m in transient_markers):
            attempts += 1
            time.sleep(1.5 * attempts)  # backoff: 1.5s, 3s
            continue
        break

    # Still failing: pick best HTTP code + Retry-After
    status_code = 429 if (last_err_text and ("429" in last_err_text or "RESOURCE_EXHAUSTED" in last_err_text)) else 503
    retry_after = _extract_retry_after_seconds(last_err_text or "", default_secs=30)
    resp = make_response(_json_response({
        "status": "error",
        "message": "Upstream LLM is unavailable / rate-limited. Please retry.",
        "details": last_err_text,
    }, status=status_code))
    resp.headers["Retry-After"] = str(retry_after)
    return resp


# -----------------------------
# Entrypoint
# -----------------------------

if __name__ == "__main__":
    print("== ROUTES ==")
    for r in app.url_map.iter_rules():
        print(r)
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
