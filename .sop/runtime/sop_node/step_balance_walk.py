from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


BALANCE_ORDER = {
    "stable": 0,
    "watch": 1,
    "reduced": 2,
    "wobbling": 3,
    "interfered": 4,
    "overloaded": 5,
    "outside": 6,
}


@dataclass(frozen=True)
class StepBalanceObservation:
    step_id: str
    action: str
    balance_score: str
    next_step: str
    signals: tuple[str, ...] = field(default_factory=tuple)
    correction_move: str = "continue"
    settled_state: str = "stable"
    evidence_pointers: tuple[str, ...] = field(default_factory=tuple)
    periphery_terms: tuple[str, ...] = field(default_factory=tuple)

    @property
    def step_key(self) -> str:
        return _safe_key(self.step_id)

    @property
    def normalized_balance(self) -> str:
        score = _normalize(self.balance_score)
        return score if score in BALANCE_ORDER else "watch"

    @property
    def momentum_effect(self) -> str:
        if self.normalized_balance in {"overloaded", "outside"}:
            return "bound_before_motion"
        if self.normalized_balance in {"wobbling", "interfered"}:
            return "correct_before_motion"
        if self.normalized_balance in {"watch", "reduced"}:
            return "continue_with_watch"
        return "continue"


@dataclass(frozen=True)
class StepBalanceWalk:
    walk_id: str
    focus_subject: str
    job_need: str
    impulse: str
    observations: tuple[StepBalanceObservation, ...]
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.walk_id and self.focus_subject and self.job_need and self.observations)

    @property
    def overall_balance(self) -> str:
        if not self.observations:
            return "outside"
        return max((observation.normalized_balance for observation in self.observations), key=BALANCE_ORDER.get)

    @property
    def momentum_state(self) -> str:
        if self.overall_balance in {"overloaded", "outside"}:
            return "bounded"
        if self.overall_balance in {"wobbling", "interfered"}:
            return "corrective"
        if self.overall_balance in {"watch", "reduced"}:
            return "flowing_with_watch"
        return "flowing"

    def render(self) -> str:
        lines = [
            "Subject: Step Balance Walk",
            "",
            f"& [StepBalanceWalk:{_safe_key(self.walk_id)}] is a momentum-in-balance step record",
            f"  + [walk_id] is {self.walk_id}",
            f"  + [focus_subject] is {self.focus_subject}",
            f"  + [job_need] is {self.job_need}",
            f"  + [impulse] is {self.impulse or 'not_supplied'}",
            f"  + [overall_balance] is {self.overall_balance}",
            f"  + [momentum_state] is {self.momentum_state}",
            "",
            "& [StepSettlementSet] is each step settled before moving",
        ]
        for index, observation in enumerate(self.observations, start=1):
            lines.extend(
                (
                    f"  + [step_{index:03d}] is {observation.action}",
                    f"    = step_id: {observation.step_id}",
                    f"    = balance_score: {observation.normalized_balance}",
                    f"    = settled_state: {observation.settled_state}",
                    f"    = correction_move: {observation.correction_move}",
                    f"    = next_step: {observation.next_step}",
                    f"    = momentum_effect: {observation.momentum_effect}",
                    f"    = signals: {', '.join(observation.signals) if observation.signals else 'none'}",
                    f"    = evidence_pointers: {', '.join(observation.evidence_pointers) if observation.evidence_pointers else 'none'}",
                    f"    = periphery_terms: {', '.join(observation.periphery_terms) if observation.periphery_terms else 'none'}",
                )
            )
        lines.extend(
            (
                "",
                "(step_balance_walk) :active_step: /step_end_balance/ |outside|",
                f"  = focus_subject: {self.focus_subject}",
                f"  = job_need: {self.job_need}",
                f"  = impulse: {self.impulse or 'not_supplied'}",
                f"  = overall_balance: {self.overall_balance}",
                "  - outside: hidden cognition, unobserved future steps, and proof not visible in step evidence",
            )
        )
        for item in self.residual_outside:
            lines.append(f"  - outside: {item}")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = _safe_key(self.walk_id)
        walk_node = HypergraphNode(
            f"N:walk:{graph_id}",
            self.walk_id,
            (("overall_balance", self.overall_balance), ("momentum_state", self.momentum_state)),
        )
        focus_node = HypergraphNode(f"N:focus:{_safe_key(self.focus_subject)}", self.focus_subject)
        impulse_node = HypergraphNode(
            f"N:signal:{graph_id}_impulse",
            self.impulse or "impulse not supplied",
            (("signal_role", "impulse"),),
        )
        outside_node = HypergraphNode("N:outside:step_balance_boundary", "hidden cognition and unobserved future steps")
        nodes: list[HypergraphNode] = [walk_node, focus_node, impulse_node, outside_node]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:walks:{graph_id}",
                "walks",
                (("walk", walk_node.key), ("focus", focus_node.key), ("impulse", impulse_node.key)),
                (("job_need", self.job_need),),
            )
        ]
        for index, observation in enumerate(self.observations, start=1):
            step_key = observation.step_key or f"step_{index:03d}"
            step_node = HypergraphNode(
                f"N:step:{step_key}",
                observation.action,
                (("step_id", observation.step_id), ("momentum_effect", observation.momentum_effect)),
            )
            balance_node = HypergraphNode(
                f"N:balance:{step_key}",
                f"{observation.step_id} balance",
                (
                    ("balance_score", observation.normalized_balance),
                    ("settled_state", observation.settled_state),
                    ("correction_move", observation.correction_move),
                ),
            )
            next_node = HypergraphNode(f"N:next:{_safe_key(observation.next_step)}", observation.next_step)
            nodes.extend((step_node, balance_node, next_node))
            edges.extend(
                (
                    HypergraphEdge(
                        f"E:settles:{step_key}",
                        "settles",
                        (("walk", walk_node.key), ("step", step_node.key), ("balance", balance_node.key)),
                        (("balance_score", observation.normalized_balance),),
                    ),
                    HypergraphEdge(
                        f"E:advances:{step_key}",
                        "advances",
                        (("step", step_node.key), ("next", next_node.key), ("walk", walk_node.key)),
                        (("momentum_effect", observation.momentum_effect),),
                    ),
                )
            )
            for signal in observation.signals:
                signal_node = HypergraphNode(f"N:signal:{_safe_key(signal)}", signal)
                nodes.append(signal_node)
                edges.append(
                    HypergraphEdge(
                        f"E:alerts:{step_key}_{_safe_key(signal)}",
                        "alerts",
                        (("balance", balance_node.key), ("signal", signal_node.key), ("outside", outside_node.key)),
                    )
                )
            if observation.momentum_effect in {"correct_before_motion", "bound_before_motion"}:
                edges.append(
                    HypergraphEdge(
                        f"E:bounds:{step_key}",
                        "bounds",
                        (("step", step_node.key), ("balance", balance_node.key), ("outside", outside_node.key)),
                        (("reason", observation.momentum_effect),),
                    )
                )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.walk_id} Step Balance Walk",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG step-balance-walk"),
                ("focus_subject", self.focus_subject),
                ("job_need", self.job_need),
                ("momentum_state", self.momentum_state),
            ),
            outside=self.residual_outside or ("step balance records visible gait, not hidden model-state balance",),
        )


def build_step_balance_walk(
    *,
    walk_id: str,
    focus_subject: str,
    job_need: str,
    impulse: str = "",
    observations: Iterable[StepBalanceObservation],
) -> StepBalanceWalk:
    normalized_observations = tuple(observations)
    return StepBalanceWalk(
        walk_id=walk_id,
        focus_subject=focus_subject,
        job_need=job_need,
        impulse=impulse,
        observations=normalized_observations,
        residual_outside=("future steps remain candidates until selected after balance settlement",),
    )


def parse_step_balance_observation(value: str) -> StepBalanceObservation:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 4:
        raise ValueError(
            "step balance observation must be step_id|action|balance_score|next_step[|signals][|correction][|settled][|evidence][|periphery]"
        )
    signals = _parse_list(parts[4]) if len(parts) > 4 else ()
    correction = parts[5] if len(parts) > 5 and parts[5] else "continue"
    settled = parts[6] if len(parts) > 6 and parts[6] else parts[2]
    evidence = _parse_list(parts[7]) if len(parts) > 7 else ()
    periphery = _parse_list(parts[8]) if len(parts) > 8 else ()
    return StepBalanceObservation(
        step_id=parts[0],
        action=parts[1],
        balance_score=parts[2],
        next_step=parts[3],
        signals=signals,
        correction_move=correction,
        settled_state=settled,
        evidence_pointers=evidence,
        periphery_terms=periphery,
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
