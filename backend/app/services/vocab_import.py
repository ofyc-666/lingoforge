"""CET-6 词表导入服务。

支持从结构化样例数据或 CSV 文件幂等导入词汇。
不依赖 LLM，不编造完整官方词表。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all
from app.storage.json_fields import to_json_text


def import_vocabulary_from_dicts(
    database_path: str | Path,
    words: list[dict[str, object]],
    *,
    source_type: str = "CET6_VOCAB",
    dedupe_by_text: bool = True,
) -> dict[str, int]:
    """从 dict 列表幂等导入词汇。

    返回 {"created": N, "skipped": N}。
    """
    created = 0
    skipped = 0
    for word in words:
        text = str(word.get("text", "")).strip()
        if not text:
            continue
        meaning = word.get("meaning_zh", "")
        pos = word.get("part_of_speech", "")
        tags = list(word.get("tags", []))
        if dedupe_by_text:
            existing = fetch_all(
                database_path,
                "SELECT id FROM vocabulary_items WHERE text = ?",
                (text,),
            )
            if existing:
                skipped += 1
                continue
        execute(
            database_path,
            """INSERT INTO vocabulary_items (text, meaning_zh, part_of_speech, tags, source_type)
               VALUES (?, ?, ?, ?, ?)""",
            (text, str(meaning) if meaning else None, str(pos) if pos else None,
             to_json_text(tags), source_type),
        )
        created += 1
    return {"created": created, "skipped": skipped}


def import_vocabulary_from_csv(
    database_path: str | Path,
    csv_path: str | Path,
    *,
    source_type: str = "CET6_VOCAB",
    dedupe_by_text: bool = True,
) -> dict[str, int]:
    """从 CSV 文件幂等导入词汇。

    CSV 列：text,meaning_zh,part_of_speech,tags
    tags 列为分号分隔的标签，可选。
    """
    created = 0
    skipped = 0
    path = Path(csv_path)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            meaning = row.get("meaning_zh", "")
            pos = row.get("part_of_speech", "")
            raw_tags = row.get("tags", "")
            tags = [t.strip() for t in raw_tags.split(";") if t.strip()]
            if dedupe_by_text:
                existing = fetch_all(
                    database_path,
                    "SELECT id FROM vocabulary_items WHERE text = ?",
                    (text,),
                )
                if existing:
                    skipped += 1
                    continue
            execute(
                database_path,
                """INSERT INTO vocabulary_items (text, meaning_zh, part_of_speech, tags, source_type)
                   VALUES (?, ?, ?, ?, ?)""",
                (text, str(meaning) if meaning else None, str(pos) if pos else None,
                 to_json_text(tags), source_type),
            )
            created += 1
    return {"created": created, "skipped": skipped}


def seed_cet6_vocabulary(database_path: str | Path) -> dict[str, int]:
    """导入 CET-6 演示词表样本。"""
    from app.data.cet6_vocab_sample import CET6_SAMPLE_WORDS
    return import_vocabulary_from_dicts(database_path, CET6_SAMPLE_WORDS, source_type="CET6_VOCAB")


def count_vocabulary_by_source(database_path: str | Path, source_type: str = "CET6_VOCAB") -> int:
    """统计指定来源的词汇数量。"""
    rows = fetch_all(
        database_path,
        "SELECT COUNT(*) as cnt FROM vocabulary_items WHERE source_type = ?",
        (source_type,),
    )
    return int(rows[0]["cnt"]) if rows else 0
