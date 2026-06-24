from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


PROFILE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("implementation_scaffold", ("implement", "runtime", "build", "test", "code", "command")),
    ("debug_scaffold", ("debug", "fault", "failure", "regression", "reverse", "trace")),
    ("branch_refinement_scaffold", ("branch", "bookend", "moment", "refinement")),
    ("concept_imagination_scaffold", ("concept", "imagination", "possibility", "speculative")),
    ("topology_map_scaffold", ("topology", "map", "periphery cell", "orbit")),
    ("seven_fold_weighted_map_scaffold", ("seven", "fold", "top three", "weighted", "pants")),
    ("corridor_navigation_scaffold", ("corridor", "navigate", "frame series", "identity probe")),
    ("resonance_governance_scaffold", ("resonance", "feedback", "recursion", "self reflective")),
    ("boundary_inspection_scaffold", ("boundary", "identity", "permission", "security", "honesty")),
    ("kernel_attention_scaffold", ("kernel", "compiled attention", "in-context", "security honesty")),
    ("model_transfer_scaffold", ("model", "transfer", "lens", "compare")),
    ("review_scaffold", ("review", "diff", "risk", "finding")),
    ("game_agent_scaffold", ("game", "stimulus", "state update", "policy choice")),
    ("manager_scaffold", ("manager", "worker", "queue", "slice", "spool")),
)

FRAME_REFERENCE_TERMS = (
    "image",
    "map",
    "ui",
    "simulation",
    "game",
    "visual",
    "screen",
    "model projection",
    "narrative",
    "presented frame",
)

HIGH_RISK_TERMS = (
    "credential",
    "destructive",
    "delete",
    "mutation",
    "authority",
    "hidden state",
    "proof",
    "security",
    "private",
)


@dataclass(frozen=True)
class ScaffoldFit:
    scaffold_profile: str
    score: int
    matched_terms: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CompiledAttentionPacket:
    packet_id: str
    job_need: str
    scaffold_profile: str
    fit_score: int
    matched_terms: tuple[str, ...]
    focus: str
    periphery_terms: tuple[str, ...]
    boundary: str
    outside: tuple[str, ...]
    depth: str
    gates: tuple[str, ...]
    expected_output: str
    balance_score: str
    balance_alert: str
    frame_reference_integrity: str
    rail_junctions: tuple[str, ...]
    source_refs: tuple[str, ...] = field(default_factory=tuple)

    @property
    def packet_key(self) -> str:
        return _safe_key(self.packet_id)

    @property
    def ready(self) -> bool:
        return bool(self.packet_id and self.job_need and self.scaffold_profile and self.expected_output)

    def render(self) -> str:
        lines = [
            "Subject: Compiled Attention Packet",
            "",
            f"& [CompiledAttentionPacket:{self.packet_key}] is a compiled_attention_packet",
            f"  + [packet_id] is {self.packet_id}",
            f"  + [job_need] is {self.job_need}",
            f"  + [scaffold_profile] is {self.scaffold_profile}",
            f"  + [fit_score] is {self.fit_score}",
            f"  + [matched_terms] is {', '.join(self.matched_terms) if self.matched_terms else 'none'}",
            f"  + [focus] is {self.focus}",
            f"  + [periphery] is {', '.join(self.periphery_terms) if self.periphery_terms else 'outside markers, source evidence, tests'}",
            f"  + [boundary] is {self.boundary}",
            f"  + [outside] is {', '.join(self.outside)}",
            f"  + [depth] is {self.depth}",
            f"  + [gates] is {', '.join(self.gates)}",
            f"  + [expected_output] is {self.expected_output}",
            f"  + [balance_score] is {self.balance_score}",
            f"  + [balance_alert] is {self.balance_alert}",
            f"  + [frame_reference_integrity] is {self.frame_reference_integrity}",
            f"  + [rail_junctions] is {', '.join(self.rail_junctions)}",
            f"  + [source_refs] is {', '.join(self.source_refs) if self.source_refs else 'none'}",
            "",
            "(compiled_attention_packet) :job_need: /scaffold_profile and gates/ |outside|",
            f"  + [job_need] is {self.job_need}",
            f"  + [scaffold_profile] is {self.scaffold_profile}",
            f"  + [balance_alert] is {self.balance_alert}",
            f"  + [frame_reference_integrity] is {self.frame_reference_integrity}",
            f"  |outside| {', '.join(self.outside)}",
        ]
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        packet_node = HypergraphNode(
            f"N:packet:{self.packet_key}",
            self.packet_id,
            (("scaffold_profile", self.scaffold_profile), ("fit_score", str(self.fit_score))),
        )
        job_node = HypergraphNode(f"N:job:{self.packet_key}", self.job_need)
        profile_node = HypergraphNode(f"N:scaffold:{_safe_key(self.scaffold_profile)}", self.scaffold_profile)
        balance_node = HypergraphNode(
            f"N:balance:{self.packet_key}",
            self.balance_score,
            (("balance_alert", self.balance_alert),),
        )
        frame_node = HypergraphNode(
            f"N:frame_reference:{self.packet_key}",
            self.frame_reference_integrity,
        )
        outside_node = HypergraphNode("N:outside:scaffold_compile_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [packet_node, job_node, profile_node, balance_node, frame_node, outside_node]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:compiles:{self.packet_key}",
                "compiles",
                (("job", job_node.key), ("profile", profile_node.key), ("packet", packet_node.key)),
                (("fit_score", str(self.fit_score)),),
            ),
            HypergraphEdge(
                f"E:checks_balance:{self.packet_key}",
                "checks_balance",
                (("packet", packet_node.key), ("balance", balance_node.key), ("outside", outside_node.key)),
            ),
            HypergraphEdge(
                f"E:checks_frame:{self.packet_key}",
                "checks_frame",
                (("packet", packet_node.key), ("frame_reference", frame_node.key), ("outside", outside_node.key)),
            ),
        ]
        for gate in self.gates:
            gate_node = HypergraphNode(f"N:gate:{_safe_key(gate)}", gate)
            nodes.append(gate_node)
            edges.append(
                HypergraphEdge(
                    f"E:gates:{self.packet_key}_{_safe_key(gate)}",
                    "gates",
                    (("packet", packet_node.key), ("gate", gate_node.key)),
                )
            )
        return HypergraphRecord(
            graph_id=self.packet_key,
            label=f"{self.packet_id} Compiled Attention Packet",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG compiled-attention-packet"),
                ("scaffold_profile", self.scaffold_profile),
                ("balance_score", self.balance_score),
            ),
            outside=self.outside,
        )


def build_compiled_attention_packet(
    *,
    packet_id: str,
    job_need: str,
    output_target: str = "inspectable SOP record",
    model_lane: str = "codex",
    depth: str = "slender",
    periphery_terms: Iterable[str] = (),
    source_refs: Iterable[str] = (),
) -> CompiledAttentionPacket:
    normalized_periphery = tuple(_parse_items(periphery_terms))
    normalized_sources = tuple(_parse_items(source_refs))
    fit = select_scaffold_profile(job_need)
    balance_score, balance_alert = assess_balance(job_need, normalized_periphery)
    frame_reference_integrity = assess_frame_reference_integrity(job_need, normalized_periphery)
    gates = (
        "source_preservation",
        "outside_preservation",
        "balance_check",
        "frame_reference_check",
        "validation_check",
        "codex_review",
    )
    rail_junctions = (
        "capture_job_need",
        "select_scaffold_profile",
        "bind_boundary_and_outside",
        "check_balance",
        "check_frame_reference",
        "emit_packet",
    )
    outside = (
        "hidden model state",
        "unvalidated scaffold optimization",
        "automatic worker launch",
        "proof beyond cited sources",
    )
    boundary = (
        f"{model_lane} owns execution; packet remains guidance until output target "
        f"{output_target} is produced and reviewed"
    )
    focus = _focus_from_job_need(job_need)
    return CompiledAttentionPacket(
        packet_id=packet_id,
        job_need=job_need,
        scaffold_profile=fit.scaffold_profile,
        fit_score=fit.score,
        matched_terms=fit.matched_terms,
        focus=focus,
        periphery_terms=normalized_periphery,
        boundary=boundary,
        outside=outside,
        depth=depth,
        gates=gates,
        expected_output=output_target,
        balance_score=balance_score,
        balance_alert=balance_alert,
        frame_reference_integrity=frame_reference_integrity,
        rail_junctions=rail_junctions,
        source_refs=normalized_sources,
    )


def select_scaffold_profile(job_need: str) -> ScaffoldFit:
    lower_job = job_need.lower()
    scored: list[ScaffoldFit] = []
    profile_priority = {profile: index for index, (profile, _) in enumerate(PROFILE_KEYWORDS)}
    for profile, keywords in PROFILE_KEYWORDS:
        matches = tuple(keyword for keyword in keywords if keyword in lower_job)
        if matches:
            scored.append(ScaffoldFit(profile, score=len(matches), matched_terms=matches))
    if not scored:
        return ScaffoldFit("implementation_scaffold", score=1, matched_terms=("default",))
    return max(scored, key=lambda item: (item.score, -profile_priority[item.scaffold_profile]))


def assess_balance(job_need: str, periphery_terms: Iterable[str] = ()) -> tuple[str, str]:
    lower_job = job_need.lower()
    periphery = tuple(_parse_items(periphery_terms))
    risk_hits = tuple(term for term in HIGH_RISK_TERMS if term in lower_job)
    if len(periphery) > 8:
        return "watch", "periphery_flood"
    if len(periphery) == 0:
        return "watch", "periphery_collapse"
    if any(term in {"credential", "destructive", "delete"} for term in risk_hits):
        return "wobbling", "action_consequence_risk"
    if risk_hits:
        return "watch", "proof_or_authority_pressure"
    return "stable", "none"


def assess_frame_reference_integrity(job_need: str, periphery_terms: Iterable[str] = ()) -> str:
    lower_job = job_need.lower()
    periphery = " ".join(_parse_items(periphery_terms)).lower()
    combined = f"{lower_job} {periphery}"
    if any(_contains_term(combined, term) for term in FRAME_REFERENCE_TERMS):
        if "source" in combined or "repo" in combined or "surface" in combined or "frame" in combined:
            return "required_and_supported"
        return "required_watch"
    return "not_required"


def parse_periphery_terms(value: str) -> tuple[str, ...]:
    return tuple(item for item in (part.strip() for part in value.split(",")) if item)


def _parse_items(values: Iterable[str]) -> tuple[str, ...]:
    items: list[str] = []
    for value in values:
        for item in str(value).split(","):
            stripped = item.strip()
            if stripped and _normalize(stripped) not in {"none", "not_supplied"}:
                items.append(stripped)
    return tuple(items)


def _focus_from_job_need(job_need: str) -> str:
    words = [_normalize(word) for word in job_need.split()]
    useful = [word for word in words if word and word not in {"a", "an", "the", "to", "for", "with", "and", "or"}]
    return " ".join(useful[:8]) or "attention scaffold job"


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _contains_term(value: str, term: str) -> bool:
    if re.fullmatch(r"[a-z0-9_]+", term):
        return re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", value) is not None
    return term in value


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
