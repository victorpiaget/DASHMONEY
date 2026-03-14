from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.db import init_db, new_session
from app.domain.profile import Profile
from app.domain.workspace import Workspace
from app.repositories.profile_repository import ProfileRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.sql_identity_models import ProfileAccessRow, ProfileRow, WorkspaceRow


class SqlWorkspaceRepository(WorkspaceRepository):
    def __init__(self) -> None:
        init_db()

    def list_workspaces(self) -> list[Workspace]:
        with new_session() as s:
            rows = s.execute(select(WorkspaceRow).order_by(WorkspaceRow.created_at.asc())).scalars().all()
            return [self._to_domain(r) for r in rows]

    def get_workspace(self, *, workspace_id: str) -> Workspace:
        wid = (workspace_id or "").strip()
        if not wid:
            raise ValueError("workspace_id cannot be empty")
        with new_session() as s:
            row = s.get(WorkspaceRow, wid)
            if row is None:
                raise KeyError(f"unknown workspace_id '{wid}'")
            return self._to_domain(row)

    def create_workspace(self, *, name: str) -> Workspace:
        n = (name or "").strip()
        if not n:
            raise ValueError("name cannot be empty")
        wid = str(uuid4())
        with new_session() as s:
            row = WorkspaceRow(id=wid, name=n)
            s.add(row)
            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: WorkspaceRow) -> Workspace:
        return Workspace(
            id=row.id,
            name=row.name,
            created_at=row.created_at,
        )


class SqlProfileRepository(ProfileRepository):
    def __init__(self) -> None:
        init_db()

    def list_profiles(self, *, workspace_id: str) -> list[Profile]:
        wid = (workspace_id or "").strip()
        if not wid:
            raise ValueError("workspace_id cannot be empty")
        with new_session() as s:
            rows = (
                s.execute(
                    select(ProfileRow)
                    .where(ProfileRow.workspace_id == wid)
                    .order_by(ProfileRow.created_at.asc())
                )
                .scalars()
                .all()
            )
            return [self._to_domain(r) for r in rows]

    def list_all(self) -> list[Profile]:
        with new_session() as s:
            rows = s.execute(select(ProfileRow).order_by(ProfileRow.created_at.asc())).scalars().all()
            return [self._to_domain(r) for r in rows]

    def get_profile(self, *, profile_id: str) -> Profile:
        pid = (profile_id or "").strip()
        if not pid:
            raise ValueError("profile_id cannot be empty")
        with new_session() as s:
            row = s.get(ProfileRow, pid)
            if row is None:
                raise KeyError(f"unknown profile_id '{pid}'")
            return self._to_domain(row)

    def create_profile(self, *, workspace_id: str, display_name: str) -> Profile:
        wid = (workspace_id or "").strip()
        if not wid:
            raise ValueError("workspace_id cannot be empty")
        dn = (display_name or "").strip()
        if not dn:
            raise ValueError("display_name cannot be empty")

        pid = str(uuid4())
        with new_session() as s:
            row = ProfileRow(id=pid, workspace_id=wid, display_name=dn)
            s.add(row)
            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    def delete_profile(self, *, profile_id: str) -> bool:
        pid = (profile_id or "").strip()
        if not pid:
            return False
        with new_session() as s:
            row = s.get(ProfileRow, pid)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def grant_profile_access(self, *, user_id: str, profile_id: str, permission: str = "OWNER") -> None:
        with new_session() as s:
            existing = s.execute(
                select(ProfileAccessRow).where(
                    ProfileAccessRow.profile_id == profile_id,
                    ProfileAccessRow.user_id == user_id,
                )
            ).scalar_one_or_none()
            if existing is None:
                s.add(ProfileAccessRow(profile_id=profile_id, user_id=user_id, permission=permission))
                s.commit()

    def has_profile_access(self, *, user_id: str, profile_id: str) -> bool:
        with new_session() as s:
            row = s.execute(
                select(ProfileAccessRow).where(
                    ProfileAccessRow.profile_id == profile_id,
                    ProfileAccessRow.user_id == user_id,
                )
            ).scalar_one_or_none()
            return row is not None

    def get_default_profile_id_for_user(self, user_id: str) -> str | None:
        """Retourne le premier profil accessible par l'user (ordre stable par profile_id)."""
        with new_session() as s:
            row = s.execute(
                select(ProfileAccessRow)
                .where(ProfileAccessRow.user_id == user_id)
                .order_by(ProfileAccessRow.profile_id.asc())
                .limit(1)
            ).scalar_one_or_none()
            return row.profile_id if row else None

    @staticmethod
    def _to_domain(row: ProfileRow) -> Profile:
        return Profile(
            id=row.id,
            workspace_id=row.workspace_id,
            display_name=row.display_name,
            created_at=row.created_at,
        )