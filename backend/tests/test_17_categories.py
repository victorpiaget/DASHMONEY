"""
Tests pour /categories :
  GET    /categories
  POST   /categories
  DELETE /categories/{id}
  POST   /categories/{id}/subcategories
  DELETE /categories/{id}/subcategories/{sub_id}
"""
from __future__ import annotations


def _create_category(client, name="Alimentation"):
    r = client.post("/categories", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def test_list_categories_auto_seeds_defaults(client):
    """Premier appel a GET /categories : le repo auto-seed les categories par defaut."""
    r = client.get("/categories")
    assert r.status_code == 200, r.text
    items = r.json()
    # Le repo seede des categories par defaut lors du premier appel — la liste ne peut pas etre vide
    assert len(items) > 0
    names = [c["name"] for c in items]
    # Quelques noms de categories attendus dans les defaults
    assert any("Logement" in n for n in names)


def test_create_category(client):
    r = client.post("/categories", json={"name": "Transport"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Transport"
    assert "id" in data
    assert data["subcategories"] == []

    listed = client.get("/categories").json()
    names = [c["name"] for c in listed]
    assert "Transport" in names


def test_create_category_duplicate_returns_409(client):
    _create_category(client, "Logement")
    r = client.post("/categories", json={"name": "Logement"})
    assert r.status_code == 409, r.text


def test_delete_category(client):
    cat = _create_category(client, "Loisirs")
    r = client.delete(f"/categories/{cat['id']}")
    assert r.status_code == 204, r.text

    listed = client.get("/categories").json()
    ids = [c["id"] for c in listed]
    assert cat["id"] not in ids


def test_delete_category_not_found_returns_404(client):
    r = client.delete("/categories/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404, r.text


def test_create_subcategory(client):
    cat = _create_category(client, "Sante")
    r = client.post(f"/categories/{cat['id']}/subcategories", json={"name": "Pharmacie"})
    assert r.status_code == 201, r.text
    sub = r.json()
    assert sub["name"] == "Pharmacie"
    assert "id" in sub

    listed = client.get("/categories").json()
    parent = next(c for c in listed if c["id"] == cat["id"])
    sub_names = [s["name"] for s in parent["subcategories"]]
    assert "Pharmacie" in sub_names


def test_create_subcategory_unknown_category_returns_404(client):
    r = client.post(
        "/categories/00000000-0000-0000-0000-000000000000/subcategories",
        json={"name": "SubGhost"},
    )
    assert r.status_code == 404, r.text


def test_delete_subcategory(client):
    cat = _create_category(client, "Education")
    sub_r = client.post(f"/categories/{cat['id']}/subcategories", json={"name": "Livres"})
    assert sub_r.status_code == 201, sub_r.text
    sub = sub_r.json()

    r = client.delete(f"/categories/{cat['id']}/subcategories/{sub['id']}")
    assert r.status_code == 204, r.text

    listed = client.get("/categories").json()
    parent = next(c for c in listed if c["id"] == cat["id"])
    sub_ids = [s["id"] for s in parent["subcategories"]]
    assert sub["id"] not in sub_ids


def test_categories_isolated_by_profile(client, auth_headers_user2):
    from fastapi.testclient import TestClient
    from app.api.main import app

    _create_category(client, "Cat_User1")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        listed_u2 = c2.get("/categories").json()

    names_u2 = [c["name"] for c in listed_u2]
    assert "Cat_User1" not in names_u2


def test_categories_require_auth(client):
    from fastapi.testclient import TestClient
    from app.api.main import app

    with TestClient(app) as anon:
        r = anon.get("/categories")
    assert r.status_code == 401, r.text
