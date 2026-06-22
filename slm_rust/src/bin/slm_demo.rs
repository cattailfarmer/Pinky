use serde::Serialize;

use slm_rust::AnalysisResult;
use slm_rust::core::{
    EvidenceSource, GrammarRole, LexicalSenseCandidate, SpanCandidate, StructuralHint, Token,
};
use slm_rust::diffusion::DiffusionPassTrace;
use slm_rust::fixtures::{design_compiler_providers, fish_swim_providers, time_flies_providers};
use slm_rust::graph::{GlyphKind, RelationKind, SemanticGraph, UncertaintyType};
use slm_rust::lexicon::LexicalSubstrateProvider;
use slm_rust::primer::{PrimerSchemaInfo, SlmPrimer};
use slm_rust::providers::ProviderAdapter;
use slm_rust::wobble::{WobbleDimensions, WobbleRoutingDecision};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum DemoOutputMode {
    Full,
    Compact,
    PrimerOnly,
    Sop,
}

impl DemoOutputMode {
    fn parse(value: &str) -> Result<Self, String> {
        match value {
            "full" => Ok(Self::Full),
            "compact" => Ok(Self::Compact),
            "primer" | "primer-only" => Ok(Self::PrimerOnly),
            "sop" => Ok(Self::Sop),
            _ => Err(format!(
                "unknown demo output mode '{value}'; expected full, compact, primer-only, or sop"
            )),
        }
    }

    fn as_str(self) -> &'static str {
        match self {
            Self::Full => "full",
            Self::Compact => "compact",
            Self::PrimerOnly => "primer-only",
            Self::Sop => "sop",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct DemoArgs {
    mode: DemoOutputMode,
    input: String,
}

#[derive(Debug, Clone, Serialize)]
struct CandidateRoleView {
    token_id: String,
    token_text: String,
    role: GrammarRole,
    support_activation: f32,
    source: EvidenceSource,
}

#[derive(Debug, Clone, Serialize)]
struct StructuralRelationHint {
    relation_id: String,
    kind: RelationKind,
    source_label: String,
    target_label: String,
    rationale: String,
}

#[derive(Debug, Serialize)]
struct DemoReport<'a> {
    input: &'a str,
    tokens: &'a [Token],
    candidate_roles: Vec<CandidateRoleView>,
    closed_class_structural_hints: &'a [StructuralHint],
    span_candidates: &'a [SpanCandidate],
    lexical_sense_candidates: &'a [LexicalSenseCandidate],
    structural_relation_hints: Vec<StructuralRelationHint>,
    diffusion_trace: &'a [DiffusionPassTrace],
    progressively_refined_semantic_graph: &'a SemanticGraph,
    wobble_score: f32,
    wobble_vector: &'a WobbleDimensions,
    final_slm_primer: &'a SlmPrimer,
}

#[derive(Debug, Serialize)]
struct CompactGlyphView {
    semantic_id: String,
    label: String,
    kind: GlyphKind,
}

#[derive(Debug, Serialize)]
struct CompactRelationView {
    relation_id: String,
    kind: RelationKind,
    source_glyph: String,
    target_glyph: String,
}

#[derive(Debug, Serialize)]
struct CompactUncertaintyView {
    semantic_id: String,
    uncertainty_type: UncertaintyType,
    boundary_statement: String,
}

#[derive(Debug, Serialize)]
struct CompactGraphView {
    glyphs: Vec<CompactGlyphView>,
    relations: Vec<CompactRelationView>,
    uncertainties: Vec<CompactUncertaintyView>,
}

#[derive(Debug, Serialize)]
struct CompactDemoReport<'a> {
    input: &'a str,
    output_mode: &'static str,
    token_surfaces: Vec<String>,
    candidate_role_count: usize,
    structural_hint_count: usize,
    span_candidate_count: usize,
    lexical_sense_candidate_count: usize,
    graph_summary: CompactGraphView,
    wobble_score: f32,
    wobble_route: &'static str,
    wobble_reason: String,
    primer_schema: &'a PrimerSchemaInfo,
    compact_evidence_count: usize,
    compaction_omitted_item_count: usize,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_demo_args(std::env::args().skip(1))
        .map_err(|message| std::io::Error::new(std::io::ErrorKind::InvalidInput, message))?;
    let input = args.input;

    let providers = providers_for(&input);
    let provider_refs = providers
        .iter()
        .map(|provider| provider.as_ref())
        .collect::<Vec<_>>();
    let result = slm_rust::analyze_with_providers("demo-input", &input, &provider_refs);

    println!("{}", render_demo_output(args.mode, &input, &result)?);
    Ok(())
}

fn parse_demo_args<I>(args: I) -> Result<DemoArgs, String>
where
    I: IntoIterator,
    I::Item: Into<String>,
{
    let mut mode = DemoOutputMode::Full;
    let mut input_parts = Vec::new();
    let mut iter = args.into_iter().map(Into::into).peekable();

    while let Some(arg) = iter.next() {
        if arg == "--mode" {
            let Some(value) = iter.next() else {
                return Err("--mode requires a value".to_string());
            };
            mode = DemoOutputMode::parse(&value)?;
        } else if let Some(value) = arg.strip_prefix("--mode=") {
            mode = DemoOutputMode::parse(value)?;
        } else if arg.starts_with("--") {
            return Err(format!("unknown argument '{arg}'"));
        } else {
            input_parts.push(arg);
        }
    }

    let input = input_parts.join(" ").trim().to_string();
    let input = if input.is_empty() {
        "Design a compiler for FPGA hardware.".to_string()
    } else {
        input
    };

    Ok(DemoArgs { mode, input })
}

fn render_demo_output(
    mode: DemoOutputMode,
    input: &str,
    result: &AnalysisResult,
) -> serde_json::Result<String> {
    match mode {
        DemoOutputMode::Full => render_full_report(input, result),
        DemoOutputMode::Compact => render_compact_report(input, result),
        DemoOutputMode::PrimerOnly => result.primer.to_json_string(),
        DemoOutputMode::Sop => Ok(result.primer.sop_rendering.clone()),
    }
}

fn render_full_report(input: &str, result: &AnalysisResult) -> serde_json::Result<String> {
    let report = DemoReport {
        input,
        tokens: &result.workspace.tokens,
        candidate_roles: result
            .workspace
            .grammar_candidates
            .iter()
            .map(|candidate| {
                let token_text = result
                    .workspace
                    .tokens
                    .iter()
                    .find(|token| token.id == candidate.token_id)
                    .map(|token| token.surface_text.clone())
                    .unwrap_or_else(|| "<unknown>".to_string());
                CandidateRoleView {
                    token_id: candidate.token_id.clone(),
                    token_text,
                    role: candidate.role,
                    support_activation: candidate.support_weight,
                    source: candidate.source,
                }
            })
            .collect(),
        closed_class_structural_hints: &result.workspace.structural_hints,
        span_candidates: &result.workspace.span_candidates,
        lexical_sense_candidates: &result.workspace.lexical_sense_candidates,
        structural_relation_hints: result
            .workspace
            .candidate_relations
            .iter()
            .map(|relation| StructuralRelationHint {
                relation_id: relation.id.clone(),
                kind: relation.relation_kind,
                source_label: relation.source_label.clone(),
                target_label: relation.target_label.clone(),
                rationale: relation.lineage.note.clone(),
            })
            .collect(),
        diffusion_trace: &result.workspace.pass_traces,
        progressively_refined_semantic_graph: &result.graph,
        wobble_score: result.wobble.aggregate_score,
        wobble_vector: &result.wobble.dimensions,
        final_slm_primer: &result.primer,
    };

    serde_json::to_string_pretty(&report)
}

fn render_compact_report(input: &str, result: &AnalysisResult) -> serde_json::Result<String> {
    let routing_decision: WobbleRoutingDecision = result.wobble.routing_decision();
    let report = CompactDemoReport {
        input,
        output_mode: DemoOutputMode::Compact.as_str(),
        token_surfaces: result
            .workspace
            .tokens
            .iter()
            .map(|token| token.surface_text.clone())
            .collect(),
        candidate_role_count: result.workspace.grammar_candidates.len(),
        structural_hint_count: result.workspace.structural_hints.len(),
        span_candidate_count: result.workspace.span_candidates.len(),
        lexical_sense_candidate_count: result.workspace.lexical_sense_candidates.len(),
        graph_summary: compact_graph_view(result),
        wobble_score: result.wobble.aggregate_score,
        wobble_route: routing_decision.route.as_str(),
        wobble_reason: routing_decision.reason,
        primer_schema: &result.primer.schema,
        compact_evidence_count: result.primer.compact_evidence.len(),
        compaction_omitted_item_count: result.primer.compaction.omitted_item_count,
    };

    serde_json::to_string_pretty(&report)
}

fn compact_graph_view(result: &AnalysisResult) -> CompactGraphView {
    CompactGraphView {
        glyphs: result
            .graph
            .glyphs
            .iter()
            .map(|glyph| CompactGlyphView {
                semantic_id: glyph.semantic_id.clone(),
                label: glyph.label.clone(),
                kind: glyph.kind,
            })
            .collect(),
        relations: result
            .graph
            .relations
            .iter()
            .map(|relation| CompactRelationView {
                relation_id: relation.relation_id.clone(),
                kind: relation.kind,
                source_glyph: relation.source_glyph.clone(),
                target_glyph: relation.target_glyph.clone(),
            })
            .collect(),
        uncertainties: result
            .graph
            .uncertainties
            .iter()
            .map(|uncertainty| CompactUncertaintyView {
                semantic_id: uncertainty.semantic_id.clone(),
                uncertainty_type: uncertainty.uncertainty_type,
                boundary_statement: uncertainty.boundary_statement.clone(),
            })
            .collect(),
    }
}

fn providers_for(input: &str) -> Vec<Box<dyn ProviderAdapter>> {
    let providers = match input {
        "The fish swim." => fish_swim_providers(),
        "Time flies like an arrow." => time_flies_providers(),
        _ => design_compiler_providers(),
    };
    with_lexicon_provider(providers)
}

fn with_lexicon_provider(
    mut providers: Vec<Box<dyn ProviderAdapter>>,
) -> Vec<Box<dyn ProviderAdapter>> {
    if let Ok(provider) = LexicalSubstrateProvider::open_default() {
        providers.insert(0, Box::new(provider));
    }
    providers
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_demo_output_modes_and_preserves_input_text() {
        let args = parse_demo_args([
            "--mode=compact",
            "Design",
            "a",
            "compiler",
            "for",
            "FPGA",
            "hardware.",
        ])
        .expect("compact args parse");

        assert_eq!(args.mode, DemoOutputMode::Compact);
        assert_eq!(args.input, "Design a compiler for FPGA hardware.");

        let args = parse_demo_args(["--mode", "primer", "The", "fish", "swim."])
            .expect("primer alias parses");
        assert_eq!(args.mode, DemoOutputMode::PrimerOnly);
        assert_eq!(args.input, "The fish swim.");

        assert!(parse_demo_args(["--mode", "wide"]).is_err());
    }

    #[test]
    fn compact_mode_omits_full_evidence_arrays() {
        let result = fixture_result();
        let output = render_demo_output(DemoOutputMode::Compact, "The fish swim.", &result)
            .expect("compact output renders");
        let json: serde_json::Value =
            serde_json::from_str(&output).expect("compact output is JSON");

        assert_eq!(json["output_mode"], "compact");
        assert!(json.get("primer_schema").is_some());
        assert!(json.get("lexical_sense_candidate_count").is_some());
        assert!(json.get("graph_summary").is_some());
        assert!(json.get("lexical_sense_candidates").is_none());
        assert!(json.get("diffusion_trace").is_none());
    }

    #[test]
    fn primer_and_sop_modes_emit_target_surface_only() {
        let result = fixture_result();
        let primer_output =
            render_demo_output(DemoOutputMode::PrimerOnly, "The fish swim.", &result)
                .expect("primer output renders");
        let primer_json: serde_json::Value =
            serde_json::from_str(&primer_output).expect("primer output is JSON");
        assert!(primer_json.get("schema").is_some());
        assert!(primer_json.get("compact_evidence").is_some());
        assert!(primer_json.get("tokens").is_none());

        let sop_output = render_demo_output(DemoOutputMode::Sop, "The fish swim.", &result)
            .expect("SOP output renders");
        assert!(sop_output.starts_with("SLM_PRIMER_V0"));
        assert!(sop_output.contains("FishConcept"));
        assert!(serde_json::from_str::<serde_json::Value>(&sop_output).is_err());
    }

    fn fixture_result() -> AnalysisResult {
        let providers = fish_swim_providers();
        let refs = providers
            .iter()
            .map(|provider| provider.as_ref())
            .collect::<Vec<_>>();
        slm_rust::analyze_with_providers("fixture-demo-mode", "The fish swim.", &refs)
    }
}
