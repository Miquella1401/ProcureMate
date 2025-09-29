# services/db/mongo_client.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

_client = None
_db = None

def get_db():
    global _client, _db
    if _db is not None:
        return _db
    uri = os.getenv("MONGODB_URI")
    dbname = os.getenv("MONGODB_DB", "procuremate")
    if not uri:
        raise RuntimeError("MONGODB_URI not set in .env")
    _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # connection test
    try:
        _client.admin.command("ping")
    except ConnectionFailure as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")
    _db = _client[dbname]
    return _db
