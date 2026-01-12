import os
import sys
from sqlalchemy import create_engine, text


# Paste your connection string here
# NOTE: In a real deployment, this should come from an environment variable.
DATABASE_URL = "postgresql://neondb_owner:npg_ANY0Q7uFlZSi@ep-restless-art-ah6dr023-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

try:
    engine = create_engine(DATABASE_URL)
    print("Database connection established for key fix.")
except Exception as e:
    print(f"FATAL: DB connection error. Error: {e}")
    sys.exit(1)


def fix_missing_primary_keys(engine):
    """
    Adds PRIMARY KEY constraints so Foreign Key constraints can work correctly.

    - users.user_id as PRIMARY KEY
    - movies.movie_id as PRIMARY KEY
    - ratings (user_id, movie_id) as a composite PRIMARY KEY
      (prevents duplicate ratings for the same user/movie pair)
    """
    print("\n[START] Fixing missing Primary Keys...")

    # Add PRIMARY KEY to users(user_id)
    fix_users_pk = text("ALTER TABLE users ADD PRIMARY KEY (user_id);")

    # Add PRIMARY KEY to movies(movie_id) for future FK references
    fix_movies_pk = text("ALTER TABLE movies ADD PRIMARY KEY (movie_id);")

    # Add a composite PRIMARY KEY to ratings(user_id, movie_id)
    fix_ratings_pk = text("ALTER TABLE ratings ADD PRIMARY KEY (user_id, movie_id);")

    with engine.begin() as connection:
        # If a PK already exists, ALTER TABLE will fail.
        # In our MovieLens ETL, we did not add PKs, so we can add them directly.

        connection.execute(fix_users_pk)
        print("-> PRIMARY KEY added to 'users' (user_id).")

        connection.execute(fix_movies_pk)
        print("-> PRIMARY KEY added to 'movies' (movie_id).")

        connection.execute(fix_ratings_pk)
        print("-> PRIMARY KEY added to 'ratings' (user_id, movie_id).")

    print("✅ Primary Key fix complete.")


if __name__ == "__main__":
    fix_missing_primary_keys(engine)
    print("\n--------------------------------------------------")
