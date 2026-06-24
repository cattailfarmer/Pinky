from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord
from .semantic_index import PeripheryImpression, SemanticHashIndex


EXACT_DIMENSIONS = {"pointer", "content_hash", "semantic_hash", "path"}
DIMENSION_WEIGHTS = {
    "pointer": 20,
    "content_hash": 20,
    "semantic_hash": 12,
    "path": 12,
    "subject": 5,
    "narrative_subject": 5,
    "identifier": 4,
    "term": 3,
    "periphery_term": 3,
    "hiding_behind": 2,
    "turned_aspect": 2,
    "nearby_association": 2,
    "stability": 1,
    "kind": 1,
}


@dataclass(frozen=True)
class SemanticTableEntry:
    pointer: str
    kind: str
    label: str
    node_key: str
    dimensions: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def normalized_dimensions(self) -> tuple[tuple[str, str], ...]:
        return tuple((_normalize_dimension(name), _normalize_value(value)) for name, value in self.dimensions)

    def values_for(self, dimension: str) -> frozenset[str]:
        normalized_dimension = _normalize_dimension(dimension)
        return frozenset(value for name, value in self.normalized_dimensions if name == normalized_dimension)

    def to_node(self) -> HypergraphNode:
        return HypergraphNode(
            self.node_key,
            self.label,
            (
                ("pointer", self.pointer),
                ("kind", self.kind),
                ("dimension_count", str(len(self.normalized_dimensions))),
            ),
        )


@dataclass(frozen=True)
class SemanticLookupResult:
    entry: SemanticTableEntry
    score: int
    matched_dimensions: tuple[tuple[str, str], ...]

    @property
    def pointer(self) -> str:
        return self.entry.pointer


@dataclass(frozen=True)
class SemanticHashTable:
    table_id: str
    entries: tuple[SemanticTableEntry, ...]
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.table_id and self.entries)

    @property
    def buckets(self) -> dict[tuple[str, str], tuple[str, ...]]:
        bucket_map: dict[tuple[str, str], set[str]] = {}
        for entry in self.entries:
            for dimension in entry.normalized_dimensions:
                bucket_map.setdefault(dimension, set()).add(entry.pointer)
        return {key: tuple(sorted(pointers)) for key, pointers in sorted(bucket_map.items())}

    def lookup(
        self,
        query: Mapping[str, str | Iterable[str]],
        *,
        mode: str = "permissive",
        limit: int | None = None,
    ) -> tuple[SemanticLookupResult, ...]:
        normalized_query = _normalize_query(query)
        if mode not in {"exact", "strict", "permissive", "inclusive"}:
            raise ValueError(f"unknown semantic lookup mode: {mode}")
        if mode == "exact" and not any(name in EXACT_DIMENSIONS for name, _ in normalized_query):
            return ()
        results = []
        for entry in self.entries:
            matches = _matched_dimensions(entry, normalized_query)
            if not matches:
                continue
            if mode == "strict" and not _matches_every_query_dimension(matches, normalized_query):
                continue
            if mode == "exact" and not any(name in EXACT_DIMENSIONS for name, _ in matches):
                continue
            score = sum(DIMENSION_WEIGHTS.get(name, 1) for name, _ in matches)
            results.append(SemanticLookupResult(entry, score, tuple(sorted(matches))))
        ordered = tuple(sorted(results, key=lambda result: (-result.score, result.entry.pointer)))
        return ordered[:limit] if limit is not None else ordered

    def to_hypergraph(
        self,
        *,
        query: Mapping[str, str | Iterable[str]] | None = None,
        mode: str = "permissive",
        limit: int = 12,
        max_entries: int = 24,
        max_bucket_edges: int = 200,
    ) -> HypergraphRecord:
        graph_id = _safe_key(self.table_id)
        table_node = HypergraphNode(
            f"N:table:{graph_id}",
            self.table_id,
            (("entry_count", str(len(self.entries))), ("bucket_count", str(len(self.buckets)))),
        )
        outside_node = HypergraphNode("N:outside:semantic_identity", "semantic identity not proven by inclusive table match")
        nodes: list[HypergraphNode] = [table_node, outside_node]
        edges: list[HypergraphEdge] = []
        normalized_query = _normalize_query(query) if query else ()
        query_results = self.lookup(query, mode=mode, limit=limit) if query else ()
        visible_entries = (
            tuple(result.entry for result in query_results)
            if query
            else self.entries[:max_entries]
        )
        visible_dimension_set = set(normalized_query)
        bucket_edge_count = 0
        for entry in visible_entries:
            nodes.append(entry.to_node())
            dimensions = _visible_dimensions(entry, visible_dimension_set, query is not None)
            for dimension, value in dimensions:
                if bucket_edge_count >= max_bucket_edges:
                    break
                bucket_node = HypergraphNode(
                    f"N:bucket:{_safe_key(dimension + '_' + value)}",
                    f"{dimension}:{value}",
                    (("dimension", dimension), ("value", value)),
                )
                nodes.append(bucket_node)
                edges.append(
                    HypergraphEdge(
                        f"E:indexes:{_safe_key(dimension + '_' + value)}_{_safe_key(entry.pointer)}",
                        "indexes",
                        (("table", table_node.key), ("bucket", bucket_node.key), ("entry", entry.node_key)),
                    )
                )
                bucket_edge_count += 1
            edges.append(
                HypergraphEdge(
                    f"E:bounds:{_safe_key(entry.pointer)}",
                    "bounds",
                    (("entry", entry.node_key), ("outside", outside_node.key)),
                )
            )
        if query:
            query_node = HypergraphNode(
                f"N:query:{graph_id}_{_safe_key(mode)}",
                f"{mode} lookup",
                tuple((name, value) for name, value in normalized_query),
            )
            nodes.append(query_node)
            for result in query_results:
                for dimension, value in result.matched_dimensions:
                    bucket_key = f"N:bucket:{_safe_key(dimension + '_' + value)}"
                    nodes.append(
                        HypergraphNode(
                            bucket_key,
                            f"{dimension}:{value}",
                            (("dimension", dimension), ("value", value)),
                        )
                    )
                    edges.append(
                        HypergraphEdge(
                            f"E:intersects:{_safe_key(mode)}_{_safe_key(dimension + '_' + value)}",
                            "intersects",
                            (("query", query_node.key), ("bucket", bucket_key)),
                        )
                    )
                edges.append(
                    HypergraphEdge(
                        f"E:retrieves:{_safe_key(mode)}_{_safe_key(result.pointer)}",
                        "retrieves",
                        (("query", query_node.key), ("entry", result.entry.node_key)),
                        (("score", str(result.score)), ("matched_count", str(len(result.matched_dimensions)))),
                    )
                )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.table_id} Semantic Hash Table",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(("format_profile", "SOP-HG semantic-hash-table"),),
            outside=self.residual_outside or ("permissive bucket retrieval is candidate evidence, not proof",),
        )


def build_semantic_hash_table(index: SemanticHashIndex, *, table_id: str | None = None) -> SemanticHashTable:
    entries: list[SemanticTableEntry] = []
    for component in index.components:
        dimensions = [
            ("kind", "component"),
            ("pointer", component.pointer_key),
            ("path", component.path),
            ("content_hash", component.content_hash),
            ("semantic_hash", component.semantic_hash),
            ("subject", component.subject),
        ]
        dimensions.extend(("identifier", identifier) for identifier in component.identifiers)
        dimensions.extend(("term", term) for term in component.terms)
        entries.append(
            SemanticTableEntry(
                pointer=component.pointer_key,
                kind="component",
                label=component.path,
                node_key=component.node_key,
                dimensions=tuple(dimensions),
            )
        )
    for impression in index.impressions:
        entries.append(_impression_to_entry(impression))
    return SemanticHashTable(
        table_id=table_id or f"{index.index_id}_table",
        entries=tuple(entries),
        residual_outside=("inclusive semantic lookup retrieves candidates and does not prove identity",),
    )


def _impression_to_entry(impression: PeripheryImpression) -> SemanticTableEntry:
    pointer = f"H:impression:{impression.impression_hash[:16]}"
    dimensions = [
        ("kind", "impression"),
        ("pointer", pointer),
        ("narrative_subject", impression.narrative_subject),
        ("periphery_term", impression.periphery_term),
        ("term", impression.periphery_term),
        ("relation_back", impression.relation_back),
        ("stability", impression.stability),
    ]
    if impression.hiding_behind:
        dimensions.append(("hiding_behind", impression.hiding_behind))
        dimensions.append(("term", impression.hiding_behind))
    if impression.turned_aspect:
        dimensions.append(("turned_aspect", impression.turned_aspect))
        dimensions.append(("term", impression.turned_aspect))
    if impression.nearby_association:
        dimensions.append(("nearby_association", impression.nearby_association))
        dimensions.append(("term", impression.nearby_association))
    dimensions.extend(("evidence_pointer", pointer) for pointer in impression.evidence_pointers)
    return SemanticTableEntry(
        pointer=pointer,
        kind="impression",
        label=impression.periphery_term,
        node_key=impression.node_key,
        dimensions=tuple(dimensions),
    )


def _matched_dimensions(
    entry: SemanticTableEntry,
    normalized_query: tuple[tuple[str, str], ...],
) -> frozenset[tuple[str, str]]:
    entry_dimensions = set(entry.normalized_dimensions)
    return frozenset(dimension for dimension in normalized_query if dimension in entry_dimensions)


def _matches_every_query_dimension(
    matches: frozenset[tuple[str, str]],
    normalized_query: tuple[tuple[str, str], ...],
) -> bool:
    matched_names = {name for name, _ in matches}
    query_names = {name for name, _ in normalized_query}
    return query_names.issubset(matched_names)


def _visible_dimensions(
    entry: SemanticTableEntry,
    visible_dimension_set: set[tuple[str, str]],
    query_limited: bool,
) -> tuple[tuple[str, str], ...]:
    dimensions = tuple(dict.fromkeys(entry.normalized_dimensions))
    if not query_limited:
        return dimensions[:24]
    core_names = {"pointer", "path", "subject", "narrative_subject", "kind"}
    visible = [
        dimension
        for dimension in dimensions
        if dimension in visible_dimension_set or dimension[0] in core_names
    ]
    return tuple(visible[:24])


def _normalize_query(query: Mapping[str, str | Iterable[str]]) -> tuple[tuple[str, str], ...]:
    normalized = []
    for dimension, values in query.items():
        if isinstance(values, str):
            iterable_values = (values,)
        else:
            iterable_values = tuple(values)
        normalized.extend((_normalize_dimension(dimension), _normalize_value(value)) for value in iterable_values)
    return tuple(sorted(set(normalized)))


def _normalize_dimension(value: str) -> str:
    return _safe_key(value).lower()


def _normalize_value(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().lower())


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
