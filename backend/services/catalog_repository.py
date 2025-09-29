# services/catalog_repository.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from .db.mongo_client import get_db

class CatalogRepository:
    """
    Mongo-backed storage for vendor catalog.
    Collection: vendor_catalog
    Schema (per doc):
      {
        vendor: str,
        product: str,
        unit_price: float,
        delivery_days: int,
        in_stock: int,
        url: str,
        updated_at: ISODate
      }
    """

    def __init__(self, collection_name: str = "vendor_catalog"):
        db = get_db()
        self.col: Collection = db[collection_name]
        # Useful indexes
        self.col.create_index([("product", "text")])
        self.col.create_index([("vendor", 1), ("product", 1)])

    def replace_all(self, items: List[Dict[str, Any]]) -> int:
        try:
            self.col.delete_many({})
            if not items:
                return 0
            for it in items:
                it["updated_at"] = datetime.utcnow()
            res = self.col.insert_many(items)
            return len(res.inserted_ids)
        except PyMongoError as e:
            raise RuntimeError(f"Catalog replace failed: {e}")

    def upsert_many(self, items: List[Dict[str, Any]]) -> int:
        # Match on (vendor, product, url)
        from pymongo import UpdateOne
        ops = []
        for it in items:
            key = {"vendor": it["vendor"], "product": it["product"], "url": it.get("url")}
            it["updated_at"] = datetime.utcnow()
            ops.append(UpdateOne(key, {"$set": it}, upsert=True))
        if not ops:
            return 0
        res = self.col.bulk_write(ops, ordered=False)
        return (res.upserted_count or 0) + (res.modified_count or 0)

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not query:
            cursor = self.col.find({}).sort("updated_at", -1).limit(limit)
        else:
            # text index fallback; if no $text score, do substring match
            cursor = self.col.find({"$text": {"$search": query}}).limit(limit)
            if cursor.count() == 0:
                cursor = self.col.find({"product": {"$regex": query, "$options": "i"}}).limit(limit)
        return [self._clean(doc) for doc in cursor]

    def all(self, limit: int = 500) -> List[Dict[str, Any]]:
        cursor = self.col.find({}).sort("updated_at", -1).limit(limit)
        return [self._clean(doc) for doc in cursor]

    def _clean(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        doc.pop("_id", None)
        return doc
