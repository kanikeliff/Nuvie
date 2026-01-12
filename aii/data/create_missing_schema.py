from __future__ import annotations

import os
import sys
from sqlalchemy import create_engine, text


# Database connection string
# NOTE: In practice, this should come from an environment variable.
DATABASE_URL = "postgresql://neondb_owner:***@ep-restless-art-ah6dr023-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

try:
    engine = create_engine(DATABASE_URL)
    print("Database connection established.")
except Exception as e:
    print(f"FATAL: Could not establish DB connection. Error: {e}")
    sys.exit(1)


def create_remaining_tables(engine):
    """
    Creates additional database tables that are not provided by the MovieLens dataset.

    These tables support:
    - Social relationships between users
    - User watch behavior logs
    - Storing precomputed recommendation results

    They are designed for future features and do not affect the core recommendation logic.
    """

    print("\n[START] Creating missing social and logging schemas...")

    # --------------------------------------------------
    # FRIENDS table
    # Stores social relationships between users.
    # Each row represents a directed relationship.
    # --------------------------------------------------
    friends_table = text("""
        CREATE TABLE IF NOT EXISTS friends (
            user_id_1 INTEGER REFERENCES users(user_id),
            user_id_2 INTEGER REFERENCES users(user_id),
            status VARCHAR(20) NOT NULL, -- e.g. 'pending', 'accepted', 'blocked'
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (user_id_1, user_id_2)
        );
    """)

    # --------------------------------------------------
    # WATCH_EVENTS table
    # Logs implicit user feedback such as watching progress.
    # This data can be used later for online or hybrid models.
    # --------------------------------------------------
    watch_events_table = text("""
        CREATE TABLE IF NOT EXISTS watch_events (
            event_id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            movie_id INTEGER REFERENCES movies(movie_id),
            event_type VARCHAR(50) NOT NULL, -- e.g. 'started', 'completed', 'paused'
            progress_percent INTEGER,
            timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """)

    # --------------------------------------------------
    # RECOMMENDATION_FEED table
    # Stores the latest recommendation list per user.
    # This avoids recomputing recommendations on every request.
    # --------------------------------------------------
    recommendation_feed_table = text("""
        CREATE TABLE IF NOT EXISTS recommendation_feed (
            feed_id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE REFERENCES users(user_id),
            movie_id_list INTEGER[], -- ordered list of recommended movie IDs
            last_calculated TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """)

    # Execute schema creation inside a transaction
    with engine.begin() as connection:
        connection.execute(friends_table)
        connection.execute(watch_events_table)
        connection.execute(recommendation_feed_table)

    print("✅ Missing schemas (friends, watch_events, recommendation_feed) created.")


if __name__ == '__main__':
    create_remaining_tables(engine)
    print("\n--------------------------------------------------")
