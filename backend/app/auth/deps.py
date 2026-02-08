from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.users.models import User
import os

bearer = HTTPBearer(auto_error=False)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")

    token = creds.credentials.strip()

    # ✅ MVP: allow fixed token from env (no JWT)
    mvp = (os.getenv("MVP_TOKEN") or "").strip()
    if mvp and token == mvp:
        # رجّع user وهمي باش باقي الكود يخدم
        return User(id=1, email="mvp@local", is_active=True)

    # ✅ otherwise fallback to JWT
    try:
        user_id = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user