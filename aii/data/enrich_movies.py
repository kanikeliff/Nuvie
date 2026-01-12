import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text
from tmdbv3api import Search, TMDb


# --- CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

if not DATABASE_URL:
    print("FATAL: DATABASE_URL env var is missing.")
    sys.exit(1)

if not TMDB_API_KEY:
    print("FATAL: TMDB_API_KEY env var is missing.")
    sys.exit(1)

POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Initialize database engine
try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    print(f"FATAL: Could not establish DB connection. Error: {e}")
    sys.exit(1)

# Initialize TMDb API
tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
tmdb.language = "en"
search = Search()

print("Configuration loaded. Starting enrichment process.")


def enrich_movies_data():
    """
    Fetches movie titles from DB, searches TMDb for metadata (posters, overview),
    and updates the 'movies' table with the new data.
    """
    print("\n[STEP 1/4] Extracting movies from PostgreSQL...")
    query = "SELECT movie_id, title FROM movies"
    movies_df = pd.read_sql(query, con=engine)
    print(f"Found {len(movies_df)} movies to enrich.")

    print("[STEP 2/4] Searching TMDb for metadata (This may take a few minutes)...")

    # Add columns if needed
    with engine.begin() as connection:
        for stmt in [
            "ALTER TABLE movies ADD COLUMN IF NOT EXISTS tmdb_id INTEGER;",
            "ALTER TABLE movies ADD COLUMN IF NOT EXISTS poster_url TEXT;",
            "ALTER TABLE movies ADD COLUMN IF NOT EXISTS overview TEXT;",
            "ALTER TABLE movies ADD COLUMN IF NOT EXISTS release_date TEXT;",
        ]:
            connection.execute(text(stmt))

    update_query = text(
        """
        UPDATE movies
        SET tmdb_id = :tmdb_id,
            poster_url = :poster_url,
            overview = :overview,
            release_date = :release_date
        WHERE movie_id = :movie_id
        """
    )

    for index, row in movies_df.iterrows():
        movie_title = row["title"]
        movie_id = row["movie_id"]

        if index % 100 == 0:
            print(f"   Processing: {index}/{len(movies_df)} - {movie_title}")

        # MovieLens title usually ends with " (YYYY)"
        clean_title = movie_title[:-6].strip() if movie_title.endswith(")") else movie_title

        try:
            results = search.movies(clean_title)
            if not results or not results[0].id:
                continue

            result = results[0]
            poster_path = result.poster_path
            full_poster_url = f"{POSTER_BASE_URL}{poster_path}" if poster_path else None

            with engine.begin() as connection:
                connection.execute(
                    update_query,
                    {
                        "tmdb_id": result.id,
                        "poster_url": full_poster_url,
                        "overview": result.overview,
                        "release_date": result.release_date,
                        "movie_id": movie_id,
                    },
                )
        except Exception:
            # If rate limit / transient error, skip and continue.
            continue

    print("\n[STEP 3/4] TMDb enrichment complete.")

    print("[STEP 4/4] Verifying updated data...")
    check_query = """
        SELECT movie_id, title, tmdb_id, poster_url
        FROM movies
        WHERE poster_url IS NOT NULL
        LIMIT 5
    """
    verified_movies = pd.read_sql(check_query, con=engine)

    print("\nSuccessfully enriched sample movies:")
    print(verified_movies[["title", "tmdb_id", "poster_url"]])


if __name__ == "__main__":
    try:
        enrich_movies_data()
        print("\nSUCCESS: All movies have been searched and database updated!")
    except Exception as e:
        print(f"\nFATAL ERROR: Enrichment process failed. Error: {e}")
        sys.exit(1)
