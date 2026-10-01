def test_create_project_success(client):
    response = client.post("/api/projects", json={"name": "Modern 3BHK Apartment"})
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["success"] is True
    data = json_data["data"]
    assert data["name"] == "Modern 3BHK Apartment"
    assert data["status"] == "created"
    assert data["id"].startswith("project_")
    assert data["images"] == []
    assert data["image_count"] == 0


def test_create_project_empty_name_fails(client):
    response = client.post("/api/projects", json={"name": "   "})
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "VALIDATION_ERROR"


def test_get_project_success(client):
    create_resp = client.post("/api/projects", json={"name": "Luxury Villa"})
    project_id = create_resp.json()["data"]["id"]

    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 200
    json_data = get_resp.json()
    assert json_data["success"] is True
    assert json_data["data"]["id"] == project_id
    assert json_data["data"]["name"] == "Luxury Villa"


def test_get_nonexistent_project_returns_404(client):
    response = client.get("/api/projects/project_non_existent_123")
    assert response.status_code == 404
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "PROJECT_NOT_FOUND"


def test_list_projects(client):
    client.post("/api/projects", json={"name": "Property 1"})
    client.post("/api/projects", json={"name": "Property 2"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert len(json_data["data"]) >= 2
