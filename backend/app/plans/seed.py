from sqlalchemy.orm import Session
from app.plans.models import Plan

FREE = dict(
    name="free",
    max_sites=1,
    crawl_limit=200,
    max_duration_min=15,
    allow_deep_scan=False,
    allow_scheduling=False,
    allow_history=False,
    priority_queue=False
)

PAID = dict(
    name="paid",
    max_sites=10,
    crawl_limit=10000,
    max_duration_min=120,
    allow_deep_scan=True,
    allow_scheduling=True,
    allow_history=True,
    priority_queue=True
)

def seed_plans(db: Session):
    for p in (FREE, PAID):
        exists = db.query(Plan).filter(Plan.name == p["name"]).first()
        if not exists:
            db.add(Plan(**p))
    db.commit()