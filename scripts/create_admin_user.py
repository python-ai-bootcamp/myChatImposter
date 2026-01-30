#!/usr/bin/env python3
"""
User Creation Script.

Creates a user (admin or regular) with secure password input (not visible in terminal or history).
Validates password strength before creating credentials.

Usage:
    python scripts/create_admin_user.py <user_id> --role <admin|user>

Examples:
    python scripts/create_admin_user.py admin --role admin
    python scripts/create_admin_user.py tal --role user
"""

import sys
import os
import getpass
import asyncio
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from motor.motor_asyncio import AsyncIOMotorClient
from services.user_auth_service import UserAuthService


async def create_user(user_id: str, role: str, mongodb_url: str):
    """
    Create user with secure password prompt.

    Args:
        user_id: User identifier
        role: User role ("admin" or "user")
        mongodb_url: MongoDB connection string
    """
    print(f"\n=== Creating {role.title()} User: {user_id} ===\n")

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

        # Create user credentials
        print(f"\nCreating {role} user '{user_id}'...")
        success, message = await auth_service.create_credentials(
            user_id=user_id,
            password=password,
            role=role
        )

        if success:
            print(f"\n✓ {message}")
            print(f"\n{role.title()} user '{user_id}' created successfully!")
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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Create a user with specified role (admin or regular user)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/create_admin_user.py admin --role admin
  python scripts/create_admin_user.py tal --role user
        """
    )

    parser.add_argument(
        "user_id",
        type=str,
        help="User identifier (alphanumeric, underscore, hyphen only)"
    )

    parser.add_argument(
        "--role",
        type=str,
        required=True,
        choices=["admin", "user"],
        help="User role (required)"
    )

    args = parser.parse_args()

    # Validate user_id
    if not args.user_id or not args.user_id.strip():
        print("Error: user_id cannot be empty")
        sys.exit(1)

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    # Run async function
    asyncio.run(create_user(args.user_id.strip(), args.role, mongodb_url))


if __name__ == "__main__":
    main()
