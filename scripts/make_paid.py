from app.db.session import SessionLocal
from app.users.models import User
from app.plans.models import Plan

EMAIL = "test@example.com"
PAID_PLAN_NAME = "paid"  # must match Plan.name in DB

def main():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        if not user:
            raise SystemExit(f"User not found: {EMAIL}")

        paid = db.query(Plan).filter(Plan.name == PAID_PLAN_NAME).first()
        if not paid:
            # helpful debug: list available plans
            plans = db.query(Plan).all()
            print("Available plans:", [(p.id, p.name) for p in plans])
            raise SystemExit(f"Plan not found: {PAID_PLAN_NAME}")

        user.plan_id = paid.id
        db.commit()
        print(f"OK: {EMAIL} -> plan={paid.name} (id={paid.id})")
    finally:
        db.close()

if __name__ == "__main__":
    main()