from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "slm_lexicon.sqlite"
PACK_DIR = ROOT / "data" / "slm_lexical_substrate"
SUBSTRATE_ID = "slm_lexical_substrate_en_oewn2025_v0"


def rows_by_key(connection: sqlite3.Connection, query: str) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    connection.row_factory = sqlite3.Row
    for row in connection.execute(query):
        value = dict(row)
        term_id = int(value.pop("term_id"))
        grouped[term_id].append(value)
    return grouped


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def write_pretty_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_entries(connection: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
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
        entries[row["normalized"]].append(
            {
                "term_id": term_id,
                "lemma": row["lemma"],
                "normalized": row["normalized"],
                "is_closed_class": bool(row["is_closed_class"]),
                "roles": roles.get(term_id, []),
                "closed_class": closed_class.get(term_id, []),
                "senses": senses.get(term_id, [])[:8],
            }
        )
    return entries


def build_closed_class_speed_table(
    entries: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    terms: dict[str, list[dict[str, Any]]] = {}
    for normalized, term_entries in entries.items():
        closed_entries = []
        for entry in term_entries:
            if not entry.get("closed_class"):
                continue
            closed_entries.append(
                {
                    "term_id": entry["term_id"],
                    "lemma": entry["lemma"],
                    "roles": entry.get("roles", []),
                    "closed_class": entry.get("closed_class", []),
                }
            )
        if closed_entries:
            terms[normalized] = closed_entries
    return {
        "format": "slm_closed_class_speed_table_v0",
        "substrate_id": SUBSTRATE_ID,
        "purpose": "first-pass structural and function-word constraints",
        "terms": terms,
    }


def build_source_provenance(connection: sqlite3.Connection) -> dict[str, Any]:
    sources = []
    for row in connection.execute(
        """
        SELECT id, source_name, source_version, source_url, license,
               retrieved_at, source_hash
        FROM source_provenance
        ORDER BY id
        """
    ):
        sources.append(dict(row))
    return {
        "format": "slm_lexical_source_provenance_v0",
        "substrate_id": SUBSTRATE_ID,
        "sources": sources,
    }


def build_manifest(
    connection: sqlite3.Connection,
    index_path: Path,
    closed_class_path: Path,
    provenance_path: Path,
) -> dict[str, Any]:
    counts = {
        row["key"].removeprefix("count:"): int(row["value"])
        for row in connection.execute("SELECT key, value FROM import_metadata")
        if row["key"].startswith("count:")
    }
    counts["substrate_entries"] = len(
        json.loads(index_path.read_text(encoding="utf-8"))["entries"]
    )
    return {
        "format": "slm_lexical_substrate_manifest_v0",
        "substrate_id": SUBSTRATE_ID,
        "artifact_kind": "first_class_slm_lexical_substrate",
        "build_time_utc": datetime.now(timezone.utc).isoformat(),
        "authority_database": str(DB_PATH.relative_to(ROOT)),
        "runtime_contract": {
            "role": "speed-dial lexical substrate for SLM evidence formation",
            "outputs": [
                "grammar role evidence",
                "closed-class structural hints",
                "open-class sense candidates",
                "source provenance",
            ],
            "non_authority": [
                "does not stabilize glyphs",
                "does not settle contextual sense alone",
                "does not replace deliberative convergence",
            ],
        },
        "tables": {
            "term_role_sense_index": {
                "path": index_path.name,
                "sha256": sha256(index_path),
            },
            "closed_class_speed_table": {
                "path": closed_class_path.name,
                "sha256": sha256(closed_class_path),
            },
            "source_provenance": {
                "path": provenance_path.name,
                "sha256": sha256(provenance_path),
            },
        },
        "counts": counts,
    }


def write_manifest_sop(path: Path, manifest: dict[str, Any]) -> None:
    counts = manifest["counts"]
    lines = [
        "& [SLMLexicalSubstratePack] is a first-class runtime lexical artifact for SLM",
        f"  + [substrate_id] is {manifest['substrate_id']}",
        "  + [artifact_kind] is first_class_slm_lexical_substrate",
        f"  + [authority_database] is {manifest['authority_database']}",
        f"  + [term_count] is {counts.get('terms', 0)}",
        f"  + [grammar_role_count] is {counts.get('grammar_roles', 0)}",
        f"  + [sense_count] is {counts.get('senses', 0)}",
        f"  + [closed_class_count] is {counts.get('closed_class_terms', 0)}",
        f"  + [substrate_entry_count] is {counts.get('substrate_entries', 0)}",
        "",
        "  & [RuntimeTables] is the speed-dial table set",
        "    + [term_role_sense_index] is term_role_sense_index.json",
        "    + [closed_class_speed_table] is closed_class_speed_table.json",
        "    + [source_provenance] is source_provenance.json",
        "",
        "  & [EvidenceBoundary] is preserved",
        "    = must: create lexical evidence, not stabilized glyphs",
        "    = must: preserve source provenance",
        "    = must: preserve competing roles and senses",
        "    - never: collapse lexical membership into semantic truth",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"missing database: {DB_PATH}")
    PACK_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    entries = build_entries(connection)
    index = {
        "format": "slm_lexical_substrate_index_v0",
        "substrate_id": SUBSTRATE_ID,
        "source_database": str(DB_PATH.relative_to(ROOT)),
        "metadata": {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM import_metadata ORDER BY key")
        },
        "entries": entries,
    }
    index_path = PACK_DIR / "term_role_sense_index.json"
    closed_class_path = PACK_DIR / "closed_class_speed_table.json"
    provenance_path = PACK_DIR / "source_provenance.json"
    manifest_path = PACK_DIR / "manifest.json"
    manifest_sop_path = PACK_DIR / "manifest.sop"

    write_json(index_path, index)
    write_json(closed_class_path, build_closed_class_speed_table(entries))
    write_pretty_json(provenance_path, build_source_provenance(connection))
    manifest = build_manifest(connection, index_path, closed_class_path, provenance_path)
    write_pretty_json(manifest_path, manifest)
    write_manifest_sop(manifest_sop_path, manifest)
    connection.close()

    print(f"Wrote {PACK_DIR}")
    print(f"substrate_id={SUBSTRATE_ID}")
    print(f"entries={len(entries)}")
    print(f"term_role_sense_index_sha256={manifest['tables']['term_role_sense_index']['sha256']}")


if __name__ == "__main__":
    main()
