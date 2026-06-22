//! Rust target projection for the Semantic Logic Model prototype.
//!
//! The language-independent authority for this crate lives in the SOP artifacts
//! under `slm_project/specifications`. The Rust code below is a deterministic
//! v0 projection of those contracts: observations and evidence stay outside the
//! graph, diffusion works over an evidence workspace, and only stabilized
//! meaning or bounded uncertainty enters the semantic graph.

pub mod core;
pub mod deliberation;
pub mod diffusion;
pub mod evidence;
pub mod fixtures;
pub mod graph;
pub mod lexicon;
pub mod primer;
pub mod providers;
pub mod rules;
pub mod sidecar;
pub mod stabilization;
pub mod wobble;

use crate::diffusion::DiffusionEngine;
use crate::evidence::EvidenceWorkspace;
use crate::graph::SemanticGraph;
use crate::primer::SlmPrimer;
use crate::providers::ProviderAdapter;
use crate::stabilization::Stabilizer;
use crate::wobble::WobbleVector;

/// End-to-end deterministic analysis result.
#[derive(Debug, Clone)]
pub struct AnalysisResult {
    pub workspace: EvidenceWorkspace,
    pub wobble: WobbleVector,
    pub graph: SemanticGraph,
    pub primer: SlmPrimer,
}

/// Run the v0 SLM pipeline with explicit lower-provider evidence.
pub fn analyze_with_providers(
    input_id: impl Into<String>,
    text: impl Into<String>,
    providers: &[&dyn ProviderAdapter],
) -> AnalysisResult {
    let mut workspace = EvidenceWorkspace::from_text(input_id, text);
    for provider in providers {
        workspace.ingest_provider_suggestions(
            provider.suggestions(&workspace.input_text, &workspace.tokens),
        );
    }

    let diffusion = DiffusionEngine::default().run(&mut workspace);
    let decisions = Stabilizer::default().decide(&workspace, &diffusion);
    let graph = SemanticGraph::from_decisions(&workspace, &diffusion, &decisions);
    let wobble = workspace
        .wobble_vectors
        .last()
        .cloned()
        .unwrap_or_else(|| WobbleVector::measure(&workspace));
    let primer = SlmPrimer::from_graph(&workspace, &graph, &wobble);

    AnalysisResult {
        workspace,
        wobble,
        graph,
        primer,
    }
}

#[cfg(test)]
mod tests {
    use super::analyze_with_providers;
    use crate::core::{ContradictionStatus, Severity};
    use crate::fixtures::{fish_swim_providers, time_flies_providers};
    use crate::graph::RelationKind;
    use crate::lexicon::LexicalSubstrateProvider;
    use crate::primer::{
        SLM_PRIMER_COMPATIBILITY_FLOOR, SLM_PRIMER_LEGACY_VERSION, SLM_PRIMER_SCHEMA_ID,
        SLM_PRIMER_SCHEMA_VERSION, normalize_evidence_ref,
    };
    use crate::stabilization::{DecisionOutcome, Faculty, Stabilizer};
    use crate::wobble::{WobbleDimensions, WobbleFactor, WobbleRoute, WobbleVector};

    #[test]
    fn fish_swim_stabilizes_compact_graph() {
        let providers = fish_swim_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();

        let result = analyze_with_providers("fixture-fish", "The fish swim.", &refs);

        assert!(result.graph.has_glyph_label("FishConcept"));
        assert!(result.graph.has_glyph_label("SwimmingAction"));
        assert!(
            result
                .graph
                .relations
                .iter()
                .any(|relation| relation.kind == RelationKind::Performs)
        );
        assert!(
            result
                .workspace
                .candidate_meanings
                .iter()
                .any(|candidate| candidate.label == "FishConcept")
        );
        assert!(result.wobble.aggregate_score < 0.5);
    }

    #[test]
    fn time_flies_preserves_provider_disagreement_as_uncertainty() {
        let providers = time_flies_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();

        let result = analyze_with_providers("fixture-time", "Time flies like an arrow.", &refs);

        assert!(!result.graph.has_glyph_label("TimeFliesAssertion"));
        assert!(result.graph.uncertainties.iter().any(|uncertainty| {
            uncertainty
                .boundary_statement
                .contains("provider disagreement")
        }));
        assert!(result.wobble.dimensions.unresolved_ambiguity > 0.0);
        assert!(!result.workspace.provider_deliberations.is_empty());
    }

    #[test]
    fn time_flies_contradiction_cites_answer_jury_and_unresolved_status() {
        let providers = time_flies_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();

        let result = analyze_with_providers(
            "fixture-time-contradiction",
            "Time flies like an arrow.",
            &refs,
        );
        let contradiction = result
            .workspace
            .contradiction_records
            .iter()
            .find(|contradiction| contradiction.target_ref == "meaning:TimeFliesAssertion")
            .expect("TimeFlies contradiction exists");

        assert_eq!(contradiction.severity, Severity::High);
        assert_eq!(contradiction.status, ContradictionStatus::Unresolved);
        assert_eq!(
            contradiction.answer_ref.as_deref(),
            Some("answer:time-flies-role-answer")
        );
        assert_eq!(
            contradiction.jury_review_ref.as_deref(),
            Some("jury:time-flies-role-objection")
        );
        assert!(
            contradiction
                .provider_deliberation_ref
                .as_deref()
                .unwrap_or_default()
                .starts_with("deliberation:")
        );
        assert!(
            contradiction
                .cited_panel_refs
                .iter()
                .any(|evidence_ref| { evidence_ref == "time-flies-support-faculty-report" })
        );
        assert!(result.primer.compact_evidence.iter().any(|item| {
            item.kind == "contradiction"
                && item
                    .refs
                    .iter()
                    .any(|evidence_ref| evidence_ref == "jury:time-flies-role-objection")
        }));
    }

    #[test]
    fn honesty_veto_blocks_missing_lineage_even_with_support() {
        let mut workspace = crate::fixtures::missing_lineage_workspace();
        let diffusion = crate::diffusion::DiffusionEngine::default().run(&mut workspace);
        let decisions = Stabilizer::default().decide(&workspace, &diffusion);

        assert!(decisions.iter().any(|decision| {
            decision.outcome == DecisionOutcome::PreserveInEvidenceWorkspace
                && decision
                    .faculty_run
                    .vetoes
                    .iter()
                    .any(|veto| veto.faculty == Faculty::Honesty)
        }));
    }

    #[test]
    fn primer_contains_machine_json_and_compact_evidence() {
        let providers = fish_swim_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        let result = analyze_with_providers("fixture-primer", "The fish swim.", &refs);

        let json = result.primer.to_json_string().expect("primer serializes");

        assert!(json.contains("\"compact_evidence\""));
        assert!(!result.primer.compact_evidence.is_empty());
        assert!(result.primer.sop_rendering.contains("FishConcept"));
    }

    #[test]
    fn primer_exposes_versioned_schema_contract() {
        let providers = fish_swim_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        let result = analyze_with_providers("fixture-schema", "The fish swim.", &refs);
        let primer_json: serde_json::Value =
            serde_json::from_str(&result.primer.to_json_string().expect("primer serializes"))
                .expect("primer JSON parses");

        assert_eq!(result.primer.version, SLM_PRIMER_LEGACY_VERSION);
        assert_eq!(result.primer.schema.schema_id, SLM_PRIMER_SCHEMA_ID);
        assert_eq!(
            result.primer.schema.schema_version,
            SLM_PRIMER_SCHEMA_VERSION
        );
        assert_eq!(
            result.primer.schema.compatibility_floor,
            SLM_PRIMER_COMPATIBILITY_FLOOR
        );
        for field in &result.primer.schema.required_fields {
            assert!(
                primer_json.get(field).is_some(),
                "required primer field {field} is present"
            );
        }
        assert!(
            result
                .primer
                .schema
                .required_fields
                .contains(&"compact_evidence".to_string())
        );
        assert!(
            result
                .primer
                .schema
                .compatibility_notes
                .iter()
                .any(|note| note.contains("schema_version"))
        );
    }

    #[test]
    fn primer_compaction_reports_omitted_verbose_evidence() {
        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();

        let result = analyze_with_providers(
            "fixture-primer-budget",
            "Design a compiler for FPGA hardware.",
            &refs,
        );
        let primer_sense_count = result
            .primer
            .compact_evidence
            .iter()
            .filter(|item| item.kind == "lexical_sense")
            .count();

        assert!(
            primer_sense_count < result.workspace.lexical_sense_candidates.len(),
            "primer should compact verbose lexical sense evidence"
        );
        assert!(
            result
                .primer
                .compaction
                .omitted_by_kind
                .iter()
                .any(|omission| omission.kind == "lexical_sense" && omission.omitted_count > 0)
        );
        assert!(
            result
                .primer
                .compact_evidence
                .iter()
                .any(|item| item.kind == "tokens")
        );
        assert!(
            result
                .primer
                .compact_evidence
                .iter()
                .any(|item| item.kind == "wobble")
        );
    }

    #[test]
    fn primer_refs_are_normalized_for_reingestion() {
        assert_eq!(
            normalize_evidence_ref("article scopes nominal span"),
            "source_note:article_scopes_nominal_span"
        );
        assert_eq!(
            normalize_evidence_ref("oewn-06585776-n"),
            "synset:oewn-06585776-n"
        );
        assert_eq!(
            normalize_evidence_ref("compiler-concept-provider"),
            "provider:compiler-concept-provider"
        );

        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();

        let result = analyze_with_providers(
            "fixture-provenance",
            "Design a compiler for FPGA hardware.",
            &refs,
        );

        for item in &result.primer.compact_evidence {
            for evidence_ref in &item.refs {
                let (namespace, source_identity) = evidence_ref
                    .split_once(':')
                    .expect("primer evidence ref has namespace separator");
                assert!(!namespace.is_empty());
                assert!(!source_identity.is_empty());
                assert!(!evidence_ref.chars().any(char::is_whitespace));
            }
        }
    }

    #[test]
    fn support_propagation_is_idempotent_across_repeated_diffusion_runs() {
        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let mut workspace = crate::evidence::EvidenceWorkspace::from_text(
            "fixture-idempotence",
            "Design a compiler for FPGA hardware.",
        );

        for provider in &providers {
            workspace.ingest_provider_suggestions(
                provider.suggestions(&workspace.input_text, &workspace.tokens),
            );
        }

        let engine = crate::diffusion::DiffusionEngine::default();
        engine.run(&mut workspace);
        let support_ids_after_first = sorted_support_ids(&workspace);
        let relation_ids_after_first = sorted_relation_ids(&workspace);

        engine.run(&mut workspace);
        let support_ids_after_second = sorted_support_ids(&workspace);
        let relation_ids_after_second = sorted_relation_ids(&workspace);

        assert_eq!(support_ids_after_first, support_ids_after_second);
        assert_eq!(relation_ids_after_first, relation_ids_after_second);
    }

    fn sorted_support_ids(workspace: &crate::evidence::EvidenceWorkspace) -> Vec<String> {
        let mut ids = workspace
            .support_records
            .iter()
            .map(|support| support.id.clone())
            .collect::<Vec<_>>();
        ids.sort();
        ids
    }

    #[test]
    fn primer_wobble_contains_local_factor_attribution() {
        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        let design_result = analyze_with_providers(
            "fixture-wobble-design",
            "Design a compiler for FPGA hardware.",
            &refs,
        );

        assert!(design_result.primer.wobble.factors.iter().any(|factor| {
            factor.dimension == "sense_instability"
                && factor.target_kind == "token"
                && factor.target_ref.starts_with("tok:")
                && factor.explanation.contains("lexical sense candidates")
        }));
        assert!(
            design_result
                .primer
                .compact_evidence
                .iter()
                .find(|item| item.kind == "wobble")
                .expect("wobble compact evidence item exists")
                .refs
                .iter()
                .any(|evidence_ref| evidence_ref.starts_with("wobble_factor:"))
        );

        let providers = time_flies_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        let time_result =
            analyze_with_providers("fixture-wobble-time", "Time flies like an arrow.", &refs);

        assert!(time_result.primer.wobble.factors.iter().any(|factor| {
            factor.dimension == "relation_instability"
                && factor.target_kind == "meaning"
                && factor.explanation.contains("provider disagreement")
        }));
    }

    #[test]
    fn imperative_subject_is_preserved_as_uncertainty() {
        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();

        let result = analyze_with_providers(
            "fixture-imperative",
            "Design a compiler for FPGA hardware.",
            &refs,
        );

        assert!(
            !result
                .primer
                .subjects
                .iter()
                .any(|subject| subject.label == "CompilerConcept")
        );
        assert!(result.graph.glyphs.iter().any(|glyph| {
            glyph.label == "CompilerConcept" && glyph.kind != crate::graph::GlyphKind::Subject
        }));
        assert!(result.graph.uncertainties.iter().any(|uncertainty| {
            uncertainty.uncertainty_type == crate::graph::UncertaintyType::UnresolvedSubjectBoundary
                && uncertainty.boundary_statement.contains("implied actor")
                && uncertainty
                    .candidate_set
                    .iter()
                    .any(|candidate| candidate == "implied_actor:command_executor")
        }));
        assert!(result.primer.uncertainty.iter().any(|uncertainty| {
            uncertainty.uncertainty_type == crate::graph::UncertaintyType::UnresolvedSubjectBoundary
        }));
        assert!(result.primer.wobble.factors.iter().any(|factor| {
            factor.dimension == "subject_boundary_instability"
                && factor.target_ref == "meaning:DesignAction"
                && factor.explanation.contains("implied actor")
        }));
    }

    #[test]
    fn graph_relations_cite_candidate_and_endpoint_decisions() {
        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();

        let result = analyze_with_providers(
            "fixture-relation-audit",
            "Design a compiler for FPGA hardware.",
            &refs,
        );
        let relation = result
            .graph
            .relations
            .iter()
            .find(|relation| relation.kind == RelationKind::ActsOn)
            .expect("acts_on relation exists");

        assert!(
            relation
                .candidate_relation_ref
                .starts_with("candidate_relation:DesignAction:CompilerConcept")
        );
        assert!(
            relation
                .endpoint_decision_refs
                .contains(&"decision:meaning:DesignAction".to_string())
        );
        assert!(
            relation
                .endpoint_decision_refs
                .contains(&"decision:meaning:CompilerConcept".to_string())
        );
        assert!(
            relation
                .lineage
                .transform_refs
                .contains(&relation.candidate_relation_ref)
        );
        for decision_ref in &relation.endpoint_decision_refs {
            assert!(relation.lineage.transform_refs.contains(decision_ref));
        }

        let primer_relation = result
            .primer
            .relations
            .iter()
            .find(|relation| relation.kind == RelationKind::ActsOn)
            .expect("acts_on primer relation exists");
        assert!(
            primer_relation
                .candidate_relation_ref
                .starts_with("candidate_relation:")
        );
        assert_eq!(primer_relation.endpoint_decision_refs.len(), 2);
    }

    #[test]
    fn uncertainty_boundaries_are_type_specific() {
        let mut role_workspace =
            crate::evidence::EvidenceWorkspace::from_text("fixture-role-boundary", "Fish");
        let role_diffusion = crate::diffusion::DiffusionEngine::default().run(&mut role_workspace);
        let role_decisions = Stabilizer::default().decide(&role_workspace, &role_diffusion);
        let role_graph = crate::graph::SemanticGraph::from_decisions(
            &role_workspace,
            &role_diffusion,
            &role_decisions,
        );
        assert!(role_graph.uncertainties.iter().any(|uncertainty| {
            uncertainty.uncertainty_type == crate::graph::UncertaintyType::UnresolvedRole
                && uncertainty.candidate_set.len() == 2
                && uncertainty
                    .candidate_set
                    .iter()
                    .all(|candidate| candidate.starts_with("grammar:"))
        }));

        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        let design_result = analyze_with_providers(
            "fixture-uncertainty-boundaries",
            "Design a compiler for FPGA hardware.",
            &refs,
        );
        assert!(design_result.graph.uncertainties.iter().any(|uncertainty| {
            uncertainty.uncertainty_type == crate::graph::UncertaintyType::UnresolvedSubjectBoundary
                && uncertainty
                    .candidate_set
                    .iter()
                    .any(|candidate| candidate.starts_with("implied_actor:"))
        }));
        assert!(design_result.graph.uncertainties.iter().any(|uncertainty| {
            uncertainty.uncertainty_type == crate::graph::UncertaintyType::UnresolvedScope
                && uncertainty
                    .candidate_set
                    .iter()
                    .any(|candidate| candidate.starts_with("candidate_relation:"))
        }));

        let providers = time_flies_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        let time_result = analyze_with_providers(
            "fixture-provider-boundary",
            "Time flies like an arrow.",
            &refs,
        );
        assert!(time_result.graph.uncertainties.iter().any(|uncertainty| {
            uncertainty.uncertainty_type == crate::graph::UncertaintyType::ProviderDisagreement
                && uncertainty
                    .boundary_statement
                    .contains("provider disagreement")
        }));
    }

    #[test]
    fn wobble_routing_uses_dimensions_and_factor_refs() {
        let wobble = WobbleVector {
            aggregate_score: 0.12,
            dimensions: WobbleDimensions {
                contradiction: 0.75,
                ..WobbleDimensions::default()
            },
            factors: vec![WobbleFactor {
                id: "wobble_factor:contradiction:0".to_string(),
                dimension: "contradiction".to_string(),
                target_kind: "meaning".to_string(),
                target_ref: "meaning:UnsafeClaim".to_string(),
                score: 0.75,
                explanation: "blocking contradiction remains".to_string(),
            }],
        };
        let decision = wobble.routing_decision();
        assert_eq!(decision.route, WobbleRoute::RouteToDeliberation);
        assert_eq!(
            decision.factor_refs,
            vec!["wobble_factor:contradiction:0".to_string()]
        );

        let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
        let mut providers = vec![Box::new(provider) as Box<dyn crate::providers::ProviderAdapter>];
        providers.extend(crate::fixtures::design_compiler_providers());
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        let design_result = analyze_with_providers(
            "fixture-wobble-route",
            "Design a compiler for FPGA hardware.",
            &refs,
        );

        assert_eq!(
            design_result.primer.wobble.routing_decision.route,
            WobbleRoute::SeekSidecar
        );
        assert!(
            design_result
                .primer
                .wobble
                .routing_decision
                .dimension_refs
                .iter()
                .any(|dimension| dimension == "wobble_dimension:subject_boundary_instability")
        );
        assert_eq!(
            design_result.primer.wobble.routing_hint,
            "seek_sidecar".to_string()
        );
    }

    fn sorted_relation_ids(workspace: &crate::evidence::EvidenceWorkspace) -> Vec<String> {
        let mut ids = workspace
            .candidate_relations
            .iter()
            .map(|relation| relation.id.clone())
            .collect::<Vec<_>>();
        ids.sort();
        ids
    }
}
