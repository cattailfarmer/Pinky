use serde::{Deserialize, Serialize};

use crate::core::{ContradictionKind, LineageRecord};
use crate::providers::{ProviderSuggestion, ProviderSuggestionKind};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DisagreementClass {
    SameMeaningDifferentWords,
    RoleConflict,
    RelationConflict,
    ScopeConflict,
    UnsupportedClaim,
    Contradiction,
    InsufficientContext,
    InvalidConsequence,
    LineageGap,
}

impl From<DisagreementClass> for ContradictionKind {
    fn from(value: DisagreementClass) -> Self {
        match value {
            DisagreementClass::RoleConflict => Self::RoleConflict,
            DisagreementClass::RelationConflict => Self::RelationConflict,
            DisagreementClass::ScopeConflict => Self::ScopeConflict,
            DisagreementClass::UnsupportedClaim => Self::UnsupportedClaim,
            DisagreementClass::InvalidConsequence => Self::InvalidConsequence,
            DisagreementClass::LineageGap => Self::LineageGap,
            DisagreementClass::SameMeaningDifferentWords
            | DisagreementClass::Contradiction
            | DisagreementClass::InsufficientContext => Self::ProviderObjection,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum JuryMeasurement {
    SupportsStabilization,
    BlocksStabilization,
    CreatesUncertainty,
    NeedsMoreContext,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DeliberationStatus {
    ResolvedSupported,
    ResolvedRejected,
    PersistentDisagreement,
    InsufficientContext,
    Deferred,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderObjection {
    pub id: String,
    pub provider_id: String,
    pub kind: DisagreementClass,
    pub rationale: String,
    pub target_ref: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderAnswer {
    pub id: String,
    pub provider_id: String,
    pub answered_objection: String,
    pub answer_kind: String,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JuryPanelMemberReview {
    pub id: String,
    pub panel_member_ref: String,
    pub measurement: JuryMeasurement,
    pub cited_refs: Vec<String>,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JuryReview {
    pub id: String,
    pub panel_member_set: Vec<String>,
    pub classification: DisagreementClass,
    pub measurement: JuryMeasurement,
    pub member_reviews: Vec<JuryPanelMemberReview>,
    pub cited_panel_refs: Vec<String>,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderDeliberation {
    pub id: String,
    pub candidate_ref: String,
    pub objecting_provider: String,
    pub supporting_provider_set: Vec<String>,
    pub objection_set: Vec<ProviderObjection>,
    pub answer_set: Vec<ProviderAnswer>,
    pub jury_review_set: Vec<JuryReview>,
    pub faculty_report_refs: Vec<String>,
    pub status: DeliberationStatus,
    pub lineage: LineageRecord,
}

pub struct ProviderDeliberationEngine;

impl ProviderDeliberationEngine {
    pub fn deliberate(suggestions: &[ProviderSuggestion]) -> Vec<ProviderDeliberation> {
        let objections = suggestions
            .iter()
            .filter(|suggestion| suggestion.kind == ProviderSuggestionKind::Objection)
            .collect::<Vec<_>>();

        objections
            .into_iter()
            .enumerate()
            .map(|(index, objection)| {
                let disagreement_class =
                    disagreement_class_from_payload(objection.disagreement_class.as_deref());
                let answers = suggestions
                    .iter()
                    .filter(|suggestion| {
                        suggestion.kind == ProviderSuggestionKind::Answer
                            && suggestion.target_ref == objection.target_ref
                    })
                    .map(|answer| ProviderAnswer {
                        id: format!("answer:{}", answer.id),
                        provider_id: answer.provenance.provider_id.clone(),
                        answered_objection: objection.id.clone(),
                        answer_kind: answer
                            .answer_kind
                            .clone()
                            .unwrap_or_else(|| "narrows".to_string()),
                        rationale: answer.rationale.clone().unwrap_or_default(),
                    })
                    .collect::<Vec<_>>();
                let faculty_report_refs = suggestions
                    .iter()
                    .filter(|suggestion| {
                        suggestion.kind == ProviderSuggestionKind::FacultyVote
                            && suggestion.target_ref == objection.target_ref
                            && suggestion.faculty_report.is_some()
                    })
                    .map(|suggestion| suggestion.id.clone())
                    .collect::<Vec<_>>();

                let member_reviews = jury_panel_member_reviews(
                    &objection.id,
                    disagreement_class,
                    &answers,
                    &faculty_report_refs,
                );
                let measurement = aggregate_jury_measurement(&member_reviews);
                let status = measurement_status(measurement);
                let cited_panel_refs = member_reviews
                    .iter()
                    .flat_map(|review| review.cited_refs.clone())
                    .collect::<Vec<_>>();
                let panel_member_set = member_reviews
                    .iter()
                    .map(|review| review.panel_member_ref.clone())
                    .collect::<Vec<_>>();

                ProviderDeliberation {
                    id: format!("deliberation:{index}:{}", objection.target_ref),
                    candidate_ref: objection.target_ref.clone(),
                    objecting_provider: objection.provenance.provider_id.clone(),
                    supporting_provider_set: answers
                        .iter()
                        .map(|answer| answer.provider_id.clone())
                        .collect(),
                    objection_set: vec![ProviderObjection {
                        id: format!("objection:{}", objection.id),
                        provider_id: objection.provenance.provider_id.clone(),
                        kind: disagreement_class,
                        rationale: objection.rationale.clone().unwrap_or_default(),
                        target_ref: objection.target_ref.clone(),
                    }],
                    answer_set: answers,
                    jury_review_set: vec![JuryReview {
                        id: format!("jury:{}", objection.id),
                        panel_member_set,
                        classification: disagreement_class,
                        measurement,
                        member_reviews,
                        cited_panel_refs,
                        rationale: format!(
                            "provider disagreement measured as {:?} before wobble classification",
                            measurement
                        ),
                    }],
                    faculty_report_refs,
                    status,
                    lineage: objection.lineage.clone(),
                }
            })
            .collect()
    }
}

pub fn jury_panel_member_reviews(
    objection_ref: &str,
    classification: DisagreementClass,
    answers: &[ProviderAnswer],
    faculty_report_refs: &[String],
) -> Vec<JuryPanelMemberReview> {
    let cited_refs = panel_cited_refs(objection_ref, answers, faculty_report_refs);
    vec![
        JuryPanelMemberReview {
            id: format!("jury_member:{objection_ref}:observer"),
            panel_member_ref: "jury_observer".to_string(),
            measurement: observer_measurement(classification, answers),
            cited_refs: cited_refs.clone(),
            rationale: "Observer checks whether the disagreement target and competing evidence are present"
                .to_string(),
        },
        JuryPanelMemberReview {
            id: format!("jury_member:{objection_ref}:honesty"),
            panel_member_ref: "jury_honesty".to_string(),
            measurement: honesty_measurement(classification, answers, faculty_report_refs),
            cited_refs: cited_refs.clone(),
            rationale: "Honesty blocks unsupported certainty and demands preserved uncertainty when support is incomplete"
                .to_string(),
        },
        JuryPanelMemberReview {
            id: format!("jury_member:{objection_ref}:weaver"),
            panel_member_ref: "jury_weaver".to_string(),
            measurement: weaver_measurement(classification, answers),
            cited_refs,
            rationale: "Weaver checks whether the relation or role conflict coheres after answers are considered"
                .to_string(),
        },
    ]
}

pub fn aggregate_jury_measurement(member_reviews: &[JuryPanelMemberReview]) -> JuryMeasurement {
    if member_reviews
        .iter()
        .any(|review| review.measurement == JuryMeasurement::BlocksStabilization)
    {
        return JuryMeasurement::BlocksStabilization;
    }

    if member_reviews
        .iter()
        .any(|review| review.measurement == JuryMeasurement::NeedsMoreContext)
    {
        return JuryMeasurement::NeedsMoreContext;
    }

    if member_reviews
        .iter()
        .any(|review| review.measurement == JuryMeasurement::CreatesUncertainty)
    {
        return JuryMeasurement::CreatesUncertainty;
    }

    JuryMeasurement::SupportsStabilization
}

pub fn measurement_status(measurement: JuryMeasurement) -> DeliberationStatus {
    match measurement {
        JuryMeasurement::SupportsStabilization => DeliberationStatus::ResolvedSupported,
        JuryMeasurement::BlocksStabilization => DeliberationStatus::PersistentDisagreement,
        JuryMeasurement::CreatesUncertainty => DeliberationStatus::PersistentDisagreement,
        JuryMeasurement::NeedsMoreContext => DeliberationStatus::InsufficientContext,
    }
}

fn panel_cited_refs(
    objection_ref: &str,
    answers: &[ProviderAnswer],
    faculty_report_refs: &[String],
) -> Vec<String> {
    let mut cited_refs = vec![format!("objection:{objection_ref}")];
    cited_refs.extend(answers.iter().map(|answer| answer.id.clone()));
    cited_refs.extend(faculty_report_refs.iter().cloned());
    cited_refs.sort();
    cited_refs.dedup();
    cited_refs
}

fn observer_measurement(
    classification: DisagreementClass,
    answers: &[ProviderAnswer],
) -> JuryMeasurement {
    match classification {
        DisagreementClass::InvalidConsequence | DisagreementClass::Contradiction => {
            JuryMeasurement::BlocksStabilization
        }
        DisagreementClass::InsufficientContext if answers.is_empty() => {
            JuryMeasurement::CreatesUncertainty
        }
        _ if answers.is_empty() => JuryMeasurement::CreatesUncertainty,
        _ => JuryMeasurement::NeedsMoreContext,
    }
}

fn honesty_measurement(
    classification: DisagreementClass,
    answers: &[ProviderAnswer],
    faculty_report_refs: &[String],
) -> JuryMeasurement {
    match classification {
        DisagreementClass::InvalidConsequence
        | DisagreementClass::Contradiction
        | DisagreementClass::LineageGap => JuryMeasurement::BlocksStabilization,
        _ if answers.is_empty() => JuryMeasurement::CreatesUncertainty,
        _ if faculty_report_refs.is_empty() => JuryMeasurement::NeedsMoreContext,
        _ => JuryMeasurement::NeedsMoreContext,
    }
}

fn weaver_measurement(
    classification: DisagreementClass,
    answers: &[ProviderAnswer],
) -> JuryMeasurement {
    match classification {
        DisagreementClass::RoleConflict
        | DisagreementClass::RelationConflict
        | DisagreementClass::ScopeConflict => {
            if answers.is_empty() {
                JuryMeasurement::CreatesUncertainty
            } else {
                JuryMeasurement::NeedsMoreContext
            }
        }
        DisagreementClass::InvalidConsequence | DisagreementClass::Contradiction => {
            JuryMeasurement::BlocksStabilization
        }
        _ if answers.is_empty() => JuryMeasurement::CreatesUncertainty,
        _ => JuryMeasurement::NeedsMoreContext,
    }
}

fn disagreement_class_from_payload(value: Option<&str>) -> DisagreementClass {
    match value.unwrap_or("role_conflict") {
        "same_meaning_different_words" => DisagreementClass::SameMeaningDifferentWords,
        "role_conflict" => DisagreementClass::RoleConflict,
        "relation_conflict" => DisagreementClass::RelationConflict,
        "scope_conflict" => DisagreementClass::ScopeConflict,
        "unsupported_claim" => DisagreementClass::UnsupportedClaim,
        "contradiction" => DisagreementClass::Contradiction,
        "insufficient_context" => DisagreementClass::InsufficientContext,
        "invalid_consequence" => DisagreementClass::InvalidConsequence,
        "lineage_gap" => DisagreementClass::LineageGap,
        _ => DisagreementClass::InsufficientContext,
    }
}

#[cfg(test)]
mod tests {
    use super::{DeliberationStatus, JuryMeasurement, ProviderDeliberationEngine};
    use crate::fixtures::time_flies_providers;
    use crate::providers::{MockProvider, ProviderSuggestion};

    #[test]
    fn time_flies_disagreement_gets_explicit_needs_more_context_jury() {
        let providers = time_flies_providers();
        let suggestions = providers
            .iter()
            .flat_map(|provider| provider.suggestions("Time flies like an arrow.", &[]))
            .collect::<Vec<_>>();
        let deliberations = ProviderDeliberationEngine::deliberate(&suggestions);
        let deliberation = deliberations
            .iter()
            .find(|deliberation| deliberation.candidate_ref == "meaning:TimeFliesAssertion")
            .expect("time flies deliberation exists");
        let review = deliberation
            .jury_review_set
            .first()
            .expect("jury review exists");

        assert_eq!(review.measurement, JuryMeasurement::NeedsMoreContext);
        assert_eq!(deliberation.status, DeliberationStatus::InsufficientContext);
        assert_eq!(review.panel_member_set.len(), 3);
        assert!(
            review
                .cited_panel_refs
                .iter()
                .any(|evidence_ref| { evidence_ref == "time-flies-support-faculty-report" })
        );
        assert!(
            review
                .member_reviews
                .iter()
                .all(|member| !member.cited_refs.is_empty())
        );
    }

    #[test]
    fn unanswered_disagreement_creates_uncertainty_measurement() {
        let objector = MockProvider::provenance_for("jury-objector");
        let suggestions = vec![ProviderSuggestion::objection_with_class(
            objector,
            "unanswered-role-objection",
            "meaning:AmbiguousRole",
            "role_conflict",
            "no answer defeats the role conflict",
        )];
        let deliberations = ProviderDeliberationEngine::deliberate(&suggestions);
        let review = &deliberations[0].jury_review_set[0];

        assert_eq!(review.measurement, JuryMeasurement::CreatesUncertainty);
        assert_eq!(
            deliberations[0].status,
            DeliberationStatus::PersistentDisagreement
        );
    }

    #[test]
    fn invalid_consequence_blocks_stabilization_measurement() {
        let objector = MockProvider::provenance_for("jury-security");
        let suggestions = vec![ProviderSuggestion::objection_with_class(
            objector,
            "invalid-consequence-objection",
            "meaning:UnsafeAction",
            "invalid_consequence",
            "security veto says this consequence is invalid",
        )];
        let deliberations = ProviderDeliberationEngine::deliberate(&suggestions);
        let review = &deliberations[0].jury_review_set[0];

        assert_eq!(review.measurement, JuryMeasurement::BlocksStabilization);
        assert_eq!(
            deliberations[0].status,
            DeliberationStatus::PersistentDisagreement
        );
    }
}
