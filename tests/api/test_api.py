from fastapi.testclient import TestClient

from src.api.main import api


def _client() -> TestClient:
    return TestClient(api)


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_users_list_includes_sarah():
    r = _client().get("/users")
    assert r.status_code == 200
    body = r.json()
    assert body["synthetic_data"] is True
    names = {u["name"] for u in body["users"]}
    assert "Sarah Chen" in names
    assert len(names) == 30


def test_root_returns_html_landing_page():
    r = _client().get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Enterprise Knowledge Agent" in r.text
    assert "synthetic" in r.text.lower()


def test_query_unknown_user_returns_404():
    r = _client().post(
        "/query",
        json={"query": "hi", "user_name": "Nobody", "user_role": "IC"},
    )
    assert r.status_code == 404


def test_query_body_validation():
    r = _client().post(
        "/query",
        json={"query": "", "user_name": "Sarah Chen", "user_role": "manager"},
    )
    assert r.status_code == 422
