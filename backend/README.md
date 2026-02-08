# SaaS Scanner (MVP)

Backend: FastAPI + SQLAlchemy\
Email: Resend HTTP API\
Reports: PDF via ReportLab + share links

## Requirements

-   Python 3.11+ (recommended)
-   (Optional) Postgres for production (Render)

## Local Setup (Windows / PowerShell)

``` powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Environment

Create `backend/.env` and set: - DATABASE_URL - JWT_SECRET -
RESEND_API_KEY - PUBLIC_BASE_URL (optional locally)

### Run API

``` powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health:

``` powershell
curl.exe http://127.0.0.1:8000/health
```

## Auth test

``` powershell
$login = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/auth/login" `
  -ContentType "application/json" `
  -Body (@{ email="test@example.com"; password="Pass1234!" } | ConvertTo-Json)

$headers = @{ Authorization = "Bearer $($login.access_token)" }
```

## Email report (Paid)

``` powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/reports/email?to_email=someone@gmail.com&scan_id=5" `
  -Headers $headers
```

## Render deploy

``` bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
