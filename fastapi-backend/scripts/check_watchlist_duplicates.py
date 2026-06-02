"""
Check for and remove duplicate watchlist items in MongoDB.
Duplicates are defined as items with the same (user_id, content_type, tmdb_id).
Also creates a unique index to prevent future duplicates.

Usage:
    cd fastapi-backend
    python scripts/check_watchlist_duplicates.py
"""

import asyncio
import sys
import os

# Add parent dir to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]
    collection = db["tblWatchlistItems"]

    print("=" * 60)
    print("Watchlist Duplicate Checker")
    print("=" * 60)

    # 1. Count total items
    total = await collection.count_documents({})
    print(f"\nTotal watchlist items: {total}")

    # 2. Find duplicates using aggregation
    pipeline = [
        {
            "$group": {
                "_id": {
                    "user_id": "$user_id",
                    "content_type": "$content_type",
                    "tmdb_id": "$tmdb_id",
                },
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"},
                "docs": {
                    "$push": {
                        "_id": "$_id",
                        "status": "$status",
                        "created_at": "$created_at",
                        "updated_at": "$updated_at",
                    }
                },
            }
        },
        {"$match": {"count": {"$gt": 1}}},
    ]

    duplicates = []
    async for doc in collection.aggregate(pipeline):
        duplicates.append(doc)

    if not duplicates:
        print("\n✅ No duplicates found!")
    else:
        print(f"\n⚠️  Found {len(duplicates)} duplicate groups:")
        total_dupes = 0
        for dup in duplicates:
            key = dup["_id"]
            count = dup["count"]
            total_dupes += count - 1
            print(f"\n  user_id={key['user_id']}, content_type={key['content_type']}, tmdb_id={key['tmdb_id']}")
            print(f"    {count} copies found:")
            for doc in dup["docs"]:
                print(f"      _id={doc['_id']}, status={doc['status']}, created={doc.get('created_at')}, updated={doc.get('updated_at')}")

        print(f"\n  Total duplicate items to remove: {total_dupes}")

        # Ask for confirmation
        answer = input("\nRemove duplicates? (keep oldest per group) [y/N]: ").strip().lower()
        if answer == "y":
            removed = 0
            for dup in duplicates:
                # Sort by created_at ascending, keep the first (oldest)
                docs_sorted = sorted(dup["docs"], key=lambda d: d.get("created_at") or "")
                ids_to_remove = [d["_id"] for d in docs_sorted[1:]]  # all except first
                if ids_to_remove:
                    result = await collection.delete_many({"_id": {"$in": ids_to_remove}})
                    removed += result.deleted_count
            print(f"\n✅ Removed {removed} duplicate items.")
        else:
            print("\nSkipped removal.")

    # 3. Create unique index
    print("\nCreating unique index on (user_id, content_type, tmdb_id)...")
    existing_indexes = await collection.index_information()
    print(f"  Existing indexes: {list(existing_indexes.keys())}")

    # Drop any existing non-unique index on these fields if it exists
    for idx_name, idx_info in existing_indexes.items():
        if idx_name == "_id_":
            continue
        key_list = idx_info.get("key", [])
        field_names = [k[0] for k in key_list]
        if "user_id" in field_names and "content_type" in field_names and "tmdb_id" in field_names:
            if not idx_info.get("unique", False):
                print(f"  Dropping non-unique index '{idx_name}' on same fields...")
                await collection.drop_index(idx_name)

    try:
        result = await collection.create_index(
            [("user_id", 1), ("content_type", 1), ("tmdb_id", 1)],
            unique=True,
            name="unique_user_content_tmdb",
        )
        print(f"  ✅ Unique index created: {result}")
    except Exception as e:
        print(f"  ⚠️  Index creation result: {e}")

    # 4. Verify
    final_count = await collection.count_documents({})
    print(f"\nFinal watchlist item count: {final_count}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
