from flask import Flask, jsonify, request
from dotenv import load_dotenv

# --- Arnav's agents ---
from agents.negotiation.negotiation_agent import NegotiationAgent
from agents.optimization.cost_optimization_agent import CostOptimizationAgent, VendorQuote as OptQuote
from agents.approval.approval_agent import ApprovalAgent, LineItem
from agents.analytics.analytics_agent import AnalyticsAgent, POEvent
from agents.evaluation.evaluation_agent import EvaluationAgent

# --- Crew pipeline (new) ---
from crew_pipeline import run_procurement

load_dotenv()

app = Flask(__name__)
app.url_map.strict_slashes = False  # tolerate trailing slashes

# -----------------------------------------------------------------------------
# Health check
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return jsonify({"message": "ProcureMate Flask backend is running!"})

# -----------------------------------------------------------------------------
# In-memory vendor catalogue (used by Cost Optimization)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Negotiation (Gemini-generated email)
# -----------------------------------------------------------------------------
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
            "negotiation_email": email_text
        })
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# Cost Optimization (budget-aware; may split across vendors)
# -----------------------------------------------------------------------------
@app.route("/optimize-cost", methods=["GET"])
def optimize_cost():
    log_id = evaluation.start_log("CostOptimizationAgent", "optimize")

    product = request.args.get("product", "office chairs")
    quantity = request.args.get("quantity", 10)
    budget = request.args.get("budget")  # optional

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
        result = opt_agent.optimize(product=product, quantity=quantity, budget=budget_val)
        evaluation.end_log(log_id, status="success")
        return jsonify(result)
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# Approval (creates PO and decides approved/pending by limit)
# Auto-logs each PO line to Analytics.
# -----------------------------------------------------------------------------
@app.route("/request-approval", methods=["POST"])
def request_approval():
    log_id = evaluation.start_log("ApprovalAgent", "request_approval")

    data = request.get_json(silent=True) or {}
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

# -----------------------------------------------------------------------------
# Analytics endpoints
# -----------------------------------------------------------------------------
@app.route("/analytics/log", methods=["POST"])
def analytics_log():
    log_id = evaluation.start_log("AnalyticsAgent", "log_po")
    data = request.get_json(silent=True) or {}
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
def analytics_kpis():
    log_id = evaluation.start_log("AnalyticsAgent", "kpis")
    try:
        res = analytics.kpis()
        evaluation.end_log(log_id, status="success")
        return jsonify(res), 200
    except Exception as e:
        evaluation.end_log(log_id, status="fail", reason=str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/analytics/reset", methods=["POST"])
def analytics_reset():
    log_id = evaluation.start_log("AnalyticsAgent", "reset")
    analytics.reset()
    evaluation.end_log(log_id, status="success")
    return jsonify({"ok": True}), 200

# -----------------------------------------------------------------------------
# Evaluation summary & reset
# -----------------------------------------------------------------------------
@app.route("/evaluation", methods=["GET"])
def evaluation_summary():
    return jsonify(evaluation.summary()), 200

@app.route("/evaluation/reset", methods=["POST"])
def evaluation_reset():
    evaluation.logs.clear()
    return jsonify({"ok": True, "message": "Evaluation logs cleared"}), 200

# -----------------------------------------------------------------------------
# NEW: Run the whole pipeline via CrewAI tools
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
