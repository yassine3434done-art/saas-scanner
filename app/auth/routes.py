from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.users.models import User
from app.plans.models import Plan
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthBody(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(body: AuthBody, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    password = body.password

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    free_plan = db.query(Plan).filter(Plan.name == "free").first()
    if not free_plan:
        raise HTTPException(status_code=500, detail="Plans not seeded")

    try:
        pwd_hash = hash_password(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = User(email=email, password_hash=pwd_hash, plan_id=free_plan.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.id)}

@router.post("/login")
def login(body: AuthBody, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    password = body.password

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"access_token": create_access_token(user.id)}