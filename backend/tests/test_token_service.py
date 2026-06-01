from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.core.database import create_db_and_tables, engine
from app.models import RevokedRefreshToken
from app.services.token_service import purge_expired_revocations


def test_purge_expired_revocations_removes_only_expired():
    create_db_and_tables()
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add(
            RevokedRefreshToken(
                jti="expired-jti",
                username="alice",
                expires_at=now - timedelta(hours=1),
            )
        )
        session.add(
            RevokedRefreshToken(
                jti="active-jti",
                username="bob",
                expires_at=now + timedelta(days=1),
            )
        )
        session.commit()

        purge_expired_revocations(session)

        assert session.get(RevokedRefreshToken, "expired-jti") is None
        assert session.get(RevokedRefreshToken, "active-jti") is not None
        session.delete(session.get(RevokedRefreshToken, "active-jti"))
        session.commit()
