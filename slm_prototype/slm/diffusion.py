"""Semantic diffusion passes for progressive ambiguity reduction."""

from __future__ import annotations

from dataclasses import dataclass

from slm.candidate_roles import RoleCandidate, build_candidate_roles
from slm.primer import build_primer
from slm.semantic_graph import GlyphKind, SemanticGraph
from slm.tokenizer import Token, tokenize
from slm.wobble import WobbleReport, score_wobble


STRUCTURAL_ROLES = {"determiner", "preposition", "conjunction", "auxiliary", "modal", "punctuation"}


@dataclass(frozen=True)
class StructuralHint:
    source_token: int
    relation: str
    target_scope: list[int]
    activation: float
    reason: str


@dataclass(frozen=True)
class DiffusionSnapshot:
    pass_name: str
    summary: str
    graph: SemanticGraph


@dataclass(frozen=True)
class AnalysisResult:
    tokens: list[Token]
    candidates: dict[int, list[RoleCandidate]]
    structural_hints: list[StructuralHint]
    snapshots: list[DiffusionSnapshot]
    graph: SemanticGraph
    wobble: WobbleReport
    primer: dict[str, object]


def analyze(text: str) -> AnalysisResult:
    tokens = tokenize(text)
    candidates = build_candidate_roles(tokens)
    graph = SemanticGraph()
    token_glyphs = {
        token.index: graph.create_glyph(
            GlyphKind.TOKEN,
            token.text,
            {"index": token.index, "normalized": token.normalized},
        )
        for token in tokens
    }
    snapshots: list[DiffusionSnapshot] = [
        DiffusionSnapshot("tokenize", "Created immutable token glyphs.", graph)
    ]

    role_glyphs: dict[tuple[int, str], str] = {}
    for token in tokens:
        for candidate in candidates[token.index]:
            glyph = graph.create_glyph(
                GlyphKind.ROLE,
                f"{token.text}:{candidate.role}",
                {"token_index": token.index, "role": candidate.role, "source": candidate.source},
            )
            role_glyphs[(token.index, candidate.role)] = glyph.semantic_id
            graph.link(
                token_glyphs[token.index].semantic_id,
                glyph.semantic_id,
                "candidate_role",
                candidate.activation,
                candidate.source,
            )
    snapshots.append(DiffusionSnapshot("candidate_roles", "Attached ranked role possibilities.", graph))

    structural_hints = infer_structural_hints(tokens, candidates)
    for hint in structural_hints:
        relation_glyph = graph.create_glyph(
            GlyphKind.RELATION,
            hint.relation,
            {"source_token": hint.source_token, "target_scope": hint.target_scope},
        )
        graph.link(
            token_glyphs[hint.source_token].semantic_id,
            relation_glyph.semantic_id,
            "structural_hint",
            hint.activation,
            hint.reason,
        )
        for target in hint.target_scope:
            graph.link(
                relation_glyph.semantic_id,
                token_glyphs[target].semantic_id,
                "scopes_over",
                hint.activation,
                hint.reason,
            )
    snapshots.append(DiffusionSnapshot("structural_diffusion", "Structural words created relation scopes.", graph))

    bind_late_semantics(tokens, candidates, graph, token_glyphs)
    snapshots.append(DiffusionSnapshot("late_binding", "Open-class roles resolved only where support converged.", graph))

    wobble = score_wobble(tokens, candidates, structural_hints)
    primer = build_primer(tokens, candidates, structural_hints, graph, wobble)
    return AnalysisResult(tokens, candidates, structural_hints, snapshots, graph, wobble, primer)


def infer_structural_hints(tokens: list[Token], candidates: dict[int, list[RoleCandidate]]) -> list[StructuralHint]:
    hints: list[StructuralHint] = []
    for token in tokens:
        top_role = candidates[token.index][0].role
        if top_role == "determiner":
            scope = _following_content_span(tokens, token.index, stop_roles={"preposition", "punctuation"})
            hints.append(StructuralHint(token.index, "introduces_subject_candidate", scope, 0.86, "determiner scopes noun phrase"))
        elif top_role == "preposition":
            scope = _following_content_span(tokens, token.index, stop_roles={"punctuation", "conjunction"})
            hints.append(StructuralHint(token.index, "opens_relation_constraint", scope, 0.9, "preposition constrains nearby phrase"))
        elif top_role == "conjunction":
            hints.append(StructuralHint(token.index, "joins_parallel_scopes", [], 0.7, "conjunction suggests coordination"))
    return hints


def bind_late_semantics(
    tokens: list[Token],
    candidates: dict[int, list[RoleCandidate]],
    graph: SemanticGraph,
    token_glyphs: dict[int, object],
) -> None:
    content_tokens = [token for token in tokens if not token.is_punctuation]
    if not content_tokens:
        return

    action_token = _best_token_for_role(content_tokens, candidates, "verb")
    if action_token:
        action = graph.create_glyph(GlyphKind.ACTION, action_token.normalized, {"token_index": action_token.index})
        graph.link(token_glyphs[action_token.index].semantic_id, action.semantic_id, "late_bound_action", 0.76, "verb support plus position")

    noun_tokens = [token for token in content_tokens if _role_activation(candidates[token.index], "noun") >= 0.5]
    for noun_token in noun_tokens:
        subject = graph.create_glyph(GlyphKind.SUBJECT, noun_token.normalized, {"token_index": noun_token.index})
        confidence = _role_activation(candidates[noun_token.index], "noun")
        graph.link(token_glyphs[noun_token.index].semantic_id, subject.semantic_id, "late_bound_subject", confidence, "noun support survived diffusion")
        if action_token and noun_token.index != action_token.index:
            relation = "object_or_target" if noun_token.index > action_token.index else "actor_or_context"
            graph.link(action.semantic_id, subject.semantic_id, relation, min(confidence, 0.7), "late subject/action binding")


def _following_content_span(tokens: list[Token], start: int, stop_roles: set[str]) -> list[int]:
    span: list[int] = []
    for token in tokens[start + 1 :]:
        if token.is_punctuation:
            if "punctuation" in stop_roles:
                break
            continue
        if token.normalized in {"for", "to", "from", "with", "and", "or", "but"}:
            break
        span.append(token.index)
    return span


def _best_token_for_role(tokens: list[Token], candidates: dict[int, list[RoleCandidate]], role: str) -> Token | None:
    scored = [(token, _role_activation(candidates[token.index], role)) for token in tokens]
    token, score = max(scored, key=lambda item: item[1])
    return token if score >= 0.5 else None


def _role_activation(candidates: list[RoleCandidate], role: str) -> float:
    for candidate in candidates:
        if candidate.role == role:
            return candidate.activation
    return 0.0
