use serde::{Deserialize, Serialize};

use crate::core::{
    CandidateRelation, ContradictionRecord, GrammarCandidate, LexicalSenseCandidate, SpanCandidate,
    StructuralHint, SupportRecord, Token,
};
use crate::evidence::{EvidenceBundle, EvidenceWorkspace};
use crate::providers::{ProviderProvenance, ProviderSuggestion};
use crate::wobble::WobbleVector;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SidecarTaskKind {
    RankSenses,
    ProposeSpans,
    ObjectToParse,
    AnswerObjection,
    RunFacultyValidation,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SidecarTaskPromptContract {
    pub contract_id: String,
    pub task_kind: SidecarTaskKind,
    pub instruction: String,
    pub allowed_evidence: Vec<String>,
    pub required_output: Vec<String>,
    pub forbidden_authority: Vec<String>,
    pub response_format: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SidecarPromptEnvelope {
    pub task_kind: SidecarTaskKind,
    pub target_ref: String,
    pub question: String,
    pub task_contract: SidecarTaskPromptContract,
    pub evidence: SidecarEvidenceBundle,
    pub response_contract: SidecarResponseContract,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SidecarEvidenceBundle {
    pub workspace_id: String,
    pub input_text: String,
    pub target_bundle: EvidenceBundle,
    pub tokens: Vec<Token>,
    pub grammar_candidates: Vec<GrammarCandidate>,
    pub structural_hints: Vec<StructuralHint>,
    pub span_candidates: Vec<SpanCandidate>,
    pub lexical_sense_candidates: Vec<LexicalSenseCandidate>,
    pub candidate_relations: Vec<CandidateRelation>,
    pub support_records: Vec<SupportRecord>,
    pub contradiction_records: Vec<ContradictionRecord>,
    pub latest_wobble: Option<WobbleVector>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SidecarResponseContract {
    pub must_return_provider_suggestions: bool,
    pub must_include_rationale: bool,
    pub must_preserve_uncertainty: bool,
    pub may_not_emit_glyphs: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LmStudioSidecarConfig {
    pub endpoint: String,
    pub model: String,
    pub temperature: f32,
    pub max_tokens: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LmStudioChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LmStudioChatRequest {
    pub model: String,
    pub messages: Vec<LmStudioChatMessage>,
    pub temperature: f32,
    pub max_tokens: usize,
    pub stream: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LmStudioProviderSuggestionResponse {
    pub provider_suggestions: Vec<ProviderSuggestion>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OllamaSidecarConfig {
    pub endpoint: String,
    pub model: String,
    pub temperature: f32,
    pub num_predict: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OllamaChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OllamaChatOptions {
    pub temperature: f32,
    pub num_predict: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OllamaChatRequest {
    pub model: String,
    pub messages: Vec<OllamaChatMessage>,
    pub stream: bool,
    pub options: OllamaChatOptions,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OllamaChatResponse {
    pub message: OllamaChatMessage,
    pub done: Option<bool>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SidecarResponseValidationStatus {
    Accepted,
    Repaired,
    Rejected,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SidecarValidatedParseOutcome {
    pub status: SidecarResponseValidationStatus,
    pub provider_suggestions: Vec<ProviderSuggestion>,
    pub repair_notes: Vec<String>,
    pub rejection_reason: Option<String>,
}

impl Default for SidecarResponseContract {
    fn default() -> Self {
        Self {
            must_return_provider_suggestions: true,
            must_include_rationale: true,
            must_preserve_uncertainty: true,
            may_not_emit_glyphs: true,
        }
    }
}

pub fn sidecar_task_prompt_contract(task_kind: SidecarTaskKind) -> SidecarTaskPromptContract {
    let (allowed_evidence, required_output, forbidden_authority) = match task_kind {
        SidecarTaskKind::RankSenses => (
            strings(&[
                "tokens",
                "grammar_candidates",
                "structural_hints",
                "lexical_sense_candidates",
                "support_records",
                "latest_wobble",
            ]),
            strings(&[
                "provider_suggestions",
                "ranked sense refs or preserved ambiguity",
                "rationale citing evidence refs",
            ]),
            strings(&[
                "no new lexical definitions",
                "no glyph creation",
                "no deletion of lower-ranked senses",
            ]),
        ),
        SidecarTaskKind::ProposeSpans => (
            strings(&[
                "tokens",
                "grammar_candidates",
                "structural_hints",
                "span_candidates",
                "latest_wobble",
            ]),
            strings(&[
                "provider_suggestions",
                "span proposal refs or uncertainty refs",
                "rationale citing token and structural refs",
            ]),
            strings(&[
                "no graph relations",
                "no glyph creation",
                "no unsupported span collapse",
            ]),
        ),
        SidecarTaskKind::ObjectToParse => (
            strings(&[
                "target_bundle",
                "candidate_relations",
                "support_records",
                "contradiction_records",
                "latest_wobble",
            ]),
            strings(&[
                "provider_suggestions",
                "typed objection payload",
                "rationale citing the challenged candidate and evidence refs",
            ]),
            strings(&[
                "no replacement parse as final truth",
                "no glyph creation",
                "no objection without cited evidence",
            ]),
        ),
        SidecarTaskKind::AnswerObjection => (
            strings(&[
                "target_bundle",
                "support_records",
                "contradiction_records",
                "provider_deliberation_refs",
                "latest_wobble",
            ]),
            strings(&[
                "provider_suggestions",
                "answer payload with supported, conceded, or unresolved status",
                "rationale citing objection and support refs",
            ]),
            strings(&[
                "no silent dismissal of objections",
                "no glyph creation",
                "no unsupported certainty",
            ]),
        ),
        SidecarTaskKind::RunFacultyValidation => (
            strings(&[
                "target_bundle",
                "tokens",
                "grammar_candidates",
                "candidate_relations",
                "support_records",
                "contradiction_records",
                "latest_wobble",
            ]),
            strings(&[
                "provider_suggestions",
                "faculty report payload",
                "vetoes from Honesty or Security when applicable",
                "rationale citing evidence refs",
            ]),
            strings(&[
                "no stabilization decision",
                "no glyph creation",
                "no missing lineage",
            ]),
        ),
    };

    SidecarTaskPromptContract {
        contract_id: format!("sidecar_task_prompt_contract_v0:{:?}", task_kind),
        task_kind,
        instruction: task_instruction_text(task_kind).to_string(),
        allowed_evidence,
        required_output,
        forbidden_authority,
        response_format: "LmStudioProviderSuggestionResponse".to_string(),
    }
}

pub fn task_instruction_text(task_kind: SidecarTaskKind) -> &'static str {
    match task_kind {
        SidecarTaskKind::RankSenses => {
            "Rank the provided lexical sense candidates for the target in context. Preserve ties and uncertainty when evidence is insufficient."
        }
        SidecarTaskKind::ProposeSpans => {
            "Propose bounded token spans that are supported by token, grammar, and structural evidence. Mark weak boundaries explicitly."
        }
        SidecarTaskKind::ObjectToParse => {
            "Object to a candidate parse only when evidence shows contradiction, weak support, boundary ambiguity, or incoherent relation fit."
        }
        SidecarTaskKind::AnswerObjection => {
            "Answer the objection from available evidence. Concede unresolved ambiguity when support does not defeat the objection."
        }
        SidecarTaskKind::RunFacultyValidation => {
            "Run Observer, Honesty, Security, Planner, Weaver, Scribe, and Refiner validation from dual-hemisphere perspectives and report votes, vetoes, and uncertainty."
        }
    }
}

fn strings(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_string()).collect()
}

impl LmStudioSidecarConfig {
    pub fn default_local(model: impl Into<String>) -> Self {
        Self {
            endpoint: "http://127.0.0.1:1234/v1/chat/completions".to_string(),
            model: model.into(),
            temperature: 0.1,
            max_tokens: 1200,
        }
    }
}

impl OllamaSidecarConfig {
    pub fn default_local(model: impl Into<String>) -> Self {
        Self {
            endpoint: "http://127.0.0.1:11434/api/chat".to_string(),
            model: model.into(),
            temperature: 0.1,
            num_predict: 1200,
        }
    }
}

impl SidecarPromptEnvelope {
    pub fn for_target(
        workspace: &EvidenceWorkspace,
        task_kind: SidecarTaskKind,
        target_ref: impl Into<String>,
        question: impl Into<String>,
    ) -> Self {
        let target_ref = target_ref.into();
        Self {
            task_kind,
            target_ref: target_ref.clone(),
            question: question.into(),
            task_contract: sidecar_task_prompt_contract(task_kind),
            evidence: SidecarEvidenceBundle::for_target(workspace, &target_ref),
            response_contract: SidecarResponseContract::default(),
        }
    }

    pub fn to_lm_studio_chat_request(
        &self,
        config: &LmStudioSidecarConfig,
    ) -> serde_json::Result<LmStudioChatRequest> {
        let envelope_json = serde_json::to_string_pretty(self)?;
        Ok(LmStudioChatRequest {
            model: config.model.clone(),
            messages: vec![
                LmStudioChatMessage {
                    role: "system".to_string(),
                    content: format!(
                        "Return only JSON matching the SLM sidecar response contract. Provider suggestions are evidence, not graph identities. Task instruction: {}",
                        self.task_contract.instruction
                    ),
                },
                LmStudioChatMessage {
                    role: "user".to_string(),
                    content: envelope_json,
                },
            ],
            temperature: config.temperature,
            max_tokens: config.max_tokens,
            stream: false,
        })
    }

    pub fn to_ollama_chat_request(
        &self,
        config: &OllamaSidecarConfig,
    ) -> serde_json::Result<OllamaChatRequest> {
        let envelope_json = serde_json::to_string_pretty(self)?;
        Ok(OllamaChatRequest {
            model: config.model.clone(),
            messages: vec![
                OllamaChatMessage {
                    role: "system".to_string(),
                    content: format!(
                        "Return only JSON matching the SLM sidecar response contract. Provider suggestions are evidence, not graph identities. Task instruction: {}",
                        self.task_contract.instruction
                    ),
                },
                OllamaChatMessage {
                    role: "user".to_string(),
                    content: envelope_json,
                },
            ],
            stream: false,
            options: OllamaChatOptions {
                temperature: config.temperature,
                num_predict: config.num_predict,
            },
        })
    }
}

pub fn parse_lm_studio_provider_suggestions(
    assistant_message_content: &str,
) -> serde_json::Result<Vec<ProviderSuggestion>> {
    let parsed: LmStudioProviderSuggestionResponse =
        serde_json::from_str(assistant_message_content)?;
    Ok(parsed.provider_suggestions)
}

pub fn parse_lm_studio_provider_suggestions_validated(
    assistant_message_content: &str,
    rejection_provenance: ProviderProvenance,
    target_ref: impl Into<String>,
) -> SidecarValidatedParseOutcome {
    let target_ref = target_ref.into();
    match parse_lm_studio_response_value(assistant_message_content) {
        Ok((value, mut repair_notes)) => {
            if value.is_array() {
                repair_notes.push("wrapped top-level provider suggestion array".to_string());
            }
            match response_from_value(value) {
                Ok(parsed) if !parsed.provider_suggestions.is_empty() => {
                    let status = if repair_notes.is_empty() {
                        SidecarResponseValidationStatus::Accepted
                    } else {
                        SidecarResponseValidationStatus::Repaired
                    };
                    SidecarValidatedParseOutcome {
                        status,
                        provider_suggestions: parsed.provider_suggestions,
                        repair_notes,
                        rejection_reason: None,
                    }
                }
                Ok(_) => rejected_sidecar_outcome(
                    rejection_provenance,
                    target_ref,
                    "sidecar response contained no provider_suggestions",
                    repair_notes,
                ),
                Err(error) => {
                    repair_notes.push(format!("structured JSON failed response contract: {error}"));
                    rejected_sidecar_outcome(
                        rejection_provenance,
                        target_ref,
                        "sidecar response did not match provider suggestion contract",
                        repair_notes,
                    )
                }
            }
        }
        Err(error) => rejected_sidecar_outcome(
            rejection_provenance,
            target_ref,
            &format!("sidecar response was not parseable JSON: {error}"),
            Vec::new(),
        ),
    }
}

pub fn parse_ollama_provider_suggestions_validated(
    response_body_or_message_content: &str,
    rejection_provenance: ProviderProvenance,
    target_ref: impl Into<String>,
) -> SidecarValidatedParseOutcome {
    let target_ref = target_ref.into();
    let assistant_content =
        match serde_json::from_str::<OllamaChatResponse>(response_body_or_message_content) {
            Ok(response) => response.message.content,
            Err(_) => response_body_or_message_content.to_string(),
        };

    parse_lm_studio_provider_suggestions_validated(
        &assistant_content,
        rejection_provenance,
        target_ref,
    )
}

fn parse_lm_studio_response_value(
    assistant_message_content: &str,
) -> serde_json::Result<(serde_json::Value, Vec<String>)> {
    let trimmed = assistant_message_content.trim();
    let mut repair_notes = Vec::new();
    if let Ok(value) = serde_json::from_str::<serde_json::Value>(trimmed) {
        return Ok((value, repair_notes));
    }

    if let Some(fenced) = extract_markdown_json_fence(trimmed) {
        repair_notes.push("extracted JSON from markdown fence".to_string());
        let value = serde_json::from_str::<serde_json::Value>(&fenced)?;
        return Ok((value, repair_notes));
    }

    if let Some(extracted) = extract_json_object_substring(trimmed) {
        repair_notes.push("extracted JSON object from surrounding text".to_string());
        let value = serde_json::from_str::<serde_json::Value>(&extracted)?;
        return Ok((value, repair_notes));
    }

    serde_json::from_str::<serde_json::Value>(trimmed).map(|value| (value, repair_notes))
}

fn response_from_value(
    value: serde_json::Value,
) -> serde_json::Result<LmStudioProviderSuggestionResponse> {
    if value.is_array() {
        return serde_json::from_value(serde_json::json!({
            "provider_suggestions": value
        }));
    }
    serde_json::from_value(value)
}

fn extract_markdown_json_fence(value: &str) -> Option<String> {
    let without_start = value
        .strip_prefix("```json")
        .or_else(|| value.strip_prefix("```"))?;
    let without_start = without_start.trim_start();
    let end = without_start.rfind("```")?;
    Some(without_start[..end].trim().to_string())
}

fn extract_json_object_substring(value: &str) -> Option<String> {
    let start = value.find('{')?;
    let end = value.rfind('}')?;
    if end <= start {
        return None;
    }
    Some(value[start..=end].to_string())
}

fn rejected_sidecar_outcome(
    provenance: ProviderProvenance,
    target_ref: String,
    reason: &str,
    repair_notes: Vec<String>,
) -> SidecarValidatedParseOutcome {
    SidecarValidatedParseOutcome {
        status: SidecarResponseValidationStatus::Rejected,
        provider_suggestions: vec![rejection_objection(provenance, target_ref, reason)],
        repair_notes,
        rejection_reason: Some(reason.to_string()),
    }
}

pub fn rejection_objection(
    provenance: ProviderProvenance,
    target_ref: impl Into<String>,
    reason: impl Into<String>,
) -> ProviderSuggestion {
    ProviderSuggestion::objection_with_class(
        provenance,
        "sidecar-response-validation-rejection",
        target_ref,
        "lineage_gap",
        reason,
    )
}

impl SidecarEvidenceBundle {
    pub fn for_target(workspace: &EvidenceWorkspace, target_ref: &str) -> Self {
        let target_bundle = if workspace.tokens.iter().any(|token| token.id == target_ref) {
            workspace.evidence_bundle_for_token(target_ref)
        } else {
            workspace.evidence_bundle_for_candidate(target_ref)
        };

        Self {
            workspace_id: workspace.workspace_id.clone(),
            input_text: workspace.input_text.clone(),
            tokens: workspace.tokens.clone(),
            grammar_candidates: workspace.grammar_candidates.clone(),
            structural_hints: workspace.structural_hints.clone(),
            span_candidates: workspace.span_candidates.clone(),
            lexical_sense_candidates: workspace.lexical_sense_candidates.clone(),
            candidate_relations: workspace.candidate_relations.clone(),
            support_records: workspace.support_records.clone(),
            contradiction_records: workspace.contradiction_records.clone(),
            latest_wobble: workspace.wobble_vectors.last().cloned(),
            target_bundle,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        LmStudioSidecarConfig, OllamaChatResponse, OllamaSidecarConfig, SidecarPromptEnvelope,
        SidecarResponseValidationStatus, SidecarTaskKind,
        parse_lm_studio_provider_suggestions_validated,
        parse_ollama_provider_suggestions_validated, sidecar_task_prompt_contract,
    };
    use crate::evidence::EvidenceWorkspace;
    use crate::providers::{MockProvider, ProviderSuggestion, ProviderSuggestionKind};

    #[test]
    fn all_sidecar_task_prompt_contracts_declare_boundaries() {
        for task_kind in [
            SidecarTaskKind::RankSenses,
            SidecarTaskKind::ProposeSpans,
            SidecarTaskKind::ObjectToParse,
            SidecarTaskKind::AnswerObjection,
            SidecarTaskKind::RunFacultyValidation,
        ] {
            let contract = sidecar_task_prompt_contract(task_kind);
            assert_eq!(contract.task_kind, task_kind);
            assert!(!contract.instruction.is_empty());
            assert!(!contract.allowed_evidence.is_empty());
            assert!(
                contract
                    .required_output
                    .contains(&"provider_suggestions".to_string())
            );
            assert!(
                contract
                    .forbidden_authority
                    .iter()
                    .any(|rule| rule.contains("glyph creation"))
            );
            assert_eq!(
                contract.response_format,
                "LmStudioProviderSuggestionResponse"
            );
        }
    }

    #[test]
    fn prompt_envelope_embeds_task_contract_for_transport() {
        let workspace =
            EvidenceWorkspace::from_text("sidecar-contract-fixture", "Design a compiler.");
        let envelope = SidecarPromptEnvelope::for_target(
            &workspace,
            SidecarTaskKind::RankSenses,
            "tok:0",
            "Rank candidate senses for the first token.",
        );
        let config = LmStudioSidecarConfig::default_local("mock-model");
        let request = envelope
            .to_lm_studio_chat_request(&config)
            .expect("LM Studio request serializes");
        let user_payload = &request.messages[1].content;

        assert_eq!(
            envelope.task_contract.task_kind,
            SidecarTaskKind::RankSenses
        );
        assert!(user_payload.contains("task_contract"));
        assert!(user_payload.contains("allowed_evidence"));
        assert!(request.messages[0].content.contains("Task instruction"));
        assert!(request.messages[0].content.contains("Rank the provided"));
    }

    #[test]
    fn validated_parser_accepts_exact_provider_suggestion_json() {
        let provenance = MockProvider::provenance_for("lm-studio-validator");
        let suggestion = ProviderSuggestion::objection_with_class(
            provenance.clone(),
            "valid-objection",
            "meaning:Candidate",
            "unsupported_claim",
            "candidate needs more support",
        );
        let response = serde_json::json!({
            "provider_suggestions": [suggestion]
        })
        .to_string();

        let outcome = parse_lm_studio_provider_suggestions_validated(
            &response,
            provenance,
            "meaning:Candidate",
        );

        assert_eq!(outcome.status, SidecarResponseValidationStatus::Accepted);
        assert!(outcome.repair_notes.is_empty());
        assert_eq!(outcome.provider_suggestions.len(), 1);
        assert_eq!(
            outcome.provider_suggestions[0].kind,
            ProviderSuggestionKind::Objection
        );
    }

    #[test]
    fn validated_parser_repairs_fenced_top_level_array_json() {
        let provenance = MockProvider::provenance_for("lm-studio-validator");
        let suggestion = ProviderSuggestion::answer_with_kind(
            provenance.clone(),
            "valid-answer",
            "meaning:Candidate",
            "defers",
            "answer defers because evidence is incomplete",
        );
        let response = format!(
            "```json\n{}\n```",
            serde_json::to_string(&vec![suggestion]).expect("suggestion serializes")
        );

        let outcome = parse_lm_studio_provider_suggestions_validated(
            &response,
            provenance,
            "meaning:Candidate",
        );

        assert_eq!(outcome.status, SidecarResponseValidationStatus::Repaired);
        assert!(
            outcome
                .repair_notes
                .iter()
                .any(|note| note.contains("fence"))
        );
        assert!(
            outcome
                .repair_notes
                .iter()
                .any(|note| note.contains("wrapped top-level"))
        );
        assert_eq!(outcome.provider_suggestions.len(), 1);
        assert_eq!(
            outcome.provider_suggestions[0].kind,
            ProviderSuggestionKind::Answer
        );
    }

    #[test]
    fn validated_parser_rejects_freeform_as_objection_evidence() {
        let provenance = MockProvider::provenance_for("lm-studio-validator");
        let outcome = parse_lm_studio_provider_suggestions_validated(
            "I think this is probably fine, no JSON needed.",
            provenance,
            "meaning:Candidate",
        );

        assert_eq!(outcome.status, SidecarResponseValidationStatus::Rejected);
        assert!(outcome.rejection_reason.is_some());
        assert_eq!(outcome.provider_suggestions.len(), 1);
        assert_eq!(
            outcome.provider_suggestions[0].kind,
            ProviderSuggestionKind::Objection
        );
        assert_eq!(
            outcome.provider_suggestions[0]
                .disagreement_class
                .as_deref(),
            Some("lineage_gap")
        );
        assert_eq!(
            outcome.provider_suggestions[0].meaning_kind, None,
            "rejected freeform must not become graph evidence"
        );
    }

    #[test]
    fn ollama_request_embeds_sidecar_prompt_envelope_without_network_call() {
        let workspace =
            EvidenceWorkspace::from_text("ollama-contract-fixture", "Design a compiler.");
        let envelope = SidecarPromptEnvelope::for_target(
            &workspace,
            SidecarTaskKind::RunFacultyValidation,
            "meaning:DesignAction",
            "Run faculty validation for the candidate action.",
        );
        let config = OllamaSidecarConfig::default_local("llama3.2");
        let request = envelope
            .to_ollama_chat_request(&config)
            .expect("Ollama request serializes");

        assert_eq!(config.endpoint, "http://127.0.0.1:11434/api/chat");
        assert_eq!(request.model, "llama3.2");
        assert!(!request.stream);
        assert_eq!(request.options.temperature, 0.1);
        assert!(request.messages[0].content.contains("Task instruction"));
        assert!(request.messages[1].content.contains("task_contract"));
    }

    #[test]
    fn ollama_response_parser_uses_validated_sidecar_content() {
        let provenance = MockProvider::provenance_for("ollama-validator");
        let suggestion = ProviderSuggestion::objection_with_class(
            provenance.clone(),
            "ollama-objection",
            "meaning:Candidate",
            "unsupported_claim",
            "candidate needs more support",
        );
        let content = serde_json::json!({
            "provider_suggestions": [suggestion]
        })
        .to_string();
        let response = OllamaChatResponse {
            message: super::OllamaChatMessage {
                role: "assistant".to_string(),
                content,
            },
            done: Some(true),
        };

        let outcome = parse_ollama_provider_suggestions_validated(
            &serde_json::to_string(&response).expect("Ollama response serializes"),
            provenance,
            "meaning:Candidate",
        );

        assert_eq!(outcome.status, SidecarResponseValidationStatus::Accepted);
        assert_eq!(outcome.provider_suggestions.len(), 1);
        assert_eq!(
            outcome.provider_suggestions[0].kind,
            ProviderSuggestionKind::Objection
        );
    }
}
