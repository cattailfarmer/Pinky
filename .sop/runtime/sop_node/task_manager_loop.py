from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


VALID_CLOCK_STATES = {"running", "waiting", "blocked", "paused", "stopped"}
VALID_DRIVE_STATES = {"continue", "retry", "validate", "integrate", "defer", "stop"}
VALID_BALANCE_STATES = {"stable", "watch", "wobbling", "blocked"}
VALID_PROOF_STATES = {"none", "captured", "validated", "committed", "pushed", "blocked"}


@dataclass(frozen=True)
class OperatingLoopTick:
    tick_id: str
    focus_subject: str
    completed_step: str
    proof_state: str
    balance_state: str
    drive_state: str
    clock_state: str
    next_step: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    outside: tuple[str, ...] = field(default_factory=tuple)
    created_utc: str = ""

    def __post_init__(self) -> None:
        if self.clock_state not in VALID_CLOCK_STATES:
            raise ValueError(f"unknown clock state: {self.clock_state}")
        if self.drive_state not in VALID_DRIVE_STATES:
            raise ValueError(f"unknown drive state: {self.drive_state}")
        if self.balance_state not in VALID_BALANCE_STATES:
            raise ValueError(f"unknown balance state: {self.balance_state}")
        if self.proof_state not in VALID_PROOF_STATES:
            raise ValueError(f"unknown proof state: {self.proof_state}")

    @property
    def safe_id(self) -> str:
        return _safe_key(self.tick_id)

    @property
    def ready(self) -> bool:
        if self.clock_state == "running":
            return bool(self.next_step)
        return bool(self.tick_id and self.focus_subject and self.completed_step)

    def render(self) -> str:
        lines = [
            "Subject: Semantic Cognition Operating Loop Tick",
            "",
            "Description: Visible task-manager heartbeat after a completed, blocked, or validated step.",
            "",
            f"& [OperatingLoopTick:{self.safe_id}] is a semantic cognition operating loop tick",
            f"  + [tick_id] is {self.tick_id}",
            f"  + [focus_subject] is {self.focus_subject}",
            f"  + [completed_step] is {self.completed_step}",
            f"  + [proof_state] is {self.proof_state}",
            f"  + [balance_state] is {self.balance_state}",
            f"  + [drive_state] is {self.drive_state}",
            f"  + [clock_state] is {self.clock_state}",
            f"  + [next_step] is {self.next_step or 'none'}",
            f"  + [created_utc] is {self.created_utc or _utc_now()}",
            f"  + [evidence_refs] is {_list_or_none(self.evidence_refs)}",
            f"  + [outside] is {_list_or_none(self.outside)}",
            "",
            "  = must: treat this tick as a continuation point unless clock_state is blocked, paused, or stopped",
            "  = must: preserve outside before scheduling next_step",
            "  - never: treat commit, proof, or report as evidence that the clock stopped",
            "",
            "(semantic_cognition_operating_loop) :clock_tick: /proof_state and balance_state/ |outside|",
            f"  + [clock_tick] is {self.tick_id}",
            f"  + [proof_state] is {self.proof_state}",
            f"  + [balance_state] is {self.balance_state}",
            f"  + [next_step] is {self.next_step or 'none'}",
            f"  |outside| {_list_or_none(self.outside)}",
        ]
        return "\n".join(lines)


def build_operating_loop_tick(
    *,
    focus_subject: str,
    completed_step: str,
    proof_state: str,
    next_step: str = "",
    evidence_refs: tuple[str, ...] = (),
    outside: tuple[str, ...] = (),
    tick_id: str = "",
    balance_state: str = "",
    drive_state: str = "",
    clock_state: str = "",
) -> OperatingLoopTick:
    resolved_tick_id = tick_id or "tick_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    resolved_clock = clock_state or _infer_clock_state(next_step=next_step, proof_state=proof_state, outside=outside)
    resolved_drive = drive_state or _infer_drive_state(clock_state=resolved_clock, proof_state=proof_state, next_step=next_step)
    resolved_balance = balance_state or _infer_balance_state(clock_state=resolved_clock, proof_state=proof_state, outside=outside)
    return OperatingLoopTick(
        tick_id=resolved_tick_id,
        focus_subject=focus_subject,
        completed_step=completed_step,
        proof_state=proof_state,
        balance_state=resolved_balance,
        drive_state=resolved_drive,
        clock_state=resolved_clock,
        next_step=next_step,
        evidence_refs=evidence_refs,
        outside=outside,
        created_utc=_utc_now(),
    )


def write_operating_loop_tick(tick: OperatingLoopTick, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tick.render() + "\n", encoding="ascii")
    return path


def _infer_clock_state(*, next_step: str, proof_state: str, outside: tuple[str, ...]) -> str:
    lower_outside = " ".join(outside).lower()
    if any(term in lower_outside for term in ("explicit user stop", "user stop", "stopped")):
        return "stopped"
    if proof_state == "blocked" or any(term in lower_outside for term in ("credential", "destructive", "missing authority")):
        return "blocked"
    if next_step:
        return "running"
    return "waiting"


def _infer_drive_state(*, clock_state: str, proof_state: str, next_step: str) -> str:
    if clock_state in {"stopped", "paused"}:
        return "stop"
    if clock_state == "blocked":
        return "defer"
    if proof_state in {"captured", "validated"} and next_step:
        return "continue"
    if proof_state in {"committed", "pushed"} and next_step:
        return "continue"
    if proof_state == "none":
        return "validate"
    return "defer"


def _infer_balance_state(*, clock_state: str, proof_state: str, outside: tuple[str, ...]) -> str:
    lower_outside = " ".join(outside).lower()
    if clock_state == "blocked" or proof_state == "blocked":
        return "blocked"
    if any(term in lower_outside for term in ("leak", "failure", "watch", "risk")):
        return "watch"
    if clock_state == "running" and proof_state in {"validated", "committed", "pushed"}:
        return "stable"
    return "watch"


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _list_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
