from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


DEFAULT_TRACKING_PERIOD_SESSIONS = 1


@dataclass(frozen=True)
class TrackedSubject:
    tracker_id: str
    subject_label: str
    reason: str
    weight: int = 1
    session_id: str = "session_0"
    last_reaffirmed_session: int = 0
    declared_period_sessions: int | None = None
    native_context: tuple[str, ...] = field(default_factory=tuple)
    periphery_context: tuple[str, ...] = field(default_factory=tuple)
    relations: tuple[str, ...] = field(default_factory=tuple)
    narrative_refs: tuple[str, ...] = field(default_factory=tuple)
    scan_refs: tuple[str, ...] = field(default_factory=tuple)
    debug_refs: tuple[str, ...] = field(default_factory=tuple)
    open_questions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def active_period_sessions(self) -> int:
        return self.declared_period_sessions if self.declared_period_sessions is not None else DEFAULT_TRACKING_PERIOD_SESSIONS

    @property
    def period_kind(self) -> str:
        return "declared_period" if self.declared_period_sessions is not None else "default_session"

    @property
    def expires_after_session(self) -> int:
        return self.last_reaffirmed_session + self.active_period_sessions

    def status_at(self, current_session: int) -> str:
        if current_session > self.expires_after_session:
            return "expired"
        if current_session == self.expires_after_session and current_session > self.last_reaffirmed_session:
            return "expiring"
        return "active"

    def effective_weight_at(self, current_session: int) -> int:
        status = self.status_at(current_session)
        if status == "expired":
            return 0
        if status == "expiring":
            return max(1, self.weight // 2)
        return self.weight

    def reaffirm(self, session_index: int, *, weight: int | None = None) -> TrackedSubject:
        return TrackedSubject(
            tracker_id=self.tracker_id,
            subject_label=self.subject_label,
            reason=self.reason,
            weight=self.weight if weight is None else weight,
            session_id=self.session_id,
            last_reaffirmed_session=session_index,
            declared_period_sessions=self.declared_period_sessions,
            native_context=self.native_context,
            periphery_context=self.periphery_context,
            relations=self.relations,
            narrative_refs=self.narrative_refs,
            scan_refs=self.scan_refs,
            debug_refs=self.debug_refs,
            open_questions=self.open_questions,
        )


@dataclass(frozen=True)
class AttentionTrackingRecord:
    record_id: str
    current_session: int
    tracked_subjects: tuple[TrackedSubject, ...]
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.record_id and self.tracked_subjects)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_key = _safe_key(self.record_id)
        session_key = f"N:session:{_safe_key(str(self.current_session))}"
        record_node = HypergraphNode(
            f"N:tracker:{graph_key}",
            self.record_id,
            (
                ("current_session", str(self.current_session)),
                ("tracked_count", str(len(self.tracked_subjects))),
            ),
        )
        session_node = HypergraphNode(session_key, f"session {self.current_session}")
        outside_node = HypergraphNode("N:outside:tracking_staleness", "tracking that has expired or lacks reaffirmation")
        nodes: list[HypergraphNode] = [record_node, session_node, outside_node]
        edges: list[HypergraphEdge] = []

        for tracked in self.tracked_subjects:
            status = tracked.status_at(self.current_session)
            tracker_key = f"N:tracker:{_safe_key(tracked.tracker_id)}"
            subject_key = f"N:subject:{_safe_key(tracked.subject_label)}"
            nodes.append(
                HypergraphNode(
                    tracker_key,
                    tracked.tracker_id,
                    (
                        ("subject", tracked.subject_label),
                        ("reason", tracked.reason),
                        ("status", status),
                        ("weight", str(tracked.effective_weight_at(self.current_session))),
                        ("period_kind", tracked.period_kind),
                        ("active_period_sessions", str(tracked.active_period_sessions)),
                        ("last_reaffirmed_session", str(tracked.last_reaffirmed_session)),
                        ("expires_after_session", str(tracked.expires_after_session)),
                    ),
                )
            )
            nodes.append(
                HypergraphNode(
                    subject_key,
                    tracked.subject_label,
                    (("native_context", ",".join(tracked.native_context) or "none"),),
                )
            )
            edges.append(
                HypergraphEdge(
                    f"E:tracks:{_safe_key(tracked.tracker_id)}",
                    "tracks",
                    (("record", record_node.key), ("tracker", tracker_key), ("subject", subject_key), ("session", session_key)),
                    (("status", status), ("weight", str(tracked.effective_weight_at(self.current_session)))),
                )
            )
            if tracked.last_reaffirmed_session == self.current_session:
                edges.append(
                    HypergraphEdge(
                        f"E:reaffirms:{_safe_key(tracked.tracker_id)}",
                        "reaffirms",
                        (("tracker", tracker_key), ("session", session_key)),
                        (("expires_after_session", str(tracked.expires_after_session)),),
                    )
                )
            if status == "expired":
                edges.append(
                    HypergraphEdge(
                        f"E:expires:{_safe_key(tracked.tracker_id)}",
                        "expires",
                        (("tracker", tracker_key), ("outside", outside_node.key)),
                        (("expired_after_session", str(tracked.expires_after_session)),),
                    )
                )
            for relation in tracked.relations:
                relation_key = f"N:term:{_safe_key(relation)}"
                nodes.append(HypergraphNode(relation_key, relation))
                edges.append(
                    HypergraphEdge(
                        f"E:associates:{_safe_key(tracked.tracker_id)}_{_safe_key(relation)}",
                        "associates",
                        (("tracker", tracker_key), ("subject", subject_key), ("relation", relation_key)),
                    )
                )
            for periphery in tracked.periphery_context:
                periphery_key = f"N:periphery:{_safe_key(periphery)}"
                nodes.append(HypergraphNode(periphery_key, periphery))
                edges.append(
                    HypergraphEdge(
                        f"E:notices:{_safe_key(tracked.tracker_id)}_{_safe_key(periphery)}",
                        "notices",
                        (("tracker", tracker_key), ("periphery", periphery_key), ("subject", subject_key)),
                    )
                )
            for reference in (*tracked.narrative_refs, *tracked.scan_refs, *tracked.debug_refs):
                reference_key = f"N:source:{_safe_key(reference)}"
                nodes.append(HypergraphNode(reference_key, reference))
                edges.append(
                    HypergraphEdge(
                        f"E:references:{_safe_key(tracked.tracker_id)}_{_safe_key(reference)}",
                        "references",
                        (("tracker", tracker_key), ("source", reference_key)),
                    )
                )
            if status in {"expiring", "expired"} or tracked.open_questions:
                edges.append(
                    HypergraphEdge(
                        f"E:bounds:{_safe_key(tracked.tracker_id)}",
                        "bounds",
                        (("tracker", tracker_key), ("outside", outside_node.key)),
                        (
                            ("status", status),
                            ("open_questions", ",".join(tracked.open_questions) or "none"),
                        ),
                    )
                )

        return HypergraphRecord(
            graph_id=graph_key,
            label=f"{self.record_id} Attention Tracking",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(("format_profile", "SOP-HG attention-tracking"),),
            outside=self.residual_outside or ("tracking directs future attention but expires unless reaffirmed",),
        )


def build_attention_tracking_record(
    *,
    record_id: str,
    current_session: int,
    tracked_subjects: Iterable[TrackedSubject],
) -> AttentionTrackingRecord:
    return AttentionTrackingRecord(
        record_id=record_id,
        current_session=current_session,
        tracked_subjects=tuple(tracked_subjects),
        residual_outside=("tracked subjects are attention impulses, not proof of importance",),
    )


def parse_tracked_subject(
    *,
    tracker_id: str,
    subject_label: str,
    reason: str,
    weight: int = 1,
    session_id: str = "session_0",
    last_reaffirmed_session: int = 0,
    declared_period_sessions: int | None = None,
    native_context: Iterable[str] = (),
    periphery_context: Iterable[str] = (),
    relations: Iterable[str] = (),
    narrative_refs: Iterable[str] = (),
    scan_refs: Iterable[str] = (),
    debug_refs: Iterable[str] = (),
    open_questions: Iterable[str] = (),
) -> TrackedSubject:
    return TrackedSubject(
        tracker_id=tracker_id,
        subject_label=subject_label,
        reason=reason,
        weight=weight,
        session_id=session_id,
        last_reaffirmed_session=last_reaffirmed_session,
        declared_period_sessions=declared_period_sessions,
        native_context=tuple(native_context),
        periphery_context=tuple(periphery_context),
        relations=tuple(relations),
        narrative_refs=tuple(narrative_refs),
        scan_refs=tuple(scan_refs),
        debug_refs=tuple(debug_refs),
        open_questions=tuple(open_questions),
    )


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
