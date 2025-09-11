# crew_pipeline.py
from typing import Any, Dict, Optional

from crewai import Agent, Task, Crew, Process

# === import your existing agents ===
from agents.optimization.cost_optimization_agent import CostOptimizationAgent, VendorQuote as OptQuote
from agents.approval.approval_agent import ApprovalAgent, LineItem
from agents.negotiation.negotiation_agent import NegotiationAgent
from agents.analytics.analytics_agent import AnalyticsAgent, POEvent

# ---- shared singletons (reuse same catalogue as app.py) ----
VENDOR_CATALOG = [
    OptQuote("AcmeCorp",      "office chairs", 79.99, 7, 120),
    OptQuote("GlobalSeating", "office chairs", 74.50, 10, 50),
    OptQuote("SeatWorks",     "office chairs", 83.00, 5, 200),
    OptQuote("FurniPro",      "office chairs", 81.25, 6, 100),
    OptQuote("AcmeCorp",      "standing desk", 199.0, 9, 40),
    OptQuote("DeskHub",       "standing desk", 185.0, 12, 60),
]
opt_agent = CostOptimizationAgent(VENDOR_CATALOG)
approval_agent = ApprovalAgent(approval_limit=5000.0)
analytics = AnalyticsAgent()

# -----------------------------------------------------------------------------
# The sequential pipeline (direct Python calls)
# -----------------------------------------------------------------------------
def run_procurement(product: str, quantity: int, budget: Optional[float],
                    requester: str, supervisor_email: str, notes: str = "") -> Dict[str, Any]:
    """Run the whole pipeline and return results from optimization, approval, negotiation."""

    # 1) Optimization
    alloc = opt_agent.optimize(product=product, quantity=quantity, budget=budget)

    # choose top vendor for negotiation
    top_vendor = alloc.get("allocations", [{}])[0].get("vendor") if alloc.get("allocations") else None

    # 2) Approval
    alloc_payload = []
    for a in alloc.get("allocations", []):
        alloc_payload.append(LineItem(
            vendor=a["vendor"],
            product=product,
            unit_price=float(a["unit_price"]),
            qty=int(a["qty"]),
            delivery_days=int(a["delivery_days"])
        ))

    po = approval_agent.create_po(requester=requester, supervisor_email=supervisor_email, items=alloc_payload, notes=notes)
    approval_res = approval_agent.evaluate(po)

    # log each line to analytics
    for line in approval_res["po"]["items"]:
        analytics.log_po(POEvent(
            po_id=approval_res["po"]["po_id"],
            vendor=line["vendor"],
            product=line["product"],
            qty=int(line["qty"]),
            unit_price=float(line["unit_price"]),
            delivery_days=int(line["delivery_days"]),
            approved=(approval_res["po"]["status"] == "approved"),
            total_cost=float(line["line_total"]),
        ))

    # 3) Negotiation draft
    email = None
    if top_vendor:
        email = NegotiationAgent(vendor_name=top_vendor, product=product, quantity=quantity).generate_email()

    return {
        "optimize": alloc,
        "approval": approval_res,
        "negotiation_email": email
    }

if __name__ == "__main__":
    out = run_procurement(
        product="office chairs",
        quantity=60,
        budget=4500,
        requester="Arnav",
        supervisor_email="boss@example.com",
        notes="CrewAI pipeline demo"
    )
    print(out)
