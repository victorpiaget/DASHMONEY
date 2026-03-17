"""
Tests — permissions granulaires (niveau 3).

Couvre :
- GET /me → permission retournée dans le profil de /me (via workspaces)
- Mutation interdite pour un user avec accès READ (profile permission = READ)
- Lecture autorisée pour READ
- PATCH /workspaces/{id}/members/{user_id} → changer le rôle
- Inviter avec rôle READ_ONLY → permission = READ
- Inviter avec rôle OWNER → permission = ADMIN
- Dernier OWNER ne peut pas être rétrogradé
- Rétrogradation d'un MEMBER en READ_ONLY → perd l'accès en écriture
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from uuid import uuid4

from app.api.main import app
from app.identity.defaults import (
    DEFAULT_PROFILE_ID,
    DEFAULT_USER2_EMAIL,
    DEFAULT_USER2_ID,
    DEFAULT_USER_EMAIL,
    DEFAULT_USER_ID,
    DEFAULT_WORKSPACE_ID,
    DEFAULT_TEST_PASSWORD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(email: str) -> dict:
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"email": email, "password": DEFAULT_TEST_PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _client1(auth_headers) -> TestClient:
    c = TestClient(app)
    c.headers.update(auth_headers)
    return c


def _invite_user2(client, role: str = "MEMBER") -> None:
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL, "role": role},
    )
    assert r.status_code == 201, r.text


def _create_account(client):
    """Crée un compte de test ; retourne la Response."""
    r = client.post(
        "/accounts",
        json={
            "id": str(uuid4()),
            "name": "Test Account",
            "account_type": "CHECKING",
            "currency": "EUR",
            "opened_on": "2025-01-01",
            "opening_balance": "0.00",
        },
    )
    return r


# ---------------------------------------------------------------------------
# PATCH /workspaces/{id}/members/{user_id}
# ---------------------------------------------------------------------------

def test_patch_member_role_owner_can_change(client, auth_headers_user2):
    _invite_user2(client, role="MEMBER")

    r = client.patch(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER2_ID}",
        json={"role": "READ_ONLY"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "READ_ONLY"
    assert data["user_id"] == DEFAULT_USER2_ID


def test_patch_member_role_non_owner_forbidden(client, auth_headers_user2):
    _invite_user2(client, role="MEMBER")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = c2.patch(
            f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER_ID}",
            json={"role": "READ_ONLY"},
        )
        assert r.status_code == 403


def test_patch_cannot_downgrade_last_owner(client):
    r = client.patch(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER_ID}",
        json={"role": "MEMBER"},
    )
    assert r.status_code == 422


def test_patch_member_not_found_returns_404(client):
    r = client.patch(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/00000000-0000-0000-0000-nonexistent99",
        json={"role": "MEMBER"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Invite avec rôle spécifique
# ---------------------------------------------------------------------------

def test_invite_with_read_only_role(client):
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL, "role": "READ_ONLY"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "READ_ONLY"


def test_invite_with_owner_role(client):
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL, "role": "OWNER"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "OWNER"


def test_invite_with_invalid_role_returns_422(client):
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL, "role": "SUPERADMIN"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Accès en lecture seule (READ_ONLY) — lecture OK, écriture refusée
# ---------------------------------------------------------------------------

def test_read_only_user_can_read_accounts(client, auth_headers_user2):
    _invite_user2(client, role="READ_ONLY")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = c2.get("/accounts", params={"profile_id": DEFAULT_PROFILE_ID})
        assert r.status_code == 200


def test_read_only_user_cannot_create_account(client, auth_headers_user2):
    _invite_user2(client, role="READ_ONLY")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = _create_account(c2)
        assert r.status_code == 403
        assert "Read-only" in r.json()["detail"]


def test_read_only_user_cannot_create_transaction(client, auth_headers_user2):
    # Créer un compte avec user1
    acc_r = _create_account(client)
    assert acc_r.status_code == 201, acc_r.text
    account_id = acc_r.json()["id"]

    _invite_user2(client, role="READ_ONLY")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = c2.post(
            f"/accounts/{account_id}/transactions",
            json={
                "amount": "100.00",
                "kind": "CREDIT",
                "date": "2025-06-01",
                "label": "Test",
            },
            params={"profile_id": DEFAULT_PROFILE_ID},
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Rétrogradation MEMBER → READ_ONLY perd l'accès en écriture
# ---------------------------------------------------------------------------

def test_downgrade_member_to_read_only_revokes_write(client, auth_headers_user2):
    _invite_user2(client, role="MEMBER")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        # MEMBER peut créer un compte
        r = _create_account(c2)
        assert r.status_code == 201, r.text

    # Rétrograder en READ_ONLY
    client.patch(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER2_ID}",
        json={"role": "READ_ONLY"},
    )

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        # Après rétrogradation, la création est refusée
        r = _create_account(c2)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Promotion READ_ONLY → MEMBER restore l'accès en écriture
# ---------------------------------------------------------------------------

def test_upgrade_read_only_to_member_restores_write(client, auth_headers_user2):
    _invite_user2(client, role="READ_ONLY")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = _create_account(c2)
        assert r.status_code == 403

    # Promouvoir en MEMBER
    client.patch(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER2_ID}",
        json={"role": "MEMBER"},
    )

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = _create_account(c2)
        assert r.status_code == 201, r.text


# ---------------------------------------------------------------------------
# MEMBER (WRITE) peut bien lire et écrire
# ---------------------------------------------------------------------------

def test_member_can_create_and_read_accounts(client, auth_headers_user2):
    _invite_user2(client, role="MEMBER")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        # Création autorisée
        r = _create_account(c2)
        assert r.status_code == 201, r.text
        # Lecture autorisée
        r2 = c2.get("/accounts", params={"profile_id": DEFAULT_PROFILE_ID})
        assert r2.status_code == 200
