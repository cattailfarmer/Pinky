"""Repeatable scoring for Symbolic Ricci Flow proof-inquiry states."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


NODE_WEIGHTS: dict[str, float] = {
    "source_claim": 1.00,
    "formal_object": 1.00,
    "proof_obligation": 1.00,
    "boundary_lock": 1.00,
    "candidate_mechanism": 0.75,
    "analogy": 0.50,
    "model_variable": 0.25,
}

EDGE_PRESSURES: dict[str, float] = {
    "unsupported_analogizes": 3.00,
    "overbroad_transfers_to": 3.00,
    "contradicts_without_boundary": 2.50,
    "depends_on_open_lock": 2.00,
    "supports_with_source_trace": -1.00,
    "refines_distinction": -1.50,
    "blocks_proof_promotion": -2.00,
}


@dataclass(frozen=True)
class FlowStateCounts:
    """Counted graph features for one proof-inquiry state."""

    active_claims: int = 0
    source_linked_claims: int = 0
    claims_with_explicit_boundary: int = 0
    distinction_loss: int = 0
    authority_leak_count: int = 0
    unresolved_locks: Mapping[str, float] = field(default_factory=dict)
    edges: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class FlowScore:
    """Normalized diagnostic scores for a proof-inquiry graph."""

    irregularity_total: float
    unresolved_lock_mass: float
    boundary_clarity: float
    source_coverage: float
    distinction_loss: int
    authority_leak_count: int


@dataclass(frozen=True)
class FlowScoreDelta:
    """Signed score movement from one proof-inquiry state to another."""

    irregularity_delta: float
    unresolved_lock_mass_delta: float
    boundary_clarity_delta: float
    source_coverage_delta: float
    distinction_loss_delta: int
    authority_leak_delta: int


def score_state(state: FlowStateCounts) -> FlowScore:
    """Score one Symbolic Ricci Flow state without treating it as proof authority."""

    _validate_count("active_claims", state.active_claims)
    _validate_count("source_linked_claims", state.source_linked_claims)
    _validate_count("claims_with_explicit_boundary", state.claims_with_explicit_boundary)
    _validate_count("distinction_loss", state.distinction_loss)
    _validate_count("authority_leak_count", state.authority_leak_count)
    if state.source_linked_claims > state.active_claims:
        raise ValueError("source_linked_claims cannot exceed active_claims")
    if state.claims_with_explicit_boundary > state.active_claims:
        raise ValueError("claims_with_explicit_boundary cannot exceed active_claims")

    edge_pressure = 0.0
    for edge_name, count in state.edges.items():
        if edge_name not in EDGE_PRESSURES:
            raise ValueError(f"unknown Symbolic Ricci Flow edge: {edge_name}")
        _validate_count(f"edges[{edge_name}]", count)
        edge_pressure += EDGE_PRESSURES[edge_name] * count

    unresolved_lock_mass = 0.0
    for lock_name, weight in state.unresolved_locks.items():
        if weight < 0:
            raise ValueError(f"unresolved lock weight cannot be negative: {lock_name}")
        unresolved_lock_mass += weight

    return FlowScore(
        irregularity_total=max(0.0, edge_pressure),
        unresolved_lock_mass=unresolved_lock_mass,
        boundary_clarity=_ratio(state.claims_with_explicit_boundary, state.active_claims),
        source_coverage=_ratio(state.source_linked_claims, state.active_claims),
        distinction_loss=state.distinction_loss,
        authority_leak_count=state.authority_leak_count,
    )


def score_delta(before: FlowStateCounts, after: FlowStateCounts) -> FlowScoreDelta:
    """Compare two states so cleanup can be separated from real lock reduction."""

    before_score = score_state(before)
    after_score = score_state(after)
    return FlowScoreDelta(
        irregularity_delta=after_score.irregularity_total - before_score.irregularity_total,
        unresolved_lock_mass_delta=after_score.unresolved_lock_mass - before_score.unresolved_lock_mass,
        boundary_clarity_delta=after_score.boundary_clarity - before_score.boundary_clarity,
        source_coverage_delta=after_score.source_coverage - before_score.source_coverage,
        distinction_loss_delta=after_score.distinction_loss - before_score.distinction_loss,
        authority_leak_delta=after_score.authority_leak_count - before_score.authority_leak_count,
    )


def _validate_count(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
