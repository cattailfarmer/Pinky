PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_provenance (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    source_url TEXT NOT NULL,
    license TEXT NOT NULL,
    retrieved_at TEXT,
    source_hash TEXT
);

CREATE TABLE IF NOT EXISTS terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lemma TEXT NOT NULL,
    normalized TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    is_closed_class INTEGER NOT NULL DEFAULT 0,
    source_id TEXT NOT NULL,
    UNIQUE(normalized, language, source_id),
    FOREIGN KEY(source_id) REFERENCES source_provenance(id)
);

CREATE INDEX IF NOT EXISTS idx_terms_normalized ON terms(normalized);

CREATE TABLE IF NOT EXISTS term_forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id INTEGER NOT NULL,
    form TEXT NOT NULL,
    normalized TEXT NOT NULL,
    form_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE(term_id, normalized, form_kind),
    FOREIGN KEY(term_id) REFERENCES terms(id),
    FOREIGN KEY(source_id) REFERENCES source_provenance(id)
);

CREATE INDEX IF NOT EXISTS idx_term_forms_normalized ON term_forms(normalized);

CREATE TABLE IF NOT EXISTS grammar_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    support_weight REAL NOT NULL,
    source_id TEXT NOT NULL,
    rationale TEXT NOT NULL,
    UNIQUE(term_id, role, source_id, rationale),
    FOREIGN KEY(term_id) REFERENCES terms(id),
    FOREIGN KEY(source_id) REFERENCES source_provenance(id)
);

CREATE INDEX IF NOT EXISTS idx_grammar_roles_term ON grammar_roles(term_id);

CREATE TABLE IF NOT EXISTS closed_class_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id INTEGER NOT NULL,
    class TEXT NOT NULL,
    subclass TEXT NOT NULL DEFAULT '',
    diffusion_priority REAL NOT NULL,
    structural_hint TEXT NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE(term_id, class, subclass),
    FOREIGN KEY(term_id) REFERENCES terms(id),
    FOREIGN KEY(source_id) REFERENCES source_provenance(id)
);

CREATE INDEX IF NOT EXISTS idx_closed_class_term ON closed_class_terms(term_id);

CREATE TABLE IF NOT EXISTS senses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id INTEGER NOT NULL,
    sense_key TEXT NOT NULL,
    synset_id TEXT NOT NULL,
    pos TEXT NOT NULL,
    definition TEXT,
    source_id TEXT NOT NULL,
    UNIQUE(term_id, sense_key, synset_id),
    FOREIGN KEY(term_id) REFERENCES terms(id),
    FOREIGN KEY(source_id) REFERENCES source_provenance(id)
);

CREATE INDEX IF NOT EXISTS idx_senses_term ON senses(term_id);
CREATE INDEX IF NOT EXISTS idx_senses_synset ON senses(synset_id);

CREATE TABLE IF NOT EXISTS synsets (
    synset_id TEXT PRIMARY KEY,
    pos TEXT NOT NULL,
    definition TEXT,
    source_id TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES source_provenance(id)
);

CREATE TABLE IF NOT EXISTS sense_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_synset_id TEXT NOT NULL,
    target_synset_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE(source_synset_id, target_synset_id, relation_type),
    FOREIGN KEY(source_id) REFERENCES source_provenance(id)
);

CREATE TABLE IF NOT EXISTS import_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
