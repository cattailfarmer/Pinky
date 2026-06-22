use std::cmp::Ordering;
use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::core::clamp_unit;
use crate::evidence::EvidenceWorkspace;
use crate::graph::{Glyph, GlyphKind, RelationKind, SemanticGraph, UncertaintyType};
use crate::wobble::{WobbleDimensions, WobbleFactor, WobbleRoutingDecision, WobbleVector};

pub const SLM_PRIMER_LEGACY_VERSION: &str = "slm_primer_v0";
pub const SLM_PRIMER_SCHEMA_ID: &str = "slm_primer";
pub const SLM_PRIMER_SCHEMA_VERSION: &str = "0.1.0";
pub const SLM_PRIMER_COMPATIBILITY_FLOOR: &str = "0.1.0";

const REQUIRED_PRIMER_FIELDS: &[&str] = &[
    "version",
    "schema",
    "input_ref",
    "graph_ref",
    "subjects",
    "actions",
    "relations",
    "modifiers",
    "constraints",
    "uncertainty",
    "wobble",
    "compact_evidence",
    "compaction",
    "lineage_refs",
    "sop_rendering",
];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrimerSchemaInfo {
    pub schema_id: String,
    pub schema_version: String,
    pub compatibility_floor: String,
    pub required_fields: Vec<String>,
    pub compatibility_notes: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GlyphPrimer {
    pub semantic_id: String,
    pub label: String,
    pub kind: GlyphKind,
    pub support_activation: f32,
    pub lineage_refs: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RelationPrimer {
    pub relation_id: String,
    pub source_glyph: String,
    pub target_glyph: String,
    pub kind: RelationKind,
    pub candidate_relation_ref: String,
    pub endpoint_decision_refs: Vec<String>,
    pub support_activation: f32,
    pub lineage_refs: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UncertaintyPrimer {
    pub semantic_id: String,
    pub uncertainty_type: UncertaintyType,
    pub boundary_statement: String,
    pub candidate_set: Vec<String>,
    pub lineage_refs: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WobblePrimer {
    pub aggregate_score: f32,
    pub dimensions: WobbleDimensions,
    pub routing_hint: String,
    pub routing_decision: WobbleRoutingDecision,
    pub factors: Vec<WobbleFactorPrimer>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WobbleFactorPrimer {
    pub id: String,
    pub dimension: String,
    pub target_kind: String,
    pub target_ref: String,
    pub score: f32,
    pub explanation: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CompactEvidenceItem {
    pub kind: String,
    pub id: String,
    pub summary: String,
    pub refs: Vec<String>,
    pub support_activation: Option<f32>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrimerCompactionBudget {
    pub policy_id: String,
    pub max_total_items: usize,
    pub max_items_per_kind: usize,
    pub support_top_k: usize,
    pub provider_suggestion_top_k: usize,
    pub lexical_sense_top_k_per_token: usize,
    pub must_keep_kinds: Vec<String>,
}

impl Default for PrimerCompactionBudget {
    fn default() -> Self {
        Self {
            policy_id: "primer_compaction_budget_v0".to_string(),
            max_total_items: 40,
            max_items_per_kind: 12,
            support_top_k: 10,
            provider_suggestion_top_k: 12,
            lexical_sense_top_k_per_token: 2,
            must_keep_kinds: vec![
                "tokens".to_string(),
                "structural_hint".to_string(),
                "span_candidate".to_string(),
                "contradiction".to_string(),
                "provider_deliberation".to_string(),
                "wobble".to_string(),
            ],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CompactEvidenceOmission {
    pub kind: String,
    pub omitted_count: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrimerCompactionSummary {
    pub policy_id: String,
    pub max_total_items: usize,
    pub max_items_per_kind: usize,
    pub support_top_k: usize,
    pub provider_suggestion_top_k: usize,
    pub lexical_sense_top_k_per_token: usize,
    pub must_keep_kinds: Vec<String>,
    pub retained_item_count: usize,
    pub omitted_item_count: usize,
    pub omitted_by_kind: Vec<CompactEvidenceOmission>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SlmPrimer {
    pub version: String,
    pub schema: PrimerSchemaInfo,
    pub input_ref: String,
    pub graph_ref: String,
    pub subjects: Vec<GlyphPrimer>,
    pub actions: Vec<GlyphPrimer>,
    pub relations: Vec<RelationPrimer>,
    pub modifiers: Vec<GlyphPrimer>,
    pub constraints: Vec<GlyphPrimer>,
    pub uncertainty: Vec<UncertaintyPrimer>,
    pub wobble: WobblePrimer,
    pub compact_evidence: Vec<CompactEvidenceItem>,
    pub compaction: PrimerCompactionSummary,
    pub lineage_refs: Vec<String>,
    pub sop_rendering: String,
}

impl SlmPrimer {
    pub fn from_graph(
        workspace: &EvidenceWorkspace,
        graph: &SemanticGraph,
        wobble: &WobbleVector,
    ) -> Self {
        let subjects = glyphs_by_kind(workspace, graph, GlyphKind::Subject);
        let actions = glyphs_by_kind(workspace, graph, GlyphKind::Action);
        let modifiers = glyphs_by_kind(workspace, graph, GlyphKind::Modifier);
        let constraints = glyphs_by_kind(workspace, graph, GlyphKind::Constraint);
        let relations = graph
            .relations
            .iter()
            .map(|relation| RelationPrimer {
                relation_id: relation.relation_id.clone(),
                source_glyph: relation.source_glyph.clone(),
                target_glyph: relation.target_glyph.clone(),
                kind: relation.kind,
                candidate_relation_ref: normalize_evidence_ref(&relation.candidate_relation_ref),
                endpoint_decision_refs: normalize_ref_list(relation.endpoint_decision_refs.clone()),
                support_activation: relation_support_activation(workspace, &relation.relation_id),
                lineage_refs: normalize_ref_list(relation.lineage.source_refs.clone()),
            })
            .collect::<Vec<_>>();
        let uncertainty = graph
            .uncertainties
            .iter()
            .map(|uncertainty| UncertaintyPrimer {
                semantic_id: uncertainty.semantic_id.clone(),
                uncertainty_type: uncertainty.uncertainty_type,
                boundary_statement: uncertainty.boundary_statement.clone(),
                candidate_set: uncertainty.candidate_set.clone(),
                lineage_refs: normalize_ref_list(uncertainty.lineage.source_refs.clone()),
            })
            .collect::<Vec<_>>();
        let (compact_evidence, compaction) = compact_evidence(workspace, wobble);
        let mut lineage_refs = graph
            .glyphs
            .iter()
            .flat_map(|glyph| glyph.lineage.source_refs.clone())
            .collect::<Vec<_>>();
        lineage_refs.extend(
            graph
                .uncertainties
                .iter()
                .flat_map(|uncertainty| uncertainty.lineage.source_refs.clone()),
        );
        lineage_refs = normalize_ref_list(lineage_refs);
        lineage_refs.sort();
        lineage_refs.dedup();

        let wobble_primer = WobblePrimer {
            aggregate_score: wobble.aggregate_score,
            dimensions: wobble.dimensions.clone(),
            routing_hint: routing_hint(wobble).to_string(),
            routing_decision: wobble.routing_decision(),
            factors: wobble.factors.iter().map(wobble_factor_primer).collect(),
        };

        let sop_rendering = render_sop(SopRenderInput {
            workspace,
            graph,
            subjects: &subjects,
            actions: &actions,
            relations: &relations,
            constraints: &constraints,
            uncertainty: &uncertainty,
            wobble: &wobble_primer,
        });

        Self {
            version: SLM_PRIMER_LEGACY_VERSION.to_string(),
            schema: primer_schema_info(),
            input_ref: workspace.workspace_id.clone(),
            graph_ref: graph.graph_id.clone(),
            subjects,
            actions,
            relations,
            modifiers,
            constraints,
            uncertainty,
            wobble: wobble_primer,
            compact_evidence,
            compaction,
            lineage_refs,
            sop_rendering,
        }
    }

    pub fn to_json_string(&self) -> serde_json::Result<String> {
        serde_json::to_string_pretty(self)
    }
}

pub fn primer_schema_info() -> PrimerSchemaInfo {
    PrimerSchemaInfo {
        schema_id: SLM_PRIMER_SCHEMA_ID.to_string(),
        schema_version: SLM_PRIMER_SCHEMA_VERSION.to_string(),
        compatibility_floor: SLM_PRIMER_COMPATIBILITY_FLOOR.to_string(),
        required_fields: REQUIRED_PRIMER_FIELDS
            .iter()
            .map(|field| (*field).to_string())
            .collect(),
        compatibility_notes: vec![
            "Additive optional fields do not require a compatibility floor change.".to_string(),
            "Required field changes require a schema_version increment.".to_string(),
            "compact_evidence is bounded by compaction metadata and is not exhaustive by default."
                .to_string(),
        ],
    }
}

fn glyphs_by_kind(
    workspace: &EvidenceWorkspace,
    graph: &SemanticGraph,
    kind: GlyphKind,
) -> Vec<GlyphPrimer> {
    graph
        .glyphs
        .iter()
        .filter(|glyph| glyph.kind == kind)
        .map(|glyph| glyph_primer(workspace, glyph))
        .collect()
}

fn glyph_primer(workspace: &EvidenceWorkspace, glyph: &Glyph) -> GlyphPrimer {
    GlyphPrimer {
        semantic_id: glyph.semantic_id.clone(),
        label: glyph.label.clone(),
        kind: glyph.kind,
        support_activation: meaning_support_activation(workspace, &glyph.label),
        lineage_refs: normalize_ref_list(glyph.lineage.source_refs.clone()),
    }
}

fn meaning_support_activation(workspace: &EvidenceWorkspace, label: &str) -> f32 {
    let target_ref = format!("meaning:{label}");
    workspace
        .support_for_target(&target_ref)
        .iter()
        .map(|support| support.support_weight)
        .fold(0.0, f32::max)
}

fn relation_support_activation(workspace: &EvidenceWorkspace, relation_id: &str) -> f32 {
    workspace
        .support_records
        .iter()
        .filter(|support| support.target_ref == relation_id)
        .map(|support| support.support_weight)
        .fold(0.7, f32::max)
}

fn wobble_factor_primer(factor: &WobbleFactor) -> WobbleFactorPrimer {
    WobbleFactorPrimer {
        id: normalize_evidence_ref(&factor.id),
        dimension: factor.dimension.clone(),
        target_kind: factor.target_kind.clone(),
        target_ref: normalize_evidence_ref(&factor.target_ref),
        score: clamp_unit(factor.score),
        explanation: factor.explanation.clone(),
    }
}

fn compact_evidence(
    workspace: &EvidenceWorkspace,
    wobble: &WobbleVector,
) -> (Vec<CompactEvidenceItem>, PrimerCompactionSummary) {
    compact_evidence_with_budget(workspace, wobble, &PrimerCompactionBudget::default())
}

pub fn compact_evidence_with_budget(
    workspace: &EvidenceWorkspace,
    wobble: &WobbleVector,
    budget: &PrimerCompactionBudget,
) -> (Vec<CompactEvidenceItem>, PrimerCompactionSummary) {
    let mut items = collect_compact_evidence_candidates(workspace, wobble);
    normalize_compact_evidence_refs(&mut items);
    apply_compaction_budget(items, budget)
}

fn collect_compact_evidence_candidates(
    workspace: &EvidenceWorkspace,
    wobble: &WobbleVector,
) -> Vec<CompactEvidenceItem> {
    let mut items = Vec::new();
    items.push(CompactEvidenceItem {
        kind: "tokens".to_string(),
        id: format!("tokens:{}", workspace.workspace_id),
        summary: workspace
            .tokens
            .iter()
            .map(|token| token.surface_text.clone())
            .collect::<Vec<_>>()
            .join(" "),
        refs: workspace
            .tokens
            .iter()
            .map(|token| token.id.clone())
            .collect(),
        support_activation: None,
    });

    items.extend(
        workspace
            .support_records
            .iter()
            .map(|support| CompactEvidenceItem {
                kind: "support".to_string(),
                id: support.id.clone(),
                summary: support.rationale.clone(),
                refs: vec![support.target_ref.clone(), support.source_ref.clone()],
                support_activation: Some(clamp_unit(support.support_weight)),
            }),
    );

    items.extend(
        workspace
            .structural_hints
            .iter()
            .map(|hint| CompactEvidenceItem {
                kind: "structural_hint".to_string(),
                id: hint.id.clone(),
                summary: format!(
                    "{}:{} - {}",
                    hint.class, hint.subclass, hint.structural_hint
                ),
                refs: vec![hint.token_id.clone()],
                support_activation: Some(clamp_unit(hint.diffusion_priority)),
            }),
    );

    items.extend(
        workspace
            .span_candidates
            .iter()
            .map(|span| CompactEvidenceItem {
                kind: "span_candidate".to_string(),
                id: span.id.clone(),
                summary: format!("{:?}: {}", span.span_kind, span.surface_text),
                refs: span.token_refs.clone(),
                support_activation: Some(clamp_unit(span.support_weight)),
            }),
    );

    items.extend(workspace.lexical_sense_candidates.iter().map(|sense| {
        CompactEvidenceItem {
            kind: "lexical_sense".to_string(),
            id: sense.id.clone(),
            summary: sense
                .definition
                .clone()
                .unwrap_or_else(|| format!("{} {}", sense.lemma, sense.synset_id)),
            refs: vec![sense.token_id.clone(), sense.synset_id.clone()],
            support_activation: Some(clamp_unit(sense.support_weight)),
        }
    }));

    items.extend(
        workspace
            .provider_suggestions
            .iter()
            .map(|suggestion| CompactEvidenceItem {
                kind: "provider_suggestion".to_string(),
                id: suggestion.id.clone(),
                summary: format!("{:?}: {}", suggestion.kind, suggestion.payload),
                refs: vec![
                    suggestion.target_ref.clone(),
                    format!("provider:{}", suggestion.provenance.provider_id),
                ],
                support_activation: suggestion.support_weight.map(clamp_unit),
            }),
    );

    items.extend(
        workspace
            .contradiction_records
            .iter()
            .map(|contradiction| CompactEvidenceItem {
                kind: "contradiction".to_string(),
                id: contradiction.id.clone(),
                summary: contradiction.rationale.clone(),
                refs: contradiction_refs(contradiction),
                support_activation: Some(contradiction.severity.score()),
            }),
    );

    items.extend(workspace.provider_deliberations.iter().map(|deliberation| {
        let mut refs = vec![
            deliberation.candidate_ref.clone(),
            format!("provider:{}", deliberation.objecting_provider),
        ];
        refs.extend(
            deliberation
                .supporting_provider_set
                .iter()
                .map(|provider| format!("provider:{provider}")),
        );
        refs.extend(
            deliberation
                .objection_set
                .iter()
                .map(|objection| objection.id.clone()),
        );
        refs.extend(
            deliberation
                .answer_set
                .iter()
                .map(|answer| answer.id.clone()),
        );
        refs.extend(
            deliberation
                .jury_review_set
                .iter()
                .map(|jury| jury.id.clone()),
        );
        refs.extend(deliberation.faculty_report_refs.clone());

        CompactEvidenceItem {
            kind: "provider_deliberation".to_string(),
            id: deliberation.id.clone(),
            summary: format!(
                "{:?}: objector={}, supporters={}",
                deliberation.status,
                deliberation.objecting_provider,
                deliberation.supporting_provider_set.len()
            ),
            refs,
            support_activation: None,
        }
    }));

    let mut wobble_refs = workspace
        .wobble_vectors
        .iter()
        .enumerate()
        .map(|(index, _)| format!("wobble:{index}"))
        .collect::<Vec<_>>();
    wobble_refs.extend(
        workspace
            .wobble_vectors
            .iter()
            .flat_map(|wobble| wobble.factors.iter().map(|factor| factor.id.clone())),
    );

    items.push(CompactEvidenceItem {
        kind: "wobble".to_string(),
        id: format!("wobble:{}", workspace.workspace_id),
        summary: routing_hint(wobble).to_string(),
        refs: wobble_refs,
        support_activation: Some(wobble.aggregate_score),
    });

    items
}

fn contradiction_refs(contradiction: &crate::core::ContradictionRecord) -> Vec<String> {
    let mut refs = vec![
        contradiction.target_ref.clone(),
        contradiction.source_ref.clone(),
    ];
    refs.extend(contradiction.answer_ref.clone());
    refs.extend(contradiction.provider_deliberation_ref.clone());
    refs.extend(contradiction.jury_review_ref.clone());
    refs.extend(contradiction.cited_panel_refs.clone());
    refs
}

fn apply_compaction_budget(
    items: Vec<CompactEvidenceItem>,
    budget: &PrimerCompactionBudget,
) -> (Vec<CompactEvidenceItem>, PrimerCompactionSummary) {
    let mut omitted_counts = BTreeMap::new();
    let mut by_kind = BTreeMap::<String, Vec<CompactEvidenceItem>>::new();
    for item in items {
        by_kind.entry(item.kind.clone()).or_default().push(item);
    }

    let mut retained = Vec::new();
    for (kind, kind_items) in by_kind {
        let selected = match kind.as_str() {
            "lexical_sense" => retain_lexical_sense_top_per_token(
                kind_items,
                budget.lexical_sense_top_k_per_token,
                &mut omitted_counts,
            ),
            "provider_suggestion" => retain_top_by_rank(
                kind_items,
                budget.provider_suggestion_top_k,
                &mut omitted_counts,
            ),
            "support" => retain_top_by_rank(kind_items, budget.support_top_k, &mut omitted_counts),
            _ if is_must_keep_kind(&kind, budget) => kind_items,
            _ => retain_top_by_rank(kind_items, budget.max_items_per_kind, &mut omitted_counts),
        };
        retained.extend(selected);
    }

    retained = apply_total_budget(retained, budget, &mut omitted_counts);
    sort_for_primer_output(&mut retained);

    let omitted_by_kind = omitted_counts
        .into_iter()
        .map(|(kind, omitted_count)| CompactEvidenceOmission {
            kind,
            omitted_count,
        })
        .collect::<Vec<_>>();
    let omitted_item_count = omitted_by_kind
        .iter()
        .map(|omission| omission.omitted_count)
        .sum();

    let summary = PrimerCompactionSummary {
        policy_id: budget.policy_id.clone(),
        max_total_items: budget.max_total_items,
        max_items_per_kind: budget.max_items_per_kind,
        support_top_k: budget.support_top_k,
        provider_suggestion_top_k: budget.provider_suggestion_top_k,
        lexical_sense_top_k_per_token: budget.lexical_sense_top_k_per_token,
        must_keep_kinds: budget.must_keep_kinds.clone(),
        retained_item_count: retained.len(),
        omitted_item_count,
        omitted_by_kind,
    };

    (retained, summary)
}

fn retain_lexical_sense_top_per_token(
    items: Vec<CompactEvidenceItem>,
    limit_per_token: usize,
    omitted_counts: &mut BTreeMap<String, usize>,
) -> Vec<CompactEvidenceItem> {
    let mut by_token = BTreeMap::<String, Vec<CompactEvidenceItem>>::new();
    for item in items {
        let token_ref = item
            .refs
            .first()
            .cloned()
            .unwrap_or_else(|| "token:unknown".to_string());
        by_token.entry(token_ref).or_default().push(item);
    }

    let mut retained = Vec::new();
    for (_, token_items) in by_token {
        retained.extend(retain_top_by_rank(
            token_items,
            limit_per_token,
            omitted_counts,
        ));
    }
    retained
}

fn retain_top_by_rank(
    mut items: Vec<CompactEvidenceItem>,
    limit: usize,
    omitted_counts: &mut BTreeMap<String, usize>,
) -> Vec<CompactEvidenceItem> {
    sort_by_evidence_rank(&mut items);
    if items.len() > limit {
        let omitted = items.split_off(limit);
        record_omissions(omitted_counts, &omitted);
    }
    items
}

fn apply_total_budget(
    items: Vec<CompactEvidenceItem>,
    budget: &PrimerCompactionBudget,
    omitted_counts: &mut BTreeMap<String, usize>,
) -> Vec<CompactEvidenceItem> {
    if items.len() <= budget.max_total_items {
        return items;
    }

    let mut must_keep = Vec::new();
    let mut optional = Vec::new();
    for item in items {
        if is_must_keep_kind(&item.kind, budget) {
            must_keep.push(item);
        } else {
            optional.push(item);
        }
    }

    let optional_limit = budget.max_total_items.saturating_sub(must_keep.len());
    sort_by_evidence_rank(&mut optional);
    if optional.len() > optional_limit {
        let omitted = optional.split_off(optional_limit);
        record_omissions(omitted_counts, &omitted);
    }

    must_keep.extend(optional);
    must_keep
}

fn record_omissions(omitted_counts: &mut BTreeMap<String, usize>, omitted: &[CompactEvidenceItem]) {
    for item in omitted {
        *omitted_counts.entry(item.kind.clone()).or_insert(0) += 1;
    }
}

fn is_must_keep_kind(kind: &str, budget: &PrimerCompactionBudget) -> bool {
    budget
        .must_keep_kinds
        .iter()
        .any(|must_keep| must_keep == kind)
}

fn sort_by_evidence_rank(items: &mut [CompactEvidenceItem]) {
    items.sort_by(compare_evidence_rank);
}

fn compare_evidence_rank(left: &CompactEvidenceItem, right: &CompactEvidenceItem) -> Ordering {
    item_support(right)
        .total_cmp(&item_support(left))
        .then_with(|| left.id.cmp(&right.id))
        .then_with(|| left.summary.cmp(&right.summary))
}

fn sort_for_primer_output(items: &mut [CompactEvidenceItem]) {
    items.sort_by(|left, right| {
        kind_priority(&left.kind)
            .cmp(&kind_priority(&right.kind))
            .then_with(|| left.id.cmp(&right.id))
    });
}

fn item_support(item: &CompactEvidenceItem) -> f32 {
    item.support_activation.unwrap_or(0.0)
}

fn kind_priority(kind: &str) -> usize {
    match kind {
        "tokens" => 0,
        "structural_hint" => 1,
        "span_candidate" => 2,
        "lexical_sense" => 3,
        "support" => 4,
        "provider_suggestion" => 5,
        "contradiction" => 6,
        "provider_deliberation" => 7,
        "wobble" => 8,
        _ => 99,
    }
}

fn normalize_compact_evidence_refs(items: &mut [CompactEvidenceItem]) {
    for item in items {
        item.refs = normalize_ref_list(std::mem::take(&mut item.refs));
    }
}

pub fn normalize_ref_list(refs: Vec<String>) -> Vec<String> {
    refs.into_iter()
        .map(|source_ref| normalize_evidence_ref(&source_ref))
        .collect()
}

pub fn normalize_evidence_ref(source_ref: &str) -> String {
    let trimmed = source_ref.trim();
    if trimmed.is_empty() {
        return "source_note:empty".to_string();
    }

    if has_parseable_namespace(trimmed) {
        return trimmed.replace(char::is_whitespace, "_");
    }

    if trimmed.starts_with("oewn-") {
        return format!("synset:{trimmed}");
    }

    let identity = sanitize_source_identity(trimmed);
    if trimmed.contains(char::is_whitespace) {
        format!("source_note:{identity}")
    } else if trimmed.contains("provider") {
        format!("provider:{identity}")
    } else {
        format!("evidence:{identity}")
    }
}

fn has_parseable_namespace(source_ref: &str) -> bool {
    let Some((namespace, identity)) = source_ref.split_once(':') else {
        return false;
    };
    !namespace.is_empty()
        && !identity.is_empty()
        && namespace
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || ch == '_')
}

fn sanitize_source_identity(source_ref: &str) -> String {
    let mut normalized = String::new();
    let mut previous_separator = false;
    for ch in source_ref.chars().flat_map(char::to_lowercase) {
        if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.') {
            normalized.push(ch);
            previous_separator = false;
        } else if !previous_separator {
            normalized.push('_');
            previous_separator = true;
        }
    }

    let normalized = normalized.trim_matches('_').to_string();
    if normalized.is_empty() {
        "unknown".to_string()
    } else {
        normalized
    }
}

fn routing_hint(wobble: &WobbleVector) -> &'static str {
    wobble.routing_decision().route.as_str()
}

struct SopRenderInput<'a> {
    workspace: &'a EvidenceWorkspace,
    graph: &'a SemanticGraph,
    subjects: &'a [GlyphPrimer],
    actions: &'a [GlyphPrimer],
    relations: &'a [RelationPrimer],
    constraints: &'a [GlyphPrimer],
    uncertainty: &'a [UncertaintyPrimer],
    wobble: &'a WobblePrimer,
}

fn render_sop(input: SopRenderInput<'_>) -> String {
    let mut lines = Vec::new();
    lines.push("SLM_PRIMER_V0".to_string());
    lines.push(format!("Input: {}", input.workspace.input_text));
    lines.push(format!("Graph: {}", input.graph.graph_id));
    lines.push(format!(
        "Wobble: {:.3} ({})",
        input.wobble.aggregate_score, input.wobble.routing_hint
    ));
    render_glyph_section(&mut lines, "Subjects", input.subjects);
    render_glyph_section(&mut lines, "Actions", input.actions);
    render_glyph_section(&mut lines, "Constraints", input.constraints);
    lines.push("Relations:".to_string());
    for relation in input.relations {
        lines.push(format!(
            "- {:?}: {} -> {}",
            relation.kind, relation.source_glyph, relation.target_glyph
        ));
    }
    lines.push("Uncertainty:".to_string());
    for item in input.uncertainty {
        lines.push(format!(
            "- {:?}: {}",
            item.uncertainty_type, item.boundary_statement
        ));
    }
    lines.join("\n")
}

fn render_glyph_section(lines: &mut Vec<String>, title: &str, glyphs: &[GlyphPrimer]) {
    lines.push(format!("{title}:"));
    for glyph in glyphs {
        lines.push(format!(
            "- {} ({:?}, support={:.3})",
            glyph.label, glyph.kind, glyph.support_activation
        ));
    }
}
