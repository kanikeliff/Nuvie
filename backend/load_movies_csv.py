"""Load movies from aii/data/processed/movies.csv into the movies table.

Run: PYTHONPATH=. python3 backend/load_movies_csv.py
"""
import csv
from pathlib import Path

from backend.session import SessionLocal, engine, Base
from backend.models.movie import Movie


CSV_PATH = Path("aii/data/processed/movies.csv")


def create_tables():
    Base.metadata.create_all(bind=engine)


def load_csv():
    if not CSV_PATH.exists():
        print("CSV not found:", CSV_PATH)
        return

    db = SessionLocal()
    try:
        with CSV_PATH.open(newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            count = 0
            for row in reader:
                try:
                    mid = int(row.get('movie_id') or 0)
                except Exception:
                    continue

                title = row.get('title') or row.get('clean_title') or ''
                year = row.get('year') or ''
                release_date = f"{year}-01-01" if year else None

                # minimal placeholders for missing fields
                poster_url = row.get('poster_url') or None
                overview = row.get('overview') or None

                existing = db.query(Movie).filter(Movie.movie_id == mid).first()
                if existing:
                    existing.title = title
                    existing.release_date = release_date
                    existing.poster_url = poster_url
                    existing.overview = overview
                else:
                    m = Movie(movie_id=mid, title=title, poster_url=poster_url, overview=overview, release_date=release_date)
                    db.add(m)

                count += 1
                if count % 500 == 0:
                    db.commit()
                    print(f"Processed {count} rows")

            db.commit()
            print(f"Loaded {count} movies")
    finally:
        db.close()


if __name__ == '__main__':
    create_tables()
    load_csv()
