from dotenv import load_dotenv
load_dotenv()

import os
import time
import random
import requests
from sqlalchemy import create_engine, text

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is not set")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

TMDB_SEARCH = "https://api.themoviedb.org/3/search/movie"
IMG_BASE = "https://image.tmdb.org/t/p/w500"

def safe_year(release_date: str | None):
    if not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except:
        return None

def tmdb_lookup(title: str, year: int | None):
    params = {"api_key": TMDB_API_KEY, "query": title, "include_adult": "false"}
    if year:
        params["year"] = year

    r = requests.get(TMDB_SEARCH, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    if not results:
        return None

    best = results[0]
    poster_path = best.get("poster_path")
    return {
        "poster_url": (IMG_BASE + poster_path) if poster_path else None,
        "overview": best.get("overview"),
        "release_date": best.get("release_date"),
    }

def count_missing(conn):
    return int(
        conn.execute(
            text("SELECT COUNT(*) FROM movies WHERE poster_url IS NULL OR poster_url = ''")
        ).scalar()
        or 0
    )

def fetch_batch(conn, batch_size: int):
    return conn.execute(
        text("""
            SELECT movie_id, title, release_date
            FROM movies
            WHERE poster_url IS NULL OR poster_url = ''
            ORDER BY movie_id
            LIMIT :n
        """),
        {"n": batch_size},
    ).mappings().all()

def update_movie(conn, movie_id: int, poster_url: str | None, overview: str | None, release_date: str | None):
    # poster_url yoksa bile “denendi” diye boş bırakmıyoruz; sadece poster varsa update ediyoruz
    if not poster_url:
        return False

    conn.execute(
        text("""
            UPDATE movies
            SET poster_url = :poster_url,
                overview = COALESCE(:overview, overview),
                release_date = COALESCE(:release_date, release_date)
            WHERE movie_id = :movie_id
        """),
        {
            "poster_url": poster_url,
            "overview": overview,
            "release_date": release_date,
            "movie_id": movie_id,
        },
    )
    return True

def main(batch_size=100, sleep_base=0.25, max_empty_rounds=10):
    """
    batch_size: her turda kaç film denenecek
    sleep_base: TMDB rate limit yememek için bekleme
    max_empty_rounds: bir sürü film poster bulamıyorsa sonsuz loop’a girmesin
    """
    empty_rounds = 0

    with engine.begin() as conn:
        missing = count_missing(conn)
    print("START missing:", missing)

    while True:
        with engine.begin() as conn:
            missing = count_missing(conn)
            if missing == 0:
                print("DONE ✅ all poster_url filled")
                break

            rows = fetch_batch(conn, batch_size)

        if not rows:
            print("No rows fetched; stopping.")
            break

        updated = 0
        tried = 0

        for r in rows:
            tried += 1
            mid = int(r["movie_id"])
            title = str(r["title"])
            year = safe_year(r.get("release_date"))

            try:
                info = tmdb_lookup(title, year)
            except requests.HTTPError as e:
                # rate limit vs olursa biraz daha uzun bekle
                print("HTTPError", mid, title, e)
                time.sleep(2.0 + random.random())
                continue
            except Exception as e:
                print("ERR", mid, title, e)
                time.sleep(sleep_base)
                continue

            if info and info.get("poster_url"):
                with engine.begin() as conn:
                    ok = update_movie(
                        conn,
                        movie_id=mid,
                        poster_url=info.get("poster_url"),
                        overview=info.get("overview"),
                        release_date=info.get("release_date"),
                    )
                if ok:
                    updated += 1
                    print("OK", mid, title)

            # küçük jitter → rate limit azaltır
            time.sleep(sleep_base + random.random() * 0.15)

        print(f"ROUND done. tried={tried} updated={updated}")

        if updated == 0:
            empty_rounds += 1
            print("No updates this round. empty_rounds=", empty_rounds)
            # backoff
            time.sleep(3.0)
            if empty_rounds >= max_empty_rounds:
                print("Stopping to avoid infinite loop. Many titles may not match TMDB.")
                break
        else:
            empty_rounds = 0

        with engine.begin() as conn:
            missing = count_missing(conn)
        print("REMAINING missing:", missing)

if __name__ == "__main__":
    main(batch_size=100, sleep_base=0.25, max_empty_rounds=10)
