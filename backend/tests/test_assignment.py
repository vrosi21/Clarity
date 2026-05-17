"""Assignment endpoint tests — exercises fallback path (no model files)."""


def test_assign_rl_uses_heuristic_when_no_model(client, alice, project):
    # Seed sandbox so there are workers + a ticket.
    client.post(
        f"/api/v1/projects/{project['id']}/sandbox/seed",
        json={"n_workers": 5, "n_tickets": 3, "seed": 1},
        headers=alice["headers"],
    )
    r = client.get(
        f"/api/v1/projects/{project['id']}/tickets", headers=alice["headers"]
    )
    ticket_id = r.json()[0]["id"]

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets/{ticket_id}/assign-rl",
        headers=alice["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # No regressor + no q-network → fallback.
    assert body["policy_used"] == "heuristic-random"
    assert body["assigned_user_id"] is not None
    assert body["q_value"] is None
    assert len(body["suggestions"]) == 5


def test_assignment_suggestions(client, alice, project):
    client.post(
        f"/api/v1/projects/{project['id']}/sandbox/seed",
        json={"n_workers": 4, "n_tickets": 2, "seed": 2},
        headers=alice["headers"],
    )
    r = client.get(
        f"/api/v1/projects/{project['id']}/tickets", headers=alice["headers"]
    )
    ticket_id = r.json()[0]["id"]

    r = client.get(
        f"/api/v1/projects/{project['id']}/tickets/{ticket_id}/assignment-suggestions",
        headers=alice["headers"],
    )
    assert r.status_code == 200
    sugs = r.json()
    assert len(sugs) == 4
    # All have proficiency + load_ratio.
    for s in sugs:
        assert "proficiency" in s
        assert "load_ratio" in s


def test_assign_with_no_workers_returns_400(client, alice, project):
    r = client.get(f"/api/v1/projects/{project['id']}/stages", headers=alice["headers"])
    start_id = r.json()[0]["id"]
    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets",
        json={
            "title": "lonely",
            "complexity": 2,
            "stage_id": start_id,
            "estimated_minutes": 30,
        },
        headers=alice["headers"],
    )
    ticket_id = r.json()["id"]
    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets/{ticket_id}/assign-rl",
        headers=alice["headers"],
    )
    assert r.status_code == 400
