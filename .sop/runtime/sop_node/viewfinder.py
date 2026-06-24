from __future__ import annotations

import re
from dataclasses import dataclass

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


@dataclass(frozen=True)
class Reweighing:
    subject_key: str
    previous_weight: int
    current_weight: int
    reason: str


@dataclass(frozen=True)
class ViewfinderSnapshot:
    snapshot_id: str
    narrative_token: str
    desired_shape: str
    commit_frame: str
    previous_reflections: tuple[str, ...]
    current_observations: tuple[str, ...]
    reweighings: tuple[Reweighing, ...]
    residual_outside: tuple[str, ...] = (
        "viewfinder snapshot routes inference and comparison; it does not prove semantic truth by itself",
    )

    @property
    def ready(self) -> bool:
        return bool(self.snapshot_id and self.narrative_token and self.desired_shape and self.commit_frame)

    def to_hypergraph(self) -> HypergraphRecord:
        snapshot_key = _safe_key(self.snapshot_id)
        viewfinder_node = HypergraphNode(
            f"N:viewfinder:{snapshot_key}",
            "Codex inference viewfinder",
            (("compiler_role", "attention graph reflection through inference"),),
        )
        narrative_node = HypergraphNode(f"N:narrative:{snapshot_key}", self.narrative_token)
        snapshot_node = HypergraphNode(f"N:snapshot:{snapshot_key}", self.snapshot_id)
        commit_node = HypergraphNode(f"N:commit:{_safe_key(self.commit_frame)}", self.commit_frame)
        shape_node = HypergraphNode(f"N:shape:{_safe_key(self.desired_shape)}", self.desired_shape)
        nodes = [viewfinder_node, narrative_node, snapshot_node, commit_node, shape_node]

        reflection_nodes = [
            HypergraphNode(f"N:reflection:{_safe_key(value)}", value)
            for value in self.previous_reflections
        ]
        observation_nodes = [
            HypergraphNode(f"N:observation:{_safe_key(value)}", value)
            for value in self.current_observations
        ]
        reframe_nodes = [
            HypergraphNode(
                f"N:reframe:{_safe_key(item.subject_key)}",
                item.subject_key,
                (
                    ("previous_weight", str(item.previous_weight)),
                    ("current_weight", str(item.current_weight)),
                    ("reason", item.reason),
                ),
            )
            for item in self.reweighings
        ]
        nodes.extend(reflection_nodes)
        nodes.extend(observation_nodes)
        nodes.extend(reframe_nodes)

        edges = [
            HypergraphEdge(
                f"E:projects:{snapshot_key}",
                "projects",
                (("viewfinder", viewfinder_node.key), ("shape", shape_node.key)),
            ),
            HypergraphEdge(
                f"E:captures:{snapshot_key}",
                "captures",
                (
                    ("viewfinder", viewfinder_node.key),
                    ("narrative", narrative_node.key),
                    ("snapshot", snapshot_node.key),
                    ("commit", commit_node.key),
                ),
            ),
        ]
        for index, reflection in enumerate(reflection_nodes, start=1):
            for observation in observation_nodes or ():
                edges.append(
                    HypergraphEdge(
                        f"E:compares:{snapshot_key}_{index:03d}_{_safe_key(observation.key)}",
                        "compares",
                        (("snapshot", snapshot_node.key), ("previous", reflection.key), ("current", observation.key)),
                    )
                )
        for item in self.reweighings:
            reframe_key = f"N:reframe:{_safe_key(item.subject_key)}"
            edges.append(
                HypergraphEdge(
                    f"E:reweighs:{_safe_key(item.subject_key)}",
                    "reweighs",
                    (("snapshot", snapshot_node.key), ("reframe", reframe_key)),
                    (
                        ("previous_weight", str(item.previous_weight)),
                        ("current_weight", str(item.current_weight)),
                        ("reason", item.reason),
                    ),
                )
            )
            edges.append(
                HypergraphEdge(
                    f"E:reframes:{_safe_key(item.subject_key)}",
                    "reframes",
                    (("snapshot", snapshot_node.key), ("reframe", reframe_key), ("narrative", narrative_node.key)),
                    (("status", "new_frame_preserves_prior"),),
                )
            )
        return HypergraphRecord(
            graph_id=snapshot_key,
            label=f"{self.snapshot_id} Viewfinder Snapshot",
            nodes=tuple(nodes),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG viewfinder-snapshot"),
                ("commit_frame", self.commit_frame),
            ),
            outside=self.residual_outside,
        )

    def render(self) -> str:
        return self.to_hypergraph().render()


def build_viewfinder_snapshot(
    *,
    snapshot_id: str,
    narrative_token: str,
    desired_shape: str,
    commit_frame: str,
    previous_reflections: tuple[str, ...] = (),
    current_observations: tuple[str, ...] = (),
    reweighings: tuple[Reweighing, ...] = (),
) -> ViewfinderSnapshot:
    return ViewfinderSnapshot(
        snapshot_id=snapshot_id,
        narrative_token=narrative_token,
        desired_shape=desired_shape,
        commit_frame=commit_frame,
        previous_reflections=previous_reflections,
        current_observations=current_observations,
        reweighings=reweighings,
    )


def parse_reweighing(value: str) -> Reweighing:
    parts = value.split(":", 3)
    if len(parts) != 4:
        raise ValueError("reweighing must be subject:previous_weight:current_weight:reason")
    return Reweighing(parts[0], int(parts[1]), int(parts[2]), parts[3])


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"
