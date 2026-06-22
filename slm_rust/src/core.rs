use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SourceSpan {
    pub start: usize,
    pub end: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct LineageRecord {
    pub source_refs: Vec<String>,
    pub transform_refs: Vec<String>,
    pub note: String,
}

impl LineageRecord {
    pub fn new(source_ref: impl Into<String>, note: impl Into<String>) -> Self {
        Self {
            source_refs: vec![source_ref.into()],
            transform_refs: Vec::new(),
            note: note.into(),
        }
    }

    pub fn empty(note: impl Into<String>) -> Self {
        Self {
            source_refs: Vec::new(),
            transform_refs: Vec::new(),
            note: note.into(),
        }
    }

    pub fn is_present(&self) -> bool {
        !self.source_refs.is_empty()
    }

    pub fn with_transform(mut self, transform_ref: impl Into<String>) -> Self {
        self.transform_refs.push(transform_ref.into());
        self
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Token {
    pub id: String,
    pub input_id: String,
    pub token_index: usize,
    pub surface_text: String,
    pub normalized_text: String,
    pub source_span: Option<SourceSpan>,
    pub token_shape: Option<String>,
}

impl Token {
    pub fn new(input_id: &str, token_index: usize, text: &str, start: usize, end: usize) -> Self {
        let token_shape = if text.chars().all(|ch| !ch.is_alphanumeric()) {
            Some("punctuation".to_string())
        } else {
            Some("word".to_string())
        };

        Self {
            id: format!("tok:{input_id}:{token_index}"),
            input_id: input_id.to_string(),
            token_index,
            surface_text: text.to_string(),
            normalized_text: text.to_lowercase(),
            source_span: Some(SourceSpan { start, end }),
            token_shape,
        }
    }

    pub fn is_punctuation(&self) -> bool {
        self.token_shape.as_deref() == Some("punctuation")
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GrammarRole {
    Noun,
    Verb,
    Adjective,
    Adverb,
    Determiner,
    Preposition,
    Conjunction,
    Auxiliary,
    Modal,
    Pronoun,
    Punctuation,
    Unknown,
    Extension,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceSource {
    Heuristic,
    LowerLlm,
    Dictionary,
    Morphology,
    Position,
    StructuralRule,
    UserRule,
    LexicalAuthority,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CandidateStatus {
    Active,
    Deferred,
    Contradicted,
    Rejected,
    Superseded,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpanKind {
    Nominal,
    Prepositional,
    Compound,
    Predicate,
    Coordination,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MeaningKind {
    Subject,
    Action,
    Relation,
    Modifier,
    Constraint,
    Reference,
    UncertaintyCandidate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Low,
    Medium,
    High,
    Blocking,
}

impl Severity {
    pub fn score(self) -> f32 {
        match self {
            Self::Low => 0.2,
            Self::Medium => 0.45,
            Self::High => 0.75,
            Self::Blocking => 1.0,
        }
    }

    pub fn blocks_stabilization(self) -> bool {
        matches!(self, Self::High | Self::Blocking)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContradictionKind {
    RoleConflict,
    RelationConflict,
    ScopeConflict,
    ProviderObjection,
    UnsupportedClaim,
    InvalidConsequence,
    LineageGap,
    SemanticIncoherence,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContradictionStatus {
    Active,
    Answered,
    Unresolved,
    Retired,
    Superseded,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GrammarCandidate {
    pub id: String,
    pub token_id: String,
    pub role: GrammarRole,
    pub support_weight: f32,
    pub source: EvidenceSource,
    pub status: CandidateStatus,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructuralHint {
    pub id: String,
    pub token_id: String,
    pub class: String,
    pub subclass: String,
    pub diffusion_priority: f32,
    pub structural_hint: String,
    pub source: EvidenceSource,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SpanCandidate {
    pub id: String,
    pub token_refs: Vec<String>,
    pub surface_text: String,
    pub normalized_text: String,
    pub span_kind: SpanKind,
    pub support_weight: f32,
    pub source: EvidenceSource,
    pub status: CandidateStatus,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LexicalSenseCandidate {
    pub id: String,
    pub token_id: String,
    pub lemma: String,
    pub sense_key: String,
    pub synset_id: String,
    pub part_of_speech: String,
    pub definition: Option<String>,
    pub support_weight: f32,
    pub source: EvidenceSource,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CandidateMeaning {
    pub id: String,
    pub kind: MeaningKind,
    pub label: String,
    pub token_refs: Vec<String>,
    pub support_record_ids: Vec<String>,
    pub contradiction_record_ids: Vec<String>,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CandidateRelation {
    pub id: String,
    pub relation_kind: crate::graph::RelationKind,
    pub source_label: String,
    pub target_label: String,
    pub support_record_ids: Vec<String>,
    pub contradiction_record_ids: Vec<String>,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SupportRecord {
    pub id: String,
    pub target_ref: String,
    pub support_weight: f32,
    pub source_ref: String,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContradictionRecord {
    pub id: String,
    pub target_ref: String,
    pub severity: Severity,
    pub kind: ContradictionKind,
    pub source_ref: String,
    pub answer_ref: Option<String>,
    pub provider_deliberation_ref: Option<String>,
    pub jury_review_ref: Option<String>,
    pub cited_panel_refs: Vec<String>,
    pub status: ContradictionStatus,
    pub rationale: String,
}

pub fn clamp_unit(value: f32) -> f32 {
    value.clamp(0.0, 1.0)
}
