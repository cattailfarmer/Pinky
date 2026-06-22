use serde::{Deserialize, Serialize};

use crate::core::{LineageRecord, MeaningKind};
use crate::diffusion::DiffusionOutput;
use crate::evidence::EvidenceWorkspace;
use crate::stabilization::{DecisionOutcome, StabilizationDecision};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GlyphKind {
    Subject,
    Action,
    RelationSubject,
    Modifier,
    Constraint,
    Uncertainty,
    Wobble,
    PrimerField,
    SemanticTrace,
}

impl From<MeaningKind> for GlyphKind {
    fn from(value: MeaningKind) -> Self {
        match value {
            MeaningKind::Subject => Self::Subject,
            MeaningKind::Action => Self::Action,
            MeaningKind::Relation => Self::RelationSubject,
            MeaningKind::Modifier => Self::Modifier,
            MeaningKind::Constraint => Self::Constraint,
            MeaningKind::Reference => Self::SemanticTrace,
            MeaningKind::UncertaintyCandidate => Self::Uncertainty,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LifecycleState {
    Active,
    Retired,
    Superseded,
    PreservedTrace,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RelationKind {
    Performs,
    ActsOn,
    Modifies,
    Constrains,
    ScopesOver,
    RefersTo,
    Supports,
    Contradicts,
    Supersedes,
    Retires,
    Extension,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UncertaintyType {
    UnresolvedRole,
    UnresolvedRelation,
    UnresolvedSubjectBoundary,
    UnresolvedReference,
    ContradictionCluster,
    LowSupportCandidate,
    ProviderDisagreement,
    UnresolvedScope,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Glyph {
    pub semantic_id: String,
    pub kind: GlyphKind,
    pub label: String,
    pub lineage: LineageRecord,
    pub stabilization_decision: String,
    pub lifecycle_state: LifecycleState,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SemanticRelation {
    pub relation_id: String,
    pub source_glyph: String,
    pub target_glyph: String,
    pub kind: RelationKind,
    pub candidate_relation_ref: String,
    pub endpoint_decision_refs: Vec<String>,
    pub stabilization_decision: String,
    pub lineage: LineageRecord,
    pub lifecycle_state: LifecycleState,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UncertaintyGlyph {
    pub semantic_id: String,
    pub uncertainty_type: UncertaintyType,
    pub boundary_statement: String,
    pub candidate_set: Vec<String>,
    pub lineage: LineageRecord,
    pub stabilization_decision: String,
    pub lifecycle_state: LifecycleState,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphLifecycleEvent {
    pub event_kind: String,
    pub target_ref: String,
    pub reason: String,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SemanticGraph {
    pub graph_id: String,
    pub glyphs: Vec<Glyph>,
    pub relations: Vec<SemanticRelation>,
    pub uncertainties: Vec<UncertaintyGlyph>,
    pub lifecycle_events: Vec<GraphLifecycleEvent>,
}

impl SemanticGraph {
    pub fn new(graph_id: impl Into<String>) -> Self {
        Self {
            graph_id: graph_id.into(),
            glyphs: Vec::new(),
            relations: Vec::new(),
            uncertainties: Vec::new(),
            lifecycle_events: Vec::new(),
        }
    }

    pub fn from_decisions(
        workspace: &EvidenceWorkspace,
        diffusion: &DiffusionOutput,
        decisions: &[StabilizationDecision],
    ) -> Self {
        let mut graph = Self::new(format!("graph:{}", workspace.workspace_id));

        for decision in decisions {
            match decision.outcome {
                DecisionOutcome::PromoteGlyph => {
                    if let Some(candidate) = workspace
                        .candidate_meanings
                        .iter()
                        .find(|candidate| candidate.id == decision.target_ref)
                    {
                        let semantic_id = format!("glyph:{}", candidate.label);
                        graph.lifecycle_events.push(GraphLifecycleEvent {
                            event_kind: "create_glyph".to_string(),
                            target_ref: semantic_id.clone(),
                            reason: decision.reason.clone(),
                            lineage: candidate.lineage.clone(),
                        });
                        graph.glyphs.push(Glyph {
                            semantic_id,
                            kind: candidate.kind.into(),
                            label: candidate.label.clone(),
                            lineage: candidate.lineage.clone(),
                            stabilization_decision: decision.id.clone(),
                            lifecycle_state: LifecycleState::Active,
                        });
                    }
                }
                DecisionOutcome::CreateUncertaintyGlyph => {
                    for proposal in &diffusion.uncertainty_proposals {
                        if proposal.id == decision.target_ref {
                            let semantic_id = format!("glyph:uncertainty:{}", proposal.id);
                            graph.lifecycle_events.push(GraphLifecycleEvent {
                                event_kind: "create_uncertainty_glyph".to_string(),
                                target_ref: semantic_id.clone(),
                                reason: proposal.boundary_statement.clone(),
                                lineage: proposal.lineage.clone(),
                            });
                            graph.uncertainties.push(UncertaintyGlyph {
                                semantic_id,
                                uncertainty_type: proposal.uncertainty_type,
                                boundary_statement: proposal.boundary_statement.clone(),
                                candidate_set: proposal.candidate_set.clone(),
                                lineage: proposal.lineage.clone(),
                                stabilization_decision: decision.id.clone(),
                                lifecycle_state: LifecycleState::Active,
                            });
                        }
                    }
                }
                DecisionOutcome::PreserveInEvidenceWorkspace | DecisionOutcome::RejectCandidate => {
                }
            }
        }

        for relation in &workspace.candidate_relations {
            let Some(source) = graph.glyph_by_label(&relation.source_label) else {
                continue;
            };
            let Some(target) = graph.glyph_by_label(&relation.target_label) else {
                continue;
            };
            let source_glyph = source.semantic_id.clone();
            let target_glyph = target.semantic_id.clone();
            let endpoint_decision_refs = vec![
                source.stabilization_decision.clone(),
                target.stabilization_decision.clone(),
            ];
            let mut relation_lineage = relation.lineage.clone().with_transform(relation.id.clone());
            for endpoint_decision_ref in &endpoint_decision_refs {
                relation_lineage = relation_lineage.with_transform(endpoint_decision_ref.clone());
            }
            let relation_id = format!(
                "relation:{}:{}:{}",
                relation.source_label,
                relation.target_label,
                graph.relations.len()
            );
            graph.lifecycle_events.push(GraphLifecycleEvent {
                event_kind: "create_relation".to_string(),
                target_ref: relation_id.clone(),
                reason: format!(
                    "candidate relation {} endpoints stabilized by {}",
                    relation.id,
                    endpoint_decision_refs.join(", ")
                ),
                lineage: relation_lineage.clone(),
            });
            graph.relations.push(SemanticRelation {
                relation_id,
                source_glyph,
                target_glyph,
                kind: relation.relation_kind,
                candidate_relation_ref: relation.id.clone(),
                endpoint_decision_refs,
                stabilization_decision: "relation_endpoint_stability".to_string(),
                lineage: relation_lineage,
                lifecycle_state: LifecycleState::Active,
            });
        }

        graph
    }

    pub fn has_glyph_label(&self, label: &str) -> bool {
        self.glyphs.iter().any(|glyph| glyph.label == label)
    }

    fn glyph_by_label(&self, label: &str) -> Option<&Glyph> {
        self.glyphs.iter().find(|glyph| glyph.label == label)
    }
}
