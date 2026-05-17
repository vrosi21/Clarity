"""Project CRUD + bootstrap defaults (stages, RL config, categories)."""


def test_create_project_seeds_default_stages(client, alice, project):
    r = client.get(f"/api/v1/projects/{project['id']}/stages", headers=alice["headers"])
    assert r.status_code == 200
    stages = r.json()
    assert len(stages) == 5
    types = [s["type"] for s in stages]
    assert types[0] == "start"
    assert types[-1] == "final"
    # The middle three should all be NORMAL.
    assert all(t == "normal" for t in types[1:-1])
    # Ordered.
    assert [s["order"] for s in stages] == [0, 1, 2, 3, 4]


def test_create_project_seeds_default_rl_config(client, alice, project):
    r = client.get(
        f"/api/v1/projects/{project['id']}/rl-config", headers=alice["headers"]
    )
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["temperature"] > 0
    assert cfg["w_efficiency"] > 0
    assert 0.0 <= cfg["gamma"] <= 1.0


def test_canonical_categories_present(client, alice):
    r = client.get("/api/v1/categories", headers=alice["headers"])
    assert r.status_code == 200
    names = {c["name"] for c in r.json()}
    # All 8 canonical categories must be there for the model's one-hot encoding.
    expected = {
        "backend",
        "frontend",
        "devops",
        "design",
        "mobile",
        "data",
        "qa",
        "security",
    }
    assert expected.issubset(names)


def test_list_projects_returns_only_user_projects(client, alice, bob):
    r = client.post(
        "/api/v1/projects",
        json={"name": "Alice's project"},
        headers=alice["headers"],
    )
    assert r.status_code == 201

    r = client.get("/api/v1/projects", headers=alice["headers"])
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get("/api/v1/projects", headers=bob["headers"])
    assert r.status_code == 200
    assert r.json() == []


def test_non_member_cannot_view_project(client, alice, bob, project):
    r = client.get(f"/api/v1/projects/{project['id']}", headers=bob["headers"])
    assert r.status_code == 403
