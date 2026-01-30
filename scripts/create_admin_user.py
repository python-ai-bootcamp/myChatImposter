#!/usr/bin/env python3
"""
Admin User Creation Script.

Creates an admin user with secure password input (not visible in terminal or history).
Validates password strength before creating credentials.

Usage:
    python scripts/create_admin_user.py <user_id>

Example:
    python scripts/create_admin_user.py admin
"""

import sys
import os
import getpass
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from motor.motor_asyncio import AsyncIOMotorClient
from services.user_auth_service import UserAuthService


async def create_admin(user_id: str, mongodb_url: str):
    """
    Create admin user with secure password prompt.

    Args:
        user_id: Admin user identifier
        mongodb_url: MongoDB connection string
    """
    print(f"\n=== Creating Admin User: {user_id} ===\n")

    # Prompt for password (not visible)
    while True:
        password = getpass.getpass("Enter password: ")
        if not password:
            print("Error: Password cannot be empty")
            continue

        password_confirm = getpass.getpass("Confirm password: ")

        if password != password_confirm:
            print("Error: Passwords do not match. Please try again.\n")
            continue

        break

    # Connect to MongoDB
    print("\nConnecting to MongoDB...")
    client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)

    try:
        # Test connection
        await client.admin.command('ismaster')
        print("Connected to MongoDB successfully")

        # Get database and collection
        db = client.get_database("chat_manager")
        credentials_collection = db.get_collection("user_auth_credentials")

        # Initialize auth service
        auth_service = UserAuthService(credentials_collection)

        # Create admin credentials
        print(f"\nCreating admin user '{user_id}'...")
        success, message = await auth_service.create_credentials(
            user_id=user_id,
            password=password,
            role="admin"
        )

        if success:
            print(f"\n✓ {message}")
            print(f"\nAdmin user '{user_id}' created successfully!")
            print("\nYou can now log in to the gateway with these credentials.")
        else:
            print(f"\n✗ Error: {message}")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

    finally:
        client.close()
        print("\nMongoDB connection closed.")


def main():
    """Main entry point."""
    # Check arguments
    if len(sys.argv) != 2:
        print("Usage: python scripts/create_admin_user.py <user_id>")
        print("\nExample:")
        print("  python scripts/create_admin_user.py admin")
        sys.exit(1)

    user_id = sys.argv[1]

    # Validate user_id
    if not user_id or not user_id.strip():
        print("Error: user_id cannot be empty")
        sys.exit(1)

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    # Run async function
    asyncio.run(create_admin(user_id.strip(), mongodb_url))


if __name__ == "__main__":
    main()
