from flask import Flask, jsonify, request
from dotenv import load_dotenv
from flask_cors import CORS
import os

# --- Arnav's agents ---
from agents.negotiation.negotiation_agent import NegotiationAgent
from agents.optimization.cost_optimization_agent import CostOptimizationAgent, VendorQuote as OptQuote
from agents.approval.approval_agent import ApprovalAgent, LineItem
from agents.analytics.analytics_agent import AnalyticsAgent, POEvent
from agents.evaluation.evaluation_agent import EvaluationAgent

# --- Crew pipeline (existing) ---
from crew_pipeline import run_procurement

# --- MongoDB (new) ---
from pymongo import MongoClient, errors

load_dotenv()

app = Flask(__name__)
app.url_map.strict_slashes = False  # tolerate trailing slashes
CORS(app, resources={r"/*": {"origins": "*"}})  # relax for dev; tighten in prod

# =============================================================================
# MongoDB setup (new)
# =============================================================================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "procuremate")
DB_OK = False
vendors_col = None

try:
    _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000)
    _client.admin.command("ping")
    _db = _client[MONGO_DB]
    vendors_col = _db["vendors"]
    DB_OK = True
except errors.PyMongoError:
    DB_OK = False
    vendors_col = None

def _doc_to_optquote(doc) -> OptQuote:
    return OptQuote(
        str(doc["vendor"]),
        str(doc["product"]),
        float(doc["unit_price"]),
        int(doc.get("delivery_days", 7)),
        int(doc.get("stock", 0)),
    )

def _load_catalog_from_db(product: str | None = None) -> list[OptQuote]:
    if not DB_OK or not vendors_col:
        return []
    q = {}
    if product:
        q["product"] = product
    docs = list(vendors_col.find(q, {"_id": 0}))
    return [_doc_to_optquote(d) for d in docs]

def _set_opt_catalog(quotes: list[OptQuote]):
    global opt_agent
    opt_agent = CostOptimizationAgent(quotes)

# =============================================================================
# Health check
# =============================================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "ok": True,
        "message": "ProcureMate Flask backend is running!",
        "mongo": {"connected": DB_OK, "db": MONGO_DB if DB_OK else None},
    })

# =============================================================================
# In-memory vendor catalogue (used by Cost Optimization)
# =============================================================================
VENDOR_CATALOG = [
    OptQuote("AcmeCorp",      "office chairs", 79.99, 7,  120),
    OptQuote("GlobalSeating", "office chairs", 74.50, 10, 50),
    OptQuote("SeatWorks",     "office chairs", 83.00, 5,  200),
    OptQuote("FurniPro",      "office chairs", 81.25, 6,  100),
    OptQuote("AcmeCorp",      "standing desk", 199.0, 9,  40),
    OptQuote("DeskHub",       "standing desk", 185.0, 12, 60),
]

# Singletons
opt_agent = CostOptimizationAgent(VENDOR_CATALOG)
approval_agent = ApprovalAgent(approval_limit=5000.0)  # tweak as needed
analytics = AnalyticsAgent()
evaluation = EvaluationAgent()

# =============================================================================
# Helpers
# =============================================================================
def _json():
    return request.get_json(force=True, silent=True) or {}

def _line_items_from_po(po_draft: dict) -> list[LineItem]:
    """
    Adapt frontend's { poDraft: { vendor?, items: [{ sku|product, qty, price|unit_price, delivery_days? }] } }
    to ApprovalAgent's LineItem model (vendor, product, unit_price, qty, delivery_days).
    """
    default_vendor = po_draft.get("vendor", "AcmeCorp")
    raw_items = po_draft.get("items", [])
    items: list[LineItem] = []
    for i in raw_items:
        product = i.get("product") or i.get("sku") or "unknown"
        unit_price = i.get("unit_price", i.get("price"))
        if unit_price is None:
            raise ValueError(f"Missing price/unit_price for item: {i}")
        items.append(
            LineItem(
                vendor=i.get("vendor", default_vendor),
                product=str(product),
                unit_price=float(unit_price),
                qty=int(i.get("qty", 1)),
                delivery_days=int(i.get("delivery_days", 7)),
            )
        )
    if not items:
        raise ValueError("poDraft.items must be a non-empty list")
    return items

def _maybe_use_db_catalog(source_hint: str | None, product: str | None):
    """
    If source_hint == 'db', try to load catalog from MongoDB and refresh the optimizer.
    If source_hint == 'mem' or db unavailable/empty, keep current in-memory catalog.
    """
    if source_hint != "db":
        return "mem"
    quotes = _load_catalog_from_db(product=None)  # load all vendors by default
    if quotes:
        _set_opt_catalog(quotes)
        return "db"
    return "mem"

# =============================================================================
# Negotiation (Gemini-generated email)
# =============================================================================
@app.route("/negotiate", methods=["GET"])
def negotiate():
    log_id = evaluation.start_log("NegotiationAgent", "generate_email")

    vendor = request.args.get("vendor", "Acme Corp")
    product = request.args.get("product", "office chairs")
    quantity = request.args.get("quantity", 10)

    try:
        quantity = int(quantity)
    except ValueError:
        evaluation.end_log(log_id, status="fail", reason="Invalid quantity")
        return jsonify({"error": "Quantity must be an integer"}), 400

    try:
        agent = NegotiationAgent(vendor_name=vendor, product=product, quantity=quantity)
        email_text = agent.generate_email()
        evaluation.end_log(log_id, status="success")
        return jsonify({
            "vendor": vendor,
            "product": product,
            "quantity": quantity,
            "negotiation_email": email_text,  # original key
            "email_text": email_text,         # frontend-friendly key
        })
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

# =============================================================================
# Cost Optimization
# - GET /optimize-cost (legacy)
# - POST /optimize (frontend-friendly)
# Add ?source=db to pull quotes from MongoDB instead of in-memory.
# =============================================================================
@app.route("/optimize-cost", methods=["GET"])
def optimize_cost():
    log_id = evaluation.start_log("CostOptimizationAgent", "optimize")

    product = request.args.get("product", "office chairs")
    quantity = request.args.get("quantity", 10)
    budget = request.args.get("budget")  # optional
    source = request.args.get("source")  # 'db' or 'mem'

    try:
        quantity = int(quantity)
    except ValueError:
        evaluation.end_log(log_id, status="fail", reason="Invalid quantity")
        return jsonify({"error": "Quantity must be an integer"}), 400

    try:
        budget_val = float(budget) if budget is not None else None
    except ValueError:
        evaluation.end_log(log_id, status="fail", reason="Invalid budget")
        return jsonify({"error": "Budget must be a number"}), 400

    try:
        catalog_source = _maybe_use_db_catalog(source_hint=source, product=product)
        result = opt_agent.optimize(product=product, quantity=quantity, budget=budget_val)
        evaluation.end_log(log_id, status="success")
        return jsonify({"catalog_source": catalog_source, **result})
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/optimize", methods=["POST"])
def optimize_post():
    log_id = evaluation.start_log("CostOptimizationAgent", "optimize_bulk")
    body = _json()
    items = body.get("items", [])
    budget = body.get("budget", None)
    source = (body.get("source") or request.args.get("source"))  # 'db' or 'mem'

    if not isinstance(items, list) or not items:
        evaluation.end_log(log_id, status="fail", reason="Empty items")
        return jsonify({"error": "items must be a non-empty list"}), 400

    # group quantities by product
    q_by_product = {}
    for i in items:
        product = i.get("product") or i.get("sku")
        if not product:
            evaluation.end_log(log_id, status="fail", reason="Missing product/sku")
            return jsonify({"error": "Each item needs product or sku"}), 400
        q_by_product[product] = q_by_product.get(product, 0) + int(i.get("qty", 0))

    try:
        catalog_source = _maybe_use_db_catalog(source_hint=source, product=None)

        out = {}
        if len(q_by_product) == 1:
            (p, qty), = q_by_product.items()
            b = float(budget) if budget is not None else None
            out[p] = opt_agent.optimize(product=p, quantity=int(qty), budget=b)
        else:
            for p, qty in q_by_product.items():
                out[p] = opt_agent.optimize(product=p, quantity=int(qty), budget=None)

        evaluation.end_log(log_id, status="success")
        return jsonify({"catalog_source": catalog_source, "by_product": out, "budget": budget})
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

# =============================================================================
# Approval
# =============================================================================
@app.route("/request-approval", methods=["POST"])
def request_approval():
    log_id = evaluation.start_log("ApprovalAgent", "request_approval")

    data = _json()
    requester = data.get("requester", "Arnav")
    supervisor_email = data.get("supervisor_email", "supervisor@example.com")
    notes = data.get("notes", "")

    if "approval_limit" in data:
        try:
            approval_agent.approval_limit = float(data["approval_limit"])
        except Exception:
            evaluation.end_log(log_id, status="fail", reason="Invalid approval_limit")
            return jsonify({"error": "approval_limit must be a number"}), 400

    raw_items = data.get("items", [])
    if not isinstance(raw_items, list) or not raw_items:
        evaluation.end_log(log_id, status="fail", reason="Empty items")
        return jsonify({"error": "items must be a non-empty list"}), 400

    try:
        items = [
            LineItem(
                vendor=i["vendor"],
                product=i["product"],
                unit_price=float(i["unit_price"]),
                qty=int(i["qty"]),
                delivery_days=int(i.get("delivery_days", 7)),
            ) for i in raw_items
        ]
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=f"Invalid item: {e}")
        return jsonify({"error": f"Invalid item format: {e}"}), 400

    try:
        po = approval_agent.create_po(
            requester=requester,
            supervisor_email=supervisor_email,
            items=items,
            notes=notes
        )
        result = approval_agent.evaluate(po)

        # --- Auto-log to Analytics ---
        quoted_map = {}
        for i in raw_items:
            key = (i.get("vendor"), i.get("product"))
            if "quoted_unit_price" in i:
                try:
                    quoted_map[key] = float(i["quoted_unit_price"])
                except Exception:
                    pass

        for line in result["po"]["items"]:
            key = (line["vendor"], line["product"])
            analytics.log_po(POEvent(
                po_id=result["po"]["po_id"],
                vendor=line["vendor"],
                product=line["product"],
                qty=int(line["qty"]),
                unit_price=float(line["unit_price"]),
                delivery_days=int(line["delivery_days"]),
                approved=(result["po"]["status"] == "approved"),
                total_cost=float(line["line_total"]),
                quoted_unit_price=quoted_map.get(key)
            ))
        # --- end auto-log ---

        evaluation.end_log(log_id, status="success")
        return jsonify(result), 200

    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/approve", methods=["POST"])
def approve_post():
    log_id = evaluation.start_log("ApprovalAgent", "approve_adapter")
    data = _json()
    po_draft = data.get("poDraft")
    approver = data.get("approver")

    if not po_draft or not approver:
        evaluation.end_log(log_id, status="fail", reason="missing poDraft/approver")
        return jsonify({"error": "poDraft and approver are required"}), 400

    try:
        items = _line_items_from_po(po_draft)
        po = approval_agent.create_po(
            requester=po_draft.get("requester", "Arnav"),
            supervisor_email=approver,
            items=items,
            notes=po_draft.get("notes", "")
        )
        result = approval_agent.evaluate(po)

        for line in result["po"]["items"]:
            analytics.log_po(POEvent(
                po_id=result["po"]["po_id"],
                vendor=line["vendor"],
                product=line["product"],
                qty=int(line["qty"]),
                unit_price=float(line["unit_price"]),
                delivery_days=int(line["delivery_days"]),
                approved=(result["po"]["status"] == "approved"),
                total_cost=float(line["line_total"]),
                quoted_unit_price=None
            ))

        evaluation.end_log(log_id, status="success")
        return jsonify(result), 200
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 400

# =============================================================================
# Analytics
# =============================================================================
@app.route("/analytics/log", methods=["POST"])
def analytics_log():
    log_id = evaluation.start_log("AnalyticsAgent", "log_po")
    data = _json()
    try:
        ev = POEvent(
            po_id=str(data["po_id"]),
            vendor=str(data["vendor"]),
            product=str(data["product"]),
            qty=int(data["qty"]),
            unit_price=float(data["unit_price"]),
            delivery_days=int(data.get("delivery_days", 7)),
            approved=bool(data.get("approved", True)),
            total_cost=float(data["total_cost"]),
            quoted_unit_price=float(data["quoted_unit_price"]) if "quoted_unit_price" in data else None,
        )
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=f"invalid payload: {e}")
        return jsonify({"error": f"invalid payload: {e}"}), 400

    out = analytics.log_po(ev)
    evaluation.end_log(log_id, status="success")
    return jsonify(out), 200

@app.route("/analytics", methods=["GET"])
def analytics_kpis_legacy():
    log_id = evaluation.start_log("AnalyticsAgent", "kpis")
    try:
        res = analytics.kpis()
        evaluation.end_log(log_id, status="success")
        return jsonify(res), 200
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/analytics/kpis", methods=["GET"])
def analytics_kpis_alias():
    return analytics_kpis_legacy()

@app.route("/analytics/reset", methods=["POST"])
def analytics_reset():
    log_id = evaluation.start_log("AnalyticsAgent", "reset")
    analytics.reset()
    evaluation.end_log(log_id, status="success")
    return jsonify({"ok": True}), 200

# =============================================================================
# Evaluation summary & reset
# =============================================================================
@app.route("/evaluation", methods=["GET"])
def evaluation_summary():
    return jsonify(evaluation.summary()), 200

@app.route("/evaluation/reset", methods=["POST"])
def evaluation_reset():
    evaluation.logs.clear()
    return jsonify({"ok": True, "message": "Evaluation logs cleared"}), 200

# =============================================================================
# Crew pipeline
# =============================================================================
@app.route("/run-pipeline", methods=["GET"])
def run_pipeline():
    """
    Example:
    /run-pipeline?product=office%20chairs&quantity=60&budget=4500&requester=Arnav&supervisor_email=boss@example.com&notes=Demo
    """
    product = request.args.get("product", "office chairs")
    quantity = int(request.args.get("quantity", 60))
    budget = request.args.get("budget")
    budget_val = float(budget) if budget is not None else None
    requester = request.args.get("requester", "Arnav")
    supervisor_email = request.args.get("supervisor_email", "boss@example.com")
    notes = request.args.get("notes", "")

    log_id = evaluation.start_log("CrewPipeline", "run_procurement")
    try:
        result = run_procurement(
            product=product,
            quantity=quantity,
            budget=budget_val,
            requester=requester,
            supervisor_email=supervisor_email,
            notes=notes
        )
        evaluation.end_log(log_id, status="success")
        return jsonify(result), 200
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

# =============================================================================
# Home page adapter: one-click pipeline
# =============================================================================
@app.route("/api/run", methods=["POST"])
def api_run():
    """
    Accepts: { request_text, policy_text }
    Returns: { ok: true, final: { negotiation, optimization, approval, analytics, meta } }
    """
    data = _json()
    request_text = data.get("request_text", "")
    policy_text  = data.get("policy_text", "")

    try:
        # Negotiation
        agent = NegotiationAgent(vendor_name="Acme Corp", product="office chairs", quantity=20)
        email_text = agent.generate_email()

        # Optimization (single product)
        opt = opt_agent.optimize(product="office chairs", quantity=20, budget=4000)

        # Build PO
        po_items = []
        try:
            allocations = opt.get("allocations") or opt.get("lines") or []
            for a in allocations:
                po_items.append({
                    "vendor": a.get("vendor", "AcmeCorp"),
                    "product": "office chairs",
                    "unit_price": float(a.get("unit_price", a.get("price", 190))),
                    "qty": int(a.get("qty", 20)),
                    "delivery_days": int(a.get("delivery_days", 7)),
                })
        except Exception:
            pass

        if not po_items:
            po_items = [{
                "vendor": "AcmeCorp",
                "product": "office chairs",
                "unit_price": 190.0,
                "qty": 20,
                "delivery_days": 7
            }]

        po = approval_agent.create_po(
            requester="Arnav",
            supervisor_email="manager@supply.example",
            items=[LineItem(**{
                "vendor": i["vendor"],
                "product": i["product"],
                "unit_price": float(i["unit_price"]),
                "qty": int(i["qty"]),
                "delivery_days": int(i["delivery_days"]),
            }) for i in po_items],
            notes="Auto-generated via /api/run"
        )
        approval_result = approval_agent.evaluate(po)

        # Log to analytics
        for line in approval_result["po"]["items"]:
            analytics.log_po(POEvent(
                po_id=approval_result["po"]["po_id"],
                vendor=line["vendor"],
                product=line["product"],
                qty=int(line["qty"]),
                unit_price=float(line["unit_price"]),
                delivery_days=int(line["delivery_days"]),
                approved=(approval_result["po"]["status"] == "approved"),
                total_cost=float(line["line_total"]),
                quoted_unit_price=None
            ))

        kpis = analytics.kpis()

        final = {
            "negotiation": {"email_text": email_text},
            "optimization": opt,
            "approval": approval_result,
            "analytics": kpis,
            "meta": {"policy_text": policy_text, "echo": request_text[:200]},
        }
        return jsonify({"ok": True, "final": final})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# =============================================================================
# Vendors API (new) — seed, add, list, refresh optimizer from DB
# =============================================================================
@app.route("/vendors/seed", methods=["POST"])
def vendors_seed():
    if not DB_OK or not vendors_col:
        return jsonify({"ok": False, "error": "MongoDB not connected"}), 503

    sample = [
        {"vendor": "AcmeCorp",      "product": "office chairs", "unit_price": 78.5, "delivery_days": 7,  "stock": 300},
        {"vendor": "GlobalSeating", "product": "office chairs", "unit_price": 74.9, "delivery_days": 10, "stock": 120},
        {"vendor": "SeatWorks",     "product": "office chairs", "unit_price": 82.0, "delivery_days": 5,  "stock": 200},
        {"vendor": "FurniPro",      "product": "office chairs", "unit_price": 80.0, "delivery_days": 6,  "stock": 150},
        {"vendor": "AcmeCorp",      "product": "standing desk", "unit_price": 198,  "delivery_days": 9,  "stock": 80},
        {"vendor": "DeskHub",       "product": "standing desk", "unit_price": 186,  "delivery_days": 12, "stock": 60},
    ]
    # upsert by (vendor, product)
    inserted, upserted = 0, 0
    for d in sample:
        res = vendors_col.update_one(
            {"vendor": d["vendor"], "product": d["product"]},
            {"$set": d},
            upsert=True
        )
        if res.upserted_id:
            upserted += 1
        else:
            inserted += 1
    return jsonify({"ok": True, "seeded_or_updated": inserted + upserted, "upserted": upserted})

@app.route("/vendors", methods=["GET"])
def vendors_list():
    if not DB_OK or not vendors_col:
        # fallback: show in-memory
        data = [{
            "vendor": q.vendor,
            "product": q.product,
            "unit_price": q.price,
            "delivery_days": q.delivery_days,
            "stock": q.stock
        } for q in VENDOR_CATALOG]
        return jsonify({"ok": True, "source": "mem", "vendors": data})

    product = request.args.get("product")
    vendor_q = request.args.get("vendor")  # exact match for simplicity
    q = {}
    if product:
        q["product"] = product
    if vendor_q:
        q["vendor"] = vendor_q
    docs = list(vendors_col.find(q, {"_id": 0}))
    return jsonify({"ok": True, "source": "db", "vendors": docs})

@app.route("/vendors", methods=["POST"])
def vendors_add():
    if not DB_OK or not vendors_col:
        return jsonify({"ok": False, "error": "MongoDB not connected"}), 503
    data = _json()
    try:
        doc = {
            "vendor": str(data["vendor"]),
            "product": str(data["product"]),
            "unit_price": float(data["unit_price"]),
            "delivery_days": int(data.get("delivery_days", 7)),
            "stock": int(data.get("stock", 0)),
        }
    except Exception as e:
        return jsonify({"ok": False, "error": f"invalid payload: {e}"}), 400

    vendors_col.update_one(
        {"vendor": doc["vendor"], "product": doc["product"]},
        {"$set": doc},
        upsert=True
    )
    return jsonify({"ok": True, "vendor": doc})

@app.route("/vendors/refresh", methods=["POST"])
def vendors_refresh_optimizer():
    if not DB_OK or not vendors_col:
        return jsonify({"ok": False, "error": "MongoDB not connected"}), 503
    quotes = _load_catalog_from_db(product=None)
    if not quotes:
        return jsonify({"ok": False, "error": "No vendor quotes in DB"}), 404
    _set_opt_catalog(quotes)
    return jsonify({"ok": True, "catalog_source": "db", "count": len(quotes)})

# =============================================================================
if __name__ == "__main__":
    # Match your frontend .env VITE_API_URL
    app.run(host="127.0.0.1", port=5001, debug=True)
