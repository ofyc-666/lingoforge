from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from temp_paths import temp_db_path


def test_health_check_initializes_database():
    settings = Settings(database_path=str(temp_db_path("health")))

    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database_initialized"] is True
    assert payload["llm_provider"] == "mock"
    assert "DEEPSEEK_API_KEY" not in payload["config"]
