"""Create movies table and insert a small sample for local development.

Run: PYTHONPATH=. python3 backend/create_movies.py
"""
from backend.session import engine, SessionLocal, Base
from backend.models.movie import Movie
from backend.models.user import User
from backend.app.auth_utils import hash_password


def create_tables():
    Base.metadata.create_all(bind=engine)


def seed_sample():
    db = SessionLocal()
    try:
        # If there are already movies, skip seeding
        existing = db.query(Movie).first()
        if existing:
            print("Movies already exist, skipping movie seed")
        else:
            db.add(m)
            db.commit()
            print("Inserted sample movie with id:", m.movie_id)
        m = Movie(
            title="The Example Movie",
            poster_url="https://example.com/poster.jpg",
            overview="A sample movie created for local dev.",
            release_date="2020-01-01",
        )

        # ensure a test user exists for auth tests; always upsert password hash
        user = db.query(User).filter(User.email == 'dev@example.com').first()
        if not user:
            u = User(id="dev-user-1", email="dev@example.com", password_hash=hash_password("password"))
            db.add(u)
            db.commit()
            print("Inserted sample user dev@example.com")
        else:
            user.password_hash = hash_password("password")
            db.add(user)
            db.commit()
            print("Updated sample user password for dev@example.com")
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    seed_sample()
