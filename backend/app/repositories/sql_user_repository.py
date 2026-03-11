from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.db import init_db, new_session
from app.domain.user import User
from app.repositories.sql_identity_models import UserRow


class SqlUserRepository:
    def __init__(self) -> None:
        init_db()

    def get(self, user_id: str) -> User:
        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id cannot be empty")
        with new_session() as s:
            row = s.get(UserRow, uid)
            if row is None:
                raise KeyError(f"unknown user_id '{uid}'")
            return self._to_domain(row)

    def get_by_email(self, email: str) -> User | None:
        addr = (email or "").strip().lower()
        if not addr:
            return None
        with new_session() as s:
            row = s.execute(
                select(UserRow).where(UserRow.email == addr)
            ).scalar_one_or_none()
            return self._to_domain(row) if row is not None else None

    def create(self, *, email: str, password_hash: str) -> User:
        addr = (email or "").strip().lower()
        if not addr:
            raise ValueError("email cannot be empty")
        if not password_hash:
            raise ValueError("password_hash cannot be empty")
        uid = str(uuid4())
        with new_session() as s:
            existing = s.execute(
                select(UserRow).where(UserRow.email == addr)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"email '{addr}' already registered")
            row = UserRow(id=uid, email=addr, password_hash=password_hash)
            s.add(row)
            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    def get_password_hash(self, user_id: str) -> str:
        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id cannot be empty")
        with new_session() as s:
            row = s.get(UserRow, uid)
            if row is None:
                raise KeyError(f"unknown user_id '{uid}'")
            return row.password_hash

    @staticmethod
    def _to_domain(row: UserRow) -> User:
        return User(
            id=row.id,
            email=row.email,
            is_disabled=row.is_disabled,
            created_at=row.created_at,
        )
