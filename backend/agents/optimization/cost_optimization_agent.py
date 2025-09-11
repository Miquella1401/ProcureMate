# agents/optimization/cost_optimization_agent.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class VendorQuote:
    vendor: str
    product: str
    unit_price: float
    delivery_days: int
    in_stock: int

class CostOptimizationAgent:
    """
    Finds the lowest-cost way to fulfill `quantity` for `product`
    under an optional `budget`. If a single vendor can't do it
    within budget, it tries a greedy split across multiple vendors.
    """
    def __init__(self, catalog: List[VendorQuote]):
        self.catalog = catalog

    def optimize(self, product: str, quantity: int, budget: float | None = None) -> Dict:
        # Eligible quotes (enough stock considered during allocation)
        quotes = [q for q in self.catalog if q.product.lower() == product.lower() and q.in_stock > 0]
        if not quotes:
            return {"ok": False, "reason": "No quotes for product", "allocations": []}

        # Sort by cheapest first (primary), then fastest delivery
        quotes.sort(key=lambda q: (q.unit_price, q.delivery_days))

        remaining = quantity
        allocations = []
        total_cost = 0.0
        total_days = 0

        for q in quotes:
            if remaining <= 0:
                break
            take = min(q.in_stock, remaining)

            # If we have a budget, check whether taking full 'take' would exceed it.
            if budget is not None and total_cost + take * q.unit_price > budget:
                # take partial to fit budget
                if q.unit_price > 0:
                    affordable = int((budget - total_cost) // q.unit_price)
                else:
                    affordable = take
                take = max(0, min(take, affordable))

            if take <= 0:
                continue

            cost = round(take * q.unit_price, 2)
            allocations.append({
                "vendor": q.vendor,
                "unit_price": q.unit_price,
                "delivery_days": q.delivery_days,
                "qty": take,
                "cost": cost
            })
            total_cost = round(total_cost + cost, 2)
            total_days = max(total_days, q.delivery_days)
            remaining -= take

        ok = remaining == 0
        within_budget = (budget is None) or (total_cost <= budget)
        return {
            "ok": ok and within_budget,
            "product": product,
            "requested_qty": quantity,
            "remaining_unfilled": remaining if not ok else 0,
            "budget": budget,
            "total_cost": total_cost,
            "max_delivery_days": total_days if allocations else None,
            "within_budget": within_budget,
            "allocations": allocations
        }
