from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.plans.models import Plan
from app.users.models import User


def get_user_plan(db: Session, user: User) -> Plan:
    plan = db.query(Plan).filter(Plan.id == user.plan_id).first()
    if not plan:
        raise HTTPException(status_code=500, detail="Plan missing")
    return plan