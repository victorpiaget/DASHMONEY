"""
Tests — gestion des membres du workspace (niveau 2).

Couvre :
- GET /me
- GET /workspaces/{id}/members
- POST /workspaces/{id}/members/invite
- DELETE /workspaces/{id}/members/{user_id}
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.identity.defaults import (
    DEFAULT_USER_EMAIL,
    DEFAULT_USER_ID,
    DEFAULT_USER2_EMAIL,
    DEFAULT_USER2_ID,
    DEFAULT_WORKSPACE_ID,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client_no_auth: TestClient, email: str, password: str) -> dict:
    r = client_no_auth.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

def test_me_returns_user_and_workspaces(client):
    r = client.get("/me")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == DEFAULT_USER_ID
    assert data["email"] == DEFAULT_USER_EMAIL
    assert len(data["workspaces"]) >= 1
    w = data["workspaces"][0]
    assert "id" in w
    assert "profiles" in w
    assert len(w["profiles"]) >= 1


def test_me_requires_auth(client):
    r = client.get("/me", headers={"Authorization": ""})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /workspaces/{id}/members
# ---------------------------------------------------------------------------

def test_list_members_owner_sees_himself(client):
    r = client.get(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members")
    assert r.status_code == 200
    members = r.json()
    ids = [m["user_id"] for m in members]
    assert DEFAULT_USER_ID in ids
    roles = {m["user_id"]: m["role"] for m in members}
    assert roles[DEFAULT_USER_ID] == "OWNER"


def test_list_members_wrong_workspace_returns_403(client):
    r = client.get("/workspaces/00000000-0000-0000-0000-nonexistent11/members")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /workspaces/{id}/members/invite
# ---------------------------------------------------------------------------

def test_invite_member_by_email(client, db_engine):
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["user_id"] == DEFAULT_USER2_ID
    assert data["email"] == DEFAULT_USER2_EMAIL
    assert data["role"] == "MEMBER"


def test_invited_user_appears_in_members_list(client):
    client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL},
    )
    r = client.get(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members")
    ids = [m["user_id"] for m in r.json()]
    assert DEFAULT_USER2_ID in ids


def test_invited_user_can_access_profiles(client, auth_headers_user2, db_engine):
    from app.api.main import app
    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)

        # Avant invitation user2 ne voit pas les profils de workspace1
        r_before = c2.get("/profiles")
        profiles_before = {p["workspace_id"] for p in r_before.json()}
        assert DEFAULT_WORKSPACE_ID not in profiles_before

        # Invitation
        client.post(
            f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
            json={"email": DEFAULT_USER2_EMAIL},
        )

        # Après invitation user2 voit les profils de workspace1
        r_after = c2.get("/profiles")
        workspace_ids_after = {p["workspace_id"] for p in r_after.json()}
        assert DEFAULT_WORKSPACE_ID in workspace_ids_after


def test_invite_unknown_email_returns_404(client):
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": "nobody@nowhere.invalid"},
    )
    assert r.status_code == 404


def test_invite_already_member_returns_409(client):
    # User1 invite user2
    client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL},
    )
    # Deuxième invitation → conflit
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL},
    )
    assert r.status_code == 409


def test_only_owner_can_invite(client, auth_headers_user2, db_engine):
    from app.api.main import app
    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = c2.post(
            f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
            json={"email": "anyone@example.com"},
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /workspaces/{id}/members/{user_id}
# ---------------------------------------------------------------------------

def test_remove_member(client):
    client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL},
    )
    r = client.delete(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER2_ID}")
    assert r.status_code == 204

    members = client.get(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members").json()
    ids = [m["user_id"] for m in members]
    assert DEFAULT_USER2_ID not in ids


def test_removed_member_loses_profile_access(client, auth_headers_user2, db_engine):
    from app.api.main import app

    # Invite user2
    client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL},
    )

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        # User2 voit les profils de workspace1
        profiles = c2.get("/profiles").json()
        w1_profiles = [p for p in profiles if p["workspace_id"] == DEFAULT_WORKSPACE_ID]
        assert len(w1_profiles) >= 1

    # Supprimer user2
    client.delete(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER2_ID}")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        # User2 ne voit plus les profils de workspace1
        profiles_after = c2.get("/profiles").json()
        w1_after = [p for p in profiles_after if p["workspace_id"] == DEFAULT_WORKSPACE_ID]
        assert len(w1_after) == 0


def test_cannot_remove_last_owner(client):
    r = client.delete(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER_ID}")
    assert r.status_code == 422


def test_remove_nonexistent_member_returns_404(client):
    r = client.delete(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/00000000-0000-0000-0000-nonexistent00")
    assert r.status_code == 404


def test_only_owner_can_remove(client, auth_headers_user2, db_engine):
    from app.api.main import app
    # Invite user2 d'abord
    client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/invite",
        json={"email": DEFAULT_USER2_EMAIL},
    )
    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r = c2.delete(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members/{DEFAULT_USER_ID}")
        assert r.status_code == 403
