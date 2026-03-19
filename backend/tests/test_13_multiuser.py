"""
Tests multi-utilisateur :
- Isolation des données entre User1 et User2 (workspaces séparés)
- Refresh tokens : rotation, révocation, logout
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.identity.defaults import (
    DEFAULT_PROFILE2_ID,
    DEFAULT_PROFILE_ID,
    DEFAULT_TEST_PASSWORD,
    DEFAULT_USER2_EMAIL,
    DEFAULT_USER_EMAIL,
    DEFAULT_WORKSPACE2_ID,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(c: TestClient, email: str, password: str = DEFAULT_TEST_PASSWORD) -> dict:
    resp = c.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _client_for(headers: dict) -> TestClient:
    """TestClient non-contextualisé avec des headers spécifiques."""
    tc = TestClient(app, raise_server_exceptions=True)
    tc.headers.update(headers)
    return tc


# ---------------------------------------------------------------------------
# Isolation User1 / User2
# ---------------------------------------------------------------------------

def test_user2_cannot_access_user1_profile(client, auth_headers_user2):
    """User2 passe profile_id=DEFAULT_PROFILE_ID → 403 (pas d'accès)."""
    c2 = TestClient(app)
    c2.headers.update(auth_headers_user2)
    r = c2.get("/accounts", params={"profile_id": DEFAULT_PROFILE_ID})
    assert r.status_code == 403


def test_user1_cannot_access_user2_profile(client, auth_headers):
    """User1 passe profile_id=DEFAULT_PROFILE2_ID → 403."""
    c1 = TestClient(app)
    c1.headers.update(auth_headers)
    r = c1.get("/accounts", params={"profile_id": DEFAULT_PROFILE2_ID})
    assert r.status_code == 403


def test_user2_can_access_own_profile(auth_headers_user2):
    """User2 accède à son propre profil → 200."""
    c2 = TestClient(app)
    c2.headers.update(auth_headers_user2)
    r = c2.get("/accounts", params={"profile_id": DEFAULT_PROFILE2_ID})
    assert r.status_code == 200


def test_data_not_shared_between_users(client, auth_headers_user2):
    """User1 crée un compte, User2 ne le voit pas dans son profil."""
    # User1 crée un compte dans son profil
    client.post("/accounts", json={
        "id": "U1_ACCOUNT",
        "name": "User1 Account",
        "currency": "EUR",
        "opening_balance": "1000.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
    })

    # User2 liste ses comptes → doit être vide
    c2 = TestClient(app)
    c2.headers.update(auth_headers_user2)
    r = c2.get("/accounts", params={"profile_id": DEFAULT_PROFILE2_ID})
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert "U1_ACCOUNT" not in ids


def test_user2_own_data_not_visible_to_user1(client, auth_headers_user2):
    """User2 crée un compte, User1 ne le voit pas."""
    c2 = TestClient(app)
    c2.headers.update(auth_headers_user2)
    c2.post("/accounts", params={"profile_id": DEFAULT_PROFILE2_ID}, json={
        "id": "U2_ACCOUNT",
        "name": "User2 Account",
        "currency": "EUR",
        "opening_balance": "500.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
    })

    # User1 liste son profil → ne voit pas U2_ACCOUNT
    r = client.get("/accounts")
    assert r.status_code == 200
    assert "U2_ACCOUNT" not in [a["id"] for a in r.json()]


def test_user2_workspace_is_separate(auth_headers_user2):
    """User2 peut créer un profil dans son workspace, pas dans celui de User1."""
    c2 = TestClient(app)
    c2.headers.update(auth_headers_user2)

    # Son workspace → OK
    r_ok = c2.post(
        f"/workspaces/{DEFAULT_WORKSPACE2_ID}/profiles",
        json={"display_name": "User2 Extra Profile"},
    )
    assert r_ok.status_code == 201


# ---------------------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------------------

def test_login_returns_refresh_token(client):
    r = client.post("/auth/login", json={"email": DEFAULT_USER_EMAIL, "password": DEFAULT_TEST_PASSWORD})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_returns_new_token_pair(client):
    # Login
    login_data = _login(client, DEFAULT_USER_EMAIL)
    old_access = login_data["access_token"]
    refresh_tok = login_data["refresh_token"]

    # Refresh
    r = client.post("/auth/refresh", json={"refresh_token": refresh_tok})
    assert r.status_code == 200
    new_data = r.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    # Les nouveaux tokens doivent être différents
    assert new_data["access_token"] != old_access
    assert new_data["refresh_token"] != refresh_tok


def test_refresh_token_rotation_revokes_old(client):
    """Après rotation, l'ancien refresh token ne fonctionne plus."""
    login_data = _login(client, DEFAULT_USER_EMAIL)
    old_refresh = login_data["refresh_token"]

    # Première rotation
    r1 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert r1.status_code == 200

    # Réutilisation de l'ancien → 401
    # On utilise un client vierge pour éviter que le cookie issu de r1 ne prenne la priorité
    fresh = TestClient(app, raise_server_exceptions=True)
    r2 = fresh.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401


def test_refresh_with_invalid_token_returns_401(client):
    r = client.post("/auth/refresh", json={"refresh_token": "completely-invalid-token"})
    assert r.status_code == 401


def test_logout_revokes_refresh_token(client):
    login_data = _login(client, DEFAULT_USER_EMAIL)
    refresh_tok = login_data["refresh_token"]

    # Logout
    r_out = client.post("/auth/logout", json={"refresh_token": refresh_tok})
    assert r_out.status_code == 204

    # Refresh après logout → 401
    r_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_tok})
    assert r_refresh.status_code == 401


def test_logout_is_idempotent(client):
    """Logout d'un token déjà révoqué → 204 (pas d'erreur)."""
    login_data = _login(client, DEFAULT_USER_EMAIL)
    refresh_tok = login_data["refresh_token"]

    client.post("/auth/logout", json={"refresh_token": refresh_tok})
    r = client.post("/auth/logout", json={"refresh_token": refresh_tok})
    assert r.status_code == 204


def test_new_access_token_after_refresh_is_valid(client):
    """Le nouvel access token obtenu via refresh permet bien d'appeler l'API."""
    login_data = _login(client, DEFAULT_USER_EMAIL)
    refresh_tok = login_data["refresh_token"]

    r_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_tok})
    new_access = r_refresh.json()["access_token"]

    # Utiliser le nouvel access token
    c_new = TestClient(app)
    c_new.headers["Authorization"] = f"Bearer {new_access}"
    r = c_new.get("/accounts")
    assert r.status_code == 200
