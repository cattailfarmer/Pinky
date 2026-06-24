from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


ORTHOGONALITY_RESULTS = {"orthogonal", "near_orthogonal", "tilted", "overlapping", "inverse", "weakened", "outside"}
HONESTY_LOADS = {"none", "watch", "alarm", "outside"}
SECURITY_LOADS = {"none", "watch", "alarm", "outside"}
HONESTY_DISPOSITIONS = {"permit", "qualify", "correct", "defer", "return_to_periphery", "reject", "outside"}
SECURITY_ALERTS = {"no_alert", "watch", "modify", "require_authorization", "stop_action", "preserve_outside", "outside"}
BOUNDARY_ALARMS = {"no_alarm", "honesty_alarm", "security_alarm", "convergent_alarm", "outside"}

DEFAULT_BOUNDARY_INSPECTION_OUTSIDE = (
    "uninspected boundary periphery",
    "hidden premise",
    "unsupported identity",
    "unsafe permission",
    "proof by framing",
    "unresolved boundary fault",
)


@dataclass(frozen=True)
class BoundaryTermInspection:
    term_id: str
    term: str
    boundary_role: str
    subject_vector: str
    boundary_vector: str
    orthogonality_result: str
    honesty_load: str
    security_load: str
    representation_claim: str
    support_surface: str
    protected_identity: str
    misdirection_vector: str = ""
    weak_boundary_fault: str = ""
    honesty_disposition: str = ""
    security_alert: str = ""

    @property
    def term_key(self) -> str:
        return _safe_key(self.term_id)

    @property
    def resolved_honesty_disposition(self) -> str:
        if self.honesty_disposition:
            return self.honesty_disposition
        if self.orthogonality_result in {"tilted", "overlapping", "inverse"} or self.honesty_load == "alarm":
            return "qualify"
        if self.orthogonality_result == "outside" or self.honesty_load == "outside":
            return "outside"
        if self.honesty_load == "watch":
            return "defer"
        return "permit"

    @property
    def resolved_security_alert(self) -> str:
        if self.security_alert:
            return self.security_alert
        if self.orthogonality_result == "weakened" or self.security_load == "alarm":
            return "modify"
        if self.security_load == "outside":
            return "outside"
        if self.security_load == "watch":
            return "watch"
        return "no_alert"

    @property
    def ready(self) -> bool:
        return bool(
            self.term_id
            and self.term
            and self.boundary_role
            and self.subject_vector
            and self.boundary_vector
            and self.orthogonality_result in ORTHOGONALITY_RESULTS
            and self.honesty_load in HONESTY_LOADS
            and self.security_load in SECURITY_LOADS
            and self.resolved_honesty_disposition in HONESTY_DISPOSITIONS
            and self.resolved_security_alert in SECURITY_ALERTS
        )

    @property
    def honesty_alarm(self) -> bool:
        return bool(
            self.orthogonality_result in {"tilted", "overlapping", "inverse"}
            or self.honesty_load in {"alarm", "outside"}
            or self.resolved_honesty_disposition in {"correct", "reject", "outside"}
        )

    @property
    def security_alarm(self) -> bool:
        return bool(
            self.orthogonality_result == "weakened"
            or self.security_load in {"alarm", "outside"}
            or self.resolved_security_alert in {"modify", "require_authorization", "stop_action", "preserve_outside", "outside"}
        )

    def render(self, index: int) -> list[str]:
        return [
            f"  + [boundary_term:{index}] is {self.term}",
            f"    = term_id: {self.term_id}",
            f"    = boundary_role: {self.boundary_role}",
            f"    = subject_vector: {self.subject_vector}",
            f"    = boundary_vector: {self.boundary_vector}",
            f"    = orthogonality_result: {self.orthogonality_result}",
            f"    = honesty_load: {self.honesty_load}",
            f"    = security_load: {self.security_load}",
            f"    = representation_claim: {self.representation_claim or 'not_supplied'}",
            f"    = support_surface: {self.support_surface or 'not_supplied'}",
            f"    = protected_identity: {self.protected_identity or 'not_supplied'}",
            f"    = misdirection_vector: {self.misdirection_vector or 'none'}",
            f"    = weak_boundary_fault: {self.weak_boundary_fault or 'none'}",
            f"    = honesty_disposition: {self.resolved_honesty_disposition}",
            f"    = security_alert: {self.resolved_security_alert}",
        ]


@dataclass(frozen=True)
class BoundaryFacultyInspectionRecord:
    inspection_id: str
    attention_subject: str
    identity_boundary: str
    boundary_periphery: tuple[str, ...]
    protected_identity: str
    terms: tuple[BoundaryTermInspection, ...]
    purpose: str = ""
    outside: tuple[str, ...] = DEFAULT_BOUNDARY_INSPECTION_OUTSIDE

    @property
    def inspection_key(self) -> str:
        return _safe_key(self.inspection_id)

    @property
    def boundary_key(self) -> str:
        return _safe_key(self.identity_boundary)

    @property
    def periphery_key(self) -> str:
        return _safe_key("_".join(self.boundary_periphery) or "boundary_periphery")

    @property
    def honesty_id(self) -> str:
        return f"{self.inspection_key}_honesty_boundary"

    @property
    def security_id(self) -> str:
        return f"{self.inspection_key}_security_boundary"

    @property
    def ready(self) -> bool:
        return bool(
            self.inspection_id
            and self.attention_subject
            and self.identity_boundary
            and self.boundary_periphery
            and self.protected_identity
            and self.terms
            and all(term.ready for term in self.terms)
            and self.outside
        )

    @property
    def boundary_alarm(self) -> str:
        honesty = any(term.honesty_alarm for term in self.terms)
        security = any(term.security_alarm for term in self.terms)
        if honesty and security:
            return "convergent_alarm"
        if honesty:
            return "honesty_alarm"
        if security:
            return "security_alarm"
        return "no_alarm"

    @property
    def orthogonality_summary(self) -> str:
        return ", ".join(f"{term.term_id}:{term.orthogonality_result}" for term in self.terms)

    @property
    def honesty_summary(self) -> str:
        return ", ".join(f"{term.term_id}:{term.resolved_honesty_disposition}" for term in self.terms)

    @property
    def security_summary(self) -> str:
        return ", ".join(f"{term.term_id}:{term.resolved_security_alert}" for term in self.terms)

    def render(self) -> str:
        lines = [
            "Subject: Boundary Faculty Inspection Runtime",
            "",
            f"& [BoundaryFacultyInspection:{self.inspection_key}] is a boundary_faculty_inspection_runtime_record",
            f"  + [inspection_id] is {self.inspection_id}",
            f"  + [attention_subject] is {self.attention_subject}",
            f"  + [identity_boundary] is {self.identity_boundary}",
            f"  + [boundary_periphery] is {', '.join(self.boundary_periphery)}",
            f"  + [protected_identity] is {self.protected_identity}",
            f"  + [purpose] is {self.purpose or 'inspect identity boundary and boundary periphery'}",
            f"  + [orthogonality_summary] is {self.orthogonality_summary}",
            f"  + [honesty_summary] is {self.honesty_summary}",
            f"  + [security_summary] is {self.security_summary}",
            f"  + [boundary_alarm] is {self.boundary_alarm}",
            f"  + [outside] is {', '.join(self.outside)}",
            "",
            "& [BoundaryTermSet] is the inspected boundary term set",
        ]
        for index, term in enumerate(self.terms, start=1):
            lines.extend(term.render(index))
        lines.extend(
            (
                "",
                f"({self.inspection_id}) :attention_subject: /identity_boundary/ |outside|",
                f"  = attention_subject: {self.attention_subject}",
                f"  = identity_boundary: {self.identity_boundary}",
                f"  = boundary_periphery: {', '.join(self.boundary_periphery)}",
                f"  = boundary_alarm: {self.boundary_alarm}",
                f"  = honesty_boundary_inspection: {self.honesty_summary}",
                f"  = security_boundary_inspection: {self.security_summary}",
                f"  - outside: {', '.join(self.outside)}",
            )
        )
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.inspection_key
        inspection_node = HypergraphNode(
            f"N:governor:{graph_id}",
            self.inspection_id,
            (
                ("boundary_alarm", self.boundary_alarm),
                ("orthogonality_summary", self.orthogonality_summary),
                ("honesty_summary", self.honesty_summary),
                ("security_summary", self.security_summary),
            ),
        )
        honesty_node = HypergraphNode(f"N:honesty:{self.honesty_id}", "Honesty boundary inspection")
        security_node = HypergraphNode(f"N:security:{self.security_id}", "Security boundary inspection")
        subject_node = HypergraphNode(f"N:subject:{_safe_key(self.attention_subject)}", self.attention_subject)
        boundary_node = HypergraphNode(f"N:boundary:{self.boundary_key}", self.identity_boundary)
        periphery_node = HypergraphNode(f"N:periphery:{self.periphery_key}", ", ".join(self.boundary_periphery))
        protected_node = HypergraphNode(f"N:identity:{_safe_key(self.protected_identity)}", self.protected_identity)
        outside_node = HypergraphNode("N:outside:boundary_faculty_inspection_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [
            inspection_node,
            honesty_node,
            security_node,
            subject_node,
            boundary_node,
            periphery_node,
            protected_node,
            outside_node,
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:inspects:{graph_id}",
                "inspects",
                (
                    ("governor", inspection_node.key),
                    ("subject", subject_node.key),
                    ("boundary", boundary_node.key),
                    ("periphery", periphery_node.key),
                ),
                (("boundary_alarm", self.boundary_alarm),),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("governor", inspection_node.key), ("outside", outside_node.key)),
            ),
        ]
        for term in self.terms:
            term_node = HypergraphNode(
                f"N:term:{term.term_key}",
                term.term,
                (
                    ("boundary_role", term.boundary_role),
                    ("subject_vector", term.subject_vector),
                    ("boundary_vector", term.boundary_vector),
                    ("orthogonality_result", term.orthogonality_result),
                    ("honesty_load", term.honesty_load),
                    ("security_load", term.security_load),
                ),
            )
            representation_node = HypergraphNode(
                f"N:claim:{term.term_key}_representation",
                term.representation_claim or f"{term.term} representation",
                (
                    ("support_surface", term.support_surface or "not_supplied"),
                    ("honesty_disposition", term.resolved_honesty_disposition),
                ),
            )
            protection_node = HypergraphNode(
                f"N:policy:{term.term_key}_protection",
                term.protected_identity or self.protected_identity,
                (
                    ("weak_boundary_fault", term.weak_boundary_fault or "none"),
                    ("security_alert", term.resolved_security_alert),
                ),
            )
            nodes.extend((term_node, representation_node, protection_node))
            edges.extend(
                (
                    HypergraphEdge(
                        f"E:represents:{term.term_key}",
                        "represents",
                        (("honesty", honesty_node.key), ("subject", subject_node.key), ("term", term_node.key), ("claim", representation_node.key)),
                        (("honesty_disposition", term.resolved_honesty_disposition),),
                    ),
                    HypergraphEdge(
                        f"E:protects:{term.term_key}",
                        "protects",
                        (
                            ("security", security_node.key),
                            ("protected", protected_node.key),
                            ("term", term_node.key),
                            ("policy", protection_node.key),
                        ),
                        (("security_alert", term.resolved_security_alert),),
                    ),
                )
            )
            if term.honesty_alarm:
                signal_label = term.misdirection_vector or "non-orthogonal boundary fault"
                signal_node = HypergraphNode(
                    f"N:signal:{term.term_key}_misdirection",
                    signal_label,
                    (("orthogonality_result", term.orthogonality_result),),
                )
                nodes.append(signal_node)
                edges.append(
                    HypergraphEdge(
                        f"E:misdirects:{term.term_key}",
                        "misdirects",
                        (("term", term_node.key), ("signal", signal_node.key), ("outside", outside_node.key)),
                        (("honesty_load", term.honesty_load),),
                    )
                )
            if term.security_alarm:
                signal_label = term.weak_boundary_fault or "weak boundary fault"
                signal_node = HypergraphNode(
                    f"N:signal:{term.term_key}_weak_boundary",
                    signal_label,
                    (("security_alert", term.resolved_security_alert),),
                )
                nodes.append(signal_node)
                edges.append(
                    HypergraphEdge(
                        f"E:weakens:{term.term_key}",
                        "weakens",
                        (("term", term_node.key), ("signal", signal_node.key), ("outside", outside_node.key)),
                        (("security_load", term.security_load),),
                    )
                )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.inspection_id} Boundary Faculty Inspection",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG boundary-faculty-inspection"),
                ("attention_subject", self.attention_subject),
                ("identity_boundary", self.identity_boundary),
                ("boundary_alarm", self.boundary_alarm),
                ("orthogonality_summary", self.orthogonality_summary),
            ),
            outside=self.outside,
        )


def build_boundary_faculty_inspection_record(
    *,
    inspection_id: str,
    attention_subject: str,
    identity_boundary: str,
    boundary_periphery: Iterable[str],
    protected_identity: str,
    terms: Iterable[BoundaryTermInspection],
    purpose: str = "",
    outside: Iterable[str] = DEFAULT_BOUNDARY_INSPECTION_OUTSIDE,
) -> BoundaryFacultyInspectionRecord:
    return BoundaryFacultyInspectionRecord(
        inspection_id=inspection_id,
        attention_subject=attention_subject,
        identity_boundary=identity_boundary,
        boundary_periphery=tuple(_parse_list_values(boundary_periphery)) or ("boundary_periphery",),
        protected_identity=protected_identity,
        terms=tuple(terms),
        purpose=purpose,
        outside=tuple(_parse_list_values(outside)) or DEFAULT_BOUNDARY_INSPECTION_OUTSIDE,
    )


def parse_boundary_term(value: str) -> BoundaryTermInspection:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 11:
        raise ValueError(
            "boundary term must be term_id|term|boundary_role|subject_vector|boundary_vector|orthogonality_result|honesty_load|security_load|representation_claim|support_surface|protected_identity[|misdirection_vector][|weak_boundary_fault][|honesty_disposition][|security_alert]"
        )
    return BoundaryTermInspection(
        term_id=parts[0],
        term=parts[1],
        boundary_role=parts[2],
        subject_vector=parts[3],
        boundary_vector=parts[4],
        orthogonality_result=parts[5],
        honesty_load=parts[6],
        security_load=parts[7],
        representation_claim=parts[8],
        support_surface=parts[9],
        protected_identity=parts[10],
        misdirection_vector=parts[11] if len(parts) > 11 else "",
        weak_boundary_fault=parts[12] if len(parts) > 12 else "",
        honesty_disposition=parts[13] if len(parts) > 13 else "",
        security_alert=parts[14] if len(parts) > 14 else "",
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
