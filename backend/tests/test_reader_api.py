"""Reader import, highlight vocabulary and export API tests."""

from __future__ import annotations

import base64
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.users import create_user
from temp_paths import temp_db_path


@pytest.fixture
def client_and_user():
    db_path = str(temp_db_path("reader_api"))
    init_database(db_path)
    settings = Settings(
        app_name="LingoForge Reader Test",
        database_path=db_path,
        cors_origins=[],
        llm_mode="mock",
        llm_provider="deepseek",
    )
    user_id = create_user(db_path, "阅读流程测试用户")
    app = create_app(settings)
    return TestClient(app), user_id


def _pdf_base64_with_text(text: str) -> str:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, text)
    pdf.save()
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_import_text_returns_body_and_keywords(client_and_user):
    client, user_id = client_and_user

    response = client.post(
        "/api/reader/import-text",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={
            "raw_text": "Climate change is a pressing challenge for worldwide cooperation.",
            "max_keywords": 4,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] >= 1
    assert payload["source_type"] == "TEXT"
    assert payload["raw_text"].startswith("Climate change")
    assert [kw["text"] for kw in payload["keywords"][:2]] == ["climate", "change"]
    assert payload["keywords"][0]["meaning_zh"] == "气候"


def test_import_pdf_extracts_body_and_keywords(client_and_user):
    client, user_id = client_and_user

    response = client.post(
        "/api/reader/import-pdf",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={
            "file_name": "climate.pdf",
            "content_base64": _pdf_base64_with_text(
                "Climate change is a pressing challenge for global research."
            ),
            "max_keywords": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_type"] == "PDF"
    assert payload["file_name"] == "climate.pdf"
    assert "Climate change" in payload["raw_text"]
    assert payload["keywords"][0]["text"] == "climate"


def test_user_can_add_list_and_export_vocabulary(client_and_user):
    client, user_id = client_and_user
    imported = client.post(
        "/api/reader/import-text",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={"raw_text": "Technology can transform industry worldwide."},
    ).json()
    keyword = imported["keywords"][0]

    add_response = client.post(
        "/api/reader/vocabulary",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={
            "text": keyword["text"],
            "meaning_zh": keyword["meaning_zh"],
            "usage_note": keyword["usage_note"],
            "ability": keyword["ability"],
            "source_document_id": imported["document_id"],
            "source_context": "Technology can transform industry worldwide.",
        },
    )
    assert add_response.status_code == 200
    added = add_response.json()
    assert added["text"] == "technology"
    assert added["source_document_id"] == imported["document_id"]

    list_response = client.get(
        "/api/reader/vocabulary",
        headers={"X-LingoForge-User-Id": str(user_id)},
    )
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["text"] == "technology"

    export_response = client.get(
        "/api/reader/vocabulary/export.csv",
        headers={"X-LingoForge-User-Id": str(user_id)},
    )
    assert export_response.status_code == 200
    assert "text,meaning_zh,usage_note,ability,source_context,created_at" in export_response.text
    assert "technology" in export_response.text


def test_cannot_add_vocabulary_from_other_users_document(client_and_user):
    client, user_id = client_and_user
    other_user_id = user_id + 1
    imported = client.post(
        "/api/reader/import-text",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={"raw_text": "Climate change is pressing."},
    ).json()

    response = client.post(
        "/api/reader/vocabulary",
        headers={"X-LingoForge-User-Id": str(other_user_id)},
        json={
            "text": "climate",
            "meaning_zh": "气候",
            "source_document_id": imported["document_id"],
        },
    )

    assert response.status_code == 404


def test_reader_api_rejects_unknown_user_with_stable_error(client_and_user):
    client, user_id = client_and_user

    response = client.post(
        "/api/reader/import-text",
        headers={"X-LingoForge-User-Id": str(user_id + 999)},
        json={"raw_text": "Climate change is pressing."},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"]["code"] == "USER_NOT_FOUND"


def test_import_pdf_rejects_invalid_base64(client_and_user):
    client, user_id = client_and_user

    response = client.post(
        "/api/reader/import-pdf",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={"file_name": "broken.pdf", "content_base64": "not-base64!!!"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_PDF_BASE64"


def test_add_vocabulary_rejects_invalid_ability(client_and_user):
    client, user_id = client_and_user

    response = client.post(
        "/api/reader/vocabulary",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={
            "text": "climate",
            "meaning_zh": "气候",
            "ability": "NOT_A_REAL_ABILITY",
        },
    )

    assert response.status_code == 422


def test_duplicate_vocabulary_add_updates_existing_item_without_duplication(client_and_user):
    client, user_id = client_and_user
    imported = client.post(
        "/api/reader/import-text",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={"raw_text": "Climate change is a pressing challenge."},
    ).json()

    for note in ("第一次加入", "第二次更新"):
        response = client.post(
            "/api/reader/vocabulary",
            headers={"X-LingoForge-User-Id": str(user_id)},
            json={
                "text": "climate",
                "meaning_zh": "气候",
                "usage_note": note,
                "ability": "VOCABULARY_CONTEXT",
                "source_document_id": imported["document_id"],
            },
        )
        assert response.status_code == 200

    listed = client.get(
        "/api/reader/vocabulary",
        headers={"X-LingoForge-User-Id": str(user_id)},
    ).json()
    assert len(listed["items"]) == 1
    assert listed["items"][0]["usage_note"] == "第二次更新"


def test_csv_export_escapes_formula_like_cells(client_and_user):
    client, user_id = client_and_user

    response = client.post(
        "/api/reader/vocabulary",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={
            "text": "=cmd",
            "meaning_zh": "危险公式样式",
            "source_context": "+SUM(1,2)",
        },
    )
    assert response.status_code == 200

    export_response = client.get(
        "/api/reader/vocabulary/export.csv",
        headers={"X-LingoForge-User-Id": str(user_id)},
    )

    assert export_response.status_code == 200
    assert "'=cmd" in export_response.text
    assert "'+SUM(1,2)" in export_response.text
