use serde::{Deserialize, Serialize};

use crate::core::{CandidateMeaning, GrammarRole, MeaningKind, Severity, Token, clamp_unit};
use crate::deliberation::{DeliberationStatus, JuryMeasurement};
use crate::evidence::EvidenceWorkspace;

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct WobbleDimensions {
    pub role_instability: f32,
    pub span_boundary_instability: f32,
    pub sense_instability: f32,
    pub relation_instability: f32,
    pub subject_boundary_instability: f32,
    pub contradiction: f32,
    pub low_support: f32,
    pub unresolved_ambiguity: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WobbleFactor {
    pub id: String,
    pub dimension: String,
    pub target_kind: String,
    pub target_ref: String,
    pub score: f32,
    pub explanation: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WobbleVector {
    pub aggregate_score: f32,
    pub dimensions: WobbleDimensions,
    pub factors: Vec<WobbleFactor>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WobbleRoute {
    RouteToDeliberation,
    SeekSidecar,
    ContinueDiffusion,
    ReadyForReingestion,
}

impl WobbleRoute {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::RouteToDeliberation => "route_to_deliberation",
            Self::SeekSidecar => "seek_sidecar",
            Self::ContinueDiffusion => "continue_diffusion",
            Self::ReadyForReingestion => "ready_for_reingestion",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WobbleRoutingDecision {
    pub route: WobbleRoute,
    pub reason: String,
    pub dimension_refs: Vec<String>,
    pub factor_refs: Vec<String>,
}

impl WobbleVector {
    pub fn measure(workspace: &EvidenceWorkspace) -> Self {
        let mut dimensions = WobbleDimensions::default();
        let mut factors = Vec::new();

        for token in &workspace.tokens {
            let mut candidates = workspace
                .grammar_candidates
                .iter()
                .filter(|candidate| candidate.token_id == token.id)
                .collect::<Vec<_>>();
            candidates.sort_by(|left, right| {
                right
                    .support_weight
                    .partial_cmp(&left.support_weight)
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
            if candidates.len() >= 2
                && !matches!(
                    candidates[0].role,
                    GrammarRole::Determiner | GrammarRole::Punctuation
                )
                && (candidates[0].support_weight - candidates[1].support_weight).abs() < 0.12
            {
                dimensions.role_instability += 0.25;
                push_factor(
                    &mut factors,
                    "role_instability",
                    token.id.clone(),
                    0.25,
                    format!("close grammatical candidates for '{}'", token.surface_text),
                );
            }
        }

        for contradiction in &workspace.contradiction_records {
            let score = contradiction.severity.score();
            dimensions.contradiction += score;
            push_factor(
                &mut factors,
                "contradiction",
                contradiction.target_ref.clone(),
                score,
                contradiction.rationale.clone(),
            );
        }

        for token in &workspace.tokens {
            let span_count = workspace
                .span_candidates
                .iter()
                .filter(|span| {
                    span.token_refs
                        .iter()
                        .any(|token_ref| token_ref == &token.id)
                })
                .count();
            if span_count > 1 {
                dimensions.span_boundary_instability += 0.1;
                push_factor(
                    &mut factors,
                    "span_boundary_instability",
                    token.id.clone(),
                    0.1,
                    format!(
                        "'{}' participates in {span_count} candidate spans",
                        token.surface_text
                    ),
                );
            }

            let sense_count = workspace.senses_for_token(&token.id).len();
            if sense_count > 1 {
                let score = (sense_count as f32 * 0.04).min(0.24);
                dimensions.sense_instability += score;
                push_factor(
                    &mut factors,
                    "sense_instability",
                    token.id.clone(),
                    score,
                    format!(
                        "'{}' has {sense_count} lexical sense candidates",
                        token.surface_text
                    ),
                );
            }
        }

        for deliberation in &workspace.provider_deliberations {
            if matches!(
                deliberation.status,
                DeliberationStatus::PersistentDisagreement
                    | DeliberationStatus::InsufficientContext
            ) {
                dimensions.unresolved_ambiguity += 0.4;
                dimensions.relation_instability += 0.2;
                push_factor(
                    &mut factors,
                    "unresolved_ambiguity",
                    deliberation.candidate_ref.clone(),
                    0.4,
                    "provider disagreement remains after objection-answer review".to_string(),
                );
                push_factor(
                    &mut factors,
                    "relation_instability",
                    deliberation.candidate_ref.clone(),
                    0.2,
                    "provider disagreement destabilizes relation fit".to_string(),
                );
            }
            if deliberation
                .jury_review_set
                .iter()
                .any(|review| review.measurement == JuryMeasurement::CreatesUncertainty)
            {
                dimensions.subject_boundary_instability += 0.15;
                push_factor(
                    &mut factors,
                    "subject_boundary_instability",
                    deliberation.candidate_ref.clone(),
                    0.15,
                    "jury review created unresolved subject-boundary uncertainty".to_string(),
                );
            }
        }

        if let Some(action) = imperative_action_candidate(workspace) {
            dimensions.subject_boundary_instability += 0.25;
            push_factor(
                &mut factors,
                "subject_boundary_instability",
                action.id.clone(),
                0.25,
                "command-leading action has no explicit subject; implied actor remains unresolved"
                    .to_string(),
            );
        }

        for candidate in &workspace.candidate_meanings {
            let supports = workspace.support_for_target(&candidate.id);
            if supports.is_empty() {
                dimensions.low_support += 0.3;
                push_factor(
                    &mut factors,
                    "low_support",
                    candidate.id.clone(),
                    0.3,
                    "candidate meaning lacks support sources".to_string(),
                );
            }
        }

        dimensions.role_instability = clamp_unit(dimensions.role_instability);
        dimensions.span_boundary_instability = clamp_unit(dimensions.span_boundary_instability);
        dimensions.sense_instability = clamp_unit(dimensions.sense_instability);
        dimensions.relation_instability = clamp_unit(dimensions.relation_instability);
        dimensions.subject_boundary_instability =
            clamp_unit(dimensions.subject_boundary_instability);
        dimensions.contradiction = clamp_unit(dimensions.contradiction);
        dimensions.low_support = clamp_unit(dimensions.low_support);
        dimensions.unresolved_ambiguity = clamp_unit(dimensions.unresolved_ambiguity);

        let aggregate_score = clamp_unit(
            (dimensions.role_instability
                + dimensions.relation_instability
                + dimensions.span_boundary_instability
                + dimensions.sense_instability
                + dimensions.subject_boundary_instability
                + dimensions.contradiction
                + dimensions.low_support
                + dimensions.unresolved_ambiguity)
                / 8.0,
        );

        Self {
            aggregate_score,
            dimensions,
            factors,
        }
    }

    pub fn blocking_contradiction_score(workspace: &EvidenceWorkspace, target_ref: &str) -> f32 {
        workspace
            .contradictions_for_target(target_ref)
            .into_iter()
            .filter(|contradiction| contradiction.severity.blocks_stabilization())
            .map(|contradiction| contradiction.severity.score())
            .fold(0.0, f32::max)
    }

    pub fn target_wobble(&self, workspace: &EvidenceWorkspace, target_ref: &str) -> f32 {
        let target_has_blocking = workspace
            .contradictions_for_target(target_ref)
            .iter()
            .any(|contradiction| contradiction.severity == Severity::Blocking);
        if target_has_blocking {
            return 1.0;
        }

        self.aggregate_score
    }

    pub fn routing_decision(&self) -> WobbleRoutingDecision {
        if self.dimensions.contradiction >= 0.7 {
            return self.route(
                WobbleRoute::RouteToDeliberation,
                "high contradiction requires deliberation before re-ingestion",
                &["contradiction"],
            );
        }
        if self.dimensions.unresolved_ambiguity >= 0.35 {
            return self.route(
                WobbleRoute::SeekSidecar,
                "unresolved ambiguity needs another evidence source",
                &["unresolved_ambiguity"],
            );
        }
        if self.dimensions.subject_boundary_instability >= 0.25 {
            return self.route(
                WobbleRoute::SeekSidecar,
                "subject boundary instability needs actor or scope evidence",
                &["subject_boundary_instability"],
            );
        }
        if self.dimensions.low_support >= 0.3 {
            return self.route(
                WobbleRoute::SeekSidecar,
                "low support needs additional evidence",
                &["low_support"],
            );
        }
        if self.dimensions.role_instability >= 0.2
            || self.dimensions.span_boundary_instability >= 0.2
            || self.dimensions.sense_instability >= 0.2
            || self.dimensions.relation_instability >= 0.2
        {
            return self.route(
                WobbleRoute::ContinueDiffusion,
                "local instability may reduce through additional deterministic diffusion",
                &[
                    "role_instability",
                    "span_boundary_instability",
                    "sense_instability",
                    "relation_instability",
                ],
            );
        }
        self.route(
            WobbleRoute::ReadyForReingestion,
            "no wobble dimension requires more work",
            &[],
        )
    }

    fn route(
        &self,
        route: WobbleRoute,
        reason: &str,
        dimensions: &[&str],
    ) -> WobbleRoutingDecision {
        let factor_refs = self
            .factors
            .iter()
            .filter(|factor| {
                dimensions.is_empty()
                    || dimensions
                        .iter()
                        .any(|dimension| factor.dimension == *dimension)
            })
            .map(|factor| factor.id.clone())
            .collect();
        WobbleRoutingDecision {
            route,
            reason: reason.to_string(),
            dimension_refs: dimensions
                .iter()
                .map(|dimension| format!("wobble_dimension:{dimension}"))
                .collect(),
            factor_refs,
        }
    }
}

fn push_factor(
    factors: &mut Vec<WobbleFactor>,
    dimension: &str,
    target_ref: String,
    score: f32,
    explanation: String,
) {
    let id = format!("wobble_factor:{dimension}:{}", factors.len());
    factors.push(WobbleFactor {
        id,
        dimension: dimension.to_string(),
        target_kind: target_kind_for_ref(&target_ref).to_string(),
        target_ref,
        score,
        explanation,
    });
}

fn target_kind_for_ref(target_ref: &str) -> &'static str {
    if target_ref.starts_with("tok:") {
        "token"
    } else if target_ref.starts_with("span:") {
        "span"
    } else if target_ref.starts_with("candidate_relation:") {
        "relation"
    } else if target_ref.starts_with("meaning:") {
        "meaning"
    } else if target_ref.starts_with("contradiction:") {
        "contradiction"
    } else if target_ref.starts_with("deliberation:") {
        "deliberation"
    } else if target_ref.starts_with("provider:") {
        "provider"
    } else if target_ref.starts_with("workspace:") {
        "workspace"
    } else {
        "evidence"
    }
}

fn imperative_action_candidate(workspace: &EvidenceWorkspace) -> Option<&CandidateMeaning> {
    let token = first_content_token(&workspace.tokens)?;
    if !has_strong_verb_evidence(workspace, &token.id) {
        return None;
    }
    let action = workspace.candidate_meanings.iter().find(|candidate| {
        candidate.kind == MeaningKind::Action
            && candidate
                .token_refs
                .iter()
                .any(|token_ref| token_ref == &token.id)
    })?;
    if explicit_subject_before(workspace, token.token_index) {
        return None;
    }
    Some(action)
}

fn first_content_token(tokens: &[Token]) -> Option<&Token> {
    tokens.iter().find(|token| !token.is_punctuation())
}

fn has_strong_verb_evidence(workspace: &EvidenceWorkspace, token_id: &str) -> bool {
    workspace.grammar_candidates.iter().any(|candidate| {
        candidate.token_id == token_id
            && candidate.role == GrammarRole::Verb
            && candidate.support_weight >= 0.6
    })
}

fn explicit_subject_before(workspace: &EvidenceWorkspace, before_index: usize) -> bool {
    workspace
        .candidate_meanings
        .iter()
        .filter(|candidate| candidate.kind == MeaningKind::Subject)
        .flat_map(|candidate| {
            candidate.token_refs.iter().filter_map(|token_ref| {
                workspace.tokens.iter().find(|token| &token.id == token_ref)
            })
        })
        .any(|token| token.token_index < before_index)
}
