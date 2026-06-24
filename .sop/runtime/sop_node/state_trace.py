from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


@dataclass(frozen=True)
class InferenceStateTrace:
    trace_id: str
    repo_root: str
    base_ref: str
    head_ref: str
    target_moment: str
    sop_state_refs: tuple[str, ...] = field(default_factory=tuple)
    narrative_refs: tuple[str, ...] = field(default_factory=tuple)
    planned_specification_refs: tuple[str, ...] = field(default_factory=tuple)
    weight_intersection_refs: tuple[str, ...] = field(default_factory=tuple)
    question: str = ""
    model_key: str = "model_service_unspecified"
    determinism_scope: str = "close_semantic_reentry"
    known_missing_inputs: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.trace_id and self.repo_root and self.base_ref and self.head_ref and self.target_moment)

    def render(self) -> str:
        lines = [
            "Subject: Inference State Trace Event",
            "",
            f"& [{self.trace_id}] is an inference state trace re-entry packet",
            f"  + [repo_root] is {self.repo_root}",
            f"  + [base_ref] is {self.base_ref}",
            f"  + [head_ref] is {self.head_ref}",
            f"  + [target_moment] is {self.target_moment}",
            f"  + [model_key] is {self.model_key}",
            f"  + [determinism_scope] is {self.determinism_scope}",
            f"  + [question] is {self.question or 'not_declared'}",
        ]
        lines.extend(_render_refs("sop_state_ref", self.sop_state_refs))
        lines.extend(_render_refs("narrative_ref", self.narrative_refs))
        lines.extend(_render_refs("planned_specification_ref", self.planned_specification_refs))
        lines.extend(_render_refs("weight_intersection_ref", self.weight_intersection_refs))
        lines.extend(_render_refs("known_missing_input", self.known_missing_inputs))
        lines.append("  + [outside] is hidden activations, private weights, unavailable context, and causal proof")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = _safe_key(self.trace_id)
        reentry_key = f"N:reentry:{graph_id}"
        state_key = f"N:state:{graph_id}_framework_state"
        model_key = f"N:model:{_safe_key(self.model_key)}"
        outside_key = "N:outside:state_trace_boundary"
        nodes: list[HypergraphNode] = [
            HypergraphNode(reentry_key, self.trace_id, (("target_moment", self.target_moment),)),
            HypergraphNode(state_key, "framework state refs", (("repo_root", self.repo_root),)),
            HypergraphNode(f"N:commit:{_safe_key(self.base_ref)}", self.base_ref),
            HypergraphNode(f"N:commit:{_safe_key(self.head_ref)}", self.head_ref),
            HypergraphNode(model_key, self.model_key, (("determinism_scope", self.determinism_scope),)),
            HypergraphNode(outside_key, "hidden state outside visible re-entry packet"),
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:span:{graph_id}",
                "span",
                (
                    ("reentry", reentry_key),
                    ("start", f"N:commit:{_safe_key(self.base_ref)}"),
                    ("end", f"N:commit:{_safe_key(self.head_ref)}"),
                ),
            ),
            HypergraphEdge(
                f"E:reenters:{graph_id}",
                "reenters",
                (("reentry", reentry_key), ("state", state_key), ("model", model_key)),
                (("scope", self.determinism_scope),),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("reentry", reentry_key), ("outside", outside_key)),
            ),
        ]
        for index, ref in enumerate(self.sop_state_refs, start=1):
            ref_key = f"N:source:{_safe_key(ref)}"
            nodes.append(HypergraphNode(ref_key, ref, (("ref_role", "sop_state"),)))
            edges.append(
                HypergraphEdge(
                    f"E:reconstructs:{graph_id}_state_{index:03d}",
                    "reconstructs",
                    (("state", state_key), ("source", ref_key)),
                )
            )
        for index, ref in enumerate(self.narrative_refs, start=1):
            narrative_key = f"N:narrative:{_safe_key(ref)}"
            nodes.append(HypergraphNode(narrative_key, ref))
            edges.append(
                HypergraphEdge(
                    f"E:references:{graph_id}_narrative_{index:03d}",
                    "references",
                    (("reentry", reentry_key), ("narrative", narrative_key)),
                )
            )
        for index, ref in enumerate(self.planned_specification_refs, start=1):
            plan_key = f"N:source:{_safe_key(ref)}"
            nodes.append(HypergraphNode(plan_key, ref, (("ref_role", "planned_specification"),)))
            edges.append(
                HypergraphEdge(
                    f"E:compares:{graph_id}_plan_{index:03d}",
                    "compares",
                    (("reentry", reentry_key), ("plan", plan_key)),
                )
            )
        for index, ref in enumerate(self.weight_intersection_refs, start=1):
            scale_key = f"N:scale:{_safe_key(ref)}"
            nodes.append(HypergraphNode(scale_key, ref))
            edges.append(
                HypergraphEdge(
                    f"E:weighs:{graph_id}_intersection_{index:03d}",
                    "weighs",
                    (("reentry", reentry_key), ("scale", scale_key)),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.trace_id} Inference State Trace",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG inference-state-trace"),
                ("base_ref", self.base_ref),
                ("head_ref", self.head_ref),
                ("determinism_scope", self.determinism_scope),
            ),
            outside=self.known_missing_inputs or ("hidden activations and private weights are not replayed",),
        )


def build_inference_state_trace(
    repo_root: str | Path,
    *,
    base_ref: str = "HEAD",
    head_ref: str = "WORKTREE",
    target_moment: str,
    sop_state_refs: tuple[str, ...] = (),
    narrative_refs: tuple[str, ...] = (),
    planned_specification_refs: tuple[str, ...] = (),
    weight_intersection_refs: tuple[str, ...] = (),
    question: str = "",
    model_key: str = "model_service_unspecified",
    determinism_scope: str = "close_semantic_reentry",
    known_missing_inputs: tuple[str, ...] = (
        "hidden activations",
        "sampling seed",
        "unlogged system context",
    ),
    trace_id: str | None = None,
) -> InferenceStateTrace:
    return InferenceStateTrace(
        trace_id=trace_id or _make_trace_id(),
        repo_root=str(Path(repo_root)),
        base_ref=base_ref,
        head_ref=head_ref,
        target_moment=target_moment,
        sop_state_refs=sop_state_refs,
        narrative_refs=narrative_refs,
        planned_specification_refs=planned_specification_refs,
        weight_intersection_refs=weight_intersection_refs,
        question=question,
        model_key=model_key,
        determinism_scope=determinism_scope,
        known_missing_inputs=known_missing_inputs,
    )


def _render_refs(label: str, refs: tuple[str, ...]) -> list[str]:
    if not refs:
        return [f"  + [{label}_set] is empty"]
    return [f"  + [{label}_{index:03d}] is {ref}" for index, ref in enumerate(refs, start=1)]


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())


def _make_trace_id() -> str:
    return "InferenceStateTrace_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
