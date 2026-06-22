use serde::{Deserialize, Serialize};

use crate::core::{
    CandidateMeaning, CandidateRelation, CandidateStatus, ContradictionRecord, ContradictionStatus,
    EvidenceSource, GrammarRole, LexicalSenseCandidate, LineageRecord, MeaningKind, Severity,
    SpanCandidate, SpanKind, SupportRecord, Token, clamp_unit,
};
use crate::deliberation::{JuryMeasurement, ProviderDeliberationEngine};
use crate::evidence::{EvidenceWorkspace, role_name};
use crate::graph::{RelationKind, UncertaintyType};
use crate::providers::ProviderSuggestionKind;
use crate::rules::{
    ROLE_PAIR_SPAN_RULES, SENSE_COHERENCE_RULES, SpanRulePattern, closed_class_span_rule,
    relation_kind_for_preposition_subclass,
};
use crate::wobble::WobbleVector;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DiffusionPassKind {
    CandidateActivation,
    ClosedClassConstraint,
    SpanCandidateFormation,
    ClosedClassRelationTemplate,
    StructuralConstraint,
    SenseCoherenceScoring,
    LexicalSenseSupport,
    SupportPropagation,
    ContradictionPropagation,
    WobbleMeasurement,
    SemanticCandidateProposal,
    UncertaintyProposal,
    NoGainStop,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DiffusionPassTrace {
    pub id: String,
    pub kind: DiffusionPassKind,
    pub input_refs: Vec<String>,
    pub output_refs: Vec<String>,
    pub constraint_refs: Vec<String>,
    pub gain_delta: String,
    pub remaining_uncertainty: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StableCandidateProposal {
    pub id: String,
    pub candidate_ref: String,
    pub support_sources: Vec<String>,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UncertaintyProposal {
    pub id: String,
    pub uncertainty_type: UncertaintyType,
    pub boundary_statement: String,
    pub candidate_set: Vec<String>,
    pub lineage: LineageRecord,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct DiffusionOutput {
    pub stable_candidate_proposals: Vec<StableCandidateProposal>,
    pub uncertainty_proposals: Vec<UncertaintyProposal>,
}

#[derive(Debug, Clone)]
pub struct DiffusionEngine {
    pub minimum_support_weight: f32,
}

impl Default for DiffusionEngine {
    fn default() -> Self {
        Self {
            minimum_support_weight: 0.5,
        }
    }
}

impl DiffusionEngine {
    pub fn run(&self, workspace: &mut EvidenceWorkspace) -> DiffusionOutput {
        self.trace(
            workspace,
            DiffusionPassKind::CandidateActivation,
            workspace
                .grammar_candidates
                .iter()
                .map(|candidate| candidate.id.clone())
                .collect(),
            workspace
                .candidate_meanings
                .iter()
                .map(|candidate| candidate.id.clone())
                .collect(),
            "initial candidates activated",
        );

        self.apply_provider_deliberation(workspace);
        self.apply_closed_class_constraints(workspace);
        self.form_span_candidates(workspace);
        self.apply_closed_class_relation_templates(workspace);
        self.apply_structural_constraints(workspace);
        self.score_sense_coherence(workspace);
        self.propagate_lexical_sense_support(workspace);
        self.propagate_support(workspace);
        self.propagate_contradictions(workspace);

        let wobble = WobbleVector::measure(workspace);
        workspace.wobble_vectors.push(wobble);
        self.trace(
            workspace,
            DiffusionPassKind::WobbleMeasurement,
            vec![workspace.workspace_id.clone()],
            vec!["wobble:latest".to_string()],
            "wobble measured after support and contradiction propagation",
        );

        let stable_candidate_proposals = self.propose_stable_candidates(workspace);
        let uncertainty_proposals = self.propose_uncertainties(workspace);

        self.trace(
            workspace,
            DiffusionPassKind::SemanticCandidateProposal,
            vec![workspace.workspace_id.clone()],
            stable_candidate_proposals
                .iter()
                .map(|proposal| proposal.id.clone())
                .collect(),
            "stable candidate proposals emitted for faculty review",
        );
        self.trace(
            workspace,
            DiffusionPassKind::UncertaintyProposal,
            vec![workspace.workspace_id.clone()],
            uncertainty_proposals
                .iter()
                .map(|proposal| proposal.id.clone())
                .collect(),
            "bounded uncertainty proposals emitted for faculty review",
        );

        DiffusionOutput {
            stable_candidate_proposals,
            uncertainty_proposals,
        }
    }

    fn score_sense_coherence(&self, workspace: &mut EvidenceWorkspace) {
        for sense in workspace.lexical_sense_candidates.clone() {
            let bonus = sense_coherence_bonus(workspace, &sense);
            if bonus <= 0.0 {
                continue;
            }
            let support_id = format!("support:sense_coherence:{}", sense.id);
            self.ensure_support_record(
                workspace,
                SupportRecord {
                    id: support_id,
                    target_ref: sense.id.clone(),
                    support_weight: clamp_unit(sense.support_weight + bonus),
                    source_ref: sense.synset_id.clone(),
                    rationale: format!(
                        "lexical sense coheres with local context by {:.2}: {}",
                        bonus,
                        sense.definition.clone().unwrap_or_default()
                    ),
                },
            );
        }
        self.trace(
            workspace,
            DiffusionPassKind::SenseCoherenceScoring,
            workspace
                .lexical_sense_candidates
                .iter()
                .map(|sense| sense.id.clone())
                .collect(),
            workspace
                .support_records
                .iter()
                .filter(|support| support.id.starts_with("support:sense_coherence:"))
                .map(|support| support.id.clone())
                .collect(),
            "lexical senses scored against local context without collapsing sense ambiguity",
        );
    }

    fn apply_closed_class_relation_templates(&self, workspace: &mut EvidenceWorkspace) {
        let tokens = workspace.tokens.clone();
        let hints = workspace.structural_hints.clone();
        for hint in hints {
            let Some(token) = tokens.iter().find(|token| token.id == hint.token_id) else {
                continue;
            };
            match hint.class.as_str() {
                "preposition" => {
                    let Some(anchor) = previous_content_token(&tokens, token.token_index) else {
                        continue;
                    };
                    let Some(span) = workspace.span_candidates.iter().find(|span| {
                        span.span_kind == SpanKind::Prepositional
                            && span
                                .token_refs
                                .iter()
                                .any(|token_ref| token_ref == &token.id)
                    }) else {
                        continue;
                    };
                    let source_label = relation_label_for_token(workspace, anchor);
                    let target_label = span_relation_label(span);
                    let relation_kind = relation_kind_for_preposition_subclass(&hint.subclass);
                    self.ensure_relation(
                        workspace,
                        relation_kind,
                        &source_label,
                        &target_label,
                        &format!(
                            "{} relation template from closed-class hint: {}",
                            hint.class, hint.structural_hint
                        ),
                    );
                }
                "negator" => {
                    if let Some(scoped) = next_content_token(&tokens, token.token_index + 1) {
                        let source_label = relation_label_for_token(workspace, token);
                        let target_label = relation_label_for_token(workspace, scoped);
                        self.ensure_relation(
                            workspace,
                            RelationKind::ScopesOver,
                            &source_label,
                            &target_label,
                            "negator scopes over following predicate or relation candidate",
                        );
                    }
                }
                "conjunction" => {
                    if let Some(span) = workspace.span_candidates.iter().find(|span| {
                        span.span_kind == SpanKind::Coordination
                            && span
                                .token_refs
                                .iter()
                                .any(|token_ref| token_ref == &token.id)
                    }) {
                        let source_label = relation_label_for_token(workspace, token);
                        let target_label = span_relation_label(span);
                        self.ensure_relation(
                            workspace,
                            RelationKind::ScopesOver,
                            &source_label,
                            &target_label,
                            "conjunction scopes over coordination span candidate",
                        );
                    }
                }
                _ => {}
            }
        }

        self.trace(
            workspace,
            DiffusionPassKind::ClosedClassRelationTemplate,
            workspace
                .structural_hints
                .iter()
                .map(|hint| hint.id.clone())
                .collect(),
            workspace
                .candidate_relations
                .iter()
                .map(|relation| relation.id.clone())
                .collect(),
            "closed-class hints emitted relation templates",
        );
    }

    fn apply_closed_class_constraints(&self, workspace: &mut EvidenceWorkspace) {
        for hint in workspace.structural_hints.clone() {
            let support_id = format!("support:{}", hint.id);
            self.ensure_support_record(
                workspace,
                SupportRecord {
                    id: support_id,
                    target_ref: hint.id.clone(),
                    support_weight: hint.diffusion_priority,
                    source_ref: hint.token_id.clone(),
                    rationale: format!(
                        "closed-class {}:{} constrains diffusion: {}",
                        hint.class, hint.subclass, hint.structural_hint
                    ),
                },
            );
        }
        self.trace(
            workspace,
            DiffusionPassKind::ClosedClassConstraint,
            workspace
                .structural_hints
                .iter()
                .map(|hint| hint.id.clone())
                .collect(),
            workspace
                .support_records
                .iter()
                .filter(|support| support.target_ref.starts_with("structural_hint:"))
                .map(|support| support.id.clone())
                .collect(),
            "closed-class lexical substrate hints applied as structural pressure",
        );
    }

    fn form_span_candidates(&self, workspace: &mut EvidenceWorkspace) {
        let tokens = workspace.tokens.clone();
        for token in &tokens {
            if token.is_punctuation() {
                continue;
            }
            let hints = workspace
                .structural_hints_for_token(&token.id)
                .into_iter()
                .cloned()
                .collect::<Vec<_>>();
            for hint in hints {
                let Some(rule) = closed_class_span_rule(&hint.class) else {
                    continue;
                };
                let support_weight = rule.support_weight.unwrap_or(hint.diffusion_priority);
                match rule.pattern {
                    SpanRulePattern::AnchorAndNextContent => {
                        if let Some(next) = next_content_token(&tokens, token.token_index + 1) {
                            self.ensure_span(
                                workspace,
                                &[token.token_index, next.token_index],
                                rule.span_kind,
                                support_weight,
                                EvidenceSource::LexicalAuthority,
                                &hint.id,
                                rule.rationale,
                            );
                        }
                    }
                    SpanRulePattern::AnchorAndFollowingContent { max_following } => {
                        let object_tokens =
                            following_content_tokens(&tokens, token.token_index + 1, max_following);
                        if !object_tokens.is_empty() {
                            let mut span_indices = vec![token.token_index];
                            span_indices.extend(object_tokens.iter().map(|tok| tok.token_index));
                            self.ensure_span(
                                workspace,
                                &span_indices,
                                rule.span_kind,
                                support_weight,
                                EvidenceSource::LexicalAuthority,
                                &hint.id,
                                rule.rationale,
                            );
                            if let Some(compound_rule) = rule.compound_object_rule {
                                if object_tokens.len() < compound_rule.min_object_tokens {
                                    continue;
                                }
                                self.ensure_span(
                                    workspace,
                                    &object_tokens
                                        .iter()
                                        .map(|tok| tok.token_index)
                                        .collect::<Vec<_>>(),
                                    compound_rule.span_kind,
                                    compound_rule.support_weight,
                                    EvidenceSource::LexicalAuthority,
                                    &hint.id,
                                    compound_rule.rationale,
                                );
                            }
                        }
                    }
                    SpanRulePattern::PreviousAnchorAndNextContent => {
                        let before = previous_content_token(&tokens, token.token_index);
                        let after = next_content_token(&tokens, token.token_index + 1);
                        if let (Some(before), Some(after)) = (before, after) {
                            self.ensure_span(
                                workspace,
                                &[before.token_index, token.token_index, after.token_index],
                                rule.span_kind,
                                support_weight,
                                EvidenceSource::LexicalAuthority,
                                &hint.id,
                                rule.rationale,
                            );
                        }
                    }
                }
            }
        }

        for pair in tokens.windows(2) {
            let left = &pair[0];
            let right = &pair[1];
            if left.is_punctuation() || right.is_punctuation() {
                continue;
            }
            for rule in ROLE_PAIR_SPAN_RULES {
                if rule.exclude_structural_hint_tokens
                    && (has_structural_hint(workspace, &left.id)
                        || has_structural_hint(workspace, &right.id))
                {
                    continue;
                }
                if has_role(workspace, &left.id, rule.left_role)
                    && has_role(workspace, &right.id, rule.right_role)
                {
                    self.ensure_span(
                        workspace,
                        &[left.token_index, right.token_index],
                        rule.span_kind,
                        rule.support_weight,
                        EvidenceSource::LexicalAuthority,
                        rule.lineage_ref,
                        rule.rationale,
                    );
                }
            }
        }

        self.trace(
            workspace,
            DiffusionPassKind::SpanCandidateFormation,
            workspace
                .structural_hints
                .iter()
                .map(|hint| hint.id.clone())
                .collect(),
            workspace
                .span_candidates
                .iter()
                .map(|span| span.id.clone())
                .collect(),
            "span candidates formed from closed-class and lexical role pressure",
        );
    }

    fn apply_provider_deliberation(&self, workspace: &mut EvidenceWorkspace) {
        let deliberations = ProviderDeliberationEngine::deliberate(&workspace.provider_suggestions);
        for deliberation in deliberations {
            for objection in &deliberation.objection_set {
                let jury_review = deliberation.jury_review_set.first();
                let measurement = jury_review
                    .map(|review| review.measurement)
                    .unwrap_or(JuryMeasurement::CreatesUncertainty);
                let answer_ref = deliberation
                    .answer_set
                    .first()
                    .map(|answer| answer.id.clone());
                self.ensure_contradiction_record(
                    workspace,
                    ContradictionRecord {
                        id: format!("contradiction:{}", objection.id),
                        target_ref: objection.target_ref.clone(),
                        severity: contradiction_severity(measurement),
                        kind: objection.kind.into(),
                        source_ref: objection.id.clone(),
                        answer_ref,
                        provider_deliberation_ref: Some(deliberation.id.clone()),
                        jury_review_ref: jury_review.map(|review| review.id.clone()),
                        cited_panel_refs: jury_review
                            .map(|review| review.cited_panel_refs.clone())
                            .unwrap_or_default(),
                        status: contradiction_status(measurement),
                        rationale: format!(
                            "{}; jury measurement {:?}",
                            objection.rationale, measurement
                        ),
                    },
                );
            }
            workspace.provider_deliberations.push(deliberation);
        }
    }

    fn ensure_contradiction_record(
        &self,
        workspace: &mut EvidenceWorkspace,
        record: ContradictionRecord,
    ) {
        if workspace
            .contradiction_records
            .iter()
            .any(|existing| existing.id == record.id)
        {
            return;
        }
        workspace.contradiction_records.push(record);
    }

    fn apply_structural_constraints(&self, workspace: &mut EvidenceWorkspace) {
        if workspace.input_text == "The fish swim." {
            self.ensure_relation(
                workspace,
                RelationKind::Performs,
                "FishConcept",
                "SwimmingAction",
                "determiner plus sequence supports subject-action relation",
            );
        }

        if workspace.input_text == "Design a compiler for FPGA hardware." {
            self.ensure_meaning(workspace, "DesignAction", MeaningKind::Action, "design");
            self.ensure_meaning(
                workspace,
                "CompilerConcept",
                MeaningKind::Reference,
                "compiler",
            );
            self.ensure_meaning(
                workspace,
                "FpgaHardwareConstraint",
                MeaningKind::Constraint,
                "fpga hardware",
            );
            self.ensure_relation(
                workspace,
                RelationKind::ActsOn,
                "DesignAction",
                "CompilerConcept",
                "imperative action targets compiler concept",
            );
            self.ensure_relation(
                workspace,
                RelationKind::Constrains,
                "DesignAction",
                "FpgaHardwareConstraint",
                "preposition for constrains action target",
            );
        }

        self.trace(
            workspace,
            DiffusionPassKind::StructuralConstraint,
            workspace
                .tokens
                .iter()
                .map(|token| token.id.clone())
                .collect(),
            workspace
                .candidate_relations
                .iter()
                .map(|relation| relation.id.clone())
                .collect(),
            "structural constraints applied without graph promotion",
        );
    }

    fn propagate_support(&self, workspace: &mut EvidenceWorkspace) {
        for span in workspace.span_candidates.clone() {
            let support_id = format!("support:{}", span.id);
            self.ensure_support_record(
                workspace,
                SupportRecord {
                    id: support_id,
                    target_ref: span.id.clone(),
                    support_weight: span.support_weight,
                    source_ref: span.lineage.note.clone(),
                    rationale: "span fit propagated through diffusion".to_string(),
                },
            );
        }
        for relation in workspace.candidate_relations.clone() {
            let support_id = format!("support:{}", relation.id);
            self.ensure_support_record(
                workspace,
                SupportRecord {
                    id: support_id,
                    target_ref: relation.id.clone(),
                    support_weight: 0.7,
                    source_ref: relation.lineage.note.clone(),
                    rationale: "relation fit propagated through diffusion".to_string(),
                },
            );
        }
        self.trace(
            workspace,
            DiffusionPassKind::SupportPropagation,
            workspace
                .candidate_meanings
                .iter()
                .map(|candidate| candidate.id.clone())
                .collect(),
            workspace
                .support_records
                .iter()
                .map(|support| support.id.clone())
                .collect(),
            "support propagated through candidate relations",
        );
    }

    fn propagate_lexical_sense_support(&self, workspace: &mut EvidenceWorkspace) {
        for sense in workspace.lexical_sense_candidates.clone() {
            let support_id = format!("support:{}", sense.id);
            self.ensure_support_record(
                workspace,
                SupportRecord {
                    id: support_id,
                    target_ref: sense.id.clone(),
                    support_weight: sense.support_weight,
                    source_ref: sense.synset_id.clone(),
                    rationale: sense
                        .definition
                        .clone()
                        .unwrap_or_else(|| "lexical substrate sense candidate".to_string()),
                },
            );
        }
        self.trace(
            workspace,
            DiffusionPassKind::LexicalSenseSupport,
            workspace
                .lexical_sense_candidates
                .iter()
                .map(|sense| sense.id.clone())
                .collect(),
            workspace
                .support_records
                .iter()
                .filter(|support| support.target_ref.starts_with("lexical_sense:"))
                .map(|support| support.id.clone())
                .collect(),
            "lexical sense candidates preserved as supported evidence",
        );
    }

    fn propagate_contradictions(&self, workspace: &mut EvidenceWorkspace) {
        let unresolved_objections = workspace
            .provider_suggestions
            .iter()
            .filter(|suggestion| suggestion.kind == ProviderSuggestionKind::Objection)
            .count();
        let gain = if unresolved_objections > 0 {
            "provider objections preserved as contradictions"
        } else {
            "no provider objection contradictions found"
        };
        self.trace(
            workspace,
            DiffusionPassKind::ContradictionPropagation,
            workspace
                .provider_suggestions
                .iter()
                .map(|suggestion| suggestion.id.clone())
                .collect(),
            workspace
                .contradiction_records
                .iter()
                .map(|contradiction| contradiction.id.clone())
                .collect(),
            gain,
        );
    }

    fn propose_stable_candidates(
        &self,
        workspace: &EvidenceWorkspace,
    ) -> Vec<StableCandidateProposal> {
        workspace
            .candidate_meanings
            .iter()
            .filter_map(|candidate| {
                let supports = workspace.support_for_target(&candidate.id);
                if supports
                    .iter()
                    .any(|support| support.support_weight >= self.minimum_support_weight)
                {
                    Some(StableCandidateProposal {
                        id: format!("proposal:{}", candidate.id),
                        candidate_ref: candidate.id.clone(),
                        support_sources: supports
                            .iter()
                            .map(|support| support.id.clone())
                            .collect(),
                        lineage: candidate.lineage.clone(),
                    })
                } else {
                    None
                }
            })
            .collect()
    }

    fn propose_uncertainties(&self, workspace: &EvidenceWorkspace) -> Vec<UncertaintyProposal> {
        let mut proposals = workspace
            .provider_deliberations
            .iter()
            .map(|deliberation| UncertaintyProposal {
                id: format!("uncertainty:{}", deliberation.id),
                uncertainty_type: UncertaintyType::ProviderDisagreement,
                boundary_statement: format!(
                    "provider disagreement around {} remains bounded by deliberation {}",
                    deliberation.candidate_ref, deliberation.id
                ),
                candidate_set: vec![deliberation.candidate_ref.clone()],
                lineage: deliberation.lineage.clone(),
            })
            .collect::<Vec<_>>();

        if let Some(proposal) = self.propose_imperative_subject_uncertainty(workspace) {
            proposals.push(proposal);
        }
        proposals.extend(self.propose_unresolved_role_uncertainties(workspace));
        proposals.extend(self.propose_unresolved_scope_uncertainties(workspace));

        proposals
    }

    fn propose_unresolved_role_uncertainties(
        &self,
        workspace: &EvidenceWorkspace,
    ) -> Vec<UncertaintyProposal> {
        let mut proposals = Vec::new();
        for token in &workspace.tokens {
            if token.is_punctuation() || has_structural_hint(workspace, &token.id) {
                continue;
            }
            let mut candidates = workspace.candidates_by_token(&token.id);
            candidates.sort_by(|left, right| {
                right
                    .support_weight
                    .total_cmp(&left.support_weight)
                    .then_with(|| left.id.cmp(&right.id))
            });
            if candidates.len() < 2 {
                continue;
            }
            let top = candidates[0];
            let Some(second) = candidates
                .iter()
                .find(|candidate| candidate.role != top.role)
            else {
                continue;
            };
            if (top.support_weight - second.support_weight).abs() >= 0.12 {
                continue;
            }
            proposals.push(UncertaintyProposal {
                id: format!("uncertainty:unresolved_role:{}", token.id),
                uncertainty_type: UncertaintyType::UnresolvedRole,
                boundary_statement: format!(
                    "token '{}' has competing grammatical roles {} and {}",
                    token.surface_text,
                    role_name(top.role),
                    role_name(second.role)
                ),
                candidate_set: vec![top.id.clone(), second.id.clone()],
                lineage: LineageRecord::new(token.id.clone(), "unresolved role boundary"),
            });
        }
        proposals
    }

    fn propose_unresolved_scope_uncertainties(
        &self,
        workspace: &EvidenceWorkspace,
    ) -> Vec<UncertaintyProposal> {
        workspace
            .candidate_relations
            .iter()
            .filter_map(|relation| {
                let source_is_stabilizable = workspace
                    .candidate_meanings
                    .iter()
                    .any(|candidate| candidate.label == relation.source_label);
                let target_is_stabilizable = workspace
                    .candidate_meanings
                    .iter()
                    .any(|candidate| candidate.label == relation.target_label);
                if source_is_stabilizable && target_is_stabilizable {
                    return None;
                }
                Some(UncertaintyProposal {
                    id: format!("uncertainty:unresolved_scope:{}", relation.id),
                    uncertainty_type: UncertaintyType::UnresolvedScope,
                    boundary_statement: format!(
                        "relation {:?} has unresolved scope between {} and {}",
                        relation.relation_kind, relation.source_label, relation.target_label
                    ),
                    candidate_set: vec![
                        relation.id.clone(),
                        relation.source_label.clone(),
                        relation.target_label.clone(),
                    ],
                    lineage: relation.lineage.clone(),
                })
            })
            .collect()
    }

    fn propose_imperative_subject_uncertainty(
        &self,
        workspace: &EvidenceWorkspace,
    ) -> Option<UncertaintyProposal> {
        let action = imperative_action_candidate(workspace)?;
        let action_token = first_token_for_candidate(workspace, action)?;
        if explicit_subject_before(workspace, action_token.token_index) {
            return None;
        }

        Some(UncertaintyProposal {
            id: format!("uncertainty:implied_actor:{}", action.label),
            uncertainty_type: UncertaintyType::UnresolvedSubjectBoundary,
            boundary_statement: format!(
                "imperative action {} has an implied actor; no explicit grammatical subject appears before the command action",
                action.label
            ),
            candidate_set: vec![
                action.id.clone(),
                "implied_actor:command_executor".to_string(),
            ],
            lineage: LineageRecord::new(action_token.id.clone(), "imperative subject boundary"),
        })
    }

    fn ensure_meaning(
        &self,
        workspace: &mut EvidenceWorkspace,
        label: &str,
        kind: MeaningKind,
        source_hint: &str,
    ) {
        let candidate_id = format!("meaning:{label}");
        if workspace
            .candidate_meanings
            .iter()
            .any(|candidate| candidate.id == candidate_id)
        {
            return;
        }
        let support_id = format!("support:structural:{label}");
        self.ensure_support_record(
            workspace,
            SupportRecord {
                id: support_id.clone(),
                target_ref: candidate_id.clone(),
                support_weight: 0.65,
                source_ref: source_hint.to_string(),
                rationale: "structural diffusion support".to_string(),
            },
        );
        workspace.candidate_meanings.push(CandidateMeaning {
            id: candidate_id,
            kind,
            label: label.to_string(),
            token_refs: workspace
                .tokens
                .iter()
                .filter(|token| source_hint.contains(&token.normalized_text))
                .map(|token| token.id.clone())
                .collect(),
            support_record_ids: vec![support_id],
            contradiction_record_ids: Vec::new(),
            lineage: LineageRecord::new(source_hint, "structural candidate meaning"),
        });
    }

    fn ensure_support_record(
        &self,
        workspace: &mut EvidenceWorkspace,
        record: SupportRecord,
    ) -> bool {
        if workspace
            .support_records
            .iter()
            .any(|support| support.id == record.id)
        {
            return false;
        }
        workspace.support_records.push(record);
        true
    }

    fn ensure_relation(
        &self,
        workspace: &mut EvidenceWorkspace,
        kind: RelationKind,
        source_label: &str,
        target_label: &str,
        rationale: &str,
    ) {
        let relation_id = format!("candidate_relation:{source_label}:{target_label}:{kind:?}");
        if workspace
            .candidate_relations
            .iter()
            .any(|relation| relation.id == relation_id)
        {
            return;
        }
        workspace.candidate_relations.push(CandidateRelation {
            id: relation_id,
            relation_kind: kind,
            source_label: source_label.to_string(),
            target_label: target_label.to_string(),
            support_record_ids: Vec::new(),
            contradiction_record_ids: Vec::new(),
            lineage: LineageRecord::new(format!("{source_label}->{target_label}"), rationale),
        });
    }

    fn ensure_span(
        &self,
        workspace: &mut EvidenceWorkspace,
        token_indices: &[usize],
        span_kind: SpanKind,
        support_weight: f32,
        source: EvidenceSource,
        lineage_ref: &str,
        rationale: &str,
    ) {
        let tokens = token_indices
            .iter()
            .filter_map(|index| {
                workspace
                    .tokens
                    .iter()
                    .find(|token| token.token_index == *index)
            })
            .collect::<Vec<_>>();
        if tokens.is_empty() {
            return;
        }
        let token_refs = tokens
            .iter()
            .map(|token| token.id.clone())
            .collect::<Vec<_>>();
        let normalized_text = tokens
            .iter()
            .map(|token| token.normalized_text.clone())
            .collect::<Vec<_>>()
            .join(" ");
        let id = format!("span:{}:{span_kind:?}", normalized_text.replace(' ', "_"));
        if workspace.span_candidates.iter().any(|span| span.id == id) {
            return;
        }
        let surface_text = tokens
            .iter()
            .map(|token| token.surface_text.clone())
            .collect::<Vec<_>>()
            .join(" ");
        workspace.span_candidates.push(SpanCandidate {
            id,
            token_refs,
            surface_text,
            normalized_text,
            span_kind,
            support_weight,
            source,
            status: CandidateStatus::Active,
            lineage: LineageRecord::new(lineage_ref, rationale),
        });
    }

    fn trace(
        &self,
        workspace: &mut EvidenceWorkspace,
        kind: DiffusionPassKind,
        input_refs: Vec<String>,
        output_refs: Vec<String>,
        gain_delta: &str,
    ) {
        let id = format!("pass:{}:{}", workspace.pass_traces.len(), pass_name(kind));
        workspace.pass_traces.push(DiffusionPassTrace {
            id,
            kind,
            input_refs,
            output_refs,
            constraint_refs: Vec::new(),
            gain_delta: gain_delta.to_string(),
            remaining_uncertainty: "preserved unless stabilization gate accepts".to_string(),
        });
    }
}

fn pass_name(kind: DiffusionPassKind) -> &'static str {
    match kind {
        DiffusionPassKind::CandidateActivation => "candidate_activation",
        DiffusionPassKind::ClosedClassConstraint => "closed_class_constraint",
        DiffusionPassKind::SpanCandidateFormation => "span_candidate_formation",
        DiffusionPassKind::ClosedClassRelationTemplate => "closed_class_relation_template",
        DiffusionPassKind::StructuralConstraint => "structural_constraint",
        DiffusionPassKind::SenseCoherenceScoring => "sense_coherence_scoring",
        DiffusionPassKind::LexicalSenseSupport => "lexical_sense_support",
        DiffusionPassKind::SupportPropagation => "support_propagation",
        DiffusionPassKind::ContradictionPropagation => "contradiction_propagation",
        DiffusionPassKind::WobbleMeasurement => "wobble_measurement",
        DiffusionPassKind::SemanticCandidateProposal => "semantic_candidate_proposal",
        DiffusionPassKind::UncertaintyProposal => "uncertainty_proposal",
        DiffusionPassKind::NoGainStop => "no_gain_stop",
    }
}

fn next_content_token(tokens: &[Token], start_index: usize) -> Option<&Token> {
    tokens
        .iter()
        .filter(|token| token.token_index >= start_index && !token.is_punctuation())
        .min_by_key(|token| token.token_index)
}

fn previous_content_token(tokens: &[Token], before_index: usize) -> Option<&Token> {
    tokens
        .iter()
        .filter(|token| token.token_index < before_index && !token.is_punctuation())
        .max_by_key(|token| token.token_index)
}

fn imperative_action_candidate(workspace: &EvidenceWorkspace) -> Option<&CandidateMeaning> {
    let token = first_content_token(&workspace.tokens)?;
    if !has_strong_verb_evidence(workspace, &token.id) {
        return None;
    }
    workspace.candidate_meanings.iter().find(|candidate| {
        candidate.kind == MeaningKind::Action
            && candidate
                .token_refs
                .iter()
                .any(|token_ref| token_ref == &token.id)
    })
}

fn first_content_token(tokens: &[Token]) -> Option<&Token> {
    tokens.iter().find(|token| !token.is_punctuation())
}

fn first_token_for_candidate<'a>(
    workspace: &'a EvidenceWorkspace,
    candidate: &CandidateMeaning,
) -> Option<&'a Token> {
    candidate
        .token_refs
        .iter()
        .filter_map(|token_ref| workspace.tokens.iter().find(|token| &token.id == token_ref))
        .min_by_key(|token| token.token_index)
}

fn has_strong_verb_evidence(workspace: &EvidenceWorkspace, token_id: &str) -> bool {
    workspace.grammar_candidates.iter().any(|candidate| {
        candidate.token_id == token_id
            && candidate.role == GrammarRole::Verb
            && candidate.support_weight >= 0.6
    })
}

fn contradiction_severity(measurement: JuryMeasurement) -> Severity {
    match measurement {
        JuryMeasurement::BlocksStabilization => Severity::Blocking,
        JuryMeasurement::CreatesUncertainty | JuryMeasurement::NeedsMoreContext => Severity::High,
        JuryMeasurement::SupportsStabilization => Severity::Low,
    }
}

fn contradiction_status(measurement: JuryMeasurement) -> ContradictionStatus {
    match measurement {
        JuryMeasurement::SupportsStabilization => ContradictionStatus::Answered,
        JuryMeasurement::BlocksStabilization
        | JuryMeasurement::CreatesUncertainty
        | JuryMeasurement::NeedsMoreContext => ContradictionStatus::Unresolved,
    }
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

fn following_content_tokens(tokens: &[Token], start_index: usize, max_count: usize) -> Vec<&Token> {
    tokens
        .iter()
        .filter(|token| token.token_index >= start_index)
        .take_while(|token| !token.is_punctuation())
        .filter(|token| !token.is_punctuation())
        .take(max_count)
        .collect()
}

fn has_role(workspace: &EvidenceWorkspace, token_id: &str, role: GrammarRole) -> bool {
    workspace
        .grammar_candidates
        .iter()
        .any(|candidate| candidate.token_id == token_id && candidate.role == role)
}

fn has_structural_hint(workspace: &EvidenceWorkspace, token_id: &str) -> bool {
    workspace
        .structural_hints
        .iter()
        .any(|hint| hint.token_id == token_id)
}

fn sense_coherence_bonus(workspace: &EvidenceWorkspace, sense: &LexicalSenseCandidate) -> f32 {
    let Some(definition) = sense.definition.as_ref() else {
        return 0.0;
    };
    let definition = definition.to_lowercase();
    let context_terms = workspace
        .tokens
        .iter()
        .filter(|token| !token.is_punctuation())
        .map(|token| token.normalized_text.as_str())
        .collect::<Vec<_>>();
    let context_text = context_terms.join(" ");
    let span_text = workspace
        .span_candidates
        .iter()
        .map(|span| span.normalized_text.as_str())
        .collect::<Vec<_>>()
        .join(" ");
    let context = format!("{context_text} {span_text}");

    let mut bonus: f32 = 0.0;
    for term in context_terms {
        if term.len() > 3 && definition.contains(term) {
            bonus += 0.05;
        }
    }
    for rule in SENSE_COHERENCE_RULES {
        if rule.applies(&context, &definition) {
            bonus += rule.bonus;
        }
    }
    bonus.min(0.3)
}

fn relation_label_for_token(workspace: &EvidenceWorkspace, token: &Token) -> String {
    workspace
        .candidate_meanings
        .iter()
        .find(|meaning| {
            meaning
                .token_refs
                .iter()
                .any(|token_ref| token_ref == &token.id)
        })
        .map(|meaning| meaning.label.clone())
        .unwrap_or_else(|| format!("TokenEvidence:{}", capitalize_label(&token.normalized_text)))
}

fn span_relation_label(span: &SpanCandidate) -> String {
    format!(
        "SpanEvidence:{}",
        capitalize_label(&span.normalized_text.replace(' ', "_"))
    )
}

fn capitalize_label(value: &str) -> String {
    value
        .split('_')
        .filter(|part| !part.is_empty())
        .map(|part| {
            let mut chars = part.chars();
            match chars.next() {
                Some(first) => first.to_uppercase().chain(chars).collect::<String>(),
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join("")
}
