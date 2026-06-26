from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


@dataclass(frozen=True)
class MathBridgeTerm:
    term_id: str
    symbolic_term: str
    formal_object: str
    problem_role: str
    evidence_status: str = "candidate"
    proof_obligations: tuple[str, ...] = field(default_factory=tuple)
    caution: str = ""

    @property
    def bridge_status(self) -> str:
        if self.evidence_status in {"defined", "accepted", "known_theorem"} and self.proof_obligations:
            return "load_bearing"
        if self.formal_object and self.proof_obligations:
            return "mapped_with_obligations"
        if self.formal_object:
            return "mapped"
        return "unmapped"

    @property
    def inquiry_route(self) -> str:
        return {
            "load_bearing": "test_in_proposition",
            "mapped_with_obligations": "resolve_obligations",
            "mapped": "add_obligations",
            "unmapped": "keep_peripheral",
        }[self.bridge_status]


@dataclass(frozen=True)
class MathBridgeMap:
    bridge_id: str
    problem_name: str
    proposition: str
    terms: tuple[MathBridgeTerm, ...]
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.bridge_id and self.problem_name and self.proposition and self.terms)

    @property
    def open_obligation_count(self) -> int:
        return sum(len(term.proof_obligations) for term in self.terms if term.bridge_status != "load_bearing")

    @property
    def weakest_terms(self) -> tuple[MathBridgeTerm, ...]:
        return tuple(term for term in self.terms if term.bridge_status in {"unmapped", "mapped"})

    def render(self) -> str:
        lines = [
            f"Subject: {self.problem_name} Math Bridge Map",
            "",
            f"& [MathBridgeMap] is {self.bridge_id}",
            f"  + [problem_name] is {self.problem_name}",
            f"  + [proposition] is {self.proposition}",
            f"  + [open_obligation_count] is {self.open_obligation_count}",
            "",
        ]
        for term in self.terms:
            lines.extend(
                [
                    f"& [{_safe_key(term.term_id)}] is a math bridge term",
                    f"  + [symbolic_term] is {term.symbolic_term}",
                    f"  + [formal_object] is {term.formal_object or 'unmapped'}",
                    f"  + [problem_role] is {term.problem_role}",
                    f"  + [evidence_status] is {term.evidence_status}",
                    f"  + [bridge_status] is {term.bridge_status}",
                    f"  + [inquiry_route] is {term.inquiry_route}",
                ]
            )
            for index, obligation in enumerate(term.proof_obligations, start=1):
                lines.append(f"    = proof_obligation_{index:03d}: {obligation}")
            if term.caution:
                lines.append(f"    = caution: {term.caution}")
            lines.append("")
        lines.append("|outside| " + "; ".join(self.residual_outside or ("bridge map is not proof",)))
        return "\n".join(lines) + "\n"

    def to_hypergraph(self) -> HypergraphRecord:
        graph_key = _safe_key(self.bridge_id)
        bridge_node = HypergraphNode(
            f"N:math_bridge:{graph_key}",
            self.bridge_id,
            (
                ("problem", self.problem_name),
                ("open_obligation_count", str(self.open_obligation_count)),
            ),
        )
        proposition_node = HypergraphNode(
            f"N:proposition:{graph_key}",
            self.proposition,
        )
        outside_node = HypergraphNode("N:outside:math_bridge_not_proof", "bridge map is not proof")
        nodes: list[HypergraphNode] = [bridge_node, proposition_node, outside_node]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:frames:{graph_key}",
                "frames",
                (("bridge", bridge_node.key), ("proposition", proposition_node.key)),
            )
        ]
        for term in self.terms:
            term_key = f"N:bridge_term:{_safe_key(term.term_id)}"
            object_key = f"N:formal_object:{_safe_key(term.formal_object or 'unmapped')}"
            nodes.append(
                HypergraphNode(
                    term_key,
                    term.symbolic_term,
                    (
                        ("bridge_status", term.bridge_status),
                        ("inquiry_route", term.inquiry_route),
                        ("evidence_status", term.evidence_status),
                    ),
                )
            )
            nodes.append(HypergraphNode(object_key, term.formal_object or "unmapped"))
            edges.append(
                HypergraphEdge(
                    f"E:maps:{_safe_key(term.term_id)}",
                    "maps_to",
                    (("term", term_key), ("formal_object", object_key), ("bridge", bridge_node.key)),
                    (("problem_role", term.problem_role),),
                )
            )
            if term.proof_obligations:
                obligation_key = f"N:obligations:{_safe_key(term.term_id)}"
                nodes.append(
                    HypergraphNode(
                        obligation_key,
                        f"{term.symbolic_term} proof obligations",
                        (("count", str(len(term.proof_obligations))),),
                    )
                )
                edges.append(
                    HypergraphEdge(
                        f"E:requires:{_safe_key(term.term_id)}",
                        "requires",
                        (("term", term_key), ("obligations", obligation_key), ("outside", outside_node.key)),
                    )
                )
        return HypergraphRecord(
            graph_id=graph_key,
            label=f"{self.problem_name} Math Bridge",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(("format_profile", "SOP-HG math-bridge-map"),),
            outside=self.residual_outside or ("bridge map is not proof",),
        )


def build_math_bridge_map(
    *,
    bridge_id: str,
    problem_name: str,
    proposition: str,
    terms: Iterable[MathBridgeTerm],
) -> MathBridgeMap:
    return MathBridgeMap(
        bridge_id=bridge_id,
        problem_name=problem_name,
        proposition=proposition,
        terms=tuple(terms),
        residual_outside=(
            "symbolic-to-formal mapping does not prove the proposition",
            "open obligations must be resolved by accepted mathematical argument",
        ),
    )


def parse_math_bridge_term(
    *,
    term_id: str,
    symbolic_term: str,
    formal_object: str = "",
    problem_role: str = "",
    evidence_status: str = "candidate",
    proof_obligations: Iterable[str] = (),
    caution: str = "",
) -> MathBridgeTerm:
    return MathBridgeTerm(
        term_id=term_id,
        symbolic_term=symbolic_term,
        formal_object=formal_object,
        problem_role=problem_role,
        evidence_status=evidence_status,
        proof_obligations=tuple(obligation for obligation in proof_obligations if obligation),
        caution=caution,
    )


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
