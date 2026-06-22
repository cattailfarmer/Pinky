use serde::{Deserialize, Serialize};

use crate::core::{
    CandidateMeaning, CandidateRelation, CandidateStatus, ContradictionRecord, EvidenceSource,
    GrammarCandidate, GrammarRole, LexicalSenseCandidate, LineageRecord, MeaningKind,
    SpanCandidate, StructuralHint, SupportRecord, Token,
};
use crate::deliberation::ProviderDeliberation;
use crate::diffusion::DiffusionPassTrace;
use crate::providers::{AdapterKind, ProviderSuggestion, ProviderSuggestionKind};
use crate::wobble::WobbleVector;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceBundle {
    pub target_ref: String,
    pub token_refs: Vec<String>,
    pub grammar_candidate_refs: Vec<String>,
    pub structural_hint_refs: Vec<String>,
    pub span_candidate_refs: Vec<String>,
    pub lexical_sense_refs: Vec<String>,
    pub candidate_meaning_refs: Vec<String>,
    pub candidate_relation_refs: Vec<String>,
    pub support_refs: Vec<String>,
    pub contradiction_refs: Vec<String>,
    pub provider_deliberation_refs: Vec<String>,
    pub wobble_factor_refs: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceWorkspace {
    pub workspace_id: String,
    pub input_text: String,
    pub tokens: Vec<Token>,
    pub grammar_candidates: Vec<GrammarCandidate>,
    pub structural_hints: Vec<StructuralHint>,
    pub span_candidates: Vec<SpanCandidate>,
    pub lexical_sense_candidates: Vec<LexicalSenseCandidate>,
    pub provider_suggestions: Vec<ProviderSuggestion>,
    pub candidate_meanings: Vec<CandidateMeaning>,
    pub candidate_relations: Vec<CandidateRelation>,
    pub support_records: Vec<SupportRecord>,
    pub contradiction_records: Vec<ContradictionRecord>,
    pub provider_deliberations: Vec<ProviderDeliberation>,
    pub wobble_vectors: Vec<WobbleVector>,
    pub pass_traces: Vec<DiffusionPassTrace>,
}

impl EvidenceWorkspace {
    pub fn from_text(input_id: impl Into<String>, text: impl Into<String>) -> Self {
        let input_id = input_id.into();
        let input_text = text.into();
        let tokens = tokenize(&input_id, &input_text);
        let mut workspace = Self {
            workspace_id: format!("workspace:{input_id}"),
            input_text,
            tokens,
            grammar_candidates: Vec::new(),
            structural_hints: Vec::new(),
            span_candidates: Vec::new(),
            lexical_sense_candidates: Vec::new(),
            provider_suggestions: Vec::new(),
            candidate_meanings: Vec::new(),
            candidate_relations: Vec::new(),
            support_records: Vec::new(),
            contradiction_records: Vec::new(),
            provider_deliberations: Vec::new(),
            wobble_vectors: Vec::new(),
            pass_traces: Vec::new(),
        };
        workspace.seed_grammar_candidates();
        workspace
    }

    pub fn ingest_provider_suggestions(&mut self, suggestions: Vec<ProviderSuggestion>) {
        for suggestion in suggestions {
            match suggestion.kind {
                ProviderSuggestionKind::GrammarRole => {
                    if let Some(role) = suggestion.grammar_role {
                        let id = format!(
                            "grammar:{}:{}:{}",
                            suggestion.target_ref,
                            role_name(role),
                            suggestion.id
                        );
                        if self
                            .grammar_candidates
                            .iter()
                            .any(|candidate| candidate.id == id)
                        {
                            self.provider_suggestions.push(suggestion);
                            continue;
                        }
                        let source =
                            if suggestion.provenance.adapter_kind == AdapterKind::LexicalDatabase {
                                EvidenceSource::LexicalAuthority
                            } else {
                                EvidenceSource::LowerLlm
                            };
                        self.grammar_candidates.push(GrammarCandidate {
                            id,
                            token_id: suggestion.target_ref.clone(),
                            role,
                            support_weight: suggestion.support_weight.unwrap_or(0.5),
                            source,
                            status: CandidateStatus::Active,
                            lineage: suggestion.lineage.clone(),
                        });
                    }
                }
                ProviderSuggestionKind::CandidateMeaning => {
                    let label = suggestion.payload.clone();
                    let candidate_id = format!("meaning:{label}");
                    if !self
                        .candidate_meanings
                        .iter()
                        .any(|candidate| candidate.id == candidate_id)
                    {
                        let support_id = format!("support:{}", suggestion.id);
                        self.support_records.push(SupportRecord {
                            id: support_id.clone(),
                            target_ref: candidate_id.clone(),
                            support_weight: suggestion.support_weight.unwrap_or(0.5),
                            source_ref: suggestion.id.clone(),
                            rationale: suggestion
                                .rationale
                                .clone()
                                .unwrap_or_else(|| "provider candidate meaning".to_string()),
                        });
                        self.candidate_meanings.push(CandidateMeaning {
                            id: candidate_id,
                            kind: suggestion.meaning_kind.unwrap_or(MeaningKind::Reference),
                            label,
                            token_refs: related_token_refs(&self.tokens, &suggestion.target_ref),
                            support_record_ids: vec![support_id],
                            contradiction_record_ids: Vec::new(),
                            lineage: suggestion.lineage.clone(),
                        });
                    }
                }
                ProviderSuggestionKind::StructuralHint => {
                    let id = format!("structural_hint:{}", suggestion.id);
                    if !self.structural_hints.iter().any(|hint| hint.id == id) {
                        let source =
                            if suggestion.provenance.adapter_kind == AdapterKind::LexicalDatabase {
                                EvidenceSource::LexicalAuthority
                            } else {
                                EvidenceSource::LowerLlm
                            };
                        self.structural_hints.push(StructuralHint {
                            id,
                            token_id: suggestion.target_ref.clone(),
                            class: suggestion.closed_class.clone().unwrap_or_default(),
                            subclass: suggestion.closed_subclass.clone().unwrap_or_default(),
                            diffusion_priority: suggestion.support_weight.unwrap_or(0.5),
                            structural_hint: suggestion
                                .structural_hint
                                .clone()
                                .or_else(|| suggestion.rationale.clone())
                                .unwrap_or_default(),
                            source,
                            lineage: suggestion.lineage.clone(),
                        });
                    }
                }
                ProviderSuggestionKind::LexicalSense => {
                    let Some(sense_key) = suggestion.sense_key.clone() else {
                        self.provider_suggestions.push(suggestion);
                        continue;
                    };
                    let Some(synset_id) = suggestion.synset_id.clone() else {
                        self.provider_suggestions.push(suggestion);
                        continue;
                    };
                    let id = format!("lexical_sense:{}", suggestion.id);
                    if !self
                        .lexical_sense_candidates
                        .iter()
                        .any(|sense| sense.id == id)
                    {
                        let source =
                            if suggestion.provenance.adapter_kind == AdapterKind::LexicalDatabase {
                                EvidenceSource::LexicalAuthority
                            } else {
                                EvidenceSource::LowerLlm
                            };
                        self.lexical_sense_candidates.push(LexicalSenseCandidate {
                            id,
                            token_id: suggestion.target_ref.clone(),
                            lemma: suggestion.payload.clone(),
                            sense_key,
                            synset_id,
                            part_of_speech: suggestion.part_of_speech.clone().unwrap_or_default(),
                            definition: suggestion.definition.clone(),
                            support_weight: suggestion.support_weight.unwrap_or(0.5),
                            source,
                            lineage: suggestion.lineage.clone(),
                        });
                    }
                }
                _ => {}
            }
            self.provider_suggestions.push(suggestion);
        }
    }

    pub fn meaning_by_label(&self, label: &str) -> Option<&CandidateMeaning> {
        self.candidate_meanings
            .iter()
            .find(|candidate| candidate.label == label)
    }

    pub fn support_for_target(&self, target_ref: &str) -> Vec<&SupportRecord> {
        self.support_records
            .iter()
            .filter(|support| support.target_ref == target_ref)
            .collect()
    }

    pub fn contradictions_for_target(&self, target_ref: &str) -> Vec<&ContradictionRecord> {
        self.contradiction_records
            .iter()
            .filter(|contradiction| contradiction.target_ref == target_ref)
            .collect()
    }

    pub fn token_by_text(&self, normalized: &str) -> Option<&Token> {
        self.tokens
            .iter()
            .find(|token| token.normalized_text == normalized)
    }

    pub fn structural_hints_for_token(&self, token_id: &str) -> Vec<&StructuralHint> {
        self.structural_hints
            .iter()
            .filter(|hint| hint.token_id == token_id)
            .collect()
    }

    pub fn candidates_by_token(&self, token_id: &str) -> Vec<&GrammarCandidate> {
        self.grammar_candidates
            .iter()
            .filter(|candidate| candidate.token_id == token_id)
            .collect()
    }

    pub fn spans_for_token(&self, token_id: &str) -> Vec<&SpanCandidate> {
        self.span_candidates
            .iter()
            .filter(|span| {
                span.token_refs
                    .iter()
                    .any(|token_ref| token_ref == token_id)
            })
            .collect()
    }

    pub fn senses_for_token(&self, token_id: &str) -> Vec<&LexicalSenseCandidate> {
        self.lexical_sense_candidates
            .iter()
            .filter(|sense| sense.token_id == token_id)
            .collect()
    }

    pub fn candidate_meanings_for_token(&self, token_id: &str) -> Vec<&CandidateMeaning> {
        self.candidate_meanings
            .iter()
            .filter(|meaning| {
                meaning
                    .token_refs
                    .iter()
                    .any(|token_ref| token_ref == token_id)
            })
            .collect()
    }

    pub fn candidate_relations_for_label(&self, label: &str) -> Vec<&CandidateRelation> {
        self.candidate_relations
            .iter()
            .filter(|relation| relation.source_label == label || relation.target_label == label)
            .collect()
    }

    pub fn evidence_bundle_for_token(&self, token_id: &str) -> EvidenceBundle {
        let grammar_candidate_refs = self
            .candidates_by_token(token_id)
            .into_iter()
            .map(|candidate| candidate.id.clone())
            .collect::<Vec<_>>();
        let structural_hint_refs = self
            .structural_hints_for_token(token_id)
            .into_iter()
            .map(|hint| hint.id.clone())
            .collect::<Vec<_>>();
        let span_candidate_refs = self
            .spans_for_token(token_id)
            .into_iter()
            .map(|span| span.id.clone())
            .collect::<Vec<_>>();
        let lexical_sense_refs = self
            .senses_for_token(token_id)
            .into_iter()
            .map(|sense| sense.id.clone())
            .collect::<Vec<_>>();
        let candidate_meaning_refs = self
            .candidate_meanings_for_token(token_id)
            .into_iter()
            .map(|meaning| meaning.id.clone())
            .collect::<Vec<_>>();
        let mut support_refs = Vec::new();
        for target in grammar_candidate_refs
            .iter()
            .chain(structural_hint_refs.iter())
            .chain(span_candidate_refs.iter())
            .chain(lexical_sense_refs.iter())
            .chain(candidate_meaning_refs.iter())
        {
            support_refs.extend(
                self.support_for_target(target)
                    .into_iter()
                    .map(|support| support.id.clone()),
            );
        }

        EvidenceBundle {
            target_ref: token_id.to_string(),
            token_refs: vec![token_id.to_string()],
            grammar_candidate_refs,
            structural_hint_refs,
            span_candidate_refs,
            lexical_sense_refs,
            candidate_meaning_refs,
            candidate_relation_refs: Vec::new(),
            support_refs,
            contradiction_refs: Vec::new(),
            provider_deliberation_refs: Vec::new(),
            wobble_factor_refs: self.wobble_factor_refs_for_target(token_id),
        }
    }

    pub fn evidence_bundle_for_candidate(&self, target_ref: &str) -> EvidenceBundle {
        let support_refs = self
            .support_for_target(target_ref)
            .into_iter()
            .map(|support| support.id.clone())
            .collect::<Vec<_>>();
        let contradiction_refs = self
            .contradictions_for_target(target_ref)
            .into_iter()
            .map(|contradiction| contradiction.id.clone())
            .collect::<Vec<_>>();
        let provider_deliberation_refs = self
            .provider_deliberations
            .iter()
            .filter(|deliberation| deliberation.candidate_ref == target_ref)
            .map(|deliberation| deliberation.id.clone())
            .collect::<Vec<_>>();

        EvidenceBundle {
            target_ref: target_ref.to_string(),
            token_refs: token_refs_for_target(self, target_ref),
            grammar_candidate_refs: ids_if_match(&self.grammar_candidates, target_ref, |item| {
                &item.id
            }),
            structural_hint_refs: ids_if_match(&self.structural_hints, target_ref, |item| &item.id),
            span_candidate_refs: ids_if_match(&self.span_candidates, target_ref, |item| &item.id),
            lexical_sense_refs: ids_if_match(&self.lexical_sense_candidates, target_ref, |item| {
                &item.id
            }),
            candidate_meaning_refs: ids_if_match(&self.candidate_meanings, target_ref, |item| {
                &item.id
            }),
            candidate_relation_refs: ids_if_match(&self.candidate_relations, target_ref, |item| {
                &item.id
            }),
            support_refs,
            contradiction_refs,
            provider_deliberation_refs,
            wobble_factor_refs: self.wobble_factor_refs_for_target(target_ref),
        }
    }

    fn wobble_factor_refs_for_target(&self, target_ref: &str) -> Vec<String> {
        self.wobble_vectors
            .iter()
            .enumerate()
            .flat_map(|(wobble_index, wobble)| {
                wobble
                    .factors
                    .iter()
                    .enumerate()
                    .filter(move |(_, factor)| factor.target_ref == target_ref)
                    .map(move |(factor_index, _)| {
                        format!("wobble:{wobble_index}:factor:{factor_index}")
                    })
            })
            .collect()
    }

    fn seed_grammar_candidates(&mut self) {
        let tokens = self.tokens.clone();
        for token in tokens {
            if token.is_punctuation() {
                self.push_grammar(
                    &token,
                    GrammarRole::Punctuation,
                    1.0,
                    EvidenceSource::Heuristic,
                );
                continue;
            }

            match token.normalized_text.as_str() {
                "the" | "a" | "an" => {
                    self.push_grammar(
                        &token,
                        GrammarRole::Determiner,
                        0.95,
                        EvidenceSource::StructuralRule,
                    );
                }
                "for" | "like" => {
                    self.push_grammar(
                        &token,
                        GrammarRole::Preposition,
                        0.75,
                        EvidenceSource::StructuralRule,
                    );
                    if token.normalized_text == "like" {
                        self.push_grammar(
                            &token,
                            GrammarRole::Verb,
                            0.45,
                            EvidenceSource::Heuristic,
                        );
                    }
                }
                "and" | "or" | "but" => {
                    self.push_grammar(
                        &token,
                        GrammarRole::Conjunction,
                        0.95,
                        EvidenceSource::StructuralRule,
                    );
                }
                "design" | "swim" => {
                    self.push_grammar(&token, GrammarRole::Verb, 0.8, EvidenceSource::Dictionary);
                    self.push_grammar(&token, GrammarRole::Noun, 0.35, EvidenceSource::Dictionary);
                }
                "fish" | "flies" => {
                    self.push_grammar(&token, GrammarRole::Noun, 0.55, EvidenceSource::Dictionary);
                    self.push_grammar(&token, GrammarRole::Verb, 0.5, EvidenceSource::Dictionary);
                }
                "compiler" | "fpga" | "hardware" | "time" | "arrow" => {
                    self.push_grammar(&token, GrammarRole::Noun, 0.75, EvidenceSource::Dictionary);
                    self.push_grammar(&token, GrammarRole::Verb, 0.25, EvidenceSource::Heuristic);
                }
                _ => {
                    self.push_grammar(&token, GrammarRole::Noun, 0.4, EvidenceSource::Heuristic);
                    self.push_grammar(&token, GrammarRole::Verb, 0.35, EvidenceSource::Heuristic);
                }
            }
        }
    }

    fn push_grammar(
        &mut self,
        token: &Token,
        role: GrammarRole,
        support_weight: f32,
        source: EvidenceSource,
    ) {
        self.grammar_candidates.push(GrammarCandidate {
            id: format!("grammar:{}:{}", token.id, role_name(role)),
            token_id: token.id.clone(),
            role,
            support_weight,
            source,
            status: CandidateStatus::Active,
            lineage: LineageRecord::new(token.id.clone(), "grammar candidate"),
        });
    }
}

pub fn tokenize(input_id: &str, text: &str) -> Vec<Token> {
    let mut tokens = Vec::new();
    let mut start: Option<usize> = None;

    for (index, ch) in text.char_indices() {
        if ch.is_alphanumeric() {
            start.get_or_insert(index);
            continue;
        }

        if let Some(word_start) = start.take() {
            let token_text = &text[word_start..index];
            tokens.push(Token::new(
                input_id,
                tokens.len(),
                token_text,
                word_start,
                index,
            ));
        }

        if !ch.is_whitespace() {
            let end = index + ch.len_utf8();
            tokens.push(Token::new(
                input_id,
                tokens.len(),
                &text[index..end],
                index,
                end,
            ));
        }
    }

    if let Some(word_start) = start {
        let token_text = &text[word_start..];
        tokens.push(Token::new(
            input_id,
            tokens.len(),
            token_text,
            word_start,
            text.len(),
        ));
    }

    tokens
}

pub fn role_name(role: GrammarRole) -> &'static str {
    match role {
        GrammarRole::Noun => "noun",
        GrammarRole::Verb => "verb",
        GrammarRole::Adjective => "adjective",
        GrammarRole::Adverb => "adverb",
        GrammarRole::Determiner => "determiner",
        GrammarRole::Preposition => "preposition",
        GrammarRole::Conjunction => "conjunction",
        GrammarRole::Auxiliary => "auxiliary",
        GrammarRole::Modal => "modal",
        GrammarRole::Pronoun => "pronoun",
        GrammarRole::Punctuation => "punctuation",
        GrammarRole::Unknown => "unknown",
        GrammarRole::Extension => "extension",
    }
}

fn related_token_refs(tokens: &[Token], target_ref: &str) -> Vec<String> {
    let normalized = target_ref.to_lowercase();
    tokens
        .iter()
        .filter(|token| {
            normalized.contains(&token.normalized_text)
                || target_ref.contains(&token.surface_text)
                || target_ref.contains(&capitalize(&token.normalized_text))
        })
        .map(|token| token.id.clone())
        .collect()
}

fn token_refs_for_target(workspace: &EvidenceWorkspace, target_ref: &str) -> Vec<String> {
    if let Some(grammar) = workspace
        .grammar_candidates
        .iter()
        .find(|candidate| candidate.id == target_ref)
    {
        return vec![grammar.token_id.clone()];
    }
    if let Some(hint) = workspace
        .structural_hints
        .iter()
        .find(|hint| hint.id == target_ref)
    {
        return vec![hint.token_id.clone()];
    }
    if let Some(span) = workspace
        .span_candidates
        .iter()
        .find(|span| span.id == target_ref)
    {
        return span.token_refs.clone();
    }
    if let Some(sense) = workspace
        .lexical_sense_candidates
        .iter()
        .find(|sense| sense.id == target_ref)
    {
        return vec![sense.token_id.clone()];
    }
    if let Some(meaning) = workspace
        .candidate_meanings
        .iter()
        .find(|meaning| meaning.id == target_ref)
    {
        return meaning.token_refs.clone();
    }
    Vec::new()
}

fn ids_if_match<T, F>(items: &[T], target_ref: &str, id_fn: F) -> Vec<String>
where
    F: Fn(&T) -> &String,
{
    items
        .iter()
        .filter_map(|item| {
            let id = id_fn(item);
            if id.as_str() == target_ref {
                Some(id.clone())
            } else {
                None
            }
        })
        .collect()
}

fn capitalize(value: &str) -> String {
    let mut chars = value.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().chain(chars).collect(),
        None => String::new(),
    }
}
