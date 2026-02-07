from app.db.session import engine
from app.db.base import Base

# Import models so SQLAlchemy registers them
from app.users.models import User  # noqa
from app.plans.models import Plan  # noqa
from app.sites.models import Site  # noqa
from app.sites.ownership_models import OwnershipToken  # noqa
from app.scans.models import Scan  # noqa
from app.scans.pages_models import ScanPage  # noqa

def init_db():
    Base.metadata.create_all(bind=engine)