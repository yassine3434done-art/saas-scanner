# backend/app/auth/deps.py

import os
from types import SimpleNamespace

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.users.models import User

bearer = HTTPBearer(auto_error=False)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")

    token = (creds.credentials or "").strip()

    # ✅ MVP token (temporary for MVP)
    mvp_token = (os.getenv("MVP_TOKEN") or "").strip()
    if mvp_token and token == mvp_token:
        # نرجع "user" بسيط باش الكود اللي كيتوقع current_user.id ما يطيحش
        return SimpleNamespace(id=0, email="mvp@local", is_mvp=True)

    # ✅ Normal JWT flow
    try:
        user_id = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user