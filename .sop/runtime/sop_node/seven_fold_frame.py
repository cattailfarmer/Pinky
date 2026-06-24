from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


MAX_FOLD_LEGS = 7

DEFAULT_SEVEN_FOLD_OUTSIDE = (
    "hidden geometry",
    "direct transformer activations",
    "unsupported heat",
    "arbitrary tessellation aesthetics",
    "unmeasured dimensions",
)


@dataclass(frozen=True)
class CorrelationCell:
    cell_id: str
    label: str
    heat: int
    salience: int
    confidence: str
    source_ref: str = ""
    caution_load: int = 0

    @property
    def cell_key(self) -> str:
        return _safe_key(self.cell_id)

    @property
    def total_weight(self) -> int:
        return self.heat + self.salience - self.caution_load

    @property
    def ready(self) -> bool:
        return bool(self.cell_id and self.label and self.heat >= 0 and self.salience >= 0 and self.confidence)

    def render(self, rank: int) -> list[str]:
        return [
            f"  + [central_anchor:{rank}] is {self.label}",
            f"    = cell_id: {self.cell_id}",
            f"    = heat: {self.heat}",
            f"    = salience: {self.salience}",
            f"    = confidence: {self.confidence}",
            f"    = caution_load: {self.caution_load}",
            f"    = total_weight: {self.total_weight}",
            f"    = source_ref: {self.source_ref or 'not_supplied'}",
        ]


@dataclass(frozen=True)
class FoldLeg:
    leg_id: str
    target_cell: str
    relation_type: str
    heat: int
    confidence: str
    source_anchor: str
    central_anchor: str = ""
    dimension: str = ""
    outside: str = "semantic proxy only"

    @property
    def leg_key(self) -> str:
        return _safe_key(self.leg_id)

    @property
    def target_key(self) -> str:
        return _safe_key(self.target_cell)

    @property
    def relation_key(self) -> str:
        return _safe_key(self.relation_type)

    @property
    def dimension_key(self) -> str:
        return _safe_key(self.dimension or self.relation_type)

    @property
    def ready(self) -> bool:
        return bool(self.leg_id and self.target_cell and self.relation_type and self.heat >= 0 and self.confidence and self.source_anchor)

    def render(self, index: int) -> list[str]:
        return [
            f"  + [fold_leg:{index}] is {self.target_cell}",
            f"    = leg_id: {self.leg_id}",
            f"    = central_anchor: {self.central_anchor or 'unassigned'}",
            f"    = relation_type: {self.relation_type}",
            f"    = dimension: {self.dimension or self.relation_type}",
            f"    = heat: {self.heat}",
            f"    = confidence: {self.confidence}",
            f"    = source_anchor: {self.source_anchor}",
            f"    = outside: {self.outside}",
        ]


@dataclass(frozen=True)
class SevenFoldPantsFrame:
    frame_id: str
    subject_surface: str
    purpose: str
    shared_boundary: str
    correlations: tuple[CorrelationCell, ...]
    fold_legs: tuple[FoldLeg, ...]
    outside: tuple[str, ...] = DEFAULT_SEVEN_FOLD_OUTSIDE

    @property
    def frame_key(self) -> str:
        return _safe_key(self.frame_id)

    @property
    def ready(self) -> bool:
        return bool(
            self.frame_id
            and self.subject_surface
            and self.shared_boundary
            and len(self.correlations) >= 3
            and all(cell.ready for cell in self.correlations)
            and len(self.fold_legs) <= MAX_FOLD_LEGS
            and all(leg.ready for leg in self.fold_legs)
            and self.outside
        )

    @property
    def top_three_correlations(self) -> tuple[CorrelationCell, ...]:
        return tuple(sorted(self.correlations, key=lambda cell: (-cell.total_weight, -cell.heat, cell.cell_key))[:3])

    @property
    def folded_periphery(self) -> tuple[CorrelationCell, ...]:
        central_ids = {cell.cell_id for cell in self.top_three_correlations}
        return tuple(cell for cell in sorted(self.correlations, key=lambda cell: (-cell.total_weight, cell.cell_key)) if cell.cell_id not in central_ids)

    @property
    def used_capacity(self) -> int:
        return len(self.fold_legs)

    @property
    def heat_order(self) -> str:
        return " > ".join(f"{cell.cell_id}:{cell.total_weight}" for cell in self.top_three_correlations)

    def render(self) -> str:
        lines = [
            "Subject: Seven-Fold Pants Correlation Frame",
            "",
            f"& [SevenFoldPantsFrame:{self.frame_key}] is a seven_fold_pants_correlation_frame",
            f"  + [frame_id] is {self.frame_id}",
            f"  + [subject_surface_frame] is {self.subject_surface}",
            f"  + [purpose] is {self.purpose or 'rank visible correlations and fold higher-dimensional periphery'}",
            f"  + [shared_boundary] is {self.shared_boundary}",
            f"  + [central_correlation_triad] is {', '.join(cell.cell_id for cell in self.top_three_correlations)}",
            f"  + [heat_order] is {self.heat_order}",
            f"  + [seven_fold_capacity] is used={self.used_capacity} max={MAX_FOLD_LEGS}",
            f"  + [relationship_scatter] is {', '.join(leg.target_cell for leg in self.fold_legs) if self.fold_legs else 'none'}",
            f"  + [outside] is {', '.join(self.outside)}",
            "",
            "& [CentralCorrelationTriad] is the immediate focus heat order",
        ]
        for rank, cell in enumerate(self.top_three_correlations, start=1):
            lines.extend(cell.render(rank))
        lines.extend(("", "& [FoldLegSet] is higher-dimensional periphery carried outside the flat slice"))
        for index, leg in enumerate(self.fold_legs, start=1):
            lines.extend(leg.render(index))
        lines.extend(
            [
                "",
                f"({self.subject_surface}) :central_correlation_triad: /{_safe_key(self.shared_boundary)}/ |outside|",
            ]
        )
        for rank, cell in enumerate(self.top_three_correlations, start=1):
            lines.extend(
                [
                    f"  + [central_anchor:{rank}] is heat_ordered_cell",
                    f"    = heat: {cell.heat}",
                    f"    = confidence: {cell.confidence}",
                ]
            )
        lines.append(f"  = seven_fold_capacity: used={self.used_capacity} max={MAX_FOLD_LEGS}")
        for index, leg in enumerate(self.fold_legs, start=1):
            lines.append(
                f"  = fold_leg:{index} -> {leg.target_cell} by {leg.relation_type} with heat={leg.heat} confidence={leg.confidence}"
            )
        lines.append(f"  - outside: {', '.join(self.outside)}")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.frame_key
        frame_node = HypergraphNode(
            f"N:map:{graph_id}",
            self.frame_id,
            (("capacity_used", str(self.used_capacity)), ("heat_order", self.heat_order)),
        )
        subject_node = HypergraphNode(f"N:subject:{_safe_key(self.subject_surface)}", self.subject_surface)
        heat_node = HypergraphNode(f"N:signal:{graph_id}_correlation_heat_map", self.heat_order)
        outside_node = HypergraphNode("N:outside:seven_fold_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [frame_node, subject_node, heat_node, outside_node]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:maps:{graph_id}",
                "maps",
                (("frame", frame_node.key), ("subject", subject_node.key), ("outside", outside_node.key)),
                (("shared_boundary", self.shared_boundary),),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("frame", frame_node.key), ("outside", outside_node.key)),
                (("proof_status", "heat_is_not_truth"),),
            ),
        ]
        central_participants = [("heat", heat_node.key)]
        for rank, cell in enumerate(self.top_three_correlations, start=1):
            cell_node = HypergraphNode(
                f"N:cell:central_{rank}_{cell.cell_key}",
                cell.label,
                (
                    ("rank", str(rank)),
                    ("heat", str(cell.heat)),
                    ("salience", str(cell.salience)),
                    ("confidence", cell.confidence),
                    ("caution_load", str(cell.caution_load)),
                    ("total_weight", str(cell.total_weight)),
                    ("source_ref", cell.source_ref or "not_supplied"),
                ),
            )
            nodes.append(cell_node)
            central_participants.append((f"cell_{rank}", cell_node.key))
            edges.append(
                HypergraphEdge(
                    f"E:weighs:central_{rank}_{cell.cell_key}",
                    "weighs",
                    (("frame", frame_node.key), ("cell", cell_node.key), ("heat", heat_node.key)),
                    (("rank", str(rank)), ("total_weight", str(cell.total_weight))),
                )
            )
        edges.append(
            HypergraphEdge(
                f"E:weighs:{graph_id}_central_triad",
                "weighs",
                tuple(central_participants),
                (("order", self.heat_order),),
            )
        )
        central_keys = {cell.cell_id: f"N:cell:central_{rank}_{cell.cell_key}" for rank, cell in enumerate(self.top_three_correlations, start=1)}
        for index, leg in enumerate(self.fold_legs, start=1):
            leg_node = HypergraphNode(
                f"N:leg:{leg.leg_key}",
                leg.relation_type,
                (("heat", str(leg.heat)), ("confidence", leg.confidence), ("source_anchor", leg.source_anchor), ("outside", leg.outside)),
            )
            target_node = HypergraphNode(f"N:cell:{leg.target_key}", leg.target_cell)
            orbit_node = HypergraphNode(f"N:orbit:{leg.dimension_key}", f"{leg.dimension or leg.relation_type} weighted balance orbit")
            dimension_node = HypergraphNode(f"N:dimension:{leg.dimension_key}", leg.dimension or leg.relation_type)
            source_node = HypergraphNode(f"N:source:{_safe_key(leg.source_anchor)}", leg.source_anchor)
            nodes.extend((leg_node, target_node, orbit_node, dimension_node, source_node))
            central_key = central_keys.get(leg.central_anchor, frame_node.key)
            edges.extend(
                (
                    HypergraphEdge(
                        f"E:folds:{leg.leg_key}",
                        "folds",
                        (("frame", frame_node.key), ("leg", leg_node.key), ("target", target_node.key), ("source", source_node.key)),
                        (("order", str(index)), ("capacity_max", str(MAX_FOLD_LEGS))),
                    ),
                    HypergraphEdge(
                        f"E:orbits:{leg.leg_key}",
                        "orbits",
                        (("orbit", orbit_node.key), ("center", central_key), ("leg", leg_node.key), ("dimension", dimension_node.key)),
                        (("weighted_balance", str(leg.heat)),),
                    ),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.frame_id} Seven-Fold Pants Correlation Frame",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG seven-fold-pants-correlation-frame"),
                ("subject_surface", self.subject_surface),
                ("capacity_used", str(self.used_capacity)),
                ("capacity_max", str(MAX_FOLD_LEGS)),
            ),
            outside=self.outside,
        )


def build_seven_fold_pants_frame(
    *,
    frame_id: str,
    subject_surface: str,
    correlations: Iterable[CorrelationCell],
    fold_legs: Iterable[FoldLeg] = (),
    purpose: str = "",
    shared_boundary: str = "visible subject surface",
    outside: Iterable[str] = DEFAULT_SEVEN_FOLD_OUTSIDE,
) -> SevenFoldPantsFrame:
    correlation_tuple = tuple(correlations)
    selected_legs = tuple(fold_legs) or _default_fold_legs(correlation_tuple)
    if len(selected_legs) > MAX_FOLD_LEGS:
        selected_legs = selected_legs[:MAX_FOLD_LEGS]
    return SevenFoldPantsFrame(
        frame_id=frame_id,
        subject_surface=subject_surface,
        purpose=purpose,
        shared_boundary=shared_boundary,
        correlations=correlation_tuple,
        fold_legs=selected_legs,
        outside=tuple(_parse_list_values(outside)) or DEFAULT_SEVEN_FOLD_OUTSIDE,
    )


def parse_correlation_cell(value: str) -> CorrelationCell:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 5:
        raise ValueError("correlation must be cell_id|label|heat|salience|confidence[|source_ref][|caution_load]")
    return CorrelationCell(
        cell_id=parts[0],
        label=parts[1],
        heat=int(parts[2]),
        salience=int(parts[3]),
        confidence=parts[4],
        source_ref=parts[5] if len(parts) > 5 else "",
        caution_load=int(parts[6]) if len(parts) > 6 and parts[6] else 0,
    )


def parse_fold_leg(value: str) -> FoldLeg:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 6:
        raise ValueError("fold leg must be leg_id|target_cell|relation_type|heat|confidence|source_anchor[|central_anchor][|dimension][|outside]")
    return FoldLeg(
        leg_id=parts[0],
        target_cell=parts[1],
        relation_type=parts[2],
        heat=int(parts[3]),
        confidence=parts[4],
        source_anchor=parts[5],
        central_anchor=parts[6] if len(parts) > 6 else "",
        dimension=parts[7] if len(parts) > 7 else "",
        outside=parts[8] if len(parts) > 8 else "semantic proxy only",
    )


def _default_fold_legs(correlations: tuple[CorrelationCell, ...]) -> tuple[FoldLeg, ...]:
    ordered = tuple(sorted(correlations, key=lambda cell: (-cell.total_weight, -cell.heat, cell.cell_key)))
    central = ordered[:3]
    periphery = ordered[3 : 3 + MAX_FOLD_LEGS]
    if not central:
        return ()
    legs: list[FoldLeg] = []
    for index, cell in enumerate(periphery, start=1):
        anchor = central[(index - 1) % len(central)]
        legs.append(
            FoldLeg(
                leg_id=f"fold_{index}_{cell.cell_id}",
                target_cell=cell.cell_id,
                relation_type=f"{anchor.cell_id}_to_{cell.cell_id}",
                heat=cell.heat,
                confidence=cell.confidence,
                source_anchor=cell.source_ref or "not_supplied",
                central_anchor=anchor.cell_id,
                dimension=cell.cell_id,
                outside="auto fold leg from visible correlation ranking",
            )
        )
    return tuple(legs)


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
