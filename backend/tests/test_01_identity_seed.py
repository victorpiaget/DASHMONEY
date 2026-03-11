from app.identity.defaults import (
    DEFAULT_PROFILE_ID,
    DEFAULT_PROFILE_NAME,
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
)


def test_list_workspaces_contains_default(client):
    r = client.get("/workspaces")
    assert r.status_code == 200
    data = r.json()

    assert isinstance(data, list)
    assert any(
        w["id"] == DEFAULT_WORKSPACE_ID and w["name"] == DEFAULT_WORKSPACE_NAME
        for w in data
    )


def test_get_default_profile(client):
    r = client.get(f"/profiles/{DEFAULT_PROFILE_ID}")
    assert r.status_code == 200
    p = r.json()

    assert p["id"] == DEFAULT_PROFILE_ID
    assert p["display_name"] == DEFAULT_PROFILE_NAME
    assert p["workspace_id"] == DEFAULT_WORKSPACE_ID


def test_create_profile_under_default_workspace(client):
    # create a new profile
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/profiles",
        json={"display_name": "QA Profile 1"},
    )
    assert r.status_code == 201
    created = r.json()

    assert "id" in created
    assert created["display_name"] == "QA Profile 1"
    assert created["workspace_id"] == DEFAULT_WORKSPACE_ID

    # list profiles in workspace -> must contain it
    r2 = client.get(f"/workspaces/{DEFAULT_WORKSPACE_ID}/profiles")
    assert r2.status_code == 200
    items = r2.json()

    assert any(p["id"] == created["id"] for p in items)