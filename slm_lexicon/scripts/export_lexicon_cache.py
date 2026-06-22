from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "slm_lexicon.sqlite"
CACHE_PATH = ROOT / "data" / "lexicon_lookup_cache.json"


def rows_by_key(connection: sqlite3.Connection, query: str) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    connection.row_factory = sqlite3.Row
    for row in connection.execute(query):
        value = dict(row)
        term_id = int(value.pop("term_id"))
        grouped[term_id].append(value)
    return grouped


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"missing database: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    roles = rows_by_key(
        connection,
        """
        SELECT gr.term_id, gr.role, gr.support_weight, gr.source_id,
               sp.source_name, gr.rationale
        FROM grammar_roles gr
        JOIN source_provenance sp ON sp.id = gr.source_id
        ORDER BY gr.support_weight DESC, gr.role ASC
        """,
    )
    closed_class = rows_by_key(
        connection,
        """
        SELECT term_id, class, subclass, diffusion_priority, structural_hint, source_id
        FROM closed_class_terms
        ORDER BY diffusion_priority DESC
        """,
    )
    senses = rows_by_key(
        connection,
        """
        SELECT term_id, sense_key, synset_id, pos, definition, source_id
        FROM senses
        ORDER BY sense_key ASC
        """,
    )

    entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        """
        SELECT id, lemma, normalized, is_closed_class
        FROM terms
        ORDER BY is_closed_class DESC, lemma COLLATE NOCASE ASC
        """
    ):
        term_id = int(row["id"])
        entry = {
            "term_id": term_id,
            "lemma": row["lemma"],
            "normalized": row["normalized"],
            "is_closed_class": bool(row["is_closed_class"]),
            "roles": roles.get(term_id, []),
            "closed_class": closed_class.get(term_id, []),
            "senses": senses.get(term_id, [])[:8],
        }
        entries[row["normalized"]].append(entry)

    metadata = {
        row["key"]: row["value"]
        for row in connection.execute("SELECT key, value FROM import_metadata ORDER BY key")
    }
    payload = {
        "format": "slm_lexicon_lookup_cache_v0",
        "source_database": str(DB_PATH.relative_to(ROOT)),
        "metadata": metadata,
        "entries": entries,
    }
    CACHE_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {CACHE_PATH}")
    print(f"entries={len(entries)}")
    connection.close()


if __name__ == "__main__":
    main()
