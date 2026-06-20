"""Reader workflow repository helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all, fetch_one
from app.repositories.vocabulary import create_vocabulary_item, get_vocabulary_by_text
from app.storage.json_fields import from_json_text, to_json_text


def create_reading_document(
    database_path: str | Path,
    *,
    user_id: int,
    source_type: str,
    raw_text: str,
    analysis: dict[str, Any],
    file_name: str | None = None,
) -> int:
    return execute(
        database_path,
        """INSERT INTO reading_documents
           (user_id, source_type, file_name, raw_text, analysis_json)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, source_type, file_name, raw_text, to_json_text(analysis)),
    )


def get_reading_document(
    database_path: str | Path,
    *,
    user_id: int,
    document_id: int,
) -> dict[str, Any] | None:
    row = fetch_one(
        database_path,
        "SELECT * FROM reading_documents WHERE id = ? AND user_id = ?",
        (document_id, user_id),
    )
    if row is None:
        return None
    row["analysis_json"] = from_json_text(row.get("analysis_json"), {})
    return row


def add_user_vocabulary_item(
    database_path: str | Path,
    *,
    user_id: int,
    text: str,
    meaning_zh: str,
    usage_note: str = "",
    ability: str | None = None,
    source_document_id: int | None = None,
    source_context: str = "",
) -> dict[str, Any]:
    normalized = text.strip().lower()
    vocabulary = get_vocabulary_by_text(database_path, normalized)
    if vocabulary is None:
        vocab_id = create_vocabulary_item(
            database_path,
            text=normalized,
            meaning_zh=meaning_zh,
            tags=["USER_BOOK"],
            source_type="USER_READER",
        )
        vocabulary = get_vocabulary_by_text(database_path, normalized)
        assert vocabulary is not None
    else:
        vocab_id = int(vocabulary["id"])

    existing = fetch_one(
        database_path,
        """SELECT uvi.*, vi.text
           FROM user_vocabulary_items uvi
           JOIN vocabulary_items vi ON vi.id = uvi.vocabulary_item_id
           WHERE uvi.user_id = ? AND uvi.vocabulary_item_id = ?""",
        (user_id, vocab_id),
    )
    if existing is None:
        item_id = execute(
            database_path,
            """INSERT INTO user_vocabulary_items
               (user_id, vocabulary_item_id, meaning_zh, usage_note, ability,
                source_document_id, source_context)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                vocab_id,
                meaning_zh,
                usage_note,
                ability,
                source_document_id,
                source_context,
            ),
        )
    else:
        item_id = int(existing["id"])
        execute(
            database_path,
            """UPDATE user_vocabulary_items
               SET meaning_zh = ?, usage_note = ?, ability = ?,
                   source_document_id = COALESCE(?, source_document_id),
                   source_context = CASE WHEN ? != '' THEN ? ELSE source_context END
               WHERE id = ?""",
            (
                meaning_zh,
                usage_note,
                ability,
                source_document_id,
                source_context,
                source_context,
                item_id,
            ),
        )

    item = get_user_vocabulary_item(database_path, user_id=user_id, item_id=item_id)
    assert item is not None
    return item


def get_user_vocabulary_item(
    database_path: str | Path,
    *,
    user_id: int,
    item_id: int,
) -> dict[str, Any] | None:
    return fetch_one(
        database_path,
        """SELECT uvi.id, uvi.user_id, vi.text, uvi.meaning_zh, uvi.usage_note,
                  uvi.ability, uvi.source_document_id, uvi.source_context,
                  uvi.created_at
           FROM user_vocabulary_items uvi
           JOIN vocabulary_items vi ON vi.id = uvi.vocabulary_item_id
           WHERE uvi.id = ? AND uvi.user_id = ?""",
        (item_id, user_id),
    )


def list_user_vocabulary_items(
    database_path: str | Path,
    *,
    user_id: int,
) -> list[dict[str, Any]]:
    return fetch_all(
        database_path,
        """SELECT uvi.id, uvi.user_id, vi.text, uvi.meaning_zh, uvi.usage_note,
                  uvi.ability, uvi.source_document_id, uvi.source_context,
                  uvi.created_at
           FROM user_vocabulary_items uvi
           JOIN vocabulary_items vi ON vi.id = uvi.vocabulary_item_id
           WHERE uvi.user_id = ?
           ORDER BY uvi.created_at DESC, uvi.id DESC""",
        (user_id,),
    )
