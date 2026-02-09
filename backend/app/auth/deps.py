import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.users.models import User

bearer = HTTPBearer(auto_error=False)

API_TOKEN = (os.getenv("API_TOKEN") or "").strip()

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")

    token = (creds.credentials or "").strip()

    # ✅ MVP: allow fixed token (no login/register)
    if API_TOKEN and token == API_TOKEN:
        # fake admin user (no DB needed)
        return {"id": 0, "email": "mvp@local", "is_mvp": True}

    # ✅ normal JWT flow (if you later implement real auth)
    try:
        user_id = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user