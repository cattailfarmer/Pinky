from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


VALID_ADVANCE_STEPS = {"slender", "normal", "wide", "deep", "leap"}
VALID_DEPTH_BUDGETS = {"slender", "normal", "wide", "deep", "explosive_controlled"}

DEFAULT_CORRIDOR_OUTSIDE = (
    "hidden activations",
    "actual transformer weights",
    "exact embedding geometry",
    "causal proof",
    "definite relationship",
    "unsupported identity",
    "arbitrary visual analogy",
)


@dataclass(frozen=True)
class CorridorFrame:
    frame_id: str
    label: str
    relation_role: str
    heat: int
    confidence: str
    return_anchor: str
    source_ref: str = ""
    distinctness: int = 1

    @property
    def frame_key(self) -> str:
        return _safe_key(self.frame_id)

    @property
    def weight(self) -> int:
        return self.heat + self.distinctness

    @property
    def ready(self) -> bool:
        return bool(
            self.frame_id
            and self.label
            and self.relation_role
            and self.heat >= 0
            and self.confidence
            and self.return_anchor
            and self.distinctness >= 0
        )

    def render(self, rank: int) -> list[str]:
        lines = [
            f"  + [corridor_frame:{rank}] is {self.label}",
            f"    = frame_id: {self.frame_id}",
            f"    = relation_role: {self.relation_role}",
            f"    = heat: {self.heat}",
            f"    = distinctness: {self.distinctness}",
            f"    = confidence: {self.confidence}",
            f"    = return_anchor: {self.return_anchor}",
        ]
        if self.source_ref:
            lines.append(f"    = source_ref: {self.source_ref}")
        return lines


@dataclass(frozen=True)
class CurvingAssociation:
    association_id: str
    source_frame: str
    target_frame: str
    relation_hint: str
    heat: int
    confidence: str
    status: str = "correlation_only"
    evidence_ref: str = ""
    outside: str = "not a definite relationship"

    @property
    def association_key(self) -> str:
        return _safe_key(self.association_id)

    @property
    def source_key(self) -> str:
        return _safe_key(self.source_frame)

    @property
    def target_key(self) -> str:
        return _safe_key(self.target_frame)

    @property
    def ready(self) -> bool:
        return bool(
            self.association_id
            and self.source_frame
            and self.target_frame
            and self.relation_hint
            and self.heat >= 0
            and self.confidence
            and self.status
        )

    @property
    def preserves_correlation_boundary(self) -> bool:
        return self.status == "correlation_only"

    def render(self, index: int) -> list[str]:
        lines = [
            f"  + [curving_association:{index}] is {self.relation_hint}",
            f"    = association_id: {self.association_id}",
            f"    = source_frame: {self.source_frame}",
            f"    = target_frame: {self.target_frame}",
            f"    = heat: {self.heat}",
            f"    = confidence: {self.confidence}",
            f"    = correlation_status: {self.status}",
            f"    = outside: {self.outside}",
        ]
        if self.evidence_ref:
            lines.append(f"    = evidence_ref: {self.evidence_ref}")
        return lines


@dataclass(frozen=True)
class HyperbolicCorridorNavigation:
    navigator_id: str
    focal_subject: str
    identity_resolution_target: str
    advance_step: str
    depth_budget: str
    frames: tuple[CorridorFrame, ...]
    associations: tuple[CurvingAssociation, ...]
    local_awareness_extension: tuple[str, ...]
    entanglement_terms: tuple[str, ...]
    identity_clarity_candidate: str
    outside: tuple[str, ...] = DEFAULT_CORRIDOR_OUTSIDE

    @property
    def navigator_key(self) -> str:
        return _safe_key(self.navigator_id)

    @property
    def corridor_id(self) -> str:
        return f"{self.navigator_key}_corridor"

    @property
    def frame_series(self) -> tuple[CorridorFrame, ...]:
        return tuple(sorted(self.frames, key=lambda frame: (-frame.weight, -frame.heat, frame.frame_key)))

    @property
    def local_awareness_extension_key(self) -> str:
        return _safe_key("_".join(self.local_awareness_extension) or "local_awareness_extension")

    @property
    def inference_surf_key(self) -> str:
        return f"{self.navigator_key}_inference_surf"

    @property
    def identity_candidate_key(self) -> str:
        return _safe_key(self.identity_clarity_candidate or "unresolved_identity_candidate")

    @property
    def ready(self) -> bool:
        frame_ids = {frame.frame_id for frame in self.frames}
        return bool(
            self.navigator_id
            and self.focal_subject
            and self.identity_resolution_target
            and self.advance_step in VALID_ADVANCE_STEPS
            and self.depth_budget in VALID_DEPTH_BUDGETS
            and self.frames
            and all(frame.ready for frame in self.frames)
            and self.associations
            and all(association.ready for association in self.associations)
            and all(association.source_frame in frame_ids and association.target_frame in frame_ids for association in self.associations)
            and self.local_awareness_extension
            and self.identity_clarity_candidate
            and self.outside
        )

    @property
    def correlation_boundary_status(self) -> str:
        if all(association.preserves_correlation_boundary for association in self.associations):
            return "all_curving_associations_are_correlation_only"
        return "promotion_candidates_require_evidence_gate"

    @property
    def frame_order(self) -> str:
        return " > ".join(f"{frame.frame_id}:{frame.weight}" for frame in self.frame_series)

    def render(self) -> str:
        lines = [
            "Subject: Hyperbolic Corridor Navigator Runtime",
            "",
            f"& [HyperbolicCorridorNavigator:{self.navigator_key}] is a hyperbolic_corridor_navigation_runtime_record",
            f"  + [navigator_id] is {self.navigator_id}",
            f"  + [focal_subject] is {self.focal_subject}",
            f"  + [identity_resolution_target] is {self.identity_resolution_target}",
            f"  + [advance_step] is {self.advance_step}",
            f"  + [depth_budget] is {self.depth_budget}",
            f"  + [local_awareness_extension] is {', '.join(self.local_awareness_extension)}",
            f"  + [entanglement_field] is {', '.join(self.entanglement_terms) if self.entanglement_terms else 'none'}",
            f"  + [frame_order] is {self.frame_order}",
            f"  + [correlation_boundary_status] is {self.correlation_boundary_status}",
            f"  + [identity_clarity_candidate] is {self.identity_clarity_candidate}",
            f"  + [outside] is {', '.join(self.outside)}",
            "",
            "& [PeripheralFrameSeries] is the ordered corridor frame set",
        ]
        for rank, frame in enumerate(self.frame_series, start=1):
            lines.extend(frame.render(rank))
        lines.extend(("", "& [CurvingAssociationSet] is correlation-only movement through periphery"))
        for index, association in enumerate(self.associations, start=1):
            lines.extend(association.render(index))
        lines.extend(
            [
                "",
                f"({self.navigator_id}) :peripheral_frame_series: /corridor_boundary/ |outside|",
            ]
        )
        for rank, frame in enumerate(self.frame_series, start=1):
            lines.extend(
                [
                    f"  + [corridor_frame:{rank}] is {frame.label}",
                    f"    = relation_role: {frame.relation_role}",
                    f"    = heat: {frame.heat}",
                    f"    = confidence: {frame.confidence}",
                    f"    = return_anchor: {frame.return_anchor}",
                ]
            )
        lines.append(f"  = advance_step: {self.advance_step}")
        lines.append(f"  = depth_budget: {self.depth_budget}")
        lines.append(f"  = local_awareness_extension: {', '.join(self.local_awareness_extension)}")
        for association in self.associations:
            lines.append(
                f"  = curving_association: {association.source_frame} -> {association.target_frame} as {association.status}"
            )
        lines.append(f"  = identity_resolution_target: {self.identity_resolution_target}")
        lines.append(f"  - outside: {', '.join(self.outside)}")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.navigator_key
        navigator_node = HypergraphNode(
            f"N:map:{graph_id}",
            self.navigator_id,
            (
                ("advance_step", self.advance_step),
                ("depth_budget", self.depth_budget),
                ("frame_order", self.frame_order),
                ("correlation_boundary_status", self.correlation_boundary_status),
            ),
        )
        corridor_node = HypergraphNode(f"N:corridor:{self.corridor_id}", self.corridor_id)
        focus_node = HypergraphNode(f"N:focus:{_safe_key(self.focal_subject)}", self.focal_subject)
        identity_node = HypergraphNode(
            f"N:subject:{_safe_key(self.identity_resolution_target)}",
            self.identity_resolution_target,
            (("identity_status", "target_not_proof"),),
        )
        extension_node = HypergraphNode(
            f"N:extension:{self.local_awareness_extension_key}",
            ", ".join(self.local_awareness_extension),
        )
        surf_node = HypergraphNode(
            f"N:surf:{self.inference_surf_key}",
            "visible semantic correlation surf only",
            (("hidden_state_access", "none"),),
        )
        candidate_node = HypergraphNode(
            f"N:finding:{self.identity_candidate_key}",
            self.identity_clarity_candidate,
            (("candidate_status", "candidate_not_proof"),),
        )
        outside_node = HypergraphNode("N:outside:hyperbolic_corridor_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [
            navigator_node,
            corridor_node,
            focus_node,
            identity_node,
            extension_node,
            surf_node,
            candidate_node,
            outside_node,
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:navigates:{self.corridor_id}",
                "navigates",
                (("navigator", navigator_node.key), ("corridor", corridor_node.key), ("focus", focus_node.key)),
                (("advance_step", self.advance_step),),
            ),
            HypergraphEdge(
                f"E:extends:{self.local_awareness_extension_key}",
                "extends",
                (("navigator", navigator_node.key), ("extension", extension_node.key), ("corridor", corridor_node.key)),
                (("depth_budget", self.depth_budget),),
            ),
            HypergraphEdge(
                f"E:surfs:{self.inference_surf_key}",
                "surfs",
                (("navigator", navigator_node.key), ("surf", surf_node.key), ("corridor", corridor_node.key)),
                (("claim_boundary", "visible_semantic_correlation_only"),),
            ),
            HypergraphEdge(
                f"E:probes:{_safe_key(self.identity_resolution_target)}",
                "probes",
                (("navigator", navigator_node.key), ("identity", identity_node.key), ("corridor", corridor_node.key)),
            ),
            HypergraphEdge(
                f"E:resolves:{self.identity_candidate_key}",
                "resolves",
                (("candidate", candidate_node.key), ("identity", identity_node.key), ("navigator", navigator_node.key)),
                (("proof_status", "candidate_not_proof"),),
            ),
            HypergraphEdge(
                f"E:bounds:{self.corridor_id}",
                "bounds",
                (("navigator", navigator_node.key), ("outside", outside_node.key), ("corridor", corridor_node.key)),
                (("outside_preserved", "true"),),
            ),
        ]
        frame_keys: dict[str, str] = {}
        for rank, frame in enumerate(self.frame_series, start=1):
            frame_node = HypergraphNode(
                f"N:frame:{frame.frame_key}",
                frame.label,
                (
                    ("rank", str(rank)),
                    ("relation_role", frame.relation_role),
                    ("heat", str(frame.heat)),
                    ("distinctness", str(frame.distinctness)),
                    ("confidence", frame.confidence),
                    ("return_anchor", frame.return_anchor),
                    ("source_ref", frame.source_ref or "not_supplied"),
                ),
            )
            periphery_node = HypergraphNode(
                f"N:periphery:{frame.frame_key}",
                frame.relation_role,
                (("heat", str(frame.heat)), ("return_anchor", frame.return_anchor)),
            )
            nodes.extend((frame_node, periphery_node))
            frame_keys[frame.frame_id] = frame_node.key
            edges.append(
                HypergraphEdge(
                    f"E:frames:{frame.frame_key}",
                    "frames",
                    (("corridor", corridor_node.key), ("frame", frame_node.key), ("periphery", periphery_node.key)),
                    (("rank", str(rank)), ("weight", str(frame.weight))),
                )
            )
        for association in self.associations:
            signal_node = HypergraphNode(
                f"N:signal:{association.association_key}",
                association.relation_hint,
                (
                    ("heat", str(association.heat)),
                    ("confidence", association.confidence),
                    ("correlation_status", association.status),
                    ("outside", association.outside),
                    ("evidence_ref", association.evidence_ref or "not_supplied"),
                ),
            )
            nodes.append(signal_node)
            edges.append(
                HypergraphEdge(
                    f"E:correlates:{association.association_key}",
                    "correlates",
                    (
                        ("signal", signal_node.key),
                        ("source_frame", frame_keys[association.source_frame]),
                        ("target_frame", frame_keys[association.target_frame]),
                        ("corridor", corridor_node.key),
                    ),
                    (("status", association.status), ("relationship_proof", "false")),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.navigator_id} Hyperbolic Corridor Navigation",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG hyperbolic-corridor-navigator"),
                ("focal_subject", self.focal_subject),
                ("identity_resolution_target", self.identity_resolution_target),
                ("advance_step", self.advance_step),
                ("depth_budget", self.depth_budget),
                ("correlation_boundary_status", self.correlation_boundary_status),
            ),
            outside=self.outside,
        )


def build_hyperbolic_corridor_navigation(
    *,
    navigator_id: str,
    focal_subject: str,
    identity_resolution_target: str,
    frames: Iterable[CorridorFrame],
    associations: Iterable[CurvingAssociation] = (),
    advance_step: str = "",
    depth_budget: str = "",
    local_awareness_extension: Iterable[str] = (),
    entanglement_terms: Iterable[str] = (),
    identity_clarity_candidate: str = "",
    outside: Iterable[str] = DEFAULT_CORRIDOR_OUTSIDE,
) -> HyperbolicCorridorNavigation:
    frame_tuple = tuple(frames)
    resolved_step = advance_step or select_advance_step(frame_tuple)
    resolved_depth = depth_budget or select_depth_budget(frame_tuple, resolved_step)
    if resolved_step not in VALID_ADVANCE_STEPS:
        raise ValueError(f"unknown advance step: {resolved_step}")
    if resolved_depth not in VALID_DEPTH_BUDGETS:
        raise ValueError(f"unknown depth budget: {resolved_depth}")
    association_tuple = tuple(associations) or _default_associations(frame_tuple)
    extension = tuple(_parse_list_values(local_awareness_extension)) or ("focal_subject", "peripheral_frame_series", "return_anchor")
    entanglement = tuple(_parse_list_values(entanglement_terms))
    candidate = identity_clarity_candidate or f"{identity_resolution_target} remains candidate from {len(frame_tuple)} correlated corridor frames"
    return HyperbolicCorridorNavigation(
        navigator_id=navigator_id,
        focal_subject=focal_subject,
        identity_resolution_target=identity_resolution_target,
        advance_step=resolved_step,
        depth_budget=resolved_depth,
        frames=frame_tuple,
        associations=association_tuple,
        local_awareness_extension=extension,
        entanglement_terms=entanglement,
        identity_clarity_candidate=candidate,
        outside=tuple(_parse_list_values(outside)) or DEFAULT_CORRIDOR_OUTSIDE,
    )


def select_advance_step(frames: tuple[CorridorFrame, ...]) -> str:
    if len(frames) <= 1:
        return "slender"
    total_weight = sum(frame.weight for frame in frames)
    if len(frames) >= 7 or total_weight >= 70:
        return "deep"
    if len(frames) >= 5 or total_weight >= 45:
        return "wide"
    return "normal"


def select_depth_budget(frames: tuple[CorridorFrame, ...], advance_step: str) -> str:
    if advance_step == "leap":
        return "explosive_controlled"
    if advance_step in {"wide", "deep"}:
        return advance_step
    if any(frame.confidence.lower() == "low" for frame in frames):
        return "wide"
    return "normal" if advance_step == "normal" else "slender"


def parse_corridor_frame(value: str) -> CorridorFrame:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 6:
        raise ValueError(
            "corridor frame must be frame_id|label|relation_role|heat|confidence|return_anchor[|source_ref][|distinctness]"
        )
    return CorridorFrame(
        frame_id=parts[0],
        label=parts[1],
        relation_role=parts[2],
        heat=int(parts[3]) if parts[3] else 0,
        confidence=parts[4],
        return_anchor=parts[5],
        source_ref=parts[6] if len(parts) > 6 else "",
        distinctness=int(parts[7]) if len(parts) > 7 and parts[7] else 1,
    )


def parse_curving_association(value: str) -> CurvingAssociation:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 6:
        raise ValueError(
            "curving association must be association_id|source_frame|target_frame|relation_hint|heat|confidence[|status][|evidence_ref][|outside]"
        )
    return CurvingAssociation(
        association_id=parts[0],
        source_frame=parts[1],
        target_frame=parts[2],
        relation_hint=parts[3],
        heat=int(parts[4]) if parts[4] else 0,
        confidence=parts[5],
        status=parts[6] if len(parts) > 6 and parts[6] else "correlation_only",
        evidence_ref=parts[7] if len(parts) > 7 else "",
        outside=parts[8] if len(parts) > 8 else "not a definite relationship",
    )


def _default_associations(frames: tuple[CorridorFrame, ...]) -> tuple[CurvingAssociation, ...]:
    ordered = tuple(sorted(frames, key=lambda frame: (-frame.weight, -frame.heat, frame.frame_key)))
    associations: list[CurvingAssociation] = []
    for index, (source, target) in enumerate(zip(ordered, ordered[1:]), start=1):
        associations.append(
            CurvingAssociation(
                association_id=f"curve_{index}_{source.frame_id}_to_{target.frame_id}",
                source_frame=source.frame_id,
                target_frame=target.frame_id,
                relation_hint=f"{source.relation_role}_to_{target.relation_role}",
                heat=min(source.heat, target.heat),
                confidence=_lower_confidence(source.confidence, target.confidence),
                status="correlation_only",
                evidence_ref=source.source_ref or target.source_ref,
                outside="auto-generated corridor adjacency is not relationship proof",
            )
        )
    return tuple(associations)


def _lower_confidence(left: str, right: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    reverse = {value: key for key, value in order.items()}
    return reverse.get(min(order.get(left.lower(), 1), order.get(right.lower(), 1)), "medium")


def _parse_list_values(values: Iterable[str]) -> tuple[str, ...]:
    items: list[str] = []
    for value in values:
        for part in str(value).split(","):
            stripped = part.strip()
            if stripped and _normalize(stripped) not in {"none", "not_supplied"}:
                items.append(stripped)
    return tuple(items)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
