from __future__ import annotations

import re
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


VALID_POSITIONS = {"focus", "periphery", "liminal", "narrative"}
VALID_RELATIONS = {"attends", "orbits", "correlates", "causes", "draws_attention", "digests", "bounds"}


@dataclass(frozen=True)
class AttentionPoint:
    subject_key: str
    label: str
    position: str
    weight: int = 1
    reason: str = ""

    def __post_init__(self) -> None:
        if self.position not in VALID_POSITIONS:
            raise ValueError(f"unknown attention position: {self.position}")

    @property
    def node_key(self) -> str:
        return f"N:{self.position}:{_safe_key(self.subject_key)}"

    def to_node(self) -> HypergraphNode:
        attributes = (("weight", str(self.weight)),)
        if self.reason:
            attributes = attributes + (("reason", self.reason),)
        return HypergraphNode(self.node_key, self.label, attributes)


@dataclass(frozen=True)
class AttentionRelation:
    relation_key: str
    kind: str
    source_key: str
    target_key: str
    weight: int = 1
    evidence: str = ""
    hypothesis: bool = False

    def __post_init__(self) -> None:
        if self.kind not in VALID_RELATIONS:
            raise ValueError(f"unknown attention relation: {self.kind}")

    @property
    def edge_key(self) -> str:
        return f"E:{self.kind}:{_safe_key(self.relation_key)}"

    def to_edge(self, node_by_subject: dict[str, AttentionPoint]) -> HypergraphEdge:
        attributes = (("weight", str(self.weight)),)
        if self.evidence:
            attributes = attributes + (("evidence", self.evidence),)
        if self.hypothesis:
            attributes = attributes + (("causal_status", "hypothesis"),)
        return HypergraphEdge(
            self.edge_key,
            self.kind,
            (
                ("source", node_by_subject[self.source_key].node_key),
                ("target", node_by_subject[self.target_key].node_key),
            ),
            attributes,
        )


@dataclass(frozen=True)
class AttentionFrame:
    frame_id: str
    narrative_moment: str
    operation_stage: str
    points: tuple[AttentionPoint, ...]
    relations: tuple[AttentionRelation, ...]
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        point_keys = {point.subject_key for point in self.points}
        return bool(
            self.frame_id
            and self.narrative_moment
            and any(point.position == "focus" for point in self.points)
            and all(relation.source_key in point_keys and relation.target_key in point_keys for relation in self.relations)
        )

    def to_hypergraph(self) -> HypergraphRecord:
        frame_key = _safe_key(self.frame_id)
        narrative_key = f"N:narrative:{frame_key}"
        nodes = [
            HypergraphNode(
                narrative_key,
                self.narrative_moment,
                (("operation_stage", self.operation_stage),),
            )
        ]
        nodes.extend(point.to_node() for point in self.points)
        node_by_subject = {point.subject_key: point for point in self.points}
        edges = [
            HypergraphEdge(
                f"E:digests:{frame_key}_{_safe_key(point.subject_key)}",
                "digests",
                (("narrative", narrative_key), ("target", point.node_key)),
                (("target_position", point.position), ("weight", str(point.weight))),
            )
            for point in self.points
            if point.position in {"focus", "periphery"}
        ]
        edges.extend(relation.to_edge(node_by_subject) for relation in self.relations)
        return HypergraphRecord(
            graph_id=frame_key,
            label=f"{self.frame_id} Attention Frame",
            nodes=tuple(nodes),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG attention-layer-frame"),
                ("operation_stage", self.operation_stage),
            ),
            outside=self.residual_outside,
        )

    def render(self) -> str:
        return self.to_hypergraph().render()


def build_attention_frame(
    *,
    frame_id: str,
    narrative_moment: str,
    operation_stage: str,
    focus_terms: tuple[str, ...],
    periphery_terms: tuple[str, ...] = (),
    causal_pairs: tuple[tuple[str, str], ...] = (),
    correlation_pairs: tuple[tuple[str, str], ...] = (),
) -> AttentionFrame:
    points = [
        AttentionPoint(term, term, "focus", weight=5, reason="explicit focus term")
        for term in focus_terms
    ]
    points.extend(
        AttentionPoint(term, term, "periphery", weight=2, reason="available related term")
        for term in periphery_terms
        if term not in focus_terms
    )
    known_terms = {point.subject_key for point in points}
    relations = []
    for left, right in correlation_pairs:
        if left in known_terms and right in known_terms:
            relations.append(
                AttentionRelation(
                    f"{left}_to_{right}_correlation",
                    "correlates",
                    left,
                    right,
                    weight=3,
                    evidence="declared correlation pair",
                )
            )
            relations.append(
                AttentionRelation(
                    f"{left}_draws_{right}",
                    "draws_attention",
                    left,
                    right,
                    weight=3,
                    evidence="correlation draw",
                )
            )
    for left, right in causal_pairs:
        if left in known_terms and right in known_terms:
            relations.append(
                AttentionRelation(
                    f"{left}_causes_{right}",
                    "causes",
                    left,
                    right,
                    weight=4,
                    evidence="declared causal pair",
                    hypothesis=True,
                )
            )
            relations.append(
                AttentionRelation(
                    f"{left}_draws_{right}",
                    "draws_attention",
                    left,
                    right,
                    weight=4,
                    evidence="causal draw hypothesis",
                    hypothesis=True,
                )
            )
    return AttentionFrame(
        frame_id=frame_id,
        narrative_moment=narrative_moment,
        operation_stage=operation_stage,
        points=tuple(points),
        relations=tuple(relations),
        residual_outside=("causation remains hypothesis until supported by evidence",),
    )


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"
