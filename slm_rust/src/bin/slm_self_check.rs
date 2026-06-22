use slm_rust::core::{EvidenceSource, GrammarRole};
use slm_rust::fixtures::{fish_swim_providers, time_flies_providers};
use slm_rust::graph::RelationKind;
use slm_rust::lexicon::{LexicalSubstrate, LexicalSubstrateProvider};
use slm_rust::providers::ProviderAdapter;
use slm_rust::stabilization::{DecisionOutcome, Faculty, Stabilizer};

fn main() {
    fish_swim_stabilizes_compact_graph();
    time_flies_preserves_provider_disagreement_as_uncertainty();
    honesty_veto_blocks_missing_lineage_even_with_support();
    primer_contains_machine_json_and_compact_evidence();
    file_lexicon_reads_closed_class_and_wordnet_entries();
    lexicon_provider_injects_authority_grammar_evidence();
    lexical_substrate_creates_hints_spans_and_senses();
    println!("slm_self_check: ok");
}

fn fish_swim_stabilizes_compact_graph() {
    let providers = fish_swim_providers();
    let refs = providers
        .iter()
        .map(|provider| provider.as_ref())
        .collect::<Vec<_>>();

    let result = slm_rust::analyze_with_providers("fixture-fish", "The fish swim.", &refs);

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

fn time_flies_preserves_provider_disagreement_as_uncertainty() {
    let providers = time_flies_providers();
    let refs = providers
        .iter()
        .map(|provider| provider.as_ref())
        .collect::<Vec<_>>();

    let result =
        slm_rust::analyze_with_providers("fixture-time", "Time flies like an arrow.", &refs);

    assert!(!result.graph.has_glyph_label("TimeFliesAssertion"));
    assert!(result.graph.uncertainties.iter().any(|uncertainty| {
        uncertainty
            .boundary_statement
            .contains("provider disagreement")
    }));
    assert!(result.wobble.dimensions.unresolved_ambiguity > 0.0);
    assert!(!result.workspace.provider_deliberations.is_empty());
    assert!(
        result
            .workspace
            .provider_deliberations
            .iter()
            .any(|deliberation| !deliberation.faculty_report_refs.is_empty())
    );
    assert!(result.primer.compact_evidence.iter().any(|evidence| {
        evidence.kind == "provider_suggestion" && evidence.id == "time-flies-support-faculty-report"
    }));
}

fn honesty_veto_blocks_missing_lineage_even_with_support() {
    let mut workspace = slm_rust::fixtures::missing_lineage_workspace();
    let diffusion = slm_rust::diffusion::DiffusionEngine::default().run(&mut workspace);
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

fn primer_contains_machine_json_and_compact_evidence() {
    let providers = fish_swim_providers();
    let refs = providers
        .iter()
        .map(|provider| provider.as_ref())
        .collect::<Vec<_>>();
    let result = slm_rust::analyze_with_providers("fixture-primer", "The fish swim.", &refs);

    let json = result.primer.to_json_string().expect("primer serializes");

    assert!(json.contains("\"compact_evidence\""));
    assert!(json.contains("\"schema\""));
    assert_eq!(result.primer.schema.schema_id, "slm_primer");
    assert!(!result.primer.compact_evidence.is_empty());
    assert!(result.primer.sop_rendering.contains("FishConcept"));
}

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

fn lexicon_provider_injects_authority_grammar_evidence() {
    let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
    let mut workspace =
        slm_rust::evidence::EvidenceWorkspace::from_text("lexicon-fixture", "Design quickly.");
    let suggestions = provider.suggestions(&workspace.input_text, &workspace.tokens);
    workspace.ingest_provider_suggestions(suggestions);

    assert!(workspace.grammar_candidates.iter().any(|candidate| {
        candidate.role == GrammarRole::Adverb
            && candidate.source == EvidenceSource::LexicalAuthority
    }));
}

fn lexical_substrate_creates_hints_spans_and_senses() {
    let provider = LexicalSubstrateProvider::open_default().expect("substrate provider opens");
    let mut providers: Vec<Box<dyn ProviderAdapter>> = vec![Box::new(provider)];
    providers.extend(slm_rust::fixtures::design_compiler_providers());
    let refs = providers
        .iter()
        .map(|provider| provider.as_ref())
        .collect::<Vec<_>>();
    let result = slm_rust::analyze_with_providers(
        "fixture-substrate",
        "Design a compiler for FPGA hardware.",
        &refs,
    );

    assert!(
        result
            .workspace
            .structural_hints
            .iter()
            .any(|hint| hint.class == "preposition")
    );
    assert!(
        result
            .workspace
            .span_candidates
            .iter()
            .any(|span| span.normalized_text == "fpga hardware")
    );
    assert!(
        result
            .workspace
            .lexical_sense_candidates
            .iter()
            .any(|sense| sense.lemma.eq_ignore_ascii_case("compiler"))
    );
    assert!(result.wobble.dimensions.sense_instability > 0.0);
}
