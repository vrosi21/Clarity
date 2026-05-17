"""Sandbox seed/reset tests."""


def test_seed_creates_workers_and_tickets(client, alice, project):
    r = client.post(
        f"/api/v1/projects/{project['id']}/sandbox/seed",
        json={"n_workers": 4, "n_tickets": 10, "seed": 42},
        headers=alice["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workers_created"] == 4
    assert body["tickets_created"] == 10
    assert len(body["bot_user_ids"]) == 4

    # Tickets visible.
    r = client.get(
        f"/api/v1/projects/{project['id']}/tickets", headers=alice["headers"]
    )
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert all(t.startswith("[sandbox]") for t in titles)
    assert len(titles) == 10

    # Bot users became members.
    r = client.get(
        f"/api/v1/projects/{project['id']}/members", headers=alice["headers"]
    )
    assert r.status_code == 200
    members = r.json()
    assert len(members) == 1 + 4  # owner + 4 bots


def test_reset_removes_only_sandbox_state(client, alice, project):
    # Add a non-sandbox ticket first.
    r = client.get(f"/api/v1/projects/{project['id']}/stages", headers=alice["headers"])
    start_id = r.json()[0]["id"]
    client.post(
        f"/api/v1/projects/{project['id']}/tickets",
        json={
            "title": "human ticket",
            "complexity": 2,
            "stage_id": start_id,
            "estimated_minutes": 30,
        },
        headers=alice["headers"],
    )

    # Seed.
    client.post(
        f"/api/v1/projects/{project['id']}/sandbox/seed",
        json={"n_workers": 3, "n_tickets": 5, "seed": 7},
        headers=alice["headers"],
    )

    # Reset.
    r = client.post(
        f"/api/v1/projects/{project['id']}/sandbox/reset",
        headers=alice["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["workers_removed"] == 3
    assert r.json()["tickets_removed"] == 5

    # Human ticket survived.
    r = client.get(
        f"/api/v1/projects/{project['id']}/tickets", headers=alice["headers"]
    )
    titles = [t["title"] for t in r.json()]
    assert titles == ["human ticket"]


def test_seed_requires_admin(client, alice, bob, project):
    # Add bob as MEMBER (not admin).
    client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": bob["user"]["id"], "role": "member"},
        headers=alice["headers"],
    )
    r = client.post(
        f"/api/v1/projects/{project['id']}/sandbox/seed",
        json={"n_workers": 2, "n_tickets": 3},
        headers=bob["headers"],
    )
    assert r.status_code == 403
