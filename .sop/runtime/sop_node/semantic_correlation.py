from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import combinations

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord
from .semantic_table import DIMENSION_WEIGHTS, SemanticHashTable, _normalize_dimension, _normalize_value


DEFAULT_EXCLUDED_BUCKET_VALUES = {
    "description",
    "file",
    "format",
    "must",
    "not",
    "should",
    "sop",
    "source",
    "subject",
}


@dataclass(frozen=True)
class AttentionDirective:
    directive_id: str
    purpose: str
    identified: str
    inside_terms: tuple[str, ...] = field(default_factory=tuple)
    boundary_terms: tuple[str, ...] = field(default_factory=tuple)
    subject_a: str = ""
    subject_b: str = ""
    tilt_dimensions: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    boost: int = 3

    @property
    def node_key(self) -> str:
        return f"N:directive:{_safe_key(self.directive_id)}"

    @property
    def normalized_buckets(self) -> frozenset[tuple[str, str]]:
        buckets: set[tuple[str, str]] = set()
        buckets.update(("term", _normalize_value(term)) for term in self.inside_terms)
        buckets.update(("term", _normalize_value(term)) for term in self.boundary_terms)
        if self.subject_a:
            buckets.add(("subject", _normalize_value(self.subject_a)))
            buckets.add(("term", _normalize_value(self.subject_a)))
        if self.subject_b:
            buckets.add(("subject", _normalize_value(self.subject_b)))
            buckets.add(("term", _normalize_value(self.subject_b)))
        buckets.update((_normalize_dimension(name), _normalize_value(value)) for name, value in self.tilt_dimensions)
        return frozenset(buckets)

    def to_node(self) -> HypergraphNode:
        return HypergraphNode(
            self.node_key,
            self.purpose,
            (
                ("identified", self.identified),
                ("inside", ",".join(self.inside_terms)),
                ("boundary", ",".join(self.boundary_terms)),
                ("subject_a", self.subject_a or "none"),
                ("subject_b", self.subject_b or "none"),
                ("boost", str(self.boost)),
            ),
        )


@dataclass(frozen=True)
class BucketCorrelation:
    bucket_a: tuple[str, str]
    bucket_b: tuple[str, str]
    base_weight: int
    directive_weight: int = 0
    shared_pointers: tuple[str, ...] = field(default_factory=tuple)
    directives: tuple[str, ...] = field(default_factory=tuple)

    @property
    def total_weight(self) -> int:
        return self.base_weight + self.directive_weight

    @property
    def edge_key(self) -> str:
        return f"E:correlates:{_safe_key(_bucket_label(self.bucket_a) + '_' + _bucket_label(self.bucket_b))}"


@dataclass(frozen=True)
class SemanticCorrelationGraph:
    graph_id: str
    correlations: tuple[BucketCorrelation, ...]
    directives: tuple[AttentionDirective, ...] = field(default_factory=tuple)
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.graph_id and self.correlations)

    def top_correlations(self, limit: int = 12) -> tuple[BucketCorrelation, ...]:
        return tuple(sorted(self.correlations, key=lambda item: (-item.total_weight, _bucket_label(item.bucket_a), _bucket_label(item.bucket_b)))[:limit])

    def to_hypergraph(self, *, limit: int = 12) -> HypergraphRecord:
        graph_key = _safe_key(self.graph_id)
        graph_node = HypergraphNode(f"N:index:{graph_key}", self.graph_id, (("correlation_count", str(len(self.correlations))),))
        outside_node = HypergraphNode("N:outside:semantic_proof", "semantic proof not established by attention direction graph")
        nodes: list[HypergraphNode] = [graph_node, outside_node]
        edges: list[HypergraphEdge] = []
        directive_by_id = {directive.directive_id: directive for directive in self.directives}
        for directive in self.directives:
            nodes.append(directive.to_node())
            for bucket in directive.normalized_buckets:
                bucket_key = _bucket_node_key(bucket)
                nodes.append(_bucket_node(bucket))
                edges.append(
                    HypergraphEdge(
                        f"E:tilts:{_safe_key(directive.directive_id + '_' + _bucket_label(bucket))}",
                        "tilts",
                        (("directive", directive.node_key), ("bucket", bucket_key)),
                        (("boost", str(directive.boost)),),
                    )
                )
            edges.append(
                HypergraphEdge(
                    f"E:captures:{_safe_key(directive.directive_id)}",
                    "captures",
                    (("directive", directive.node_key), ("outside", outside_node.key)),
                    (("identified", directive.identified), ("inside", ",".join(directive.inside_terms)), ("boundary", ",".join(directive.boundary_terms))),
                )
            )
        for correlation in self.top_correlations(limit):
            nodes.append(_bucket_node(correlation.bucket_a))
            nodes.append(_bucket_node(correlation.bucket_b))
            participants = (
                ("bucket_a", _bucket_node_key(correlation.bucket_a)),
                ("bucket_b", _bucket_node_key(correlation.bucket_b)),
            )
            edges.append(
                HypergraphEdge(
                    correlation.edge_key,
                    "correlates",
                    participants,
                    (
                        ("base_weight", str(correlation.base_weight)),
                        ("directive_weight", str(correlation.directive_weight)),
                        ("total_weight", str(correlation.total_weight)),
                        ("shared_count", str(len(correlation.shared_pointers))),
                    ),
                )
            )
            for directive_id in correlation.directives:
                directive = directive_by_id.get(directive_id)
                if directive:
                    association_key = f"N:term:{_safe_key(directive.identified + '_association_surface')}"
                    nodes.append(HypergraphNode(association_key, f"{directive.identified} association surface"))
                    edges.append(
                        HypergraphEdge(
                            f"E:associates:{_safe_key(directive_id + '_' + _bucket_label(correlation.bucket_a) + '_' + _bucket_label(correlation.bucket_b))}",
                            "associates",
                            (("directive", directive.node_key), ("bucket_a", _bucket_node_key(correlation.bucket_a)), ("bucket_b", _bucket_node_key(correlation.bucket_b)), ("surface", association_key)),
                            (("subject_a", directive.subject_a), ("subject_b", directive.subject_b), ("total_weight", str(correlation.total_weight))),
                        )
                    )
        edges.append(
            HypergraphEdge(
                f"E:bounds:{graph_key}",
                "bounds",
                (("graph", graph_node.key), ("outside", outside_node.key)),
            )
        )
        return HypergraphRecord(
            graph_id=graph_key,
            label=f"{self.graph_id} Semantic Correlation Graph",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(("format_profile", "SOP-HG semantic-correlation-graph"),),
            outside=self.residual_outside or ("directive tilt steers attention but does not prove semantic association",),
        )


def build_semantic_correlation_graph(
    table: SemanticHashTable,
    *,
    graph_id: str = "semantic_correlation_graph",
    directives: tuple[AttentionDirective, ...] = (),
    dimensions: tuple[str, ...] = ("subject", "term", "periphery_term", "hiding_behind", "turned_aspect", "nearby_association"),
    excluded_bucket_values: tuple[str, ...] = tuple(sorted(DEFAULT_EXCLUDED_BUCKET_VALUES)),
    min_shared: int = 1,
    max_correlations: int = 128,
) -> SemanticCorrelationGraph:
    allowed_dimensions = {_normalize_dimension(dimension) for dimension in dimensions}
    excluded_values = {_normalize_value(value) for value in excluded_bucket_values}
    buckets = {
        bucket: pointers
        for bucket, pointers in table.buckets.items()
        if bucket[0] in allowed_dimensions and bucket[1] not in excluded_values and len(pointers) >= min_shared
    }
    directive_buckets_by_id = {directive.directive_id: directive.normalized_buckets for directive in directives}
    correlations: list[BucketCorrelation] = []
    for bucket_a, bucket_b in combinations(sorted(buckets), 2):
        shared = tuple(sorted(set(buckets[bucket_a]).intersection(buckets[bucket_b])))
        if len(shared) < min_shared:
            continue
        base_weight = _bucket_weight(bucket_a, bucket_b, len(shared))
        directive_ids = []
        directive_weight = 0
        for directive in directives:
            directive_buckets = directive_buckets_by_id[directive.directive_id]
            matches = int(bucket_a in directive_buckets) + int(bucket_b in directive_buckets)
            if matches:
                directive_ids.append(directive.directive_id)
                directive_weight += directive.boost * matches
        correlations.append(
            BucketCorrelation(
                bucket_a=bucket_a,
                bucket_b=bucket_b,
                base_weight=base_weight,
                directive_weight=directive_weight,
                shared_pointers=shared,
                directives=tuple(directive_ids),
            )
        )
    ordered = tuple(sorted(correlations, key=lambda item: (-item.total_weight, -item.base_weight, _bucket_label(item.bucket_a), _bucket_label(item.bucket_b)))[:max_correlations])
    return SemanticCorrelationGraph(
        graph_id=graph_id,
        correlations=ordered,
        directives=directives,
        residual_outside=("weighted bucket correlation directs attention and does not prove meaning",),
    )


def parse_directive(
    *,
    directive_id: str,
    purpose: str,
    identified: str,
    inside: Iterable[str] = (),
    boundary: Iterable[str] = (),
    subject_a: str = "",
    subject_b: str = "",
    tilt: Iterable[tuple[str, str]] = (),
    boost: int = 3,
) -> AttentionDirective:
    return AttentionDirective(
        directive_id=directive_id,
        purpose=purpose,
        identified=identified,
        inside_terms=tuple(inside),
        boundary_terms=tuple(boundary),
        subject_a=subject_a,
        subject_b=subject_b,
        tilt_dimensions=tuple(tilt),
        boost=boost,
    )


def _bucket_weight(bucket_a: tuple[str, str], bucket_b: tuple[str, str], shared_count: int) -> int:
    return shared_count * (DIMENSION_WEIGHTS.get(bucket_a[0], 1) + DIMENSION_WEIGHTS.get(bucket_b[0], 1))


def _bucket_label(bucket: tuple[str, str]) -> str:
    return f"{bucket[0]}:{bucket[1]}"


def _bucket_node_key(bucket: tuple[str, str]) -> str:
    return f"N:bucket:{_safe_key(_bucket_label(bucket))}"


def _bucket_node(bucket: tuple[str, str]) -> HypergraphNode:
    return HypergraphNode(
        _bucket_node_key(bucket),
        _bucket_label(bucket),
        (("dimension", bucket[0]), ("value", bucket[1])),
    )


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
