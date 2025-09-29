# services/catalog_service.py
from __future__ import annotations
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CatalogItem:
    vendor: str
    product: str
    unit_price: float
    delivery_days: int
    in_stock: int
    url: str

class CatalogService:
    def __init__(self):
        self.items: List[CatalogItem] = []
        self.last_updated: str | None = None

    def replace(self, new_items: List[Dict[str, Any]]) -> None:
        self.items = [CatalogItem(**i) for i in new_items]
        self.last_updated = datetime.utcnow().isoformat() + "Z"

    def extend(self, new_items: List[Dict[str, Any]]) -> None:
        self.items.extend(CatalogItem(**i) for i in new_items)
        self.last_updated = datetime.utcnow().isoformat() + "Z"

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        res = [i for i in self.items if q in i.product.lower()]
        return [i.__dict__ for i in res]

    def all(self) -> List[Dict[str, Any]]:
        return [i.__dict__ for i in self.items]
