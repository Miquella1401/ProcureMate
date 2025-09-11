# agents/approval/approval_agent.py
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime
import uuid

@dataclass
class LineItem:
    vendor: str
    product: str
    unit_price: float
    qty: int
    delivery_days: int

    @property
    def line_total(self) -> float:
        return round(self.unit_price * self.qty, 2)

class ApprovalAgent:
    """
    Creates a Purchase Order payload and applies a simple approval policy.
    - Auto-approve if total_cost <= approval_limit
    - Otherwise mark as 'pending' (to be approved by supervisor)
    """
    def __init__(self, approval_limit: float = 5000.0):
        self.approval_limit = approval_limit

    def create_po(
        self,
        requester: str,
        supervisor_email: str,
        items: List[LineItem],
        notes: str | None = None
    ) -> Dict[str, Any]:
        total_cost = round(sum(i.line_total for i in items), 2)
        po_id = f"PO-{uuid.uuid4().hex[:8].upper()}"

        po = {
            "po_id": po_id,
            "status": "draft",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "requester": requester,
            "supervisor_email": supervisor_email,
            "items": [
                {
                    "vendor": i.vendor,
                    "product": i.product,
                    "unit_price": i.unit_price,
                    "qty": i.qty,
                    "delivery_days": i.delivery_days,
                    "line_total": i.line_total,
                } for i in items
            ],
            "total_cost": total_cost,
            "notes": notes or "",
            "policy": {"auto_approval_limit": self.approval_limit},
        }
        return po

    def evaluate(self, po: Dict[str, Any]) -> Dict[str, Any]:
        total = po.get("total_cost", 0.0)
        if total <= self.approval_limit:
            po["status"] = "approved"
            decision = {
                "decision": "approved",
                "reason": f"Total {total} <= limit {self.approval_limit}",
            }
        else:
            po["status"] = "pending"
            decision = {
                "decision": "pending",
                "reason": f"Total {total} exceeds limit {self.approval_limit}. Supervisor review required.",
            }
        return {
            "po": po,
            "decision": decision
        }

