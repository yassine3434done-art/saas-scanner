from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_admin = Column(Boolean, default=False)
    plan_id = Column(Integer, ForeignKey("plans.id"))
