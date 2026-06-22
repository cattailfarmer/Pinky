use serde::{Deserialize, Serialize};

use crate::core::{GrammarRole, LineageRecord, MeaningKind, Token};
use crate::graph::RelationKind;
use crate::stabilization::{Faculty, FacultyResult};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AdapterKind {
    Mock,
    LmStudioOpenAiCompatible,
    Ollama,
    LlamaCppServer,
    HostedOpenAiCompatible,
    LexicalDatabase,
    Extension,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderCapability {
    DictionaryService,
    RoleSuggestion,
    CandidateMeaning,
    CandidateRelation,
    FacultyRun,
    Objection,
    Answer,
    JuryReview,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProviderConfig {
    pub provider_id: String,
    pub adapter_kind: AdapterKind,
    pub model_id: String,
    pub endpoint: Option<String>,
    pub prompt_contract: String,
    pub adapter_version: String,
    pub enabled: bool,
    pub capabilities: Vec<ProviderCapability>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProviderSetConfig {
    pub provider_set_id: String,
    pub description: String,
    pub providers: Vec<ProviderConfig>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProviderProvenance {
    pub provider_id: String,
    pub model_id: String,
    pub adapter_kind: AdapterKind,
    pub prompt_contract: String,
    pub response_hash: Option<String>,
    pub timestamp: Option<String>,
    pub adapter_version: String,
}

impl ProviderConfig {
    pub fn provenance_template(&self) -> ProviderProvenance {
        ProviderProvenance {
            provider_id: self.provider_id.clone(),
            model_id: self.model_id.clone(),
            adapter_kind: self.adapter_kind.clone(),
            prompt_contract: self.prompt_contract.clone(),
            response_hash: None,
            timestamp: None,
            adapter_version: self.adapter_version.clone(),
        }
    }

    pub fn has_capability(&self, capability: &ProviderCapability) -> bool {
        self.capabilities.iter().any(|item| item == capability)
    }
}

impl ProviderSetConfig {
    pub fn enabled_for_capability(&self, capability: ProviderCapability) -> Vec<&ProviderConfig> {
        self.providers
            .iter()
            .filter(|provider| provider.enabled && provider.has_capability(&capability))
            .collect()
    }

    pub fn default_local() -> Self {
        Self {
            provider_set_id: "local_provider_set_v0".to_string(),
            description: "Local deterministic/mock-first provider set for SLM prototype work."
                .to_string(),
            providers: vec![
                ProviderConfig {
                    provider_id: "mock-fixture".to_string(),
                    adapter_kind: AdapterKind::Mock,
                    model_id: "mock-model".to_string(),
                    endpoint: None,
                    prompt_contract: "mock-fixture".to_string(),
                    adapter_version: "v0".to_string(),
                    enabled: true,
                    capabilities: vec![
                        ProviderCapability::RoleSuggestion,
                        ProviderCapability::CandidateMeaning,
                        ProviderCapability::CandidateRelation,
                        ProviderCapability::FacultyRun,
                        ProviderCapability::Objection,
                        ProviderCapability::Answer,
                        ProviderCapability::JuryReview,
                    ],
                },
                ProviderConfig {
                    provider_id: "local-lm-studio".to_string(),
                    adapter_kind: AdapterKind::LmStudioOpenAiCompatible,
                    model_id: "local-model".to_string(),
                    endpoint: Some("http://127.0.0.1:1234/v1/chat/completions".to_string()),
                    prompt_contract: "sidecar_task_prompt_contracts_v0".to_string(),
                    adapter_version: "source-only-v0".to_string(),
                    enabled: false,
                    capabilities: vec![
                        ProviderCapability::RoleSuggestion,
                        ProviderCapability::CandidateMeaning,
                        ProviderCapability::CandidateRelation,
                        ProviderCapability::FacultyRun,
                        ProviderCapability::Objection,
                        ProviderCapability::Answer,
                    ],
                },
                ProviderConfig {
                    provider_id: "local-ollama".to_string(),
                    adapter_kind: AdapterKind::Ollama,
                    model_id: "llama3.2".to_string(),
                    endpoint: Some("http://127.0.0.1:11434/api/chat".to_string()),
                    prompt_contract: "sidecar_task_prompt_contracts_v0".to_string(),
                    adapter_version: "source-only-v0".to_string(),
                    enabled: false,
                    capabilities: vec![
                        ProviderCapability::RoleSuggestion,
                        ProviderCapability::CandidateMeaning,
                        ProviderCapability::CandidateRelation,
                        ProviderCapability::FacultyRun,
                        ProviderCapability::Objection,
                        ProviderCapability::Answer,
                    ],
                },
            ],
        }
    }
}

pub fn provider_set_from_json(json: &str) -> serde_json::Result<ProviderSetConfig> {
    serde_json::from_str(json)
}

pub fn validate_provider_set(config: &ProviderSetConfig) -> Result<(), Vec<String>> {
    let mut errors = Vec::new();
    if config.provider_set_id.trim().is_empty() {
        errors.push("provider_set_id is required".to_string());
    }
    for provider in &config.providers {
        if provider.provider_id.trim().is_empty() {
            errors.push("provider_id is required".to_string());
        }
        if provider.model_id.trim().is_empty() {
            errors.push(format!("{} model_id is required", provider.provider_id));
        }
        if provider.adapter_version.trim().is_empty() {
            errors.push(format!(
                "{} adapter_version is required",
                provider.provider_id
            ));
        }
        if provider.capabilities.is_empty() {
            errors.push(format!(
                "{} must declare at least one capability",
                provider.provider_id
            ));
        }
        if provider.adapter_kind != AdapterKind::Mock && provider.prompt_contract.trim().is_empty()
        {
            errors.push(format!(
                "{} non-mock provider requires prompt_contract",
                provider.provider_id
            ));
        }
        if provider.enabled
            && provider.adapter_kind != AdapterKind::Mock
            && provider
                .endpoint
                .as_deref()
                .unwrap_or_default()
                .trim()
                .is_empty()
        {
            errors.push(format!(
                "{} enabled non-mock provider requires endpoint",
                provider.provider_id
            ));
        }
    }

    if errors.is_empty() {
        Ok(())
    } else {
        Err(errors)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HemispherePerspective {
    LeftAnalytic,
    RightAssociative,
    Integrated,
    Unspecified,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderFacultyVote {
    pub faculty: Faculty,
    pub result: FacultyResult,
    pub perspective: HemispherePerspective,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderFacultyVeto {
    pub faculty: Faculty,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderFacultyReport {
    pub run_id: String,
    pub target_ref: String,
    pub votes: Vec<ProviderFacultyVote>,
    pub vetoes: Vec<ProviderFacultyVeto>,
    pub convergence_score: f32,
    pub convergence_statement: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderSuggestionKind {
    GrammarRole,
    StructuralHint,
    LexicalSense,
    CandidateMeaning,
    CandidateRelation,
    FacultyVote,
    Objection,
    Answer,
    JuryMeasurement,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderSuggestion {
    pub id: String,
    pub provenance: ProviderProvenance,
    pub kind: ProviderSuggestionKind,
    pub target_ref: String,
    pub payload: String,
    pub support_weight: Option<f32>,
    pub rationale: Option<String>,
    pub grammar_role: Option<GrammarRole>,
    pub meaning_kind: Option<MeaningKind>,
    pub relation_kind: Option<RelationKind>,
    pub source_label: Option<String>,
    pub target_label: Option<String>,
    pub disagreement_class: Option<String>,
    pub answer_kind: Option<String>,
    pub faculty_report: Option<ProviderFacultyReport>,
    pub closed_class: Option<String>,
    pub closed_subclass: Option<String>,
    pub structural_hint: Option<String>,
    pub sense_key: Option<String>,
    pub synset_id: Option<String>,
    pub part_of_speech: Option<String>,
    pub definition: Option<String>,
    pub lineage: LineageRecord,
}

impl ProviderSuggestion {
    pub fn grammar_role(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        token_id: impl Into<String>,
        role: GrammarRole,
        support_weight: f32,
        rationale: impl Into<String>,
    ) -> Self {
        let id = id.into();
        Self {
            id: id.clone(),
            provenance,
            kind: ProviderSuggestionKind::GrammarRole,
            target_ref: token_id.into(),
            payload: role_name_payload(role).to_string(),
            support_weight: Some(support_weight),
            rationale: Some(rationale.into()),
            grammar_role: Some(role),
            meaning_kind: None,
            relation_kind: None,
            source_label: None,
            target_label: None,
            disagreement_class: None,
            answer_kind: None,
            faculty_report: None,
            closed_class: None,
            closed_subclass: None,
            structural_hint: None,
            sense_key: None,
            synset_id: None,
            part_of_speech: None,
            definition: None,
            lineage: LineageRecord::new(id, "provider grammar role"),
        }
    }

    pub fn structural_hint(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        token_id: impl Into<String>,
        class: impl Into<String>,
        subclass: impl Into<String>,
        diffusion_priority: f32,
        structural_hint: impl Into<String>,
    ) -> Self {
        let id = id.into();
        let class = class.into();
        let subclass = subclass.into();
        let structural_hint = structural_hint.into();
        Self {
            id: id.clone(),
            provenance,
            kind: ProviderSuggestionKind::StructuralHint,
            target_ref: token_id.into(),
            payload: structural_hint.clone(),
            support_weight: Some(diffusion_priority),
            rationale: Some(structural_hint.clone()),
            grammar_role: None,
            meaning_kind: None,
            relation_kind: None,
            source_label: None,
            target_label: None,
            disagreement_class: None,
            answer_kind: None,
            faculty_report: None,
            closed_class: Some(class),
            closed_subclass: Some(subclass),
            structural_hint: Some(structural_hint),
            sense_key: None,
            synset_id: None,
            part_of_speech: None,
            definition: None,
            lineage: LineageRecord::new(id, "provider structural hint"),
        }
    }

    pub fn lexical_sense(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        token_id: impl Into<String>,
        lemma: impl Into<String>,
        sense_key: impl Into<String>,
        synset_id: impl Into<String>,
        part_of_speech: impl Into<String>,
        definition: Option<String>,
    ) -> Self {
        let id = id.into();
        let lemma = lemma.into();
        let sense_key = sense_key.into();
        let synset_id = synset_id.into();
        let part_of_speech = part_of_speech.into();
        let rationale = definition
            .clone()
            .unwrap_or_else(|| "lexical substrate sense candidate".to_string());
        Self {
            id: id.clone(),
            provenance,
            kind: ProviderSuggestionKind::LexicalSense,
            target_ref: token_id.into(),
            payload: lemma,
            support_weight: Some(0.58),
            rationale: Some(rationale),
            grammar_role: None,
            meaning_kind: None,
            relation_kind: None,
            source_label: None,
            target_label: None,
            disagreement_class: None,
            answer_kind: None,
            faculty_report: None,
            closed_class: None,
            closed_subclass: None,
            structural_hint: None,
            sense_key: Some(sense_key),
            synset_id: Some(synset_id),
            part_of_speech: Some(part_of_speech),
            definition,
            lineage: LineageRecord::new(id, "provider lexical sense"),
        }
    }

    pub fn candidate_meaning(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        label: impl Into<String>,
        kind: MeaningKind,
        support_weight: f32,
        rationale: impl Into<String>,
    ) -> Self {
        let id = id.into();
        Self {
            id: id.clone(),
            provenance,
            kind: ProviderSuggestionKind::CandidateMeaning,
            target_ref: id.clone(),
            payload: label.into(),
            support_weight: Some(support_weight),
            rationale: Some(rationale.into()),
            grammar_role: None,
            meaning_kind: Some(kind),
            relation_kind: None,
            source_label: None,
            target_label: None,
            disagreement_class: None,
            answer_kind: None,
            faculty_report: None,
            closed_class: None,
            closed_subclass: None,
            structural_hint: None,
            sense_key: None,
            synset_id: None,
            part_of_speech: None,
            definition: None,
            lineage: LineageRecord::new(id, "provider candidate meaning"),
        }
    }

    pub fn objection(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        target_ref: impl Into<String>,
        rationale: impl Into<String>,
    ) -> Self {
        Self::objection_with_class(provenance, id, target_ref, "role_conflict", rationale)
    }

    pub fn objection_with_class(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        target_ref: impl Into<String>,
        disagreement_class: impl Into<String>,
        rationale: impl Into<String>,
    ) -> Self {
        let id = id.into();
        Self {
            id: id.clone(),
            provenance,
            kind: ProviderSuggestionKind::Objection,
            target_ref: target_ref.into(),
            payload: "provider_objection".to_string(),
            support_weight: Some(0.8),
            rationale: Some(rationale.into()),
            grammar_role: None,
            meaning_kind: None,
            relation_kind: None,
            source_label: None,
            target_label: None,
            disagreement_class: Some(disagreement_class.into()),
            answer_kind: None,
            faculty_report: None,
            closed_class: None,
            closed_subclass: None,
            structural_hint: None,
            sense_key: None,
            synset_id: None,
            part_of_speech: None,
            definition: None,
            lineage: LineageRecord::new(id, "provider objection"),
        }
    }

    pub fn answer(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        target_ref: impl Into<String>,
        rationale: impl Into<String>,
    ) -> Self {
        Self::answer_with_kind(provenance, id, target_ref, "narrows", rationale)
    }

    pub fn answer_with_kind(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        target_ref: impl Into<String>,
        answer_kind: impl Into<String>,
        rationale: impl Into<String>,
    ) -> Self {
        let id = id.into();
        Self {
            id: id.clone(),
            provenance,
            kind: ProviderSuggestionKind::Answer,
            target_ref: target_ref.into(),
            payload: "provider_answer".to_string(),
            support_weight: Some(0.6),
            rationale: Some(rationale.into()),
            grammar_role: None,
            meaning_kind: None,
            relation_kind: None,
            source_label: None,
            target_label: None,
            disagreement_class: None,
            answer_kind: Some(answer_kind.into()),
            faculty_report: None,
            closed_class: None,
            closed_subclass: None,
            structural_hint: None,
            sense_key: None,
            synset_id: None,
            part_of_speech: None,
            definition: None,
            lineage: LineageRecord::new(id, "provider answer"),
        }
    }

    pub fn faculty_report(
        provenance: ProviderProvenance,
        id: impl Into<String>,
        target_ref: impl Into<String>,
        report: ProviderFacultyReport,
    ) -> Self {
        let id = id.into();
        let target_ref = target_ref.into();
        let rationale = report.convergence_statement.clone();
        Self {
            id: id.clone(),
            provenance,
            kind: ProviderSuggestionKind::FacultyVote,
            target_ref,
            payload: "provider_faculty_report".to_string(),
            support_weight: Some(report.convergence_score),
            rationale: Some(rationale),
            grammar_role: None,
            meaning_kind: None,
            relation_kind: None,
            source_label: None,
            target_label: None,
            disagreement_class: None,
            answer_kind: None,
            faculty_report: Some(report),
            closed_class: None,
            closed_subclass: None,
            structural_hint: None,
            sense_key: None,
            synset_id: None,
            part_of_speech: None,
            definition: None,
            lineage: LineageRecord::new(id, "provider internal faculty report"),
        }
    }
}

fn role_name_payload(role: GrammarRole) -> &'static str {
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

pub trait ProviderAdapter {
    fn provenance(&self) -> &ProviderProvenance;
    fn suggestions(&self, input: &str, tokens: &[Token]) -> Vec<ProviderSuggestion>;
}

#[derive(Debug, Clone)]
pub struct MockProvider {
    provenance: ProviderProvenance,
    suggestions: Vec<ProviderSuggestion>,
}

impl MockProvider {
    pub fn new(provider_id: impl Into<String>, suggestions: Vec<ProviderSuggestion>) -> Self {
        let provider_id = provider_id.into();
        Self {
            provenance: ProviderProvenance {
                provider_id: provider_id.clone(),
                model_id: "mock-model".to_string(),
                adapter_kind: AdapterKind::Mock,
                prompt_contract: "mock-fixture".to_string(),
                response_hash: None,
                timestamp: None,
                adapter_version: "v0".to_string(),
            },
            suggestions,
        }
    }

    pub fn provenance_for(provider_id: impl Into<String>) -> ProviderProvenance {
        let provider_id = provider_id.into();
        ProviderProvenance {
            provider_id,
            model_id: "mock-model".to_string(),
            adapter_kind: AdapterKind::Mock,
            prompt_contract: "mock-fixture".to_string(),
            response_hash: None,
            timestamp: None,
            adapter_version: "v0".to_string(),
        }
    }
}

impl ProviderAdapter for MockProvider {
    fn provenance(&self) -> &ProviderProvenance {
        &self.provenance
    }

    fn suggestions(&self, _input: &str, _tokens: &[Token]) -> Vec<ProviderSuggestion> {
        self.suggestions.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        AdapterKind, ProviderCapability, ProviderConfig, ProviderSetConfig, provider_set_from_json,
        validate_provider_set,
    };

    #[test]
    fn default_provider_set_declares_mock_lm_studio_and_ollama() {
        let config = ProviderSetConfig::default_local();

        validate_provider_set(&config).expect("default provider set validates");
        assert!(config.providers.iter().any(|provider| {
            provider.provider_id == "mock-fixture" && provider.adapter_kind == AdapterKind::Mock
        }));
        assert!(config.providers.iter().any(|provider| {
            provider.provider_id == "local-lm-studio"
                && provider.adapter_kind == AdapterKind::LmStudioOpenAiCompatible
                && !provider.prompt_contract.is_empty()
        }));
        assert!(config.providers.iter().any(|provider| {
            provider.provider_id == "local-ollama"
                && provider.adapter_kind == AdapterKind::Ollama
                && !provider.prompt_contract.is_empty()
        }));
        assert_eq!(
            config.enabled_for_capability(ProviderCapability::CandidateMeaning)[0].provider_id,
            "mock-fixture"
        );
    }

    #[test]
    fn provider_set_loads_from_json_and_preserves_provenance_template() {
        let json = include_str!("../../slm_project/provider_sets/local_provider_set_v0.json");
        let config = provider_set_from_json(json).expect("provider set JSON parses");
        validate_provider_set(&config).expect("provider set JSON validates");
        let ollama = config
            .providers
            .iter()
            .find(|provider| provider.provider_id == "local-ollama")
            .expect("ollama config exists");
        let provenance = ollama.provenance_template();

        assert_eq!(provenance.provider_id, "local-ollama");
        assert_eq!(provenance.adapter_kind, AdapterKind::Ollama);
        assert_eq!(
            provenance.prompt_contract,
            "sidecar_task_prompt_contracts_v0"
        );
        assert_eq!(provenance.response_hash, None);
        assert_eq!(provenance.timestamp, None);
    }

    #[test]
    fn provider_set_validation_rejects_non_mock_missing_prompt_contract() {
        let mut config = ProviderSetConfig::default_local();
        config.providers.push(ProviderConfig {
            provider_id: "bad-live-provider".to_string(),
            adapter_kind: AdapterKind::HostedOpenAiCompatible,
            model_id: "hosted-model".to_string(),
            endpoint: Some("https://example.invalid/v1/chat/completions".to_string()),
            prompt_contract: String::new(),
            adapter_version: "test".to_string(),
            enabled: false,
            capabilities: vec![ProviderCapability::Answer],
        });

        let errors = validate_provider_set(&config).expect_err("bad provider set fails");
        assert!(errors.iter().any(|error| {
            error.contains("bad-live-provider") && error.contains("prompt_contract")
        }));
    }
}
