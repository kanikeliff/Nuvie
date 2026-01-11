from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    user_id: int
    gender: Optional[str]
    age: Optional[int]
    occupation: Optional[int]
    zip_code: Optional[str]

class UserCreate(UserBase):
    pass

class User(UserBase):
    created_at: datetime

    class Config:
        from_attributes = True
