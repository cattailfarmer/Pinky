from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


@dataclass(frozen=True)
class PeripheryRunFrame:
    frame_id: str
    focus_observation: str
    direction: str
    periphery_terms: tuple[str, ...] = field(default_factory=tuple)
    stable_markers: tuple[str, ...] = field(default_factory=tuple)
    evidence_pointers: tuple[str, ...] = field(default_factory=tuple)

    @property
    def frame_key(self) -> str:
        return _safe_key(self.frame_id)

    @property
    def focus_tokens(self) -> tuple[str, ...]:
        return tuple(sorted({_normalize(token) for token in self.focus_observation.split() if _normalize(token)}))

    @property
    def periphery_set(self) -> set[str]:
        return {_normalize(term) for term in self.periphery_terms if _normalize(term)}

    @property
    def stable_marker_set(self) -> set[str]:
        return {_normalize(marker) for marker in self.stable_markers if _normalize(marker)}


@dataclass(frozen=True)
class PeripheryContinuityLink:
    from_frame: str
    to_frame: str
    shared_stable_markers: tuple[str, ...]
    shared_periphery_terms: tuple[str, ...]
    shared_focus_terms: tuple[str, ...]
    direction_continues: bool

    @property
    def visible_continuity(self) -> bool:
        return bool(self.shared_stable_markers or self.shared_periphery_terms)

    @property
    def focus_contiguous(self) -> bool:
        return self.direction_continues and bool(self.shared_focus_terms or self.visible_continuity)

    @property
    def heat(self) -> int:
        return (
            len(self.shared_stable_markers) * 3
            + len(self.shared_periphery_terms) * 2
            + len(self.shared_focus_terms)
            + (2 if self.direction_continues else 0)
        )


@dataclass(frozen=True)
class PeripheryContinuityRun:
    run_id: str
    focus_subject: str
    run_direction: str
    frames: tuple[PeripheryRunFrame, ...]
    impulse: str = ""
    horizon_hint: str = ""
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.run_id and self.focus_subject and self.run_direction and len(self.frames) >= 2)

    @property
    def links(self) -> tuple[PeripheryContinuityLink, ...]:
        return tuple(
            _link_frames(before, after, self.run_direction)
            for before, after in zip(self.frames, self.frames[1:])
        )

    @property
    def focus_chain_coherent(self) -> bool:
        return bool(self.ready and self.links and all(link.focus_contiguous for link in self.links))

    @property
    def periphery_continuity(self) -> str:
        if not self.links:
            return "outside"
        visible_links = sum(1 for link in self.links if link.visible_continuity)
        if visible_links == len(self.links) and all(frame.stable_marker_set for frame in self.frames):
            return "stable"
        if visible_links:
            return "thinning"
        return "broken"

    @property
    def run_state(self) -> str:
        if not self.ready:
            return "outside"
        if self.focus_chain_coherent and self.periphery_continuity == "stable" and self.horizon_hint:
            return "run"
        if self.focus_chain_coherent and self.periphery_continuity == "stable":
            return "flow"
        if self.focus_chain_coherent and self.periphery_continuity == "thinning":
            return "walk_with_watch"
        return "rebalance"

    @property
    def run_balance(self) -> str:
        return {
            "run": "stable",
            "flow": "stable",
            "walk_with_watch": "watch",
            "rebalance": "wobbling",
            "outside": "outside",
        }[self.run_state]

    @property
    def checkpoint_pressure(self) -> str:
        if self.run_state == "run":
            return "reduced"
        if self.run_state == "flow":
            return "light"
        if self.run_state == "walk_with_watch":
            return "restored_lightly"
        return "restored"

    def render(self) -> str:
        lines = [
            "Subject: Periphery Continuity Run",
            "",
            f"& [PeripheryContinuityRun:{_safe_key(self.run_id)}] is a rolling-periphery run record",
            f"  + [run_id] is {self.run_id}",
            f"  + [focus_subject] is {self.focus_subject}",
            f"  + [run_direction] is {self.run_direction}",
            f"  + [horizon_hint] is {self.horizon_hint or 'not_supplied'}",
            f"  + [impulse] is {self.impulse or 'not_supplied'}",
            f"  + [focus_chain_coherent] is {str(self.focus_chain_coherent).lower()}",
            f"  + [periphery_continuity] is {self.periphery_continuity}",
            f"  + [run_state] is {self.run_state}",
            f"  + [run_balance] is {self.run_balance}",
            f"  + [checkpoint_pressure] is {self.checkpoint_pressure}",
            "",
            "& [FocusFrameSet] is the path between rolling periphery",
        ]
        for index, frame in enumerate(self.frames, start=1):
            lines.extend(
                (
                    f"  + [frame_{index:03d}] is {frame.focus_observation}",
                    f"    = frame_id: {frame.frame_id}",
                    f"    = direction: {frame.direction}",
                    f"    = periphery_terms: {', '.join(frame.periphery_terms) if frame.periphery_terms else 'none'}",
                    f"    = stable_markers: {', '.join(frame.stable_markers) if frame.stable_markers else 'none'}",
                    f"    = evidence_pointers: {', '.join(frame.evidence_pointers) if frame.evidence_pointers else 'none'}",
                )
            )
        lines.extend(("", "& [ContinuityLinkSet] is rolling periphery between frames"))
        for index, link in enumerate(self.links, start=1):
            lines.extend(
                (
                    f"  + [link_{index:03d}] is {link.from_frame} to {link.to_frame}",
                    f"    = shared_stable_markers: {', '.join(link.shared_stable_markers) if link.shared_stable_markers else 'none'}",
                    f"    = shared_periphery_terms: {', '.join(link.shared_periphery_terms) if link.shared_periphery_terms else 'none'}",
                    f"    = shared_focus_terms: {', '.join(link.shared_focus_terms) if link.shared_focus_terms else 'none'}",
                    f"    = direction_continues: {str(link.direction_continues).lower()}",
                    f"    = heat: {link.heat}",
                )
            )
        lines.extend(
            (
                "",
                "(periphery_continuity_run) :focus_path: /rolling_periphery/ |outside|",
                f"  = run_state: {self.run_state}",
                f"  = run_balance: {self.run_balance}",
                f"  = checkpoint_pressure: {self.checkpoint_pressure}",
                "  - outside: hidden cognition, unobserved future frames, and proof not visible in the continuity links",
            )
        )
        for item in self.residual_outside:
            lines.append(f"  - outside: {item}")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = _safe_key(self.run_id)
        run_node = HypergraphNode(
            f"N:run:{graph_id}",
            self.run_id,
            (
                ("run_state", self.run_state),
                ("run_balance", self.run_balance),
                ("checkpoint_pressure", self.checkpoint_pressure),
            ),
        )
        focus_node = HypergraphNode(f"N:focus:{_safe_key(self.focus_subject)}", self.focus_subject)
        direction_node = HypergraphNode(f"N:direction:{_safe_key(self.run_direction)}", self.run_direction)
        horizon_node = HypergraphNode(f"N:horizon:{_safe_key(self.horizon_hint or 'not_supplied')}", self.horizon_hint or "not supplied")
        outside_node = HypergraphNode("N:outside:periphery_continuity_boundary", "hidden cognition and unobserved future frames")
        nodes: list[HypergraphNode] = [run_node, focus_node, direction_node, horizon_node, outside_node]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:follows:{graph_id}",
                "follows",
                (("run", run_node.key), ("focus", focus_node.key), ("direction", direction_node.key)),
                (("focus_chain_coherent", str(self.focus_chain_coherent).lower()),),
            ),
            HypergraphEdge(
                f"E:sees_horizon:{graph_id}",
                "sees_horizon",
                (("run", run_node.key), ("horizon", horizon_node.key)),
                (("checkpoint_pressure", self.checkpoint_pressure),),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("run", run_node.key), ("outside", outside_node.key)),
                (("run_balance", self.run_balance),),
            ),
        ]
        for index, frame in enumerate(self.frames, start=1):
            frame_node = HypergraphNode(
                f"N:frame:{frame.frame_key}",
                frame.focus_observation,
                (
                    ("frame_id", frame.frame_id),
                    ("direction", frame.direction),
                    ("evidence_pointers", ",".join(frame.evidence_pointers) or "none"),
                ),
            )
            nodes.append(frame_node)
            edges.append(
                HypergraphEdge(
                    f"E:steps:{graph_id}_{index:03d}",
                    "steps",
                    (("run", run_node.key), ("frame", frame_node.key)),
                    (("order", str(index)),),
                )
            )
            for marker in frame.stable_markers:
                marker_node = HypergraphNode(f"N:periphery:{_safe_key(marker)}", marker)
                nodes.append(marker_node)
                edges.append(
                    HypergraphEdge(
                        f"E:orbits:{frame.frame_key}_{_safe_key(marker)}",
                        "orbits",
                        (("frame", frame_node.key), ("periphery", marker_node.key)),
                    )
                )
        for link in self.links:
            from_key = f"N:frame:{_safe_key(link.from_frame)}"
            to_key = f"N:frame:{_safe_key(link.to_frame)}"
            edges.append(
                HypergraphEdge(
                    f"E:rolls:{_safe_key(link.from_frame)}_{_safe_key(link.to_frame)}",
                    "rolls",
                    (("from", from_key), ("to", to_key), ("run", run_node.key)),
                    (
                        ("shared_stable_markers", ",".join(link.shared_stable_markers) or "none"),
                        ("shared_periphery_terms", ",".join(link.shared_periphery_terms) or "none"),
                        ("heat", str(link.heat)),
                    ),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.run_id} Periphery Continuity Run",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG periphery-continuity-run"),
                ("focus_subject", self.focus_subject),
                ("run_direction", self.run_direction),
                ("run_state", self.run_state),
            ),
            outside=self.residual_outside or ("continuity run records visible path/periphery coherence, not hidden model attention",),
        )


def build_periphery_continuity_run(
    *,
    run_id: str,
    focus_subject: str,
    run_direction: str,
    frames: Iterable[PeripheryRunFrame],
    impulse: str = "",
    horizon_hint: str = "",
) -> PeripheryContinuityRun:
    return PeripheryContinuityRun(
        run_id=run_id,
        focus_subject=focus_subject,
        run_direction=run_direction,
        frames=tuple(frames),
        impulse=impulse,
        horizon_hint=horizon_hint,
        residual_outside=("future frames remain outside until observed in the rolling periphery",),
    )


def parse_periphery_run_frame(value: str) -> PeripheryRunFrame:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 3:
        raise ValueError("periphery run frame must be frame_id|focus_observation|direction[|periphery][|stable_markers][|evidence]")
    return PeripheryRunFrame(
        frame_id=parts[0],
        focus_observation=parts[1],
        direction=parts[2],
        periphery_terms=_parse_list(parts[3]) if len(parts) > 3 else (),
        stable_markers=_parse_list(parts[4]) if len(parts) > 4 else (),
        evidence_pointers=_parse_list(parts[5]) if len(parts) > 5 else (),
    )


def _link_frames(before: PeripheryRunFrame, after: PeripheryRunFrame, run_direction: str) -> PeripheryContinuityLink:
    shared_stable = tuple(sorted(before.stable_marker_set & after.stable_marker_set))
    shared_periphery = tuple(sorted(before.periphery_set & after.periphery_set))
    shared_focus = tuple(sorted(set(before.focus_tokens) & set(after.focus_tokens)))
    direction_continues = _direction_continues(before.direction, after.direction, run_direction)
    return PeripheryContinuityLink(
        from_frame=before.frame_id,
        to_frame=after.frame_id,
        shared_stable_markers=shared_stable,
        shared_periphery_terms=shared_periphery,
        shared_focus_terms=shared_focus,
        direction_continues=direction_continues,
    )


def _direction_continues(before: str, after: str, run_direction: str) -> bool:
    normalized_before = _normalize(before)
    normalized_after = _normalize(after)
    normalized_run = _normalize(run_direction)
    return bool(
        normalized_before
        and normalized_after
        and (normalized_before == normalized_after or normalized_after == normalized_run or normalized_before == normalized_run)
    )


def _parse_list(value: str) -> tuple[str, ...]:
    if _normalize(value) in {"", "none", "not_supplied"}:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip() and _normalize(item) != "none")


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
