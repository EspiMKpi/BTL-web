"""Quick dump of all watchlist items to diagnose duplicate title issue."""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]

    print("=== watchlist_items ===")
    async for doc in db.tblWatchlistItems.find().sort([("user_id", 1), ("tmdb_id", 1)]):
        print(f"  user={str(doc['user_id'])[:8]}.. tmdb={doc['tmdb_id']} type={doc['content_type']} status={doc.get('status','-')} fav={doc.get('is_favorite',False)} id={str(doc['_id'])[:8]}..")

    print("\n=== watch_history (continue-watching source) ===")
    async for doc in db.tblWatchHistory.find().sort([("user_id", 1), ("tmdb_id", 1)]):
        print(f"  user={str(doc['user_id'])[:8]}.. tmdb={doc['tmdb_id']} type={doc.get('content_type','-')} progress={doc.get('progress_seconds',0)}s id={str(doc['_id'])[:8]}..")

    # Check for same tmdb_id with different content_type in watchlist
    pipeline = [
        {"$group": {"_id": {"user_id": "$user_id", "tmdb_id": "$tmdb_id"}, "types": {"$addToSet": "$content_type"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    print("\n=== Same tmdb_id with multiple entries in watchlist ===")
    found = False
    async for doc in db.tblWatchlistItems.aggregate(pipeline):
        found = True
        print(f"  user={str(doc['_id']['user_id'])[:8]}.. tmdb={doc['_id']['tmdb_id']} types={doc['types']} count={doc['count']}")
    if not found:
        print("  (none)")

    # Check for same tmdb_id appearing in both watchlist and history
    wl_tmdb = set()
    async for doc in db.tblWatchlistItems.find({}, {"user_id": 1, "tmdb_id": 1, "content_type": 1}):
        wl_tmdb.add((str(doc["user_id"]), doc["tmdb_id"], doc["content_type"]))
    hist_tmdb = set()
    async for doc in db.tblWatchHistory.find({}, {"user_id": 1, "tmdb_id": 1, "content_type": 1}):
        hist_tmdb.add((str(doc["user_id"]), doc.get("tmdb_id"), doc.get("content_type")))
    overlap = wl_tmdb & hist_tmdb
    print(f"\n=== Items in BOTH watchlist and history ===")
    if overlap:
        for item in overlap:
            print(f"  user={item[0][:8]}.. tmdb={item[1]} type={item[2]}")
    else:
        print("  (none)")

    client.close()

asyncio.run(main())
