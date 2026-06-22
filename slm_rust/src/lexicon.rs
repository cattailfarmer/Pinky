use std::collections::HashMap;
use std::fmt::{Display, Formatter};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::core::{GrammarRole, Token};
use crate::providers::{AdapterKind, ProviderAdapter, ProviderProvenance, ProviderSuggestion};

#[derive(Debug)]
pub enum LexiconError {
    Io(std::io::Error),
    Json(serde_json::Error),
    MissingSubstrate(PathBuf),
}

impl Display for LexiconError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(error) => write!(formatter, "lexical substrate I/O error: {error}"),
            Self::Json(error) => write!(formatter, "lexical substrate JSON error: {error}"),
            Self::MissingSubstrate(path) => {
                write!(
                    formatter,
                    "lexical substrate not found at {}",
                    path.display()
                )
            }
        }
    }
}

impl std::error::Error for LexiconError {}

impl From<std::io::Error> for LexiconError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for LexiconError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LexicalRoleEvidence {
    pub role: GrammarRole,
    pub support_weight: f32,
    pub source_id: String,
    pub source_name: String,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ClosedClassEvidence {
    pub class: String,
    pub subclass: String,
    pub diffusion_priority: f32,
    pub structural_hint: String,
    pub source_id: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LexicalSenseEvidence {
    pub sense_key: String,
    pub synset_id: String,
    pub pos: String,
    pub definition: Option<String>,
    pub source_id: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LexicalEntryEvidence {
    pub term_id: i64,
    pub lemma: String,
    pub normalized: String,
    pub is_closed_class: bool,
    pub roles: Vec<LexicalRoleEvidence>,
    pub closed_class: Vec<ClosedClassEvidence>,
    pub senses: Vec<LexicalSenseEvidence>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LexicalSubstrateIndex {
    pub format: String,
    pub substrate_id: String,
    pub source_database: String,
    pub metadata: HashMap<String, Value>,
    pub entries: HashMap<String, Vec<LexicalEntryEvidence>>,
}

pub struct LexicalSubstrate {
    index: LexicalSubstrateIndex,
    path: PathBuf,
}

impl LexicalSubstrate {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, LexiconError> {
        let path = path.as_ref().to_path_buf();
        if !path.exists() {
            return Err(LexiconError::MissingSubstrate(path));
        }
        let text = std::fs::read_to_string(&path)?;
        let index = serde_json::from_str(&text)?;
        Ok(Self { index, path })
    }

    pub fn open_default() -> Result<Self, LexiconError> {
        Self::open(default_lexical_substrate_index_path())
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn lookup(&self, token_text: &str) -> Vec<LexicalEntryEvidence> {
        self.index
            .entries
            .get(&normalize(token_text))
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .map(normalize_roles)
            .collect()
    }

    pub fn metadata_value(&self, key: &str) -> Option<String> {
        self.index.metadata.get(key).map(|value| match value {
            Value::String(text) => text.clone(),
            other => other.to_string(),
        })
    }

    pub fn substrate_id(&self) -> &str {
        &self.index.substrate_id
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LexicalSenseRoutingPolicy {
    DeferClosedClassTokenSenses,
    EmitAllSenses,
}

pub struct LexicalSubstrateProvider {
    substrate: LexicalSubstrate,
    provenance: ProviderProvenance,
    sense_routing_policy: LexicalSenseRoutingPolicy,
}

impl LexicalSubstrateProvider {
    pub fn open_default() -> Result<Self, LexiconError> {
        Self::open(LexicalSubstrate::open_default()?)
    }

    pub fn open(substrate: LexicalSubstrate) -> Result<Self, LexiconError> {
        Ok(Self {
            provenance: ProviderProvenance {
                provider_id: "slm-lexical-substrate".to_string(),
                model_id: substrate.substrate_id().to_string(),
                adapter_kind: AdapterKind::LexicalDatabase,
                prompt_contract: "lexical-substrate-speed-dial-v0".to_string(),
                response_hash: None,
                timestamp: None,
                adapter_version: "0.1.0".to_string(),
            },
            substrate,
            sense_routing_policy: LexicalSenseRoutingPolicy::DeferClosedClassTokenSenses,
        })
    }

    pub fn with_sense_routing_policy(mut self, policy: LexicalSenseRoutingPolicy) -> Self {
        self.sense_routing_policy = policy;
        self
    }
}

impl ProviderAdapter for LexicalSubstrateProvider {
    fn provenance(&self) -> &ProviderProvenance {
        &self.provenance
    }

    fn suggestions(&self, _input: &str, tokens: &[Token]) -> Vec<ProviderSuggestion> {
        let mut suggestions = Vec::new();
        for token in tokens {
            let entries = self.substrate.lookup(&token.surface_text);
            let token_has_closed_class_authority = entries
                .iter()
                .any(|entry| entry.is_closed_class || !entry.closed_class.is_empty());
            for entry in entries {
                for role in entry.roles {
                    suggestions.push(ProviderSuggestion::grammar_role(
                        self.provenance.clone(),
                        format!(
                            "lexicon:{}:{}:{}",
                            token.id,
                            entry.term_id,
                            role_name_for_id(role.role)
                        ),
                        token.id.clone(),
                        role.role,
                        role.support_weight,
                        format!("{}: {}", role.source_name, role.rationale),
                    ));
                }
                for closed_class in &entry.closed_class {
                    suggestions.push(ProviderSuggestion::structural_hint(
                        self.provenance.clone(),
                        format!(
                            "lexicon:{}:{}:closed:{}:{}",
                            token.id, entry.term_id, closed_class.class, closed_class.subclass
                        ),
                        token.id.clone(),
                        closed_class.class.clone(),
                        closed_class.subclass.clone(),
                        closed_class.diffusion_priority,
                        closed_class.structural_hint.clone(),
                    ));
                }
                if token_has_closed_class_authority
                    && self.sense_routing_policy
                        == LexicalSenseRoutingPolicy::DeferClosedClassTokenSenses
                {
                    continue;
                }
                for sense in &entry.senses {
                    suggestions.push(ProviderSuggestion::lexical_sense(
                        self.provenance.clone(),
                        format!(
                            "lexicon:{}:{}:sense:{}",
                            token.id, entry.term_id, sense.sense_key
                        ),
                        token.id.clone(),
                        entry.lemma.clone(),
                        sense.sense_key.clone(),
                        sense.synset_id.clone(),
                        sense.pos.clone(),
                        sense.definition.clone(),
                    ));
                }
            }
        }
        suggestions
    }
}

pub fn default_lexical_substrate_index_path() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")))
        .join("slm_lexicon")
        .join("data")
        .join("slm_lexical_substrate")
        .join("term_role_sense_index.json")
}

fn normalize_roles(mut entry: LexicalEntryEvidence) -> LexicalEntryEvidence {
    entry
        .roles
        .retain(|role| !matches!(role.role, GrammarRole::Unknown | GrammarRole::Extension));
    entry
}

fn role_name_for_id(role: GrammarRole) -> &'static str {
    match role {
        GrammarRole::Noun => "noun",
        GrammarRole::Verb => "verb",
        GrammarRole::Adjective => "adjective",
        GrammarRole::Adverb => "adverb",
        GrammarRole::Determiner => "determiner",
        GrammarRole::Preposition => "preposition",
        GrammarRole::Conjunction => "conjunction",
        GrammarRole::Auxiliary => "auxiliary",
        GrammarRole::Modal => "modal",
        GrammarRole::Pronoun => "pronoun",
        GrammarRole::Punctuation => "punctuation",
        GrammarRole::Unknown => "unknown",
        GrammarRole::Extension => "extension",
    }
}

fn normalize(value: &str) -> String {
    value.trim().replace('_', " ").to_lowercase()
}

#[cfg(test)]
mod tests {
    use crate::core::{EvidenceSource, GrammarRole};
    use crate::evidence::EvidenceWorkspace;
    use crate::providers::{ProviderAdapter, ProviderSuggestionKind};

    use super::{LexicalSenseRoutingPolicy, LexicalSubstrate, LexicalSubstrateProvider};

    #[test]
    fn file_lexicon_reads_closed_class_and_wordnet_entries() {
        let lexicon = LexicalSubstrate::open_default().expect("lexical substrate exists");

        let for_entries = lexicon.lookup("for");
        assert!(for_entries.iter().any(|entry| {
            entry
                .closed_class
                .iter()
                .any(|closed| closed.class == "preposition")
        }));

        let quickly_entries = lexicon.lookup("quickly");
        assert!(quickly_entries.iter().any(|entry| {
            entry
                .roles
                .iter()
                .any(|role| role.role == GrammarRole::Adverb)
        }));

        let compiler_entries = lexicon.lookup("compiler");
        assert!(
            compiler_entries
                .iter()
                .any(|entry| entry.senses.iter().any(|sense| sense
                    .definition
                    .as_deref()
                    .unwrap_or_default()
                    .contains("computer science")))
        );
    }

    #[test]
    fn lexicon_provider_injects_authority_grammar_evidence() {
        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut workspace = EvidenceWorkspace::from_text("lexicon-fixture", "Design quickly.");
        let suggestions = provider.suggestions(&workspace.input_text, &workspace.tokens);
        workspace.ingest_provider_suggestions(suggestions);

        assert!(workspace.grammar_candidates.iter().any(|candidate| {
            candidate.role == GrammarRole::Adverb
                && candidate.source == EvidenceSource::LexicalAuthority
        }));
    }

    #[test]
    fn lexicon_provider_defers_closed_class_token_senses_by_default() {
        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let workspace = EvidenceWorkspace::from_text("lexicon-closed-class", "a");
        let suggestions = provider.suggestions(&workspace.input_text, &workspace.tokens);

        assert!(
            suggestions
                .iter()
                .any(|suggestion| suggestion.kind == ProviderSuggestionKind::StructuralHint)
        );
        assert!(
            !suggestions
                .iter()
                .any(|suggestion| suggestion.kind == ProviderSuggestionKind::LexicalSense)
        );
    }

    #[test]
    fn lexicon_provider_can_emit_closed_class_token_senses_when_explicitly_requested() {
        let provider = LexicalSubstrateProvider::open_default()
            .expect("substrate provider opens")
            .with_sense_routing_policy(LexicalSenseRoutingPolicy::EmitAllSenses);
        let workspace = EvidenceWorkspace::from_text("lexicon-closed-class-query", "a");
        let suggestions = provider.suggestions(&workspace.input_text, &workspace.tokens);

        assert!(
            suggestions
                .iter()
                .any(|suggestion| suggestion.kind == ProviderSuggestionKind::LexicalSense)
        );
    }
}
