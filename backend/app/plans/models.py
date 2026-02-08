from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    max_sites = Column(Integer)
    crawl_limit = Column(Integer)
    max_duration_min = Column(Integer)

    allow_deep_scan = Column(Boolean)
    allow_scheduling = Column(Boolean)
    allow_history = Column(Boolean)
    priority_queue = Column(Boolean)
