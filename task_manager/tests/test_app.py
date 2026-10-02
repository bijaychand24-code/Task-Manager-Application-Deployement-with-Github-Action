import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def c():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as client:
        yield client


def auth(c, email="a@x.com"):
    c.post("/api/register", json={"email": email, "password": "secret1"})
    assert c.post("/api/login", json={"email": email, "password": "secret1"}).status_code == 200


def mk(c, **kw):
    r = c.post("/api/tasks", json={"title": "T1", **kw})
    assert r.status_code == 201
    return r.json()


def test_register_duplicate(c):
    body = {"email": "a@x.com", "password": "secret1"}
    assert c.post("/api/register", json=body).status_code == 201
    assert c.post("/api/register", json=body).status_code == 409


def test_login_wrong_password(c):
    c.post("/api/register", json={"email": "a@x.com", "password": "secret1"})
    assert c.post("/api/login", json={"email": "a@x.com", "password": "wrong11"}).status_code == 401


def test_requires_auth(c):
    assert c.get("/api/tasks").status_code == 401


def test_create_and_list(c):
    auth(c)
    mk(c, title="Buy milk")
    r = c.get("/api/tasks").json()
    assert r["total"] == 1 and r["items"][0]["title"] == "Buy milk"


def test_update_status(c):
    auth(c)
    t = mk(c)
    assert c.patch(f"/api/tasks/{t['id']}", json={"status": "Done"}).json()["status"] == "Done"


def test_delete(c):
    auth(c)
    t = mk(c)
    assert c.delete(f"/api/tasks/{t['id']}").status_code == 204
    assert c.get("/api/tasks").json()["total"] == 0


def test_user_isolation(c):
    auth(c)
    t = mk(c)
    other = TestClient(app)
    auth(other, "b@x.com")
    assert other.get("/api/tasks").json()["total"] == 0
    assert other.patch(f"/api/tasks/{t['id']}", json={"status": "Done"}).status_code == 404
    assert other.delete(f"/api/tasks/{t['id']}").status_code == 404


def test_search_filter_sort(c):
    auth(c)
    mk(c, title="Alpha", priority="Low")
    mk(c, title="Beta", priority="Urgent")
    assert c.get("/api/tasks?q=alph").json()["total"] == 1
    assert c.get("/api/tasks?priority=Urgent").json()["items"][0]["title"] == "Beta"
    assert c.get("/api/tasks?sort=priority").json()["items"][0]["title"] == "Beta"


def test_subtask_toggle(c):
    auth(c)
    t = mk(c)
    sid = c.post(f"/api/tasks/{t['id']}/subtasks", json={"title": "s"}).json()["subtasks"][0]["id"]
    r = c.patch(f"/api/tasks/{t['id']}/subtasks/{sid}", json={"done": True}).json()
    assert r["subtasks"][0]["done"] is True


def test_recurring_creates_next(c):
    auth(c)
    t = mk(c, due_date="2026-10-01", recurrence="weekly")
    c.patch(f"/api/tasks/{t['id']}", json={"status": "Done"})
    items = c.get("/api/tasks").json()["items"]
    assert len(items) == 2
    assert any(i["due_date"] == "2026-10-08" and i["status"] == "Todo" for i in items)


def test_overdue_and_stats(c):
    auth(c)
    mk(c, due_date="2020-01-01")
    s = c.get("/api/stats").json()
    assert s["total"] == 1 and s["overdue"] == 1 and s["completion_rate"] == 0


def test_export_csv(c):
    auth(c)
    mk(c, title="CSV me")
    r = c.get("/api/export?format=csv")
    assert "CSV me" in r.text and r.headers["content-type"].startswith("text/csv")
