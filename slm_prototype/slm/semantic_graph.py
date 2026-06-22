"""Append-only semantic graph with immutable glyph identities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from typing import Any


class GlyphKind(str, Enum):
    TOKEN = "token"
    ROLE = "role"
    SUBJECT = "subject"
    ACTION = "action"
    RELATION = "relation"
    MODIFIER = "modifier"
    CONSTRAINT = "constraint"


@dataclass(frozen=True)
class Glyph:
    semantic_id: str
    kind: GlyphKind
    label: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str
    activation: float
    evidence: str
    retired: bool = False


@dataclass(frozen=True)
class GraphEvent:
    event_type: str
    target: str
    detail: dict[str, Any]


class SemanticGraph:
    """Immutable glyph store with append-only links and events."""

    def __init__(self) -> None:
        self._ids = count(1)
        self.glyphs: dict[str, Glyph] = {}
        self.edges: list[Edge] = []
        self.events: list[GraphEvent] = []

    def create_glyph(self, kind: GlyphKind, label: str, payload: dict[str, Any] | None = None) -> Glyph:
        semantic_id = f"g{next(self._ids):04d}"
        glyph = Glyph(semantic_id=semantic_id, kind=kind, label=label, payload=payload or {})
        self.glyphs[semantic_id] = glyph
        self.events.append(GraphEvent("create", semantic_id, {"kind": kind.value, "label": label}))
        return glyph

    def link(self, source: str, target: str, relation: str, activation: float, evidence: str) -> Edge:
        edge = Edge(source, target, relation, activation, evidence)
        self.edges.append(edge)
        self.events.append(
            GraphEvent(
                "link",
                source,
                {"target": target, "relation": relation, "activation": activation, "evidence": evidence},
            )
        )
        return edge

    def activate(self, target: str, amount: float, reason: str) -> None:
        self.events.append(GraphEvent("activate", target, {"amount": amount, "reason": reason}))

    def retire_edge(self, edge: Edge, reason: str) -> None:
        self.edges.append(
            Edge(
                source=edge.source,
                target=edge.target,
                relation=edge.relation,
                activation=edge.activation,
                evidence=edge.evidence,
                retired=True,
            )
        )
        self.events.append(GraphEvent("retire", edge.source, {"target": edge.target, "reason": reason}))
