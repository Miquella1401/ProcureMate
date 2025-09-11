# agents/analytics/analytics_agent.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class POEvent:
    po_id: str
    vendor: str
    product: str
    qty: int
    unit_price: float
    delivery_days: int
    approved: bool
    total_cost: float
    quoted_unit_price: Optional[float] = None   # if known, to compute savings
    created_at: str = datetime.utcnow().isoformat() + "Z"

class AnalyticsAgent:
    def __init__(self):
        self.events: List[POEvent] = []

    def log_po(self, ev: POEvent) -> Dict[str, Any]:
        self.events.append(ev)
        return {"ok": True, "count": len(self.events)}

    def reset(self) -> None:
        self.events.clear()

    def kpis(self) -> Dict[str, Any]:
        if not self.events:
            return {
                "total_orders": 0,
                "total_spend": 0.0,
                "avg_delivery_days": None,
                "avg_unit_price": None,
                "avg_savings_pct": None,
                "top_vendors_by_orders": [],
            }

        total_spend = sum(e.total_cost for e in self.events)
        total_qty   = sum(e.qty for e in self.events if e.qty > 0)
        avg_unit    = round(total_spend / total_qty, 2) if total_qty else None
        avg_days    = round(sum(e.delivery_days for e in self.events) / len(self.events), 2)

        # Savings vs quoted price (if provided)
        savings_pcts = []
        for e in self.events:
            if e.quoted_unit_price and e.quoted_unit_price > 0:
                diff = e.quoted_unit_price - e.unit_price
                savings_pcts.append(100.0 * diff / e.quoted_unit_price)
        avg_savings_pct = round(sum(savings_pcts) / len(savings_pcts), 2) if savings_pcts else None

        # Vendor ranking (by number of line items)
        rank: Dict[str, int] = {}
        for e in self.events:
            rank[e.vendor] = rank.get(e.vendor, 0) + 1
        top_vendors = sorted(rank.items(), key=lambda x: (-x[1], x[0]))[:5]

        return {
            "total_orders": len(self.events),
            "total_spend": round(total_spend, 2),
            "avg_delivery_days": avg_days,
            "avg_unit_price": avg_unit,
            "avg_savings_pct": avg_savings_pct,
            "top_vendors_by_orders": [{"vendor": v, "count": c} for v, c in top_vendors],
        }
