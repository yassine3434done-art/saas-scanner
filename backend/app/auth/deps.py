import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer(auto_error=False)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")

    api_key = os.getenv("MVP_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="MVP_API_KEY not set on server")

    if creds.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid token")

    # MVP: كنرجعو user بسيط بلا DB
    return {"id": 1, "email": "mvp@local"}