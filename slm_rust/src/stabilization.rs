use serde::{Deserialize, Serialize};

use crate::diffusion::{DiffusionOutput, UncertaintyProposal};
use crate::evidence::EvidenceWorkspace;
use crate::graph::UncertaintyType;
use crate::wobble::WobbleVector;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Faculty {
    Observer,
    Honesty,
    Security,
    Planner,
    Weaver,
    Scribe,
    Refiner,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FacultyResult {
    Approve,
    Reject,
    Abstain,
    NeedsMoreEvidence,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FacultyVote {
    pub faculty: Faculty,
    pub result: FacultyResult,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VetoRecord {
    pub faculty: Faculty,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FacultyRun {
    pub id: String,
    pub votes: Vec<FacultyVote>,
    pub vetoes: Vec<VetoRecord>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DecisionOutcome {
    PromoteGlyph,
    CreateUncertaintyGlyph,
    PreserveInEvidenceWorkspace,
    RejectCandidate,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StabilizationDecision {
    pub id: String,
    pub target_ref: String,
    pub outcome: DecisionOutcome,
    pub faculty_vote_count: usize,
    pub faculty_threshold: usize,
    pub contradiction_score: f32,
    pub contradiction_threshold: f32,
    pub wobble_score: f32,
    pub wobble_threshold: f32,
    pub lineage_present: bool,
    pub faculty_run: FacultyRun,
    pub reason: String,
}

#[derive(Debug, Clone)]
pub struct Stabilizer {
    pub faculty_threshold: usize,
    pub contradiction_threshold: f32,
    pub wobble_threshold: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UncertaintyBoundaryCriteria {
    pub uncertainty_type: UncertaintyType,
    pub minimum_candidate_count: usize,
    pub required_boundary_terms: Vec<String>,
    pub candidate_prefixes: Vec<String>,
    pub rationale: String,
}

impl Default for Stabilizer {
    fn default() -> Self {
        Self {
            faculty_threshold: 5,
            contradiction_threshold: 0.7,
            wobble_threshold: 0.55,
        }
    }
}

impl Stabilizer {
    pub fn decide(
        &self,
        workspace: &EvidenceWorkspace,
        diffusion: &DiffusionOutput,
    ) -> Vec<StabilizationDecision> {
        let wobble = workspace
            .wobble_vectors
            .last()
            .cloned()
            .unwrap_or_else(|| WobbleVector::measure(workspace));
        let mut decisions = Vec::new();

        for proposal in &diffusion.stable_candidate_proposals {
            let Some(candidate) = workspace
                .candidate_meanings
                .iter()
                .find(|candidate| candidate.id == proposal.candidate_ref)
            else {
                continue;
            };
            let contradiction_score =
                WobbleVector::blocking_contradiction_score(workspace, &candidate.id);
            let lineage_present = candidate.lineage.is_present();
            let support_count = workspace.support_for_target(&candidate.id).len();
            let target_wobble = wobble.target_wobble(workspace, &candidate.id);
            let faculty_run = self.faculty_run(
                &candidate.id,
                support_count,
                contradiction_score,
                target_wobble,
                lineage_present,
            );
            let faculty_vote_count = faculty_run
                .votes
                .iter()
                .filter(|vote| vote.result == FacultyResult::Approve)
                .count();
            let has_veto = !faculty_run.vetoes.is_empty();
            let outcome = if support_count >= 1
                && faculty_vote_count >= self.faculty_threshold
                && contradiction_score < self.contradiction_threshold
                && target_wobble < self.wobble_threshold
                && lineage_present
                && !has_veto
            {
                DecisionOutcome::PromoteGlyph
            } else {
                DecisionOutcome::PreserveInEvidenceWorkspace
            };

            decisions.push(StabilizationDecision {
                id: format!("decision:{}", candidate.id),
                target_ref: candidate.id.clone(),
                outcome,
                faculty_vote_count,
                faculty_threshold: self.faculty_threshold,
                contradiction_score,
                contradiction_threshold: self.contradiction_threshold,
                wobble_score: target_wobble,
                wobble_threshold: self.wobble_threshold,
                lineage_present,
                faculty_run,
                reason: match outcome {
                    DecisionOutcome::PromoteGlyph => {
                        "faculty convergence passed stabilization gates".to_string()
                    }
                    _ => "candidate preserved in evidence workspace".to_string(),
                },
            });
        }

        for proposal in &diffusion.uncertainty_proposals {
            let criteria = uncertainty_boundary_criteria(proposal.uncertainty_type);
            let lineage_present = proposal.lineage.is_present();
            let boundary_passes = uncertainty_boundary_passes(proposal, &criteria);
            let faculty_run =
                self.uncertainty_faculty_run(proposal, &criteria, boundary_passes, lineage_present);
            let faculty_vote_count = faculty_run
                .votes
                .iter()
                .filter(|vote| vote.result == FacultyResult::Approve)
                .count();
            let has_veto = !faculty_run.vetoes.is_empty();
            let outcome = if boundary_passes
                && lineage_present
                && faculty_vote_count >= self.faculty_threshold
                && !has_veto
            {
                DecisionOutcome::CreateUncertaintyGlyph
            } else {
                DecisionOutcome::PreserveInEvidenceWorkspace
            };
            decisions.push(StabilizationDecision {
                id: format!("decision:{}", proposal.id),
                target_ref: proposal.id.clone(),
                outcome,
                faculty_vote_count,
                faculty_threshold: self.faculty_threshold,
                contradiction_score: 0.0,
                contradiction_threshold: self.contradiction_threshold,
                wobble_score: wobble.aggregate_score,
                wobble_threshold: 1.0,
                lineage_present,
                faculty_run,
                reason: match outcome {
                    DecisionOutcome::CreateUncertaintyGlyph => {
                        format!(
                            "bounded {:?} uncertainty passed type-specific criteria",
                            proposal.uncertainty_type
                        )
                    }
                    _ => {
                        "uncertainty boundary is not specific enough for graph identity".to_string()
                    }
                },
            });
        }

        decisions
    }

    fn faculty_run(
        &self,
        target_ref: &str,
        support_count: usize,
        contradiction_score: f32,
        target_wobble: f32,
        lineage_present: bool,
    ) -> FacultyRun {
        let mut votes = Vec::new();
        let mut vetoes = Vec::new();

        votes.push(if support_count > 0 {
            approve(
                Faculty::Observer,
                "candidate is present in evidence workspace",
            )
        } else {
            reject(Faculty::Observer, "candidate is not supported by evidence")
        });

        if support_count == 0 || !lineage_present {
            let rationale = if !lineage_present {
                "lineage is missing"
            } else {
                "support is insufficient"
            };
            votes.push(reject(Faculty::Honesty, rationale));
            vetoes.push(VetoRecord {
                faculty: Faculty::Honesty,
                rationale: rationale.to_string(),
            });
        } else {
            votes.push(approve(
                Faculty::Honesty,
                "support and lineage are sufficient",
            ));
        }

        if contradiction_score >= self.contradiction_threshold {
            votes.push(reject(
                Faculty::Security,
                "unresolved high-severity contradiction remains",
            ));
            vetoes.push(VetoRecord {
                faculty: Faculty::Security,
                rationale: "unresolved high-severity contradiction remains".to_string(),
            });
        } else {
            votes.push(approve(
                Faculty::Security,
                "no blocking contradiction remains",
            ));
        }

        votes.push(approve(Faculty::Planner, "candidate fits current sequence"));
        if target_wobble < self.wobble_threshold {
            votes.push(approve(Faculty::Weaver, "candidate coheres relationally"));
        } else {
            votes.push(reject(Faculty::Weaver, "wobble remains too high"));
        }
        if lineage_present {
            votes.push(approve(Faculty::Scribe, "lineage is preserved"));
        } else {
            votes.push(reject(Faculty::Scribe, "lineage is absent"));
        }
        votes.push(approve(
            Faculty::Refiner,
            format!("{target_ref} is compressed without changing identity"),
        ));

        FacultyRun {
            id: format!("faculty:{target_ref}"),
            votes,
            vetoes,
        }
    }

    fn uncertainty_faculty_run(
        &self,
        proposal: &UncertaintyProposal,
        criteria: &UncertaintyBoundaryCriteria,
        boundary_passes: bool,
        lineage_present: bool,
    ) -> FacultyRun {
        let mut votes = Vec::new();
        let mut vetoes = Vec::new();

        if boundary_passes {
            votes.push(approve(
                Faculty::Observer,
                format!("{} is present", criteria.rationale),
            ));
        } else {
            votes.push(reject(
                Faculty::Observer,
                "uncertainty boundary is not sufficiently bounded",
            ));
        }

        if lineage_present && boundary_passes {
            votes.push(approve(
                Faculty::Honesty,
                "uncertainty is preserved without pretending certainty",
            ));
        } else {
            let rationale = if !lineage_present {
                "uncertainty lineage is missing"
            } else {
                "uncertainty candidate set or boundary statement is insufficient"
            };
            votes.push(reject(Faculty::Honesty, rationale));
            vetoes.push(VetoRecord {
                faculty: Faculty::Honesty,
                rationale: rationale.to_string(),
            });
        }

        votes.push(approve(
            Faculty::Security,
            "bounded uncertainty does not assert an unsafe stable meaning",
        ));
        votes.push(approve(
            Faculty::Planner,
            "uncertainty can be revisited by later diffusion",
        ));
        if boundary_passes {
            votes.push(approve(
                Faculty::Weaver,
                "uncertainty boundary is relationally local",
            ));
        } else {
            votes.push(reject(Faculty::Weaver, "uncertainty boundary is too broad"));
        }
        if lineage_present {
            votes.push(approve(Faculty::Scribe, "uncertainty lineage is preserved"));
        } else {
            votes.push(reject(Faculty::Scribe, "uncertainty lineage is absent"));
        }
        votes.push(approve(
            Faculty::Refiner,
            format!(
                "{:?} uncertainty is compressed without collapsing candidates",
                proposal.uncertainty_type
            ),
        ));

        FacultyRun {
            id: format!("faculty:{}", proposal.id),
            votes,
            vetoes,
        }
    }
}

pub fn uncertainty_boundary_criteria(
    uncertainty_type: UncertaintyType,
) -> UncertaintyBoundaryCriteria {
    match uncertainty_type {
        UncertaintyType::ProviderDisagreement => UncertaintyBoundaryCriteria {
            uncertainty_type,
            minimum_candidate_count: 1,
            required_boundary_terms: vec!["provider disagreement".to_string()],
            candidate_prefixes: vec!["meaning:".to_string(), "candidate_relation:".to_string()],
            rationale: "provider disagreement boundary".to_string(),
        },
        UncertaintyType::UnresolvedRole => UncertaintyBoundaryCriteria {
            uncertainty_type,
            minimum_candidate_count: 2,
            required_boundary_terms: vec!["competing grammatical roles".to_string()],
            candidate_prefixes: vec!["grammar:".to_string()],
            rationale: "unresolved role boundary".to_string(),
        },
        UncertaintyType::UnresolvedScope => UncertaintyBoundaryCriteria {
            uncertainty_type,
            minimum_candidate_count: 2,
            required_boundary_terms: vec!["unresolved scope".to_string()],
            candidate_prefixes: vec!["candidate_relation:".to_string()],
            rationale: "unresolved scope boundary".to_string(),
        },
        UncertaintyType::UnresolvedSubjectBoundary => UncertaintyBoundaryCriteria {
            uncertainty_type,
            minimum_candidate_count: 2,
            required_boundary_terms: vec![
                "implied actor".to_string(),
                "command subject".to_string(),
            ],
            candidate_prefixes: vec!["meaning:".to_string(), "implied_actor:".to_string()],
            rationale: "unresolved subject boundary".to_string(),
        },
        _ => UncertaintyBoundaryCriteria {
            uncertainty_type,
            minimum_candidate_count: 2,
            required_boundary_terms: Vec::new(),
            candidate_prefixes: Vec::new(),
            rationale: "generic bounded uncertainty".to_string(),
        },
    }
}

fn uncertainty_boundary_passes(
    proposal: &UncertaintyProposal,
    criteria: &UncertaintyBoundaryCriteria,
) -> bool {
    if proposal.candidate_set.len() < criteria.minimum_candidate_count {
        return false;
    }
    let boundary = proposal.boundary_statement.to_lowercase();
    if !criteria.required_boundary_terms.is_empty()
        && !criteria
            .required_boundary_terms
            .iter()
            .any(|term| boundary.contains(term))
    {
        return false;
    }
    if criteria.candidate_prefixes.is_empty() {
        return true;
    }
    proposal.candidate_set.iter().any(|candidate| {
        criteria
            .candidate_prefixes
            .iter()
            .any(|prefix| candidate.starts_with(prefix))
    })
}

fn approve(faculty: Faculty, rationale: impl Into<String>) -> FacultyVote {
    FacultyVote {
        faculty,
        result: FacultyResult::Approve,
        rationale: rationale.into(),
    }
}

fn reject(faculty: Faculty, rationale: impl Into<String>) -> FacultyVote {
    FacultyVote {
        faculty,
        result: FacultyResult::Reject,
        rationale: rationale.into(),
    }
}

#[cfg(test)]
mod tests {
    use super::{DecisionOutcome, Stabilizer};
    use crate::core::{
        CandidateMeaning, ContradictionKind, ContradictionRecord, ContradictionStatus,
        LineageRecord, MeaningKind, Severity, SupportRecord,
    };
    use crate::diffusion::{DiffusionOutput, StableCandidateProposal};
    use crate::evidence::EvidenceWorkspace;
    use crate::wobble::{WobbleDimensions, WobbleVector};

    #[test]
    fn faculty_threshold_boundary_preserves_without_enough_votes() {
        let (workspace, diffusion) = threshold_fixture_workspace(None, 0.1);
        let strict = Stabilizer {
            faculty_threshold: 8,
            ..Stabilizer::default()
        };
        let default = Stabilizer::default();

        let strict_decision = strict.decide(&workspace, &diffusion);
        let default_decision = default.decide(&workspace, &diffusion);

        assert_eq!(strict_decision[0].faculty_vote_count, 7);
        assert_eq!(
            strict_decision[0].outcome,
            DecisionOutcome::PreserveInEvidenceWorkspace
        );
        assert_eq!(default_decision[0].outcome, DecisionOutcome::PromoteGlyph);
    }

    #[test]
    fn high_contradiction_threshold_blocks_stabilization() {
        let (workspace, diffusion) = threshold_fixture_workspace(Some(Severity::High), 0.1);
        let decision = Stabilizer::default().decide(&workspace, &diffusion);

        assert_eq!(decision[0].contradiction_score, Severity::High.score());
        assert_eq!(
            decision[0].outcome,
            DecisionOutcome::PreserveInEvidenceWorkspace
        );
        assert!(
            decision[0]
                .faculty_run
                .vetoes
                .iter()
                .any(|veto| veto.faculty == super::Faculty::Security)
        );
    }

    #[test]
    fn wobble_threshold_boundary_preserves_at_threshold_and_promotes_below() {
        let (at_workspace, diffusion) = threshold_fixture_workspace(None, 0.55);
        let at_decision = Stabilizer::default().decide(&at_workspace, &diffusion);
        assert_eq!(
            at_decision[0].outcome,
            DecisionOutcome::PreserveInEvidenceWorkspace
        );
        assert_eq!(at_decision[0].wobble_score, 0.55);

        let (below_workspace, diffusion) = threshold_fixture_workspace(None, 0.54);
        let below_decision = Stabilizer::default().decide(&below_workspace, &diffusion);
        assert_eq!(below_decision[0].outcome, DecisionOutcome::PromoteGlyph);
        assert_eq!(below_decision[0].wobble_score, 0.54);
    }

    fn threshold_fixture_workspace(
        contradiction: Option<Severity>,
        wobble_score: f32,
    ) -> (EvidenceWorkspace, DiffusionOutput) {
        let mut workspace =
            EvidenceWorkspace::from_text("threshold-fixture", "Maybe design a compiler.");
        let candidate_id = "meaning:ThresholdCandidate".to_string();
        let support_id = "support:threshold-candidate".to_string();
        workspace.support_records.push(SupportRecord {
            id: support_id.clone(),
            target_ref: candidate_id.clone(),
            support_weight: 0.76,
            source_ref: "threshold-fixture-provider".to_string(),
            rationale: "candidate has enough support to test gates".to_string(),
        });
        let mut contradiction_record_ids = Vec::new();
        if let Some(severity) = contradiction {
            let contradiction_id = "contradiction:threshold-candidate".to_string();
            workspace.contradiction_records.push(ContradictionRecord {
                id: contradiction_id.clone(),
                target_ref: candidate_id.clone(),
                severity,
                kind: ContradictionKind::ProviderObjection,
                source_ref: "objection:threshold".to_string(),
                answer_ref: None,
                provider_deliberation_ref: None,
                jury_review_ref: None,
                cited_panel_refs: Vec::new(),
                status: ContradictionStatus::Unresolved,
                rationale: "threshold contradiction fixture".to_string(),
            });
            contradiction_record_ids.push(contradiction_id);
        }
        workspace.candidate_meanings.push(CandidateMeaning {
            id: candidate_id.clone(),
            kind: MeaningKind::Action,
            label: "ThresholdCandidate".to_string(),
            token_refs: vec!["tok:threshold-fixture:1".to_string()],
            support_record_ids: vec![support_id.clone()],
            contradiction_record_ids,
            lineage: LineageRecord::new("threshold-fixture-provider", "threshold fixture"),
        });
        workspace.wobble_vectors.push(WobbleVector {
            aggregate_score: wobble_score,
            dimensions: WobbleDimensions::default(),
            factors: Vec::new(),
        });

        (
            workspace,
            DiffusionOutput {
                stable_candidate_proposals: vec![StableCandidateProposal {
                    id: "proposal:threshold-candidate".to_string(),
                    candidate_ref: candidate_id,
                    support_sources: vec![support_id],
                    lineage: LineageRecord::new("threshold-fixture-provider", "threshold proposal"),
                }],
                uncertainty_proposals: Vec::new(),
            },
        )
    }
}
