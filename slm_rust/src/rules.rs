use crate::core::{GrammarRole, SpanKind};
use crate::graph::RelationKind;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpanRulePattern {
    AnchorAndNextContent,
    AnchorAndFollowingContent { max_following: usize },
    PreviousAnchorAndNextContent,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CompoundObjectRule {
    pub min_object_tokens: usize,
    pub span_kind: SpanKind,
    pub support_weight: f32,
    pub rationale: &'static str,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ClosedClassSpanRule {
    pub class: &'static str,
    pub span_kind: SpanKind,
    pub pattern: SpanRulePattern,
    pub support_weight: Option<f32>,
    pub rationale: &'static str,
    pub compound_object_rule: Option<CompoundObjectRule>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RolePairSpanRule {
    pub left_role: GrammarRole,
    pub right_role: GrammarRole,
    pub span_kind: SpanKind,
    pub support_weight: f32,
    pub exclude_structural_hint_tokens: bool,
    pub lineage_ref: &'static str,
    pub rationale: &'static str,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PrepositionRelationRule {
    pub subclass_contains_any: &'static [&'static str],
    pub relation_kind: RelationKind,
    pub rationale: &'static str,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SenseCoherenceRule {
    pub id: &'static str,
    pub required_context_terms: &'static [&'static str],
    pub definition_contains_any: &'static [&'static str],
    pub bonus: f32,
    pub rationale: &'static str,
}

impl SenseCoherenceRule {
    pub fn applies(self, context: &str, definition: &str) -> bool {
        self.required_context_terms
            .iter()
            .all(|term| context.contains(term))
            && self
                .definition_contains_any
                .iter()
                .any(|term| definition.contains(term))
    }
}

pub const CLOSED_CLASS_SPAN_RULES: &[ClosedClassSpanRule] = &[
    ClosedClassSpanRule {
        class: "article",
        span_kind: SpanKind::Nominal,
        pattern: SpanRulePattern::AnchorAndNextContent,
        support_weight: None,
        rationale: "article scopes nominal span",
        compound_object_rule: None,
    },
    ClosedClassSpanRule {
        class: "demonstrative",
        span_kind: SpanKind::Nominal,
        pattern: SpanRulePattern::AnchorAndNextContent,
        support_weight: None,
        rationale: "demonstrative scopes nominal span",
        compound_object_rule: None,
    },
    ClosedClassSpanRule {
        class: "quantifier",
        span_kind: SpanKind::Nominal,
        pattern: SpanRulePattern::AnchorAndNextContent,
        support_weight: None,
        rationale: "quantifier scopes nominal span",
        compound_object_rule: None,
    },
    ClosedClassSpanRule {
        class: "preposition",
        span_kind: SpanKind::Prepositional,
        pattern: SpanRulePattern::AnchorAndFollowingContent { max_following: 3 },
        support_weight: None,
        rationale: "preposition opens constrained relational span",
        compound_object_rule: Some(CompoundObjectRule {
            min_object_tokens: 2,
            span_kind: SpanKind::Compound,
            support_weight: 0.72,
            rationale: "prepositional object forms compound candidate",
        }),
    },
    ClosedClassSpanRule {
        class: "conjunction",
        span_kind: SpanKind::Coordination,
        pattern: SpanRulePattern::PreviousAnchorAndNextContent,
        support_weight: None,
        rationale: "conjunction creates coordination boundary candidate",
        compound_object_rule: None,
    },
];

pub const ROLE_PAIR_SPAN_RULES: &[RolePairSpanRule] = &[RolePairSpanRule {
    left_role: GrammarRole::Noun,
    right_role: GrammarRole::Noun,
    span_kind: SpanKind::Compound,
    support_weight: 0.68,
    exclude_structural_hint_tokens: true,
    lineage_ref: "role_pair:noun_noun",
    rationale: "adjacent noun evidence forms compound span candidate",
}];

pub const PREPOSITION_RELATION_RULES: &[PrepositionRelationRule] = &[
    PrepositionRelationRule {
        subclass_contains_any: &["possession", "composition"],
        relation_kind: RelationKind::RefersTo,
        rationale: "possessive or compositional preposition refers between concepts",
    },
    PrepositionRelationRule {
        subclass_contains_any: &[],
        relation_kind: RelationKind::Constrains,
        rationale: "default preposition constrains the scoped relation candidate",
    },
];

pub const SENSE_COHERENCE_RULES: &[SenseCoherenceRule] = &[
    SenseCoherenceRule {
        id: "compiler_hardware_computing_context",
        required_context_terms: &["compiler", "hardware"],
        definition_contains_any: &["computer", "program"],
        bonus: 0.18,
        rationale: "compiler plus hardware context supports computing-related senses",
    },
    SenseCoherenceRule {
        id: "fpga_electronic_computing_context",
        required_context_terms: &["fpga"],
        definition_contains_any: &["electronic", "computer"],
        bonus: 0.12,
        rationale: "FPGA context supports electronic or computer hardware senses",
    },
];

pub fn closed_class_span_rule(class: &str) -> Option<&'static ClosedClassSpanRule> {
    CLOSED_CLASS_SPAN_RULES
        .iter()
        .find(|rule| rule.class == class)
}

pub fn relation_kind_for_preposition_subclass(subclass: &str) -> RelationKind {
    PREPOSITION_RELATION_RULES
        .iter()
        .find(|rule| {
            rule.subclass_contains_any.is_empty()
                || rule
                    .subclass_contains_any
                    .iter()
                    .any(|term| subclass.contains(term))
        })
        .map(|rule| rule.relation_kind)
        .unwrap_or(RelationKind::Constrains)
}
