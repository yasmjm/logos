from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import DUMMY_PASSWORD_HASH, verify_password
from app.models import Analyst


def authenticate(db: Session, username: str, password: str) -> Analyst | None:
    analyst = db.scalars(select(Analyst).where(Analyst.username == username)).one_or_none()
    # Always run the (slow) hash check so unknown users take as long as wrong passwords.
    password_hash = analyst.password_hash if analyst else DUMMY_PASSWORD_HASH
    if not verify_password(password, password_hash) or analyst is None:
        return None
    return analyst
