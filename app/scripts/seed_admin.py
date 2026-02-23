"""Seed script to create or update a superadmin user.

Usage:
    python -m app.scripts.seed_admin --email=admin@example.com --password=SecurePass123!
    
NEVER hardcode credentials in this file. Always pass via CLI arguments.
"""

import argparse
import asyncio
import sys
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.user import User
from app.models.business import Business
from app.services.auth import hash_password


async def create_or_update_superadmin(email: str, password: str) -> None:
    """Create a new superadmin or update existing user to superadmin role.
    
    Args:
        email: Admin email address
        password: Admin password (will be hashed)
    """
    async with async_session_maker() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            # User exists - update to superadmin
            print(f"✅ User {email} already exists. Updating to superadmin role...")
            user.role = "superadmin"
            user.is_verified = True
            user.is_trial = False
            user.is_active = True
            user.hashed_password = hash_password(password)
            await db.commit()
            print(f"✅ User {email} updated to superadmin role.")
        else:
            # User doesn't exist - create new superadmin
            print(f"🆕 Creating new superadmin user: {email}...")
            
            # Check if a business exists, or create a default admin business
            result = await db.execute(select(Business).limit(1))
            business = result.scalar_one_or_none()
            
            if not business:
                # Create a default admin business
                business = Business(
                    name="MindRobo Admin",
                    owner_email=email,
                    owner_phone="+10000000000",
                    is_active=True
                )
                db.add(business)
                await db.flush()
                print(f"📦 Created default admin business: {business.name}")
            
            # Create superadmin user
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Superadmin",
                business_id=business.id,
                role="superadmin",
                is_active=True,
                is_verified=True,
                is_trial=False,
                created_at=datetime.utcnow(),
            )
            db.add(user)
            await db.commit()
            print(f"✅ Superadmin user created: {email}")
        
        print(f"\n🎉 Superadmin setup complete!")
        print(f"   Email: {email}")
        print(f"   Role: superadmin")
        print(f"   Status: active, verified, no trial")


def main():
    """Parse CLI arguments and run the seed script."""
    parser = argparse.ArgumentParser(
        description="Create or update a superadmin user for MindRobo API"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Admin email address (e.g., admin@mindrobo.co)"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Admin password (will be hashed before storing)"
    )
    
    args = parser.parse_args()
    
    if not args.email or not args.password:
        print("❌ Error: Both --email and --password are required.", file=sys.stderr)
        sys.exit(1)
    
    # Validate email format (basic check)
    if "@" not in args.email or "." not in args.email:
        print("❌ Error: Invalid email format.", file=sys.stderr)
        sys.exit(1)
    
    # Validate password strength (basic check)
    if len(args.password) < 8:
        print("❌ Error: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)
    
    print(f"🚀 Starting superadmin seed script...\n")
    asyncio.run(create_or_update_superadmin(args.email, args.password))


if __name__ == "__main__":
    main()
