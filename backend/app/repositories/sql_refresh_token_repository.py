from __future__ import annotations

import datetime as dt
from uuid import uuid4

from sqlalchemy import select

from app.db import init_db, new_session
from app.domain.refresh_token import RefreshToken
from app.repositories.sql_identity_models import RefreshTokenRow


class SqlRefreshTokenRepository:
    def __init__(self) -> None:
        init_db()

    def create(self, *, user_id: str, token_hash: str, expires_at: dt.datetime) -> RefreshToken:
        row = RefreshTokenRow(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        with new_session() as s:
            s.add(row)
            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        with new_session() as s:
            row = s.execute(
                select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
            ).scalar_one_or_none()
            return self._to_domain(row) if row is not None else None

    def revoke(self, token_id: str) -> None:
        with new_session() as s:
            row = s.get(RefreshTokenRow, token_id)
            if row is not None:
                row.revoked = True
                s.commit()

    def revoke_all_for_user(self, user_id: str) -> None:
        with new_session() as s:
            rows = s.execute(
                select(RefreshTokenRow).where(
                    RefreshTokenRow.user_id == user_id,
                    RefreshTokenRow.revoked == False,  # noqa: E712
                )
            ).scalars().all()
            for row in rows:
                row.revoked = True
            s.commit()

    @staticmethod
    def _to_domain(row: RefreshTokenRow) -> RefreshToken:
        return RefreshToken(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            expires_at=row.expires_at,
            revoked=row.revoked,
            created_at=row.created_at,
        )
