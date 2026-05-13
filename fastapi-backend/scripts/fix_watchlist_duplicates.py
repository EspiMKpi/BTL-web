"""
Fix duplicate watchlist items where the same tmdb_id has multiple entries
with different content_type values (e.g., 'series' + 'mixed').

Strategy: For each (user_id, tmdb_id) group, keep the entry with the most
specific content_type ('movie' or 'series' over 'mixed'), and the one with
the most data (is_favorite=True, higher progress, etc.).

Also cleans up duplicate watch_history entries the same way.
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient


from datetime import datetime as _dt

TYPE_PRIORITY = {"movie": 0, "series": 0, "mixed": 1, "": 2}

def pick_best(docs):
    """Pick the best entry from a group of duplicates."""
    def sort_key(d):
        ct = d.get("content_type", "")
        ts = d.get("updated_at") or d.get("created_at") or _dt.min
        return (
            TYPE_PRIORITY.get(ct, 9),            # prefer movie/series over mixed
            0 if d.get("is_favorite") else 1,    # prefer favorites
            0 if d.get("status") == "completed" else 1,  # prefer completed
            _dt.max - ts,  # prefer newer (inverted so larger = smaller sort key)
        )
    return sorted(docs, key=sort_key)[0]


async def clean_collection(db, coll_name, label):
    coll = db[coll_name]
    pipeline = [
        {"$group": {
            "_id": {"user_id": "$user_id", "tmdb_id": "$tmdb_id"},
            "count": {"$sum": 1},
            "docs": {"$push": "$$ROOT"},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]

    total_removed = 0
    async for group in coll.aggregate(pipeline):
        docs = group["docs"]
        best = pick_best(docs)
        ids_to_remove = [d["_id"] for d in docs if d["_id"] != best["_id"]]
        if ids_to_remove:
            result = await coll.delete_many({"_id": {"$in": ids_to_remove}})
            total_removed += result.deleted_count
            print(f"  {label}: tmdb={group['_id']['tmdb_id']} kept type={best.get('content_type')} removed={result.deleted_count}")

    return total_removed


async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]

    print("=== Cleaning duplicate watchlist_items ===")
    removed_wl = await clean_collection(db, "watchlist_items", "watchlist")
    print(f"  Total watchlist items removed: {removed_wl}")

    print("\n=== Cleaning duplicate watch_history ===")
    removed_hist = await clean_collection(db, "watch_history", "history")
    print(f"  Total history items removed: {removed_hist}")

    print(f"\nGrand total removed: {removed_wl + removed_hist}")

    # Verify no more dupes
    for coll_name in ["watchlist_items", "watch_history"]:
        pipeline = [
            {"$group": {"_id": {"user_id": "$user_id", "tmdb_id": "$tmdb_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
        ]
        remaining = 0
        async for _ in db[coll_name].aggregate(pipeline):
            remaining += 1
        print(f"  Remaining dupes in {coll_name}: {remaining}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
