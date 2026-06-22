"""Compact structured primer emission."""

from __future__ import annotations

from slm.candidate_roles import RoleCandidate
from slm.semantic_graph import GlyphKind, SemanticGraph
from slm.tokenizer import Token
from slm.wobble import WobbleReport


def build_primer(
    tokens: list[Token],
    candidates: dict[int, list[RoleCandidate]],
    structural_hints: object,
    graph: SemanticGraph,
    wobble: WobbleReport,
) -> dict[str, object]:
    subjects = _glyphs_by_kind(graph, GlyphKind.SUBJECT)
    actions = _glyphs_by_kind(graph, GlyphKind.ACTION)
    relations = [
        {
            "source": edge.source,
            "target": edge.target,
            "relation": edge.relation,
            "activation": edge.activation,
            "evidence": edge.evidence,
        }
        for edge in graph.edges
        if not edge.retired and edge.relation in {"structural_hint", "scopes_over", "object_or_target", "actor_or_context"}
    ]
    return {
        "version": "slm-primer/0.1",
        "surface": " ".join(token.text for token in tokens),
        "subjects": subjects,
        "actions": actions,
        "relations": relations,
        "modifiers": _glyphs_by_kind(graph, GlyphKind.MODIFIER),
        "constraints": _glyphs_by_kind(graph, GlyphKind.CONSTRAINT),
        "uncertainty": {
            "wobble": wobble.score,
            "factors": wobble.factors,
            "deferred_roles": {
                token.text: [
                    {"role": candidate.role, "activation": candidate.activation}
                    for candidate in candidates[token.index][1:4]
                ]
                for token in tokens
                if not token.is_punctuation and len(candidates[token.index]) > 1
            },
        },
    }


def _glyphs_by_kind(graph: SemanticGraph, kind: GlyphKind) -> list[dict[str, object]]:
    return [
        {"id": glyph.semantic_id, "label": glyph.label, **glyph.payload}
        for glyph in graph.glyphs.values()
        if glyph.kind == kind
    ]
