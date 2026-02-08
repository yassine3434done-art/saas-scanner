from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), index=True, nullable=False)

    scan_type = Column(String, nullable=False)  # public | deep (later)
    status = Column(String, nullable=False, default="queued")  # queued|running|done|failed

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    summary = Column(JSON, nullable=True)  # headers/tls/crawl metrics
    error = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())