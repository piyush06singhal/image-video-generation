def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "healthy"
    assert json_data["data"]["service"] == "walkthrough-backend"
    assert json_data["error"] is None
