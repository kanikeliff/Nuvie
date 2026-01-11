from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    gender = Column(String(1))
    age = Column(Integer)
    occupation = Column(Integer)
    zip_code = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
