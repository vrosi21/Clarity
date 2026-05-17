def test_register_login_me(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "x@y.com", "username": "xy", "password": "longenough"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "x@y.com"

    r = client.post("/api/v1/auth/login", json={"email": "x@y.com", "password": "longenough"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "xy"


def test_login_with_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "username": "ab", "password": "longenough"},
    )
    r = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_register_duplicate_email(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "dup@x.com", "username": "one", "password": "longenough"},
    )
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@x.com", "username": "two", "password": "longenough"},
    )
    assert r.status_code == 409


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
