"""
Create an admin user in the database.
Run: python scripts/create_admin.py
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from app.core.config import settings
from app.core.security import hash_password
from app.database import connect_to_mongo, close_mongo_connection, get_database


async def create_admin():
    """Create admin user if it doesn't exist."""
    email = "admin@vozflix.com"
    password = "admin123"

    await connect_to_mongo()
    db = get_database()

    # Check if admin already exists
    existing = await db.users.find_one({"email": email})
    if existing:
        print(f"Admin user already exists: {email}")
        # Update to admin role if not already
        if existing.get("role") != "admin":
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"role": "admin", "updated_at": datetime.utcnow()}}
            )
            print(f"Updated {email} to admin role")
        else:
            print("User already has admin role")
    else:
        # Create new admin user
        user_doc = {
            "email": email,
            "password": hash_password(password),
            "username": "admin",
            "avatar_url": None,
            "role": "admin",
            "is_active": True,
            "is_banned": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await db.users.insert_one(user_doc)
        print(f"Created admin user: {email}")
        print(f"User ID: {result.inserted_id}")

    print(f"\nAdmin credentials:")
    print(f"  Email: {email}")
    print(f"  Password: {password}")

    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(create_admin())
