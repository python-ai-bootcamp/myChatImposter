#!/usr/bin/env python3
"""
User Creation Script.

Creates a user (admin or regular) with secure password input.
Supports extended profile fields (Name, Email, Phone, etc.).

Usage:
    python scripts/create_user.py <user_id> --role <admin|user> [options]

Examples:
    python scripts/create_user.py admin --role admin --email admin@example.com
    python scripts/create_user.py john --role user --first-name John --last-name Doe
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


async def create_user(args, mongodb_url: str):
    """
    Create user with secure password prompt.
    """
    user_id = args.user_id
    role = args.role
    
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
            role=role,
            first_name=args.first_name,
            last_name=args.last_name,
            email=args.email,
            phone_number=args.phone_number,
            gov_id=args.gov_id,
            country_value=args.country,
            language=args.language
        )

        if success:
            print(f"\n✓ {message}")
            print(f"\n{role.title()} user '{user_id}' created successfully!")
            print(f"Details: {args.first_name} {args.last_name} ({args.email})")
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
        description="Create a user with specified role and profile details.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("user_id", help="User identifier (alphanumeric, underscore, hyphen only)")
    parser.add_argument("--role", required=True, choices=["admin", "user"], help="User role")
    
    # Profile fields
    parser.add_argument("--first-name", default="Unknown", help="First Name")
    parser.add_argument("--last-name", default="User", help="Last Name")
    parser.add_argument("--email", default="", help="Email Address")
    parser.add_argument("--phone-number", default="", help="Phone Number (E.164)")
    parser.add_argument("--gov-id", default="", help="Government ID")
    parser.add_argument("--country", default="US", help="Country Code (ISO 3166-1 alpha-2)")
    parser.add_argument("--language", default="en", help="Language Code (ISO 639-1)")

    args = parser.parse_args()

    # Validate user_id
    if not args.user_id or not args.user_id.strip():
        print("Error: user_id cannot be empty")
        sys.exit(1)

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    # Run async function
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass

    asyncio.run(create_user(args, mongodb_url))


if __name__ == "__main__":
    main()
