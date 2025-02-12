from fastapi_users.db import SQLAlchemyBaseUserTable
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate  # ✅ Fixed imports
from sqlalchemy import Column, Integer, String
from database import Base

# ✅ Define the SQLAlchemy User model
class User(Base, SQLAlchemyBaseUserTable):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)  # ✅ Ensure passwords are stored **hashed**

# ✅ Define Pydantic User Schemas for FastAPI Users
class UserRead(BaseUser):  # ✅ Use BaseUser instead of BaseUserDB
    pass

class UserCreate(BaseUserCreate):
    pass

class UserUpdate(BaseUserUpdate):
    pass
