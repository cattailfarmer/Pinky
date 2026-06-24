from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class HypergraphNode:
    key: str
    label: str
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def kind(self) -> str:
        parts = self.key.split(":", 2)
        return parts[1] if len(parts) >= 3 and parts[0] == "N" else "unknown"

    def render(self) -> list[str]:
        lines = [f"  + [{self.key}] is {self.label}"]
        for name, value in self.attributes:
            lines.append(f"    = {name}: {value}")
        return lines


@dataclass(frozen=True)
class HypergraphEdge:
    key: str
    kind: str
    participants: tuple[tuple[str, str], ...]
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def render(self, graph_key: str) -> str:
        fields = [self.kind]
        fields.extend(f"{role}={node_key}" for role, node_key in self.participants)
        fields.extend(f"{name}={value}" for name, value in self.attributes)
        return f"/ [{self.key}] -({'; '.join(fields)})> [{graph_key}]"


@dataclass(frozen=True)
class HypergraphRecord:
    graph_id: str
    label: str
    nodes: tuple[HypergraphNode, ...]
    edges: tuple[HypergraphEdge, ...]
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def graph_key(self) -> str:
        return f"Graph:{self.graph_id}"

    @property
    def ready(self) -> bool:
        node_keys = {node.key for node in self.nodes}
        return bool(
            self.graph_id
            and self.nodes
            and all(_valid_node_key(node.key) for node in self.nodes)
            and all(_valid_edge_key(edge.key) for edge in self.edges)
            and all(node_key in node_keys for edge in self.edges for _, node_key in edge.participants)
        )

    def render(self) -> str:
        lines = [
            f"Subject: {self.label}",
            "",
            f"& [{self.graph_key}] is a SOP-HG graph",
            "  = format: SOP-HG",
        ]
        for name, value in self.attributes:
            lines.append(f"  = {name}: {value}")
        lines.append("")
        for node in self.nodes:
            lines.extend(node.render())
        lines.append("")
        for edge in self.edges:
            lines.append(edge.render(self.graph_key))
        if self.outside:
            lines.append("")
            for item in self.outside:
                lines.append(f"- outside: {item}")
        return "\n".join(lines)


def scan_to_hypergraph(scan) -> HypergraphRecord:
    graph_id = _safe_key(scan.scan_id)
    nodes: list[HypergraphNode] = [
        HypergraphNode(f"N:bookend:{_safe_key(scan.base_ref)}", scan.base_ref),
        HypergraphNode(f"N:bookend:{_safe_key(scan.head_ref)}", scan.head_ref),
        HypergraphNode(f"N:event:{graph_id}", scan.scan_id),
        HypergraphNode("N:outside:semantic_truth", "semantic truth not proven by correlation heat"),
    ]
    edges: list[HypergraphEdge] = [
        HypergraphEdge(
            f"E:span:{graph_id}",
            "span",
            (
                ("start", f"N:bookend:{_safe_key(scan.base_ref)}"),
                ("end", f"N:bookend:{_safe_key(scan.head_ref)}"),
                ("event", f"N:event:{graph_id}"),
            ),
        )
    ]
    for index, change in enumerate(scan.changes, start=1):
        file_key = f"N:file:{_safe_key(change.path)}"
        nodes.append(
            HypergraphNode(
                file_key,
                change.path,
                (("status", change.status), ("additions", str(change.additions)), ("deletions", str(change.deletions))),
            )
        )
        edges.append(
            HypergraphEdge(
                f"E:changed:{graph_id}_{index:03d}",
                "changed",
                (("event", f"N:event:{graph_id}"), ("file", file_key)),
            )
        )
    seen_layers: set[str] = set()
    for signal in scan.signals:
        signal_key = f"N:signal:{_safe_key(signal.subject_key)}"
        nodes.append(
            HypergraphNode(
                signal_key,
                signal.subject_key,
                (("touch_count", str(signal.touch_count)), ("heat", str(signal.heat))),
            )
        )
        layer_key = f"N:layer:{_safe_key(signal.layer)}"
        if layer_key not in seen_layers:
            nodes.append(HypergraphNode(layer_key, signal.layer, (("retention_policy", signal.retention_policy),)))
            seen_layers.add(layer_key)
        participant_files = tuple(("file", f"N:file:{_safe_key(path)}") for path in signal.evidence_paths)
        edges.append(
            HypergraphEdge(
                f"E:touches:{_safe_key(signal.subject_key)}",
                "touches",
                (("signal", signal_key), *participant_files),
                (("weight", str(signal.heat)),),
            )
        )
        edges.append(
            HypergraphEdge(
                f"E:classifies:{_safe_key(signal.subject_key)}",
                "classifies",
                (("signal", signal_key), ("layer", layer_key)),
                (("retention", signal.retention_policy),),
            )
        )
        edges.append(
            HypergraphEdge(
                f"E:bounds:{_safe_key(signal.subject_key)}",
                "bounds",
                (("signal", signal_key), ("outside", "N:outside:semantic_truth")),
            )
        )
    return HypergraphRecord(
        graph_id=graph_id,
        label=f"{scan.scan_id} Hypergraph",
        nodes=tuple(_dedupe_nodes(nodes)),
        edges=tuple(edges),
        attributes=(
            ("source_scan_id", scan.scan_id),
            ("base_ref", scan.base_ref),
            ("head_ref", scan.head_ref),
        ),
        outside=(scan.residual_outside,),
    )


def parse_edge_participants(edge_line: str) -> tuple[tuple[str, str], ...]:
    match = re.search(r"-\((?P<body>.*)\)>", edge_line)
    if not match:
        return ()
    fields = [field.strip() for field in match.group("body").split(";") if field.strip()]
    participants = []
    for field in fields[1:]:
        if "=" not in field:
            continue
        role, value = field.split("=", 1)
        if value.startswith("N:"):
            participants.append((role.strip(), value.strip()))
    return tuple(participants)


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _valid_node_key(key: str) -> bool:
    return bool(re.match(r"^N:[A-Za-z0-9_]+:[A-Za-z0-9_]+$", key))


def _valid_edge_key(key: str) -> bool:
    return bool(re.match(r"^E:[A-Za-z0-9_]+:[A-Za-z0-9_]+$", key))
