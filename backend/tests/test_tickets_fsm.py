"""Ticket move integration test — FSM should reject START → FINAL."""


def _stage_ids_by_type(client, alice, project):
    r = client.get(f"/api/v1/projects/{project['id']}/stages", headers=alice["headers"])
    by_type = {}
    for s in r.json():
        by_type.setdefault(s["type"], []).append(s)
    return by_type


def test_create_and_list_ticket(client, alice, project):
    by_type = _stage_ids_by_type(client, alice, project)
    start_id = by_type["start"][0]["id"]

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets",
        json={
            "title": "Test ticket",
            "description": "x",
            "priority": "p3",
            "complexity": 3,
            "stage_id": start_id,
            "estimated_minutes": 60,
        },
        headers=alice["headers"],
    )
    assert r.status_code == 201, r.text

    r = client.get(
        f"/api/v1/projects/{project['id']}/tickets", headers=alice["headers"]
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_move_one_step_forward_succeeds(client, alice, project):
    by_type = _stage_ids_by_type(client, alice, project)
    start_id = by_type["start"][0]["id"]
    todo_id = by_type["normal"][0]["id"]  # first NORMAL = "Todo"

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets",
        json={
            "title": "ticket",
            "complexity": 3,
            "stage_id": start_id,
            "estimated_minutes": 60,
        },
        headers=alice["headers"],
    )
    ticket_id = r.json()["id"]

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets/{ticket_id}/move",
        json={"stage_id": todo_id},
        headers=alice["headers"],
    )
    assert r.status_code == 200
    assert r.json()["stage_id"] == todo_id


def test_move_start_to_final_rejected_by_fsm(client, alice, project):
    """Safety property: ticket cannot jump from START to FINAL."""
    by_type = _stage_ids_by_type(client, alice, project)
    start_id = by_type["start"][0]["id"]
    final_id = by_type["final"][0]["id"]

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets",
        json={
            "title": "shortcut",
            "complexity": 3,
            "stage_id": start_id,
            "estimated_minutes": 60,
        },
        headers=alice["headers"],
    )
    ticket_id = r.json()["id"]

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets/{ticket_id}/move",
        json={"stage_id": final_id},
        headers=alice["headers"],
    )
    assert r.status_code == 400
    assert "Safety" in r.json()["detail"] or "topology" in r.json()["detail"].lower()


def test_normal_to_final_succeeds(client, alice, project):
    by_type = _stage_ids_by_type(client, alice, project)
    start_id = by_type["start"][0]["id"]
    review_id = by_type["normal"][-1]["id"]  # last NORMAL = "In Review"
    final_id = by_type["final"][0]["id"]

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets",
        json={
            "title": "moves through",
            "complexity": 3,
            "stage_id": review_id,  # already in NORMAL
            "estimated_minutes": 60,
        },
        headers=alice["headers"],
    )
    ticket_id = r.json()["id"]

    r = client.post(
        f"/api/v1/projects/{project['id']}/tickets/{ticket_id}/move",
        json={"stage_id": final_id},
        headers=alice["headers"],
    )
    assert r.status_code == 200, r.text
