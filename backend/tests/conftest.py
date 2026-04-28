# backend/tests/conftest.py
import os
os.environ.setdefault("DASHMONEY_SECRET_KEY", "test-secret-key-for-tests-only")

import pytest
from sqlalchemy import select, text

from app.db import get_engine, get_session_factory
from app.db_base import Base
from app.identity.auth import hash_password
from app.identity.defaults import (
    DEFAULT_PROFILE_ID,
    DEFAULT_PROFILE_NAME,
    DEFAULT_PROFILE2_ID,
    DEFAULT_PROFILE2_NAME,
    DEFAULT_TEST_PASSWORD,
    DEFAULT_USER_EMAIL,
    DEFAULT_USER_ID,
    DEFAULT_USER2_EMAIL,
    DEFAULT_USER2_ID,
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE2_ID,
    DEFAULT_WORKSPACE2_NAME,
)
from app.repositories.sql_identity_models import (
    ProfileAccessRow,
    ProfileRow,
    UserRow,
    WorkspaceMembershipRow,
    WorkspaceProfileLinkRow,
    WorkspaceRow,
)

# Pre-compute once — bcrypt is intentionally slow, no need to re-hash 114 times
_HASHED_TEST_PASSWORD = hash_password(DEFAULT_TEST_PASSWORD)


def _import_models() -> None:
    # Ensure all models are registered on Base.metadata.
    from app.repositories import sql_account_repository  # noqa: F401
    from app.repositories import sql_transaction_repository  # noqa: F401
    from app.repositories import sql_instrument_repository  # noqa: F401
    from app.repositories import sql_trade_repository  # noqa: F401
    from app.repositories import sql_portfolio_repository  # noqa: F401
    from app.repositories import sql_portfolio_snapshot_repository  # noqa: F401
    from app.repositories import sql_price_repository  # noqa: F401
    from app.repositories import sql_identity_models  # noqa: F401
    from app.repositories import sql_category_repository  # noqa: F401
    from app.repositories import sql_budget_envelope_repository  # noqa: F401


def _seed_default_identity() -> None:
    SessionLocal = get_session_factory()
    with SessionLocal() as s:
        # --- 1) Parents: user + workspace ---
        if s.get(UserRow, DEFAULT_USER_ID) is None:
            s.add(
                UserRow(
                    id=DEFAULT_USER_ID,
                    email=DEFAULT_USER_EMAIL,
                    password_hash=_HASHED_TEST_PASSWORD,
                    is_disabled=False,
                )
            )

        if s.get(WorkspaceRow, DEFAULT_WORKSPACE_ID) is None:
            s.add(
                WorkspaceRow(
                    id=DEFAULT_WORKSPACE_ID,
                    name=DEFAULT_WORKSPACE_NAME,
                )
            )

        # Force insert of parents first (so workspace exists for profile FK)
        s.flush()

        # --- 2) Child: profile (depends on workspace_id FK) ---
        if s.get(ProfileRow, DEFAULT_PROFILE_ID) is None:
            s.add(
                ProfileRow(
                    id=DEFAULT_PROFILE_ID,
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    display_name=DEFAULT_PROFILE_NAME,
                )
            )

        # Force insert of profile before profile_access FK
        s.flush()

        # --- 3) workspace_profile_link (required by list_profiles JOIN) ---
        link1 = s.execute(
            select(WorkspaceProfileLinkRow).where(
                WorkspaceProfileLinkRow.workspace_id == DEFAULT_WORKSPACE_ID,
                WorkspaceProfileLinkRow.profile_id == DEFAULT_PROFILE_ID,
            )
        ).scalar_one_or_none()
        if link1 is None:
            s.add(WorkspaceProfileLinkRow(workspace_id=DEFAULT_WORKSPACE_ID, profile_id=DEFAULT_PROFILE_ID))

        # --- 4) FK rows: workspace_membership + profile_access ---
        membership = s.execute(
            select(WorkspaceMembershipRow).where(
                WorkspaceMembershipRow.workspace_id == DEFAULT_WORKSPACE_ID,
                WorkspaceMembershipRow.user_id == DEFAULT_USER_ID,
            )
        ).scalar_one_or_none()
        if membership is None:
            s.add(
                WorkspaceMembershipRow(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    user_id=DEFAULT_USER_ID,
                    role="OWNER",
                )
            )

        access = s.execute(
            select(ProfileAccessRow).where(
                ProfileAccessRow.profile_id == DEFAULT_PROFILE_ID,
                ProfileAccessRow.user_id == DEFAULT_USER_ID,
            )
        ).scalar_one_or_none()
        if access is None:
            s.add(
                ProfileAccessRow(
                    profile_id=DEFAULT_PROFILE_ID,
                    user_id=DEFAULT_USER_ID,
                    permission="ADMIN",
                )
            )

        # --- User 2 : workspace + profil isolés ---
        if s.get(UserRow, DEFAULT_USER2_ID) is None:
            s.add(
                UserRow(
                    id=DEFAULT_USER2_ID,
                    email=DEFAULT_USER2_EMAIL,
                    password_hash=_HASHED_TEST_PASSWORD,
                    is_disabled=False,
                )
            )

        if s.get(WorkspaceRow, DEFAULT_WORKSPACE2_ID) is None:
            s.add(
                WorkspaceRow(
                    id=DEFAULT_WORKSPACE2_ID,
                    name=DEFAULT_WORKSPACE2_NAME,
                )
            )

        s.flush()

        if s.get(ProfileRow, DEFAULT_PROFILE2_ID) is None:
            s.add(
                ProfileRow(
                    id=DEFAULT_PROFILE2_ID,
                    workspace_id=DEFAULT_WORKSPACE2_ID,
                    display_name=DEFAULT_PROFILE2_NAME,
                )
            )

        s.flush()

        link2 = s.execute(
            select(WorkspaceProfileLinkRow).where(
                WorkspaceProfileLinkRow.workspace_id == DEFAULT_WORKSPACE2_ID,
                WorkspaceProfileLinkRow.profile_id == DEFAULT_PROFILE2_ID,
            )
        ).scalar_one_or_none()
        if link2 is None:
            s.add(WorkspaceProfileLinkRow(workspace_id=DEFAULT_WORKSPACE2_ID, profile_id=DEFAULT_PROFILE2_ID))

        s.flush()

        membership2 = s.execute(
            select(WorkspaceMembershipRow).where(
                WorkspaceMembershipRow.workspace_id == DEFAULT_WORKSPACE2_ID,
                WorkspaceMembershipRow.user_id == DEFAULT_USER2_ID,
            )
        ).scalar_one_or_none()
        if membership2 is None:
            s.add(
                WorkspaceMembershipRow(
                    workspace_id=DEFAULT_WORKSPACE2_ID,
                    user_id=DEFAULT_USER2_ID,
                    role="OWNER",
                )
            )

        access2 = s.execute(
            select(ProfileAccessRow).where(
                ProfileAccessRow.profile_id == DEFAULT_PROFILE2_ID,
                ProfileAccessRow.user_id == DEFAULT_USER2_ID,
            )
        ).scalar_one_or_none()
        if access2 is None:
            s.add(
                ProfileAccessRow(
                    profile_id=DEFAULT_PROFILE2_ID,
                    user_id=DEFAULT_USER2_ID,
                    permission="ADMIN",
                )
            )

        s.commit()


@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.getenv("DASHMONEY_TEST_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "Set DASHMONEY_TEST_DATABASE_URL : "
            "Postgres ('postgresql+psycopg://...') ou SQLite ('sqlite:///./test.db')."
        )

    os.environ["DASHMONEY_DATABASE_URL"] = url
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    return url


@pytest.fixture(scope="session")
def db_engine(db_url: str):
    _import_models()
    return get_engine()


@pytest.fixture(scope="session", autouse=True)
def db_schema(db_engine) -> None:
    Base.metadata.drop_all(bind=db_engine)
    Base.metadata.create_all(bind=db_engine)
    _seed_default_identity()


@pytest.fixture(autouse=True)
def db_reset(db_engine) -> None:
    dialect = db_engine.dialect.name
    sorted_tables = list(Base.metadata.sorted_tables)
    if not sorted_tables:
        _seed_default_identity()
        return

    if dialect == "postgresql":
        table_names = [f'"{t.name}"' for t in sorted_tables]
        with db_engine.begin() as conn:
            conn.execute(
                text(f"TRUNCATE {', '.join(table_names)} RESTART IDENTITY CASCADE")
            )
    elif dialect == "sqlite":
        # SQLite n'a pas TRUNCATE CASCADE : on désactive les FK puis DELETE
        # dans l'ordre inverse de création (sécurité supplémentaire).
        with db_engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys = OFF")
            for table in reversed(sorted_tables):
                conn.execute(text(f'DELETE FROM "{table.name}"'))
            conn.exec_driver_sql("PRAGMA foreign_keys = ON")
    else:
        raise RuntimeError(f"Dialect non supporté pour les tests : {dialect}")

    _seed_default_identity()


@pytest.fixture(scope="session")
def auth_headers(db_schema) -> dict:
    from fastapi.testclient import TestClient
    from app.api.main import app

    with TestClient(app) as c:
        resp = c.post("/auth/login", json={"email": DEFAULT_USER_EMAIL, "password": DEFAULT_TEST_PASSWORD})
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def auth_headers_user2(db_schema) -> dict:
    from fastapi.testclient import TestClient
    from app.api.main import app

    with TestClient(app) as c:
        resp = c.post("/auth/login", json={"email": DEFAULT_USER2_EMAIL, "password": DEFAULT_TEST_PASSWORD})
        assert resp.status_code == 200, f"Login user2 failed: {resp.text}"
        token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(db_engine, db_url: str, auth_headers: dict):
    from fastapi.testclient import TestClient
    from app.api.main import app

    with TestClient(app) as test_client:
        test_client.headers.update(auth_headers)
        yield test_client
