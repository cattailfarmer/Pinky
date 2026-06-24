from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


VALID_SCALES = {"closed", "slender", "normal", "wide", "deep", "explosive_controlled"}

DEFAULT_TOPOLOGY_OUTSIDE = (
    "hidden activations",
    "actual transformer weights",
    "exact embedding geometry",
    "unsupported causation",
    "unrepresented cells beyond the map",
)


@dataclass(frozen=True)
class TopologyCell:
    cell_id: str
    label: str
    cell_role: str
    dimension: str = ""
    relation_to_focus: str = ""
    density: int = 1
    salience: int = 1
    source_ref: str = ""

    @property
    def cell_key(self) -> str:
        return _safe_key(self.cell_id)

    @property
    def dimension_key(self) -> str:
        return _safe_key(self.dimension or "local_meaning_body")

    @property
    def relation_key(self) -> str:
        return _safe_key(self.relation_to_focus or self.cell_role)

    @property
    def ready(self) -> bool:
        return bool(self.cell_id and self.label and self.cell_role and self.density >= 0 and self.salience >= 0)

    @property
    def heat(self) -> int:
        return self.density + self.salience

    def render(self, index: int) -> list[str]:
        lines = [
            f"  + [cell_{index:03d}_{self.cell_key}] is {self.label}",
            f"    = cell_role: {self.cell_role}",
            f"    = dimension: {self.dimension or 'local_meaning_body'}",
            f"    = relation_to_focus: {self.relation_to_focus or 'self'}",
            f"    = meaning_connection_density: {self.density}",
            f"    = salience: {self.salience}",
        ]
        if self.source_ref:
            lines.append(f"    = source_ref: {self.source_ref}")
        return lines


@dataclass(frozen=True)
class PantsLeg:
    leg_id: str
    from_cell: str
    to_cell: str
    relation_type: str
    weight: int = 1
    boundary: str = ""

    @property
    def leg_key(self) -> str:
        return _safe_key(self.leg_id or f"{self.from_cell}_{self.to_cell}_{self.relation_type}")

    @property
    def relation_key(self) -> str:
        return _safe_key(self.relation_type)

    @property
    def ready(self) -> bool:
        return bool(self.from_cell and self.to_cell and self.relation_type and self.weight >= 0)

    def render(self, index: int) -> list[str]:
        return [
            f"  + [leg_{index:03d}_{self.leg_key}] is {self.relation_type}",
            f"    = from_cell: {self.from_cell}",
            f"    = to_cell: {self.to_cell}",
            f"    = weight: {self.weight}",
            f"    = boundary: {self.boundary or 'semantic proxy only'}",
        ]


@dataclass(frozen=True)
class HyperbolicPantsTopologyMap:
    map_id: str
    focus_subject: str
    focal_cell: TopologyCell
    periphery_cells: tuple[TopologyCell, ...]
    pants_legs: tuple[PantsLeg, ...]
    scale: str
    purpose: str = ""
    outside: tuple[str, ...] = DEFAULT_TOPOLOGY_OUTSIDE

    @property
    def map_key(self) -> str:
        return _safe_key(self.map_id)

    @property
    def ready(self) -> bool:
        cell_ids = {self.focal_cell.cell_id, *(cell.cell_id for cell in self.periphery_cells)}
        return bool(
            self.map_id
            and self.focus_subject
            and self.focal_cell.ready
            and self.periphery_cells
            and all(cell.ready for cell in self.periphery_cells)
            and self.pants_legs
            and all(leg.ready for leg in self.pants_legs)
            and all(leg.from_cell in cell_ids and leg.to_cell in cell_ids for leg in self.pants_legs)
            and self.scale in VALID_SCALES
            and self.outside
        )

    @property
    def dimensionality_count(self) -> int:
        return len({cell.dimension_key for cell in self.periphery_cells if cell.dimension_key})

    @property
    def adjacency_ring(self) -> tuple[str, ...]:
        ordered = sorted(self.periphery_cells, key=lambda cell: (-cell.heat, cell.cell_key))
        return tuple(cell.cell_id for cell in ordered)

    @property
    def association_gradient(self) -> str:
        if not self.periphery_cells:
            return "none"
        ordered = sorted(self.periphery_cells, key=lambda cell: (-cell.heat, cell.cell_key))
        return " > ".join(f"{cell.cell_id}:{cell.heat}" for cell in ordered)

    def render(self) -> str:
        lines = [
            "Subject: Hyperbolic Pants Topology Map",
            "",
            f"& [HyperbolicPantsTopologyMap:{self.map_key}] is a HyperbolicPantsAttentionMap SOP-HG source record",
            f"  + [map_id] is {self.map_id}",
            f"  + [focus_subject] is {self.focus_subject}",
            f"  + [purpose] is {self.purpose or 'map focal meaning and periphery meaning'}",
            f"  + [focal_cell] is {self.focal_cell.cell_id}",
            f"  + [local_meaning_body] is {self.focal_cell.label}",
            f"  + [dimensionality_count] is {self.dimensionality_count}",
            f"  + [adjacency_ring] is {', '.join(self.adjacency_ring)}",
            f"  + [hyperbolic_scale] is {self.scale}",
            f"  + [association_gradient] is {self.association_gradient}",
            f"  + [transformer_hypergeometry_proxy] is visible semantic topology only",
            f"  + [outside] is {', '.join(self.outside)}",
            "",
            "& [TopologyCellSet] is focal and orbital meaning cells",
        ]
        lines.extend(self.focal_cell.render(1))
        for index, cell in enumerate(self.periphery_cells, start=2):
            lines.extend(cell.render(index))
        lines.extend(("", "& [PantsLegSet] is typed exits for map navigation"))
        for index, leg in enumerate(self.pants_legs, start=1):
            lines.extend(leg.render(index))
        lines.extend(
            [
                "",
                f"({self.focal_cell.cell_id}) :{_safe_key(self.focal_cell.label)}: /semantic_proxy_boundary/ |outside|",
            ]
        )
        for cell in self.periphery_cells:
            lines.extend(
                [
                    f"  + [periphery_cell:{cell.cell_key}] is orbital_component",
                    f"    = dimension: {cell.dimension or 'unspecified'}",
                    f"    = adjacency: {self.focal_cell.cell_id} by {cell.relation_to_focus or 'related'}",
                ]
            )
            for leg in self.pants_legs:
                if leg.to_cell == cell.cell_id:
                    lines.append(f"    = leg: {leg.relation_type} -> {cell.cell_id}")
        lines.append(f"  - outside: {', '.join(self.outside)}")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.map_key
        map_node = HypergraphNode(
            f"N:map:{graph_id}",
            self.map_id,
            (
                ("scale", self.scale),
                ("dimensionality_count", str(self.dimensionality_count)),
                ("association_gradient", self.association_gradient),
            ),
        )
        focus_node = HypergraphNode(f"N:focus:{_safe_key(self.focus_subject)}", self.focus_subject)
        focal_node = HypergraphNode(
            f"N:cell:{self.focal_cell.cell_key}",
            self.focal_cell.label,
            (
                ("cell_role", self.focal_cell.cell_role),
                ("meaning_connection_density", str(self.focal_cell.density)),
                ("salience", str(self.focal_cell.salience)),
            ),
        )
        outside_node = HypergraphNode("N:outside:hyperbolic_map_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [map_node, focus_node, focal_node, outside_node]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:maps:{graph_id}",
                "maps",
                (("map", map_node.key), ("focus", focus_node.key), ("cell", focal_node.key)),
                (("scale", self.scale),),
            ),
            HypergraphEdge(
                f"E:contains:{self.focal_cell.cell_key}",
                "contains",
                (("map", map_node.key), ("focal_cell", focal_node.key)),
                (("local_meaning_body", self.focal_cell.label),),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("map", map_node.key), ("outside", outside_node.key)),
                (("proxy_status", "semantic_not_hidden_geometry"),),
            ),
        ]
        for cell in self.periphery_cells:
            cell_node = HypergraphNode(
                f"N:cell:{cell.cell_key}",
                cell.label,
                (
                    ("cell_role", cell.cell_role),
                    ("dimension", cell.dimension or "unspecified"),
                    ("meaning_connection_density", str(cell.density)),
                    ("salience", str(cell.salience)),
                ),
            )
            dimension_node = HypergraphNode(f"N:dimension:{cell.dimension_key}", cell.dimension or "unspecified")
            orbit_node = HypergraphNode(f"N:orbit:{cell.dimension_key}", f"{cell.dimension or 'unspecified'} orbit")
            nodes.extend((cell_node, dimension_node, orbit_node))
            edges.extend(
                (
                    HypergraphEdge(
                        f"E:orbits:{cell.dimension_key}",
                        "orbits",
                        (("focal", focal_node.key), ("periphery", cell_node.key), ("orbit", orbit_node.key), ("dimension", dimension_node.key)),
                        (("heat", str(cell.heat)),),
                    ),
                    HypergraphEdge(
                        f"E:adjoins:{self.focal_cell.cell_key}_{cell.cell_key}",
                        "adjoins",
                        (("cell_a", focal_node.key), ("cell_b", cell_node.key), ("map", map_node.key)),
                        (("relation", cell.relation_to_focus or "related"),),
                    ),
                )
            )
        cell_node_keys = {self.focal_cell.cell_id: focal_node.key}
        cell_node_keys.update({cell.cell_id: f"N:cell:{cell.cell_key}" for cell in self.periphery_cells})
        for leg in self.pants_legs:
            leg_node = HypergraphNode(
                f"N:leg:{leg.leg_key}",
                leg.relation_type,
                (("weight", str(leg.weight)), ("boundary", leg.boundary or "semantic proxy only")),
            )
            relation_node = HypergraphNode(f"N:term:{leg.relation_key}", leg.relation_type)
            nodes.extend((leg_node, relation_node))
            edges.append(
                HypergraphEdge(
                    f"E:navigates:{leg.leg_key}",
                    "navigates",
                    (
                        ("map", map_node.key),
                        ("leg", leg_node.key),
                        ("from", cell_node_keys[leg.from_cell]),
                        ("to", cell_node_keys[leg.to_cell]),
                        ("relation", relation_node.key),
                    ),
                    (("weight", str(leg.weight)),),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.map_id} Hyperbolic Pants Topology Map",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG hyperbolic-pants-topology-map"),
                ("focus_subject", self.focus_subject),
                ("scale", self.scale),
                ("dimensionality_count", str(self.dimensionality_count)),
            ),
            outside=self.outside,
        )


def build_hyperbolic_pants_topology_map(
    *,
    map_id: str,
    focus_subject: str,
    focal_terms: Iterable[str],
    periphery_cells: Iterable[TopologyCell],
    pants_legs: Iterable[PantsLeg] = (),
    scale: str = "",
    purpose: str = "",
    outside: Iterable[str] = DEFAULT_TOPOLOGY_OUTSIDE,
) -> HyperbolicPantsTopologyMap:
    cells = tuple(periphery_cells)
    focal_items = tuple(_parse_list_values(focal_terms))
    focal_cell = TopologyCell(
        cell_id="focal_cell",
        label=", ".join(focal_items) or focus_subject,
        cell_role="focal_cell",
        dimension="local_meaning_body",
        relation_to_focus="self",
        density=max(1, len(focal_items) * 2),
        salience=max(1, len(cells) + 2),
    )
    legs = tuple(pants_legs) or _default_legs(focal_cell, cells)
    resolved_scale = scale or select_hyperbolic_scale(cells)
    if resolved_scale not in VALID_SCALES:
        raise ValueError(f"unknown topology scale: {resolved_scale}")
    return HyperbolicPantsTopologyMap(
        map_id=map_id,
        focus_subject=focus_subject,
        focal_cell=focal_cell,
        periphery_cells=cells,
        pants_legs=legs,
        scale=resolved_scale,
        purpose=purpose,
        outside=tuple(_parse_list_values(outside)) or DEFAULT_TOPOLOGY_OUTSIDE,
    )


def select_hyperbolic_scale(periphery_cells: tuple[TopologyCell, ...]) -> str:
    if not periphery_cells:
        return "closed"
    dimensionality = len({cell.dimension_key for cell in periphery_cells})
    total_heat = sum(cell.heat for cell in periphery_cells)
    if dimensionality >= 6 or total_heat >= 60:
        return "deep"
    if dimensionality >= 4 or total_heat >= 32:
        return "wide"
    if dimensionality >= 2:
        return "normal"
    return "slender"


def parse_topology_cell(value: str) -> TopologyCell:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 5:
        raise ValueError("cell must be cell_id|label|dimension|relation_to_focus|density[|salience][|source_ref]")
    return TopologyCell(
        cell_id=parts[0],
        label=parts[1],
        cell_role="periphery_cell",
        dimension=parts[2],
        relation_to_focus=parts[3],
        density=int(parts[4]) if parts[4] else 1,
        salience=int(parts[5]) if len(parts) > 5 and parts[5] else 1,
        source_ref=parts[6] if len(parts) > 6 else "",
    )


def parse_pants_leg(value: str) -> PantsLeg:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 4:
        raise ValueError("leg must be leg_id|from_cell|to_cell|relation_type[|weight][|boundary]")
    return PantsLeg(
        leg_id=parts[0],
        from_cell=parts[1],
        to_cell=parts[2],
        relation_type=parts[3],
        weight=int(parts[4]) if len(parts) > 4 and parts[4] else 1,
        boundary=parts[5] if len(parts) > 5 else "",
    )


def _default_legs(focal_cell: TopologyCell, cells: tuple[TopologyCell, ...]) -> tuple[PantsLeg, ...]:
    return tuple(
        PantsLeg(
            leg_id=f"{focal_cell.cell_id}_to_{cell.cell_id}",
            from_cell=focal_cell.cell_id,
            to_cell=cell.cell_id,
            relation_type=cell.relation_to_focus or cell.dimension or "related",
            weight=max(1, cell.heat),
            boundary="semantic proxy only",
        )
        for cell in cells
    )


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
