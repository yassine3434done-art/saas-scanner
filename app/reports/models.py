# backend/app/reports/models.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.base import Base


class ReportEvent(Base):
    __tablename__ = "report_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.id"), index=True, nullable=True)

    # examples: pdf, pdf_download, pdf_email
    kind = Column(String, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ReportShareLink(Base):
    __tablename__ = "report_share_links"

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.id"), index=True, nullable=False)

    # expires_at stored in UTC
    expires_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)