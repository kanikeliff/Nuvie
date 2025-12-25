from sqlalchemy import Column, Integer, String
from backend.session import Base


class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    poster_url = Column(String)
    overview = Column(String)
    release_date = Column(String)
