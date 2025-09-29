# scrapers/base_scraper.py
from __future__ import annotations
from typing import List, Dict, Any
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    vendor_name: str

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return list of dicts:
        {
          "vendor": str,
          "product": str,
          "unit_price": float,
          "delivery_days": int | None,
          "in_stock": int | None,
          "url": str
        }
        """
        ...
