from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


@dataclass(frozen=True)
class SupportProbe:
    support_id: str
    support_name: str
    terms: tuple[str, ...] = field(default_factory=tuple)
    carried_from: str = ""
    evidence_pointers: tuple[str, ...] = field(default_factory=tuple)
    contradicts: bool = False


@dataclass(frozen=True)
class SupportObservation:
    probe: SupportProbe
    subject_hits: tuple[str, ...] = field(default_factory=tuple)
    periphery_hits: tuple[str, ...] = field(default_factory=tuple)

    @property
    def origin(self) -> str:
        return "carried" if self.probe.carried_from else "observed"

    @property
    def fit_status(self) -> str:
        if self.probe.contradicts:
            return "contradicting"
        if self.subject_hits:
            return "native"
        if self.periphery_hits:
            return "weak"
        if self.probe.carried_from:
            return "carried"
        return "absent"

    @property
    def balance_effect(self) -> str:
        return {
            "native": "stabilizes",
            "weak": "watch_periphery",
            "carried": "names_import",
            "absent": "release_or_justify",
            "contradicting": "distortion_risk",
        }[self.fit_status]

    @property
    def matched_terms(self) -> tuple[tuple[str, str], ...]:
        subject_matches = tuple(("subject", term) for term in self.subject_hits)
        periphery_matches = tuple(("periphery", term) for term in self.periphery_hits if term not in self.subject_hits)
        return subject_matches + periphery_matches


@dataclass(frozen=True)
class SupportBalance:
    balance_id: str
    active_subject: str
    subject_terms: tuple[str, ...]
    periphery_terms: tuple[str, ...]
    observations: tuple[SupportObservation, ...]
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.balance_id and self.active_subject and self.observations)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_key = _safe_key(self.balance_id)
        balance_node = HypergraphNode(
            f"N:balance:{graph_key}",
            self.balance_id,
            (
                ("active_subject", self.active_subject),
                ("support_count", str(len(self.observations))),
            ),
        )
        subject_node = HypergraphNode(
            f"N:subject:{_safe_key(self.active_subject)}",
            self.active_subject,
            (
                ("subject_terms", ",".join(self.subject_terms)),
                ("periphery_terms", ",".join(self.periphery_terms)),
            ),
        )
        outside_node = HypergraphNode("N:outside:forced_support", "support forced beyond visible fit")
        nodes: list[HypergraphNode] = [balance_node, subject_node, outside_node]
        edges: list[HypergraphEdge] = []

        for observation in self.observations:
            probe = observation.probe
            support_key = f"N:support:{_safe_key(probe.support_id)}"
            nodes.append(
                HypergraphNode(
                    support_key,
                    probe.support_name,
                    (
                        ("origin", observation.origin),
                        ("fit_status", observation.fit_status),
                        ("balance_effect", observation.balance_effect),
                        ("carried_from", probe.carried_from or "none"),
                        ("evidence_pointers", ",".join(probe.evidence_pointers) or "none"),
                        ("native_hits", str(len(observation.subject_hits))),
                        ("periphery_hits", str(len(observation.periphery_hits))),
                    ),
                )
            )
            edges.append(
                HypergraphEdge(
                    f"E:supports:{_safe_key(probe.support_id)}",
                    "supports",
                    (("balance", balance_node.key), ("support", support_key), ("subject", subject_node.key)),
                    (("fit_status", observation.fit_status), ("balance_effect", observation.balance_effect)),
                )
            )
            if probe.carried_from:
                source_key = f"N:source:{_safe_key(probe.carried_from)}"
                nodes.append(HypergraphNode(source_key, probe.carried_from))
                edges.append(
                    HypergraphEdge(
                        f"E:imports:{_safe_key(probe.support_id)}",
                        "imports",
                        (("support", support_key), ("source", source_key), ("subject", subject_node.key)),
                        (("origin", observation.origin),),
                    )
                )
            for scope, term in observation.matched_terms:
                term_key = f"N:term:{_safe_key(term)}"
                nodes.append(HypergraphNode(term_key, term))
                edges.append(
                    HypergraphEdge(
                        f"E:fits:{_safe_key(probe.support_id)}_{_safe_key(scope)}_{_safe_key(term)}",
                        "fits",
                        (("support", support_key), ("term", term_key), ("subject", subject_node.key)),
                        (("scope", scope),),
                    )
                )
            if observation.fit_status == "native":
                edges.append(
                    HypergraphEdge(
                        f"E:stabilizes:{_safe_key(probe.support_id)}",
                        "stabilizes",
                        (("support", support_key), ("subject", subject_node.key)),
                        (("weight", str(len(observation.subject_hits) + len(observation.periphery_hits))),),
                    )
                )
            if observation.fit_status in {"absent", "contradicting"}:
                edges.append(
                    HypergraphEdge(
                        f"E:distorts:{_safe_key(probe.support_id)}",
                        "distorts",
                        (("support", support_key), ("subject", subject_node.key), ("outside", outside_node.key)),
                        (("risk", observation.balance_effect),),
                    )
                )
            if observation.fit_status in {"carried", "absent", "contradicting"}:
                edges.append(
                    HypergraphEdge(
                        f"E:bounds:{_safe_key(probe.support_id)}",
                        "bounds",
                        (("support", support_key), ("outside", outside_node.key)),
                        (("reason", observation.fit_status),),
                    )
                )

        return HypergraphRecord(
            graph_id=graph_key,
            label=f"{self.balance_id} Support Balance",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(("format_profile", "SOP-HG carried-support-balance"),),
            outside=self.residual_outside or ("support fit is visible posture, not hidden cognition or final proof",),
        )


def build_support_balance(
    *,
    balance_id: str,
    active_subject: str,
    subject_terms: Iterable[str],
    periphery_terms: Iterable[str],
    probes: Iterable[SupportProbe],
) -> SupportBalance:
    normalized_subject_terms = tuple(sorted({_normalize_term(term) for term in subject_terms if _normalize_term(term)}))
    normalized_periphery_terms = tuple(sorted({_normalize_term(term) for term in periphery_terms if _normalize_term(term)}))
    subject_set = set(normalized_subject_terms)
    periphery_set = set(normalized_periphery_terms)
    observations = tuple(
        _observe_support(probe, subject_set=subject_set, periphery_set=periphery_set)
        for probe in probes
    )
    return SupportBalance(
        balance_id=balance_id,
        active_subject=active_subject,
        subject_terms=normalized_subject_terms,
        periphery_terms=normalized_periphery_terms,
        observations=observations,
        residual_outside=("balance audit records visible support fit and does not prove subject truth",),
    )


def parse_support_probe(
    *,
    support_id: str,
    support_name: str,
    terms: Iterable[str] = (),
    carried_from: str = "",
    evidence_pointers: Iterable[str] = (),
    contradicts: bool = False,
) -> SupportProbe:
    return SupportProbe(
        support_id=support_id,
        support_name=support_name,
        terms=tuple(_normalize_term(term) for term in terms if _normalize_term(term)),
        carried_from=carried_from,
        evidence_pointers=tuple(evidence_pointers),
        contradicts=contradicts,
    )


def _observe_support(
    probe: SupportProbe,
    *,
    subject_set: set[str],
    periphery_set: set[str],
) -> SupportObservation:
    terms = tuple(_normalize_term(term) for term in probe.terms if _normalize_term(term))
    subject_hits = tuple(sorted(term for term in terms if term in subject_set))
    periphery_hits = tuple(sorted(term for term in terms if term in periphery_set))
    normalized_probe = SupportProbe(
        support_id=probe.support_id,
        support_name=probe.support_name,
        terms=terms,
        carried_from=probe.carried_from,
        evidence_pointers=probe.evidence_pointers,
        contradicts=probe.contradicts,
    )
    return SupportObservation(
        probe=normalized_probe,
        subject_hits=subject_hits,
        periphery_hits=periphery_hits,
    )


def _normalize_term(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
