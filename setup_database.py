#!/usr/bin/env python3
"""
Setup script to create database tables and load MovieLens data.
Run this after setting DATABASE_URL in .env file.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.session import create_tables, engine
from aii.data.load_movielens_data import load_ratings, load_movies, load_users, verify_load

def main():
    print("🚀 Starting Nuvie Database Setup...")

    # Check DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set. Please update .env file with your database connection string.")
        sys.exit(1)

    print(f"✅ Database URL found: {database_url[:50]}...")

    try:
        # Create tables
        print("📋 Creating database tables...")
        create_tables()
        print("✅ Tables created successfully")

        # Load MovieLens data
        print("📊 Loading MovieLens data...")
        ratings_count = load_ratings()
        movies_count = load_movies()
        users_count = load_users()

        # Verify
        success = verify_load(ratings_count, movies_count, users_count)
        if success:
            print("🎉 Setup completed successfully!")
            print("You can now run the backend and AI services.")
        else:
            print("⚠️  Setup completed with warnings. Check the logs above.")

    except Exception as e:
        print(f"❌ ERROR during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()