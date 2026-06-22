from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "lexical_schema.sql"
CLOSED_CLASS = ROOT / "seeds" / "closed_class_terms.json"
OEWN_MANIFEST = ROOT / "data" / "raw" / "open_english_wordnet" / "manifest.json"
DB_PATH = ROOT / "data" / "slm_lexicon.sqlite"

POS_TO_ROLE = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}


def connect(reset: bool) -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    return connection


def upsert_source(connection: sqlite3.Connection, source: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO source_provenance
          (id, source_name, source_version, source_url, license, retrieved_at, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source["id"],
            source["source_name"],
            source["source_version"],
            source["source_url"],
            source["license"],
            source.get("retrieved_at"),
            source.get("source_hash") or source.get("sha256"),
        ),
    )


def normalize(value: str) -> str:
    return value.strip().replace("_", " ").lower()


def get_or_create_term(
    connection: sqlite3.Connection,
    lemma: str,
    source_id: str,
    *,
    is_closed_class: bool = False,
) -> int:
    normalized = normalize(lemma)
    connection.execute(
        """
        INSERT OR IGNORE INTO terms (lemma, normalized, language, is_closed_class, source_id)
        VALUES (?, ?, 'en', ?, ?)
        """,
        (lemma, normalized, 1 if is_closed_class else 0, source_id),
    )
    row = connection.execute(
        """
        SELECT id FROM terms
        WHERE normalized = ? AND language = 'en' AND source_id = ?
        """,
        (normalized, source_id),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"term insert failed for {lemma}")
    return int(row[0])


def add_term_form(
    connection: sqlite3.Connection,
    term_id: int,
    form: str,
    form_kind: str,
    source_id: str,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO term_forms
          (term_id, form, normalized, form_kind, source_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (term_id, form, normalize(form), form_kind, source_id),
    )


def add_grammar_role(
    connection: sqlite3.Connection,
    term_id: int,
    role: str,
    support: float,
    source_id: str,
    rationale: str,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO grammar_roles
          (term_id, role, support_weight, source_id, rationale)
        VALUES (?, ?, ?, ?, ?)
        """,
        (term_id, role, support, source_id, rationale),
    )


def import_closed_class(connection: sqlite3.Connection) -> None:
    payload = json.loads(CLOSED_CLASS.read_text(encoding="utf-8"))
    source = payload["source"]
    upsert_source(connection, source)
    source_id = source["id"]

    for term in payload["terms"]:
        term_id = get_or_create_term(
            connection,
            term["lemma"],
            source_id,
            is_closed_class=True,
        )
        add_term_form(connection, term_id, term["lemma"], "lemma", source_id)
        for role in term["roles"]:
            add_grammar_role(
                connection,
                term_id,
                role,
                term["diffusion_priority"],
                source_id,
                term["structural_hint"],
            )
        connection.execute(
            """
            INSERT OR IGNORE INTO closed_class_terms
              (term_id, class, subclass, diffusion_priority, structural_hint, source_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                term_id,
                term["class"],
                term.get("subclass") or "",
                term["diffusion_priority"],
                term["structural_hint"],
                source_id,
            ),
        )


def import_oewn(connection: sqlite3.Connection, limit: int | None = None) -> None:
    if not OEWN_MANIFEST.exists():
        print("Open English WordNet manifest not found; skipping open-class import.")
        return

    manifest = json.loads(OEWN_MANIFEST.read_text(encoding="utf-8"))
    source = {
        "id": manifest["source_id"],
        "source_name": manifest["source_name"],
        "source_version": manifest["source_version"],
        "source_url": manifest["source_url"],
        "license": manifest["license"],
        "retrieved_at": manifest["retrieved_at"],
        "source_hash": manifest["sha256"],
    }
    upsert_source(connection, source)
    source_id = source["id"]
    xml_path = ROOT / manifest["file"]

    with gzip.open(xml_path, "rb") as handle:
        tree = ET.parse(handle)
    root = tree.getroot()
    ns = namespace(root.tag)

    synset_definitions: dict[str, tuple[str, str | None]] = {}
    for synset in root.findall(f".//{ns}Synset"):
        synset_id = required_attr(synset, "id")
        pos = synset.attrib.get("partOfSpeech") or synset.attrib.get("pos") or "unknown"
        definition = first_text(synset, f"{ns}Definition")
        synset_definitions[synset_id] = (pos, definition)
        connection.execute(
            """
            INSERT OR IGNORE INTO synsets (synset_id, pos, definition, source_id)
            VALUES (?, ?, ?, ?)
            """,
            (synset_id, pos, definition, source_id),
        )
        for relation in synset.findall(f"{ns}SynsetRelation"):
            target = relation.attrib.get("target")
            relation_type = relation.attrib.get("relType") or relation.attrib.get("type")
            if target and relation_type:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO sense_relations
                      (source_synset_id, target_synset_id, relation_type, source_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (synset_id, target, relation_type, source_id),
                )

    imported_senses = 0
    for lexical_entry in root.findall(f".//{ns}LexicalEntry"):
        lemma_element = lexical_entry.find(f"{ns}Lemma")
        if lemma_element is None:
            continue
        lemma = lemma_element.attrib.get("writtenForm")
        pos = lemma_element.attrib.get("partOfSpeech") or lemma_element.attrib.get("pos")
        if not lemma or not pos:
            continue
        role = POS_TO_ROLE.get(pos)
        if role is None:
            continue

        term_id = get_or_create_term(connection, lemma, source_id)
        add_term_form(connection, term_id, lemma, "lemma", source_id)
        add_grammar_role(
            connection,
            term_id,
            role,
            0.72,
            source_id,
            f"Open English WordNet lemma partOfSpeech={pos}",
        )

        for form in lexical_entry.findall(f"{ns}Form"):
            written = form.attrib.get("writtenForm")
            if written:
                add_term_form(connection, term_id, written, "inflected", source_id)

        for sense in lexical_entry.findall(f"{ns}Sense"):
            sense_id = required_attr(sense, "id")
            synset_id = required_attr(sense, "synset")
            synset_pos, definition = synset_definitions.get(synset_id, (pos, None))
            connection.execute(
                """
                INSERT OR IGNORE INTO senses
                  (term_id, sense_key, synset_id, pos, definition, source_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (term_id, sense_id, synset_id, synset_pos, definition, source_id),
            )
            imported_senses += 1
            if limit and imported_senses >= limit:
                return


def namespace(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[0] + "}"
    return ""


def required_attr(element: ET.Element, name: str) -> str:
    value = element.attrib.get(name)
    if value is None:
        raise RuntimeError(f"missing required XML attribute {name}")
    return value


def first_text(element: ET.Element, path: str) -> str | None:
    child = element.find(path)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def write_metadata(connection: sqlite3.Connection) -> None:
    counts = {
        "terms": "SELECT COUNT(*) FROM terms",
        "term_forms": "SELECT COUNT(*) FROM term_forms",
        "grammar_roles": "SELECT COUNT(*) FROM grammar_roles",
        "closed_class_terms": "SELECT COUNT(*) FROM closed_class_terms",
        "senses": "SELECT COUNT(*) FROM senses",
        "synsets": "SELECT COUNT(*) FROM synsets",
        "sense_relations": "SELECT COUNT(*) FROM sense_relations",
    }
    for key, query in counts.items():
        value = str(connection.execute(query).fetchone()[0])
        connection.execute(
            "INSERT OR REPLACE INTO import_metadata (key, value) VALUES (?, ?)",
            (f"count:{key}", value),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument("--wordnet-limit", type=int)
    args = parser.parse_args()

    connection = connect(reset=not args.no_reset)
    with connection:
        import_closed_class(connection)
        import_oewn(connection, limit=args.wordnet_limit)
        write_metadata(connection)

    print(f"Wrote {DB_PATH}")
    for key, value in connection.execute(
        "SELECT key, value FROM import_metadata ORDER BY key"
    ):
        print(f"{key}={value}")
    connection.close()


if __name__ == "__main__":
    main()
