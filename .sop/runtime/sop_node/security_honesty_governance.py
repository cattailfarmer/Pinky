from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


TRUTH_DISPOSITIONS = {"supported", "provisional", "speculative", "contradicted", "unsupported", "outside", "rejected"}
SECURITY_DISPOSITIONS = {
    "permit",
    "permit_with_boundary",
    "modify",
    "pause",
    "require_authorization",
    "route_to_periphery",
    "stop_action",
    "outside",
}
GUARD_DISPOSITIONS = {
    "continue",
    "narrow",
    "evidence_refresh_required",
    "route_to_periphery",
    "checksum_later",
    "stop_action",
    "outside",
}

DEFAULT_SECURITY_HONESTY_OUTSIDE = (
    "hidden cognition",
    "unsupported mechanistic control",
    "proof without evidence",
    "unsafe action",
    "concealed uncertainty",
    "runaway reflection",
)


@dataclass(frozen=True)
class CandidateClaim:
    claim_id: str
    claim: str
    support: str
    assumption: str = ""
    contradiction: str = ""
    uncertainty: str = ""
    truth_disposition: str = ""

    @property
    def claim_key(self) -> str:
        return _safe_key(self.claim_id)

    @property
    def resolved_truth_disposition(self) -> str:
        if self.truth_disposition:
            return self.truth_disposition
        if _meaningful(self.contradiction):
            return "contradicted"
        if _meaningful(self.support):
            return "supported"
        if _meaningful(self.assumption):
            return "provisional"
        if _meaningful(self.uncertainty):
            return "speculative"
        return "unsupported"

    @property
    def ready(self) -> bool:
        return bool(
            self.claim_id
            and self.claim
            and self.resolved_truth_disposition in TRUTH_DISPOSITIONS
        )

    @property
    def honesty_objection(self) -> bool:
        return self.resolved_truth_disposition in {"contradicted", "unsupported", "outside", "rejected"}

    def render(self, index: int) -> list[str]:
        return [
            f"  + [candidate_claim:{index}] is {self.claim}",
            f"    = claim_id: {self.claim_id}",
            f"    = support: {self.support or 'not_supplied'}",
            f"    = assumption: {self.assumption or 'none'}",
            f"    = contradiction: {self.contradiction or 'none'}",
            f"    = uncertainty: {self.uncertainty or 'none'}",
            f"    = truth_disposition: {self.resolved_truth_disposition}",
        ]


@dataclass(frozen=True)
class CandidateAction:
    action_id: str
    action: str
    risk: str
    admissible_path: str
    security_disposition: str = ""

    @property
    def action_key(self) -> str:
        return _safe_key(self.action_id)

    @property
    def admissible_path_key(self) -> str:
        return _safe_key(self.admissible_path or f"{self.action_id}_no_admissible_path")

    @property
    def resolved_security_disposition(self) -> str:
        if self.security_disposition:
            return self.security_disposition
        risk = _normalize(self.risk)
        if any(term in risk for term in ("destructive", "credential", "privacy", "unsafe", "remote", "worker_mutation")):
            return "require_authorization"
        if any(term in risk for term in ("runaway", "resonance", "hidden_state")):
            return "pause"
        if _meaningful(self.admissible_path):
            return "permit_with_boundary"
        return "route_to_periphery"

    @property
    def ready(self) -> bool:
        return bool(
            self.action_id
            and self.action
            and self.risk
            and self.resolved_security_disposition in SECURITY_DISPOSITIONS
        )

    @property
    def security_objection(self) -> bool:
        return self.resolved_security_disposition in {
            "pause",
            "require_authorization",
            "route_to_periphery",
            "stop_action",
            "outside",
        }

    def render(self, index: int) -> list[str]:
        return [
            f"  + [candidate_action:{index}] is {self.action}",
            f"    = action_id: {self.action_id}",
            f"    = risk: {self.risk}",
            f"    = admissible_path: {self.admissible_path or 'not_supplied'}",
            f"    = security_disposition: {self.resolved_security_disposition}",
        ]


@dataclass(frozen=True)
class FeedbackSignal:
    feedback_id: str
    feedback_source: str
    recursion_depth: int
    return_anchor: str
    evidence_refresh: str
    resonance_condition: str = "self_reflective_feedback"
    guard_disposition: str = ""
    resonance_cap: int = 2

    @property
    def signal_key(self) -> str:
        return _safe_key(self.feedback_id)

    @property
    def resolved_guard_disposition(self) -> str:
        if self.guard_disposition:
            return self.guard_disposition
        if not _meaningful(self.return_anchor):
            return "stop_action"
        if self.recursion_depth > self.resonance_cap and not _meaningful(self.evidence_refresh):
            return "evidence_refresh_required"
        if self.recursion_depth >= self.resonance_cap:
            return "narrow"
        return "continue"

    @property
    def ready(self) -> bool:
        return bool(
            self.feedback_id
            and self.feedback_source
            and self.recursion_depth >= 0
            and self.return_anchor
            and self.resolved_guard_disposition in GUARD_DISPOSITIONS
        )

    @property
    def resonance_objection(self) -> bool:
        return self.resolved_guard_disposition in {
            "evidence_refresh_required",
            "route_to_periphery",
            "stop_action",
            "outside",
        }

    def render(self, index: int) -> list[str]:
        return [
            f"  + [feedback_signal:{index}] is {self.feedback_source}",
            f"    = feedback_id: {self.feedback_id}",
            f"    = resonance_condition: {self.resonance_condition}",
            f"    = recursion_depth: {self.recursion_depth}",
            f"    = resonance_cap: {self.resonance_cap}",
            f"    = return_anchor: {self.return_anchor}",
            f"    = evidence_refresh: {self.evidence_refresh or 'not_supplied'}",
            f"    = guard_disposition: {self.resolved_guard_disposition}",
        ]


@dataclass(frozen=True)
class SecurityHonestyGovernanceRecord:
    governance_id: str
    focal_subject: str
    return_anchor: str
    claims: tuple[CandidateClaim, ...]
    actions: tuple[CandidateAction, ...]
    feedback: tuple[FeedbackSignal, ...]
    outside: tuple[str, ...] = DEFAULT_SECURITY_HONESTY_OUTSIDE

    @property
    def governance_key(self) -> str:
        return _safe_key(self.governance_id)

    @property
    def honesty_id(self) -> str:
        return f"{self.governance_key}_honesty"

    @property
    def security_id(self) -> str:
        return f"{self.governance_key}_security"

    @property
    def ready(self) -> bool:
        return bool(
            self.governance_id
            and self.focal_subject
            and self.return_anchor
            and self.claims
            and self.actions
            and self.feedback
            and all(claim.ready for claim in self.claims)
            and all(action.ready for action in self.actions)
            and all(signal.ready for signal in self.feedback)
            and self.outside
        )

    @property
    def truth_summary(self) -> str:
        return ", ".join(f"{claim.claim_id}:{claim.resolved_truth_disposition}" for claim in self.claims)

    @property
    def security_summary(self) -> str:
        return ", ".join(f"{action.action_id}:{action.resolved_security_disposition}" for action in self.actions)

    @property
    def guard_summary(self) -> str:
        return ", ".join(f"{signal.feedback_id}:{signal.resolved_guard_disposition}" for signal in self.feedback)

    @property
    def convergent_override(self) -> bool:
        return any(claim.honesty_objection for claim in self.claims) and (
            any(action.security_objection for action in self.actions) or any(signal.resonance_objection for signal in self.feedback)
        )

    def render(self) -> str:
        lines = [
            "Subject: Security Honesty Governance Runtime",
            "",
            f"& [SecurityHonestyGovernance:{self.governance_key}] is a security_honesty_governance_runtime_record",
            f"  + [governance_id] is {self.governance_id}",
            f"  + [focal_subject] is {self.focal_subject}",
            f"  + [return_anchor] is {self.return_anchor}",
            f"  + [truth_summary] is {self.truth_summary}",
            f"  + [security_summary] is {self.security_summary}",
            f"  + [guard_summary] is {self.guard_summary}",
            f"  + [convergent_override] is {str(self.convergent_override).lower()}",
            f"  + [outside] is {', '.join(self.outside)}",
            "",
            "& [HonestyGovernancePass] is the truth-status pass",
        ]
        for index, claim in enumerate(self.claims, start=1):
            lines.extend(claim.render(index))
        lines.extend(("", "& [SecurityGovernancePass] is the stability and admissibility pass"))
        for index, action in enumerate(self.actions, start=1):
            lines.extend(action.render(index))
        lines.extend(("", "& [FeedbackLoopGuard] is the resonance control pass"))
        for index, signal in enumerate(self.feedback, start=1):
            lines.extend(signal.render(index))
        lines.extend(
            (
                "",
                f"({self.governance_id}) :claim_and_assignment: /truth_security_boundary/ |outside|",
                f"  = return_anchor: {self.return_anchor}",
                f"  = truth_disposition: {self.truth_summary}",
                f"  = security_disposition: {self.security_summary}",
                f"  = guard_disposition: {self.guard_summary}",
                f"  = convergent_override: {str(self.convergent_override).lower()}",
                f"  - outside: {', '.join(self.outside)}",
            )
        )
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.governance_key
        governor_node = HypergraphNode(
            f"N:governor:{graph_id}",
            self.governance_id,
            (
                ("truth_summary", self.truth_summary),
                ("security_summary", self.security_summary),
                ("guard_summary", self.guard_summary),
                ("convergent_override", str(self.convergent_override).lower()),
            ),
        )
        honesty_node = HypergraphNode(f"N:honesty:{self.honesty_id}", "Honesty claim evidence gate")
        security_node = HypergraphNode(f"N:security:{self.security_id}", "Security feedback and action guard")
        focus_node = HypergraphNode(f"N:focus:{_safe_key(self.focal_subject)}", self.focal_subject)
        return_node = HypergraphNode(f"N:anchor:{_safe_key(self.return_anchor)}", self.return_anchor)
        outside_node = HypergraphNode("N:outside:security_honesty_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [
            governor_node,
            honesty_node,
            security_node,
            focus_node,
            return_node,
            outside_node,
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:governs:{graph_id}",
                "governs",
                (
                    ("governor", governor_node.key),
                    ("honesty", honesty_node.key),
                    ("security", security_node.key),
                    ("focus", focus_node.key),
                ),
            ),
            HypergraphEdge(
                f"E:returns:{_safe_key(self.focal_subject)}",
                "returns",
                (("governor", governor_node.key), ("focus", focus_node.key), ("anchor", return_node.key)),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("governor", governor_node.key), ("outside", outside_node.key)),
            ),
        ]
        for claim in self.claims:
            claim_node = HypergraphNode(
                f"N:claim:{claim.claim_key}",
                claim.claim,
                (
                    ("support", claim.support or "not_supplied"),
                    ("assumption", claim.assumption or "none"),
                    ("contradiction", claim.contradiction or "none"),
                    ("uncertainty", claim.uncertainty or "none"),
                    ("truth_disposition", claim.resolved_truth_disposition),
                ),
            )
            nodes.append(claim_node)
            edges.append(
                HypergraphEdge(
                    f"E:tests:{claim.claim_key}",
                    "tests",
                    (("honesty", honesty_node.key), ("claim", claim_node.key), ("outside", outside_node.key)),
                    (("truth_disposition", claim.resolved_truth_disposition),),
                )
            )
            if claim.honesty_objection:
                edges.append(
                    HypergraphEdge(
                        f"E:vetoes:{claim.claim_key}",
                        "vetoes",
                        (("honesty", honesty_node.key), ("candidate", claim_node.key), ("outside", outside_node.key)),
                        (("reason", claim.resolved_truth_disposition),),
                    )
                )
        for action in self.actions:
            action_node = HypergraphNode(
                f"N:policy:{action.action_key}",
                action.action,
                (
                    ("risk", action.risk),
                    ("admissible_path", action.admissible_path or "not_supplied"),
                    ("security_disposition", action.resolved_security_disposition),
                ),
            )
            path_node = HypergraphNode(f"N:path:{action.admissible_path_key}", action.admissible_path or "no admissible path")
            nodes.extend((action_node, path_node))
            edges.append(
                HypergraphEdge(
                    f"E:guards:{action.action_key}",
                    "guards",
                    (("security", security_node.key), ("action", action_node.key), ("outside", outside_node.key)),
                    (("security_disposition", action.resolved_security_disposition),),
                )
            )
            if action.resolved_security_disposition in {"permit", "permit_with_boundary", "modify"}:
                edges.append(
                    HypergraphEdge(
                        f"E:authorizes:{action.admissible_path_key}",
                        "authorizes",
                        (("security", security_node.key), ("action", action_node.key), ("path", path_node.key)),
                        (("security_disposition", action.resolved_security_disposition),),
                    )
                )
            if action.security_objection:
                edges.append(
                    HypergraphEdge(
                        f"E:vetoes:{action.action_key}",
                        "vetoes",
                        (("security", security_node.key), ("candidate", action_node.key), ("outside", outside_node.key)),
                        (("reason", action.resolved_security_disposition),),
                    )
                )
        for signal in self.feedback:
            signal_node = HypergraphNode(
                f"N:signal:{signal.signal_key}",
                signal.feedback_source,
                (
                    ("resonance_condition", signal.resonance_condition),
                    ("recursion_depth", str(signal.recursion_depth)),
                    ("resonance_cap", str(signal.resonance_cap)),
                    ("return_anchor", signal.return_anchor),
                    ("evidence_refresh", signal.evidence_refresh or "not_supplied"),
                    ("guard_disposition", signal.resolved_guard_disposition),
                ),
            )
            nodes.append(signal_node)
            edges.append(
                HypergraphEdge(
                    f"E:guards:{signal.signal_key}",
                    "guards",
                    (("security", security_node.key), ("feedback", signal_node.key), ("anchor", return_node.key)),
                    (("guard_disposition", signal.resolved_guard_disposition),),
                )
            )
            if signal.resonance_objection:
                edges.append(
                    HypergraphEdge(
                        f"E:vetoes:{signal.signal_key}",
                        "vetoes",
                        (("security", security_node.key), ("candidate", signal_node.key), ("outside", outside_node.key)),
                        (("reason", signal.resolved_guard_disposition),),
                    )
                )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.governance_id} Security Honesty Governance",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG security-honesty-governance"),
                ("focal_subject", self.focal_subject),
                ("truth_summary", self.truth_summary),
                ("security_summary", self.security_summary),
                ("guard_summary", self.guard_summary),
                ("convergent_override", str(self.convergent_override).lower()),
            ),
            outside=self.outside,
        )


def build_security_honesty_governance_record(
    *,
    governance_id: str,
    focal_subject: str,
    return_anchor: str,
    claims: Iterable[CandidateClaim],
    actions: Iterable[CandidateAction],
    feedback: Iterable[FeedbackSignal],
    outside: Iterable[str] = DEFAULT_SECURITY_HONESTY_OUTSIDE,
) -> SecurityHonestyGovernanceRecord:
    return SecurityHonestyGovernanceRecord(
        governance_id=governance_id,
        focal_subject=focal_subject,
        return_anchor=return_anchor,
        claims=tuple(claims),
        actions=tuple(actions),
        feedback=tuple(feedback),
        outside=tuple(_parse_list_values(outside)) or DEFAULT_SECURITY_HONESTY_OUTSIDE,
    )


def parse_candidate_claim(value: str) -> CandidateClaim:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 3:
        raise ValueError("claim must be claim_id|claim|support[|assumption][|contradiction][|uncertainty][|truth_disposition]")
    return CandidateClaim(
        claim_id=parts[0],
        claim=parts[1],
        support=parts[2],
        assumption=parts[3] if len(parts) > 3 else "",
        contradiction=parts[4] if len(parts) > 4 else "",
        uncertainty=parts[5] if len(parts) > 5 else "",
        truth_disposition=parts[6] if len(parts) > 6 else "",
    )


def parse_candidate_action(value: str) -> CandidateAction:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 4:
        raise ValueError("action must be action_id|action|risk|admissible_path[|security_disposition]")
    return CandidateAction(
        action_id=parts[0],
        action=parts[1],
        risk=parts[2],
        admissible_path=parts[3],
        security_disposition=parts[4] if len(parts) > 4 else "",
    )


def parse_feedback_signal(value: str) -> FeedbackSignal:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 5:
        raise ValueError(
            "feedback must be feedback_id|feedback_source|recursion_depth|return_anchor|evidence_refresh[|resonance_condition][|guard_disposition][|resonance_cap]"
        )
    return FeedbackSignal(
        feedback_id=parts[0],
        feedback_source=parts[1],
        recursion_depth=int(parts[2]) if parts[2] else 0,
        return_anchor=parts[3],
        evidence_refresh=parts[4],
        resonance_condition=parts[5] if len(parts) > 5 and parts[5] else "self_reflective_feedback",
        guard_disposition=parts[6] if len(parts) > 6 else "",
        resonance_cap=int(parts[7]) if len(parts) > 7 and parts[7] else 2,
    )


def _meaningful(value: str) -> bool:
    return bool(value.strip()) and _normalize(value) not in {"none", "not_supplied", "outside", "unknown"}


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
