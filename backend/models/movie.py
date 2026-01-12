from sqlalchemy import Column, Integer, String, Date
from backend.session import Base

class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)

    poster_url = Column(String, nullable=True)
    overview = Column(String, nullable=True)
    release_date = Column(Date, nullable=True)

    year = Column(Integer, nullable=True)
