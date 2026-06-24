from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


VALID_DEPTHS = {"closed", "slender", "normal", "wide", "deep", "explosive_controlled"}

DEFAULT_APERTURE_OUTSIDE = (
    "hidden model state",
    "unsupported causation",
    "unbounded periphery",
    "worker mutation authority",
    "durable subject declarations before close pass",
)


@dataclass(frozen=True)
class FocalPointSeed:
    source_ref: str
    focus_subject: str
    focus_mode: str = ""
    executive_drive: str = ""
    inside: tuple[str, ...] = field(default_factory=tuple)
    boundary: str = ""
    outside: tuple[str, ...] = field(default_factory=tuple)
    active_reflection: str = ""
    open_question: str = ""

    @property
    def focus_key(self) -> str:
        return _safe_key(self.focus_subject)

    @property
    def ready(self) -> bool:
        return bool(self.source_ref and self.focus_subject and self.boundary and self.outside)


@dataclass(frozen=True)
class ApertureSupport:
    support_id: str
    label: str
    source_ref: str
    relation: str
    heat: int = 1
    prompt_hint: str = ""

    @property
    def support_key(self) -> str:
        return _safe_key(self.support_id or self.label)

    @property
    def relation_key(self) -> str:
        return _safe_key(self.relation)

    @property
    def ready(self) -> bool:
        return bool(self.support_id and self.label and self.source_ref and self.relation and self.heat >= 0)

    def render(self, index: int) -> list[str]:
        return [
            f"  + [support_{index:03d}_{self.support_key}] is {self.label}",
            f"    = source_ref: {self.source_ref}",
            f"    = relation: {self.relation}",
            f"    = heat: {self.heat}",
            f"    = prompt_hint: {self.prompt_hint or 'not_supplied'}",
        ]


@dataclass(frozen=True)
class ApertureReentrySpringboard:
    cycle_id: str
    focal_seed: FocalPointSeed
    depth_adjustment: str
    support_draws: tuple[ApertureSupport, ...]
    relation_survey: tuple[str, ...]
    approach_set: tuple[str, ...]
    supported_core: str
    new_perspective: str
    second_pass_narrative_prompts: tuple[str, ...]
    subject_declaration_prompts: tuple[str, ...]
    balance_state: str
    outside: tuple[str, ...] = DEFAULT_APERTURE_OUTSIDE

    @property
    def cycle_key(self) -> str:
        return _safe_key(self.cycle_id)

    @property
    def ready(self) -> bool:
        return bool(
            self.cycle_id
            and self.focal_seed.ready
            and self.depth_adjustment in VALID_DEPTHS
            and self.support_draws
            and all(support.ready for support in self.support_draws)
            and self.relation_survey
            and self.approach_set
            and self.supported_core
            and self.second_pass_narrative_prompts
            and self.subject_declaration_prompts
            and self.outside
        )

    def render(self) -> str:
        lines = [
            "Subject: Aperture Reentry Springboard",
            "",
            f"& [ApertureReentrySpringboard:{self.cycle_key}] is a reentry_springboard",
            f"  + [cycle_id] is {self.cycle_id}",
            f"  + [focal_source] is {self.focal_seed.source_ref}",
            f"  + [focal_subject] is {self.focal_seed.focus_subject}",
            f"  + [focus_mode] is {self.focal_seed.focus_mode or 'not_supplied'}",
            f"  + [active_reflection] is {self.focal_seed.active_reflection or 'not_supplied'}",
            f"  + [depth_adjustment] is {self.depth_adjustment}",
            f"  + [support_draw_count] is {len(self.support_draws)}",
            f"  + [relation_survey] is {', '.join(self.relation_survey)}",
            f"  + [approach_set] is {', '.join(self.aperture_set)}",
            "  + [open_pass] is support_draw admitted by focal boundary and depth_adjustment",
            "  + [deepening_pass] is fold selected supports, then unwind to supported_core, uncertainty, and outside",
            "  + [close_pass] is close widened attention into this compact springboard before narrative or subject declarations",
            f"  + [supported_core] is {self.supported_core}",
            f"  + [new_perspective] is {self.new_perspective}",
            f"  + [balance_state] is {self.balance_state}",
            f"  + [outside] is {', '.join(self.outside)}",
            "",
            "& [SupportDrawSet] is selected periphery admitted into the aperture",
        ]
        for index, support in enumerate(self.support_draws, start=1):
            lines.extend(support.render(index))
        lines.extend(("", "& [SecondPassNarrativePromptSet] is downstream narrative work after close_pass"))
        for index, prompt in enumerate(self.second_pass_narrative_prompts, start=1):
            lines.append(f"  + [second_pass_narrative_prompt_{index:03d}] is {prompt}")
        lines.extend(("", "& [SubjectDeclarationPromptSet] is downstream subject work after second-pass narrative"))
        for index, prompt in enumerate(self.subject_declaration_prompts, start=1):
            lines.append(f"  + [subject_declaration_prompt_{index:03d}] is {prompt}")
        lines.extend(
            [
                "",
                "(aperture_reentry_springboard) :focal_subject: /support_draw and close_pass/ |outside|",
                f"  + [focal_subject] is {self.focal_seed.focus_subject}",
                f"  + [support_draw] is {', '.join(support.label for support in self.support_draws)}",
                f"  + [close_pass] is compact reentry_springboard",
                f"  |outside| {', '.join(self.outside)}",
            ]
        )
        return "\n".join(lines)

    @property
    def aperture_set(self) -> tuple[str, ...]:
        return self.approach_set

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.cycle_key
        cycle_node = HypergraphNode(
            f"N:policy:{graph_id}",
            self.cycle_id,
            (("depth_adjustment", self.depth_adjustment), ("balance_state", self.balance_state)),
        )
        focus_node = HypergraphNode(f"N:focus:{self.focal_seed.focus_key}", self.focal_seed.focus_subject)
        aperture_node = HypergraphNode(f"N:aperture:{_safe_key(self.depth_adjustment)}", self.depth_adjustment)
        reentry_node = HypergraphNode(
            f"N:reentry:{graph_id}",
            "reentry springboard",
            (("supported_core", self.supported_core),),
        )
        narrative_node = HypergraphNode(
            f"N:narrative:{graph_id}_second_pass",
            "second-pass narrative prompts",
            (("prompt_count", str(len(self.second_pass_narrative_prompts))),),
        )
        declaration_node = HypergraphNode(
            f"N:subject:{graph_id}_declaration_pass",
            "subject declaration prompts",
            (("prompt_count", str(len(self.subject_declaration_prompts))),),
        )
        outside_node = HypergraphNode("N:outside:aperture_reentry_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [
            cycle_node,
            focus_node,
            aperture_node,
            reentry_node,
            narrative_node,
            declaration_node,
            outside_node,
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:opens:{graph_id}",
                "opens",
                (("cycle", cycle_node.key), ("focus", focus_node.key), ("aperture", aperture_node.key)),
                (("support_draw_count", str(len(self.support_draws))),),
            ),
            HypergraphEdge(
                f"E:closes:{graph_id}",
                "closes",
                (("cycle", cycle_node.key), ("aperture", aperture_node.key), ("reentry", reentry_node.key)),
                (("close_pass", "required_before_narrative"),),
            ),
            HypergraphEdge(
                f"E:springboards:{graph_id}",
                "springboards",
                (("reentry", reentry_node.key), ("narrative", narrative_node.key), ("subject", declaration_node.key)),
            ),
            HypergraphEdge(
                f"E:digests:{graph_id}",
                "digests",
                (("narrative", narrative_node.key), ("focus", focus_node.key), ("outside", outside_node.key)),
            ),
            HypergraphEdge(
                f"E:defines:{graph_id}",
                "defines",
                (("subject", declaration_node.key), ("focus", focus_node.key), ("reentry", reentry_node.key)),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("cycle", cycle_node.key), ("outside", outside_node.key)),
            ),
        ]
        for index, support in enumerate(self.support_draws, start=1):
            support_node = HypergraphNode(
                f"N:periphery:{support.support_key}",
                support.label,
                (("heat", str(support.heat)), ("source_ref", support.source_ref)),
            )
            source_node = HypergraphNode(f"N:source:{_safe_key(support.source_ref)}", support.source_ref)
            relation_node = HypergraphNode(f"N:term:{support.relation_key}", support.relation)
            nodes.extend((support_node, source_node, relation_node))
            edges.append(
                HypergraphEdge(
                    f"E:probes:{graph_id}_{index:03d}",
                    "probes",
                    (
                        ("cycle", cycle_node.key),
                        ("support", support_node.key),
                        ("source", source_node.key),
                        ("relation", relation_node.key),
                    ),
                    (("heat", str(support.heat)),),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.cycle_id} Aperture Reentry Springboard",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG aperture-reentry-springboard"),
                ("focal_subject", self.focal_seed.focus_subject),
                ("depth_adjustment", self.depth_adjustment),
                ("support_draw_count", str(len(self.support_draws))),
            ),
            outside=self.outside,
        )


def read_focal_point_seed(path: str | Path) -> FocalPointSeed:
    focal_path = Path(path)
    fields = _parse_sop_fields(focal_path.read_text(encoding="utf-8"))
    return FocalPointSeed(
        source_ref=str(focal_path),
        focus_subject=fields.get("focus_subject", ""),
        focus_mode=fields.get("focus_mode", ""),
        executive_drive=fields.get("executive_drive", ""),
        inside=_parse_list(fields.get("inside", "")),
        boundary=fields.get("boundary", ""),
        outside=_parse_list(fields.get("outside", "")),
        active_reflection=fields.get("active_reflection", ""),
        open_question=fields.get("open_question", ""),
    )


def build_aperture_reentry_springboard(
    *,
    focal_point_path: str | Path,
    supports: Iterable[ApertureSupport],
    cycle_id: str = "aperture_reentry_springboard",
    depth_adjustment: str = "",
    outside: Iterable[str] = DEFAULT_APERTURE_OUTSIDE,
) -> ApertureReentrySpringboard:
    focal_seed = read_focal_point_seed(focal_point_path)
    support_tuple = tuple(supports)
    depth = select_depth_adjustment(support_tuple, requested=depth_adjustment)
    relation_survey = tuple(dict.fromkeys(support.relation for support in support_tuple if support.relation))
    approach_set = _select_approach_set(support_tuple, depth)
    prompts = _build_second_pass_prompts(focal_seed, support_tuple)
    declarations = _build_subject_declaration_prompts(focal_seed, support_tuple)
    return ApertureReentrySpringboard(
        cycle_id=cycle_id,
        focal_seed=focal_seed,
        depth_adjustment=depth,
        support_draws=support_tuple,
        relation_survey=relation_survey,
        approach_set=approach_set,
        supported_core=_build_supported_core(focal_seed, support_tuple, relation_survey),
        new_perspective=_build_new_perspective(focal_seed, support_tuple, depth),
        second_pass_narrative_prompts=prompts,
        subject_declaration_prompts=declarations,
        balance_state=_balance_state(depth, support_tuple),
        outside=tuple(_parse_list_values(outside)) or DEFAULT_APERTURE_OUTSIDE,
    )


def select_depth_adjustment(supports: tuple[ApertureSupport, ...], *, requested: str = "") -> str:
    if requested:
        normalized = _normalize(requested)
        if normalized not in VALID_DEPTHS:
            raise ValueError(f"unknown aperture depth: {requested}")
        return normalized
    if not supports:
        return "closed"
    support_count = len(supports)
    heat_total = sum(max(support.heat, 0) for support in supports)
    heat_max = max((support.heat for support in supports), default=0)
    if heat_max >= 12 or heat_total >= 36:
        return "deep"
    if heat_max >= 8 or support_count >= 4:
        return "wide"
    if support_count <= 2:
        return "slender"
    return "normal"


def parse_aperture_support(value: str) -> ApertureSupport:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 4:
        raise ValueError("support must be support_id|label|source_ref|relation[|heat][|prompt_hint]")
    heat = int(parts[4]) if len(parts) > 4 and parts[4] else 1
    return ApertureSupport(
        support_id=parts[0],
        label=parts[1],
        source_ref=parts[2],
        relation=parts[3],
        heat=heat,
        prompt_hint=parts[5] if len(parts) > 5 else "",
    )


def support_from_file(path: str | Path, *, relation: str = "source_anchor", heat: int = 4) -> ApertureSupport:
    support_path = Path(path)
    text = support_path.read_text(encoding="utf-8")
    label = _first_subject(text) or support_path.stem
    return ApertureSupport(
        support_id=support_path.stem,
        label=label,
        source_ref=str(support_path),
        relation=relation,
        heat=heat,
        prompt_hint=f"ask what {label} changes about the focal subject",
    )


def _build_supported_core(
    focal_seed: FocalPointSeed,
    supports: tuple[ApertureSupport, ...],
    relation_survey: tuple[str, ...],
) -> str:
    relation_text = ", ".join(relation_survey) if relation_survey else "no visible relations"
    return (
        f"{focal_seed.focus_subject} can open through {len(supports)} support_draw signals, "
        f"survey {relation_text}, then close into a compact springboard before durable narrative or subject declarations"
    )


def _build_new_perspective(
    focal_seed: FocalPointSeed,
    supports: tuple[ApertureSupport, ...],
    depth: str,
) -> str:
    strongest = max(supports, key=lambda support: support.heat).label if supports else "no support"
    return (
        f"{focal_seed.focus_subject} should treat {strongest} as a draw input under {depth} aperture, "
        "while preserving springboard prompts as downstream work rather than completed integration"
    )


def _build_second_pass_prompts(
    focal_seed: FocalPointSeed,
    supports: tuple[ApertureSupport, ...],
) -> tuple[str, ...]:
    prompts = []
    for support in supports:
        hint = support.prompt_hint or f"what changed through {support.relation}"
        prompts.append(
            f"Re-narrate {focal_seed.focus_subject} through {support.label}; answer {hint}; preserve outside and first-pass source."
        )
    return tuple(prompts)


def _build_subject_declaration_prompts(
    focal_seed: FocalPointSeed,
    supports: tuple[ApertureSupport, ...],
) -> tuple[str, ...]:
    return tuple(
        f"Declare or update the subject relation between {focal_seed.focus_subject} and {support.label}; cite {support.source_ref}; name boundary and outside."
        for support in supports
    )


def _select_approach_set(supports: tuple[ApertureSupport, ...], depth: str) -> tuple[str, ...]:
    limit = {"closed": 0, "slender": 2, "normal": 3, "wide": 4, "deep": 6, "explosive_controlled": 8}[depth]
    ordered = sorted(supports, key=lambda support: (-support.heat, support.support_key))
    return tuple(support.relation for support in ordered[:limit] if support.relation)


def _balance_state(depth: str, supports: tuple[ApertureSupport, ...]) -> str:
    if depth in {"deep", "explosive_controlled"}:
        return "watch"
    if not supports:
        return "blocked"
    return "stable"


def _parse_sop_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"\s*\+ \[(?P<name>[^\]]+)\] is (?P<value>.*)\s*$", line)
        if match:
            fields[match.group("name")] = match.group("value").strip()
    return fields


def _first_subject(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("Subject:"):
            return line.split(":", 1)[1].strip()
    return ""


def _parse_list(value: str) -> tuple[str, ...]:
    return tuple(_parse_list_values((value,)))


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
