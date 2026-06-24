from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


STOP_TERMS = {
    "and",
    "are",
    "but",
    "for",
    "from",
    "into",
    "that",
    "the",
    "their",
    "this",
    "with",
}


@dataclass(frozen=True)
class SemanticComponent:
    path: str
    subject: str
    content_hash: str
    semantic_hash: str
    identifiers: tuple[str, ...] = field(default_factory=tuple)
    terms: tuple[str, ...] = field(default_factory=tuple)

    @property
    def node_key(self) -> str:
        return f"N:component:{self.content_hash[:16]}"

    @property
    def pointer_key(self) -> str:
        return f"H:component:{self.content_hash[:16]}"

    def to_node(self) -> HypergraphNode:
        return HypergraphNode(
            self.node_key,
            self.path,
            (
                ("pointer", self.pointer_key),
                ("subject", self.subject),
                ("content_hash", self.content_hash),
                ("semantic_hash", self.semantic_hash),
                ("identifier_count", str(len(self.identifiers))),
                ("term_count", str(len(self.terms))),
            ),
        )


@dataclass(frozen=True)
class PeripheryImpression:
    narrative_subject: str
    periphery_term: str
    relation_back: str
    hiding_behind: str = ""
    turned_aspect: str = ""
    nearby_association: str = ""
    evidence_pointers: tuple[str, ...] = field(default_factory=tuple)
    weight: int = 1
    stability: str = "unstable"

    @property
    def impression_hash(self) -> str:
        return _digest(
            "|".join(
                (
                    self.narrative_subject,
                    self.periphery_term,
                    self.relation_back,
                    self.hiding_behind,
                    self.turned_aspect,
                    self.nearby_association,
                    ",".join(self.evidence_pointers),
                    str(self.weight),
                    self.stability,
                )
            )
        )

    @property
    def node_key(self) -> str:
        return f"N:periphery:{self.impression_hash[:16]}"

    def to_node(self) -> HypergraphNode:
        return HypergraphNode(
            self.node_key,
            self.periphery_term,
            (
                ("narrative_subject", self.narrative_subject),
                ("relation_back", self.relation_back),
                ("hiding_behind", self.hiding_behind or "unknown"),
                ("turned_aspect", self.turned_aspect or "unknown"),
                ("nearby_association", self.nearby_association or "unknown"),
                ("weight", str(self.weight)),
                ("stability", self.stability),
            ),
        )


@dataclass(frozen=True)
class SemanticHashIndex:
    index_id: str
    root: str
    components: tuple[SemanticComponent, ...]
    impressions: tuple[PeripheryImpression, ...] = field(default_factory=tuple)
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.index_id and self.components)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = _safe_key(self.index_id)
        index_node = HypergraphNode(
            f"N:index:{graph_id}",
            self.index_id,
            (("root", self.root), ("component_count", str(len(self.components))), ("impression_count", str(len(self.impressions)))),
        )
        outside_node = HypergraphNode("N:outside:semantic_proof", "semantic proof not established by hash index")
        nodes: list[HypergraphNode] = [index_node, outside_node]
        edges: list[HypergraphEdge] = []
        seen_terms: set[str] = set()
        for component in self.components:
            nodes.append(component.to_node())
            edges.append(
                HypergraphEdge(
                    f"E:indexes:{component.content_hash[:16]}",
                    "indexes",
                    (("index", index_node.key), ("component", component.node_key)),
                    (("pointer", component.pointer_key),),
                )
            )
            for term in component.terms[:12]:
                term_key = f"N:term:{_safe_key(term)}"
                if term_key not in seen_terms:
                    nodes.append(HypergraphNode(term_key, term))
                    seen_terms.add(term_key)
                edges.append(
                    HypergraphEdge(
                        f"E:points_to:{component.content_hash[:8]}_{_safe_key(term)}",
                        "points_to",
                        (("component", component.node_key), ("term", term_key)),
                        (("semantic_hash", component.semantic_hash),),
                    )
                )
            edges.append(
                HypergraphEdge(
                    f"E:bounds:{component.content_hash[:16]}",
                    "bounds",
                    (("component", component.node_key), ("outside", outside_node.key)),
                )
            )
        component_by_pointer = {component.pointer_key: component for component in self.components}
        for impression in self.impressions:
            nodes.append(impression.to_node())
            narrative_key = f"N:narrative:{_safe_key(impression.narrative_subject)}"
            term_key = f"N:term:{_safe_key(impression.periphery_term)}"
            if narrative_key not in {node.key for node in nodes}:
                nodes.append(HypergraphNode(narrative_key, impression.narrative_subject))
            if term_key not in {node.key for node in nodes}:
                nodes.append(HypergraphNode(term_key, impression.periphery_term))
            edges.append(
                HypergraphEdge(
                    f"E:notices:{impression.impression_hash[:16]}",
                    "notices",
                    (("narrative", narrative_key), ("periphery", impression.node_key), ("term", term_key)),
                    (("weight", str(impression.weight)), ("stability", impression.stability)),
                )
            )
            if impression.hiding_behind:
                hidden_key = f"N:term:{_safe_key(impression.hiding_behind)}"
                nodes.append(HypergraphNode(hidden_key, impression.hiding_behind))
                edges.append(
                    HypergraphEdge(
                        f"E:hides_behind:{impression.impression_hash[:16]}",
                        "hides_behind",
                        (("periphery", impression.node_key), ("hidden", hidden_key)),
                    )
                )
            if impression.nearby_association:
                nearby_key = f"N:term:{_safe_key(impression.nearby_association)}"
                nodes.append(HypergraphNode(nearby_key, impression.nearby_association))
                edges.append(
                    HypergraphEdge(
                        f"E:entangles:{impression.impression_hash[:16]}",
                        "entangles",
                        (("periphery", impression.node_key), ("nearby", nearby_key)),
                    )
                )
            for pointer in impression.evidence_pointers:
                component = component_by_pointer.get(pointer)
                if component:
                    edges.append(
                        HypergraphEdge(
                            f"E:supports:{impression.impression_hash[:8]}_{component.content_hash[:8]}",
                            "supports",
                            (("periphery", impression.node_key), ("component", component.node_key)),
                            (("pointer", pointer),),
                        )
                    )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.index_id} Semantic Hash Index",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG semantic-hash-index"),
                ("root", self.root),
            ),
            outside=self.residual_outside or ("hashes preserve pointers; semantic truth remains revisable",),
        )

    def render(self) -> str:
        return self.to_hypergraph().render()


def build_semantic_hash_index(
    root: str | Path,
    *,
    index_id: str = "semantic_hash_index",
    paths: tuple[str | Path, ...] = (),
    impressions: tuple[PeripheryImpression, ...] = (),
) -> SemanticHashIndex:
    root_path = Path(root)
    selected_paths = [Path(path) for path in paths] if paths else sorted(root_path.rglob("*.sop"))
    components = []
    for path in selected_paths:
        full_path = path if path.is_absolute() else root_path / path
        if not full_path.is_file() or _skip_path(full_path):
            continue
        text = full_path.read_text(encoding="utf-8")
        relative = str(full_path.relative_to(root_path)).replace("\\", "/") if full_path.is_relative_to(root_path) else str(full_path)
        components.append(build_semantic_component(relative, text))
    return SemanticHashIndex(
        index_id=index_id,
        root=str(root_path),
        components=tuple(components),
        impressions=impressions,
        residual_outside=("semantic associations are extracted surfaces, not final proof",),
    )


def build_semantic_component(path: str, text: str) -> SemanticComponent:
    subject = _extract_subject(text)
    identifiers = _extract_identifiers(text)
    terms = _extract_terms(text, identifiers)
    content_hash = _digest(text)
    semantic_hash = _digest("|".join((subject, ",".join(identifiers), ",".join(terms))))
    return SemanticComponent(
        path=path,
        subject=subject,
        content_hash=content_hash,
        semantic_hash=semantic_hash,
        identifiers=identifiers,
        terms=terms,
    )


def _extract_subject(text: str) -> str:
    match = re.search(r"^Subject:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else "unnamed SOP component"


def _extract_identifiers(text: str) -> tuple[str, ...]:
    identifiers = sorted({match.strip() for match in re.findall(r"\[([^\]]+)\]", text) if match.strip()})
    return tuple(identifiers)


def _extract_terms(text: str, identifiers: tuple[str, ...]) -> tuple[str, ...]:
    raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text)
    identifier_terms = " ".join(identifiers).replace("_", " ").split()
    terms = {
        term.lower()
        for term in (*raw_terms, *identifier_terms)
        if len(term) >= 3 and term.lower() not in STOP_TERMS
    }
    return tuple(sorted(terms))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())


def _skip_path(path: Path) -> bool:
    parts = set(path.parts)
    if ".git" in parts or "__pycache__" in parts:
        return True
    normalized_parts = tuple(part.lower() for part in path.parts)
    return "events" in normalized_parts and "indexes" in normalized_parts
