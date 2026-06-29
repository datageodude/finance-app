def test_login_valid(client, test_user):
    res = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "correct-password"},
    )
    assert res.status_code == 200
    assert "session" in res.cookies
    assert res.json()["user"]["email"] == "test@example.com"


def test_login_wrong_password(client, test_user):
    res = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert res.status_code == 401


def test_login_unknown_email(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
    )
    assert res.status_code == 401


def test_me_authenticated(client, test_user):
    client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "correct-password"},
    )
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"


def test_me_unauthenticated(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_logout_clears_session(client, test_user):
    client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "correct-password"},
    )
    assert client.get("/api/auth/me").status_code == 200

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_change_password(client, test_user):
    client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "correct-password"},
    )
    res = client.post(
        "/api/auth/change-password",
        json={"old_password": "correct-password", "new_password": "new-secure-password"},
    )
    assert res.status_code == 200

    # Old password no longer works
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "correct-password"},
    ).status_code == 401

    # New password works
    assert client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "new-secure-password"},
    ).status_code == 200


def test_change_password_wrong_old(client, test_user):
    client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "correct-password"},
    )
    res = client.post(
        "/api/auth/change-password",
        json={"old_password": "wrong", "new_password": "new-password"},
    )
    assert res.status_code == 400


def test_health(client):
    assert client.get("/api/health").status_code == 200
