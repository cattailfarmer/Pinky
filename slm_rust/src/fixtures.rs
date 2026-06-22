use crate::core::{CandidateMeaning, LineageRecord, MeaningKind, SupportRecord};
use crate::evidence::EvidenceWorkspace;
use crate::providers::{
    HemispherePerspective, MockProvider, ProviderAdapter, ProviderFacultyReport,
    ProviderFacultyVote, ProviderSuggestion,
};
use crate::stabilization::{Faculty, FacultyResult};

pub fn fish_swim_providers() -> Vec<Box<dyn ProviderAdapter>> {
    let observer = MockProvider::provenance_for("mock-observer");
    let weaver = MockProvider::provenance_for("mock-weaver");

    vec![
        Box::new(MockProvider::new(
            "mock-observer",
            vec![
                ProviderSuggestion::candidate_meaning(
                    observer.clone(),
                    "fish-concept-observer",
                    "FishConcept",
                    MeaningKind::Subject,
                    0.84,
                    "fish is present as the likely subject concept",
                ),
                ProviderSuggestion::candidate_meaning(
                    observer,
                    "swimming-action-observer",
                    "SwimmingAction",
                    MeaningKind::Action,
                    0.82,
                    "swim is present as the likely action",
                ),
            ],
        )),
        Box::new(MockProvider::new(
            "mock-weaver",
            vec![
                ProviderSuggestion::candidate_meaning(
                    weaver.clone(),
                    "fish-concept-weaver",
                    "FishConcept",
                    MeaningKind::Subject,
                    0.78,
                    "determiner plus position supports fish as subject",
                ),
                ProviderSuggestion::candidate_meaning(
                    weaver,
                    "swimming-action-weaver",
                    "SwimmingAction",
                    MeaningKind::Action,
                    0.8,
                    "fish and swim cohere as subject-action relation",
                ),
            ],
        )),
    ]
}

pub fn time_flies_providers() -> Vec<Box<dyn ProviderAdapter>> {
    let support = MockProvider::provenance_for("mock-support");
    let objector = MockProvider::provenance_for("mock-objector");
    let answer = MockProvider::provenance_for("mock-answer");
    let faculty = MockProvider::provenance_for("mock-support-faculty");
    let target_ref = "meaning:TimeFliesAssertion";

    vec![
        Box::new(MockProvider::new(
            "mock-support",
            vec![ProviderSuggestion::candidate_meaning(
                support,
                "time-flies-assertion-support",
                "TimeFliesAssertion",
                MeaningKind::Reference,
                0.63,
                "one reading treats the sentence as an idiomatic assertion about time passing",
            )],
        )),
        Box::new(MockProvider::new(
            "mock-objector",
            vec![ProviderSuggestion::objection_with_class(
                objector,
                "time-flies-role-objection",
                target_ref,
                "role_conflict",
                "time and flies each carry plausible competing noun or verb roles",
            )],
        )),
        Box::new(MockProvider::new(
            "mock-answer",
            vec![ProviderSuggestion::answer_with_kind(
                answer,
                "time-flies-role-answer",
                target_ref,
                "narrows",
                "the idiomatic reading is plausible but does not eliminate the role conflict",
            )],
        )),
        Box::new(MockProvider::new(
            "mock-support-faculty",
            vec![ProviderSuggestion::faculty_report(
                faculty,
                "time-flies-support-faculty-report",
                target_ref,
                ProviderFacultyReport {
                    run_id: "faculty-run:time-flies-support".to_string(),
                    target_ref: target_ref.to_string(),
                    votes: vec![
                        ProviderFacultyVote {
                            faculty: Faculty::Observer,
                            result: FacultyResult::Approve,
                            perspective: HemispherePerspective::LeftAnalytic,
                            rationale: "idiomatic assertion is present as one candidate reading"
                                .to_string(),
                        },
                        ProviderFacultyVote {
                            faculty: Faculty::Honesty,
                            result: FacultyResult::NeedsMoreEvidence,
                            perspective: HemispherePerspective::Integrated,
                            rationale: "role ambiguity remains after the supporting reading"
                                .to_string(),
                        },
                        ProviderFacultyVote {
                            faculty: Faculty::Weaver,
                            result: FacultyResult::NeedsMoreEvidence,
                            perspective: HemispherePerspective::RightAssociative,
                            rationale: "the idiom coheres, but literal grammar remains competitive"
                                .to_string(),
                        },
                    ],
                    vetoes: Vec::new(),
                    convergence_score: 0.46,
                    convergence_statement:
                        "supporting provider finds partial convergence, not stabilization"
                            .to_string(),
                },
            )],
        )),
    ]
}

pub fn design_compiler_providers() -> Vec<Box<dyn ProviderAdapter>> {
    let observer = MockProvider::provenance_for("mock-design-observer");

    vec![Box::new(MockProvider::new(
        "mock-design-observer",
        vec![
            ProviderSuggestion::candidate_meaning(
                observer.clone(),
                "design-action-provider",
                "DesignAction",
                MeaningKind::Action,
                0.76,
                "design is present as an imperative action",
            ),
            ProviderSuggestion::candidate_meaning(
                observer.clone(),
                "compiler-concept-provider",
                "CompilerConcept",
                MeaningKind::Reference,
                0.72,
                "compiler is present as the design target",
            ),
            ProviderSuggestion::candidate_meaning(
                observer,
                "fpga-hardware-constraint-provider",
                "FpgaHardwareConstraint",
                MeaningKind::Constraint,
                0.74,
                "for FPGA hardware constrains the compiler design target",
            ),
        ],
    ))]
}

pub fn missing_lineage_workspace() -> EvidenceWorkspace {
    let mut workspace = EvidenceWorkspace::from_text("fixture-missing-lineage", "Unsupported");
    let candidate_id = "meaning:UnsupportedClaim".to_string();
    let support_id = "support:manual:unsupported-claim".to_string();

    workspace.support_records.push(SupportRecord {
        id: support_id.clone(),
        target_ref: candidate_id.clone(),
        support_weight: 0.99,
        source_ref: "manual-fixture".to_string(),
        rationale: "high support is intentionally paired with absent lineage".to_string(),
    });
    workspace.candidate_meanings.push(CandidateMeaning {
        id: candidate_id,
        kind: MeaningKind::Reference,
        label: "UnsupportedClaim".to_string(),
        token_refs: Vec::new(),
        support_record_ids: vec![support_id],
        contradiction_record_ids: Vec::new(),
        lineage: LineageRecord::empty("fixture candidate has no provenance"),
    });

    workspace
}
