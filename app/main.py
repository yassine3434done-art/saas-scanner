from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
import asyncio

# ✅ SlowAPI setup
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.ratelimit import limiter, rate_limit_exceeded_handler

from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.plans.seed import seed_plans

from app.auth.routes import router as auth_router
from app.sites.routes import router as sites_router
from app.sites.routes_verification import router as sites_verif_router

from app.scans.routes import router as scans_router
from app.scans.detail_routes import router as scans_detail_router
from app.scans.pages_routes import router as scans_pages_router

from app.scans.cleanup import auto_cleanup_scans
from app.scans.worker import scans_worker_loop

try:
    from app.reports.routes import router as reports_router
except Exception:
    reports_router = None


app = FastAPI(title="SaaS Scanner MVP")

# ✅ attach limiter + middleware + handler
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.on_event("startup")
async def on_startup():
    init_db()

    db = SessionLocal()
    try:
        seed_plans(db)

        result = auto_cleanup_scans(db, queued_ttl_minutes=30, running_ttl_minutes=60)
        if result["fixed_queued"] or result["fixed_running"]:
            print("[startup] cleanup:", result)
    finally:
        db.close()

    asyncio.create_task(scans_worker_loop(poll_seconds=1.0))


app.include_router(auth_router)
app.include_router(sites_router)
app.include_router(sites_verif_router)

app.include_router(scans_detail_router)
app.include_router(scans_router)
app.include_router(scans_pages_router)

if reports_router:
    app.include_router(reports_router)


@app.get("/health")
def health():
    return {"ok": True}