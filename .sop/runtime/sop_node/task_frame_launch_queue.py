from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


VALID_QUEUE_STATUSES = {"empty", "queued", "ready_for_inspection", "blocked", "running", "completed", "closed"}
VALID_CANDIDATE_STATUSES = {
    "proposed",
    "queue_ready",
    "blocked",
    "deferred",
    "launched",
    "returned",
    "validated",
    "rejected",
    "integrated",
}
VALID_LANE_FITS = {"lm_studio_cli", "codex_cli", "openai_codex", "manual", "deferred", "outside"}
DEFAULT_LMSTUDIO_GATES = (
    "sop_language_primer_gate",
    "scratch_isolation_gate",
    "capture_gate",
    "validator_gate",
    "codex_review_gate",
    "action_gate",
)
DEFAULT_LMSTUDIO_OUTSIDE = (
    "automatic launch",
    "worker file mutation",
    "hidden model state",
    "project-root authority",
    "unvalidated output",
)


@dataclass(frozen=True)
class TaskFrameLaunchCandidate:
    candidate_id: str
    task_frame_id: str
    task_subject: str
    objective: str
    lane_fit: str
    launch_mode: str
    prompt_packet: str
    launch_command: str
    capture_target: str
    required_gates: tuple[str, ...] = field(default_factory=tuple)
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    allowed_surface: tuple[str, ...] = field(default_factory=tuple)
    blocked_surface: tuple[str, ...] = field(default_factory=tuple)
    block_reasons: tuple[str, ...] = field(default_factory=tuple)
    outside: tuple[str, ...] = field(default_factory=tuple)
    status: str = "proposed"
    created_utc: str = ""

    def __post_init__(self) -> None:
        if self.lane_fit not in VALID_LANE_FITS:
            raise ValueError(f"unknown lane fit: {self.lane_fit}")
        if self.status not in VALID_CANDIDATE_STATUSES:
            raise ValueError(f"unknown candidate status: {self.status}")

    @property
    def safe_id(self) -> str:
        return _safe_key(self.candidate_id)

    @property
    def ready_for_inspection(self) -> bool:
        return self.status == "queue_ready" and not self.block_reasons

    def render(self) -> str:
        lines = [
            f"& [TaskFrameLaunchCandidate:{self.safe_id}] is a queued task-frame launch candidate",
            f"  + [candidate_id] is {self.candidate_id}",
            f"  + [task_frame_id] is {self.task_frame_id}",
            f"  + [task_subject] is {self.task_subject}",
            f"  + [objective] is {self.objective}",
            f"  + [lane_fit] is {self.lane_fit}",
            f"  + [launch_mode] is {self.launch_mode}",
            f"  + [status] is {self.status}",
            f"  + [ready_for_inspection] is {str(self.ready_for_inspection).lower()}",
            f"  + [prompt_packet] is {self.prompt_packet}",
            f"  + [launch_command] is {self.launch_command}",
            f"  + [capture_target] is {self.capture_target}",
            f"  + [required_gates] is {_list_or_none(self.required_gates)}",
            f"  + [source_refs] is {_list_or_none(self.source_refs)}",
            f"  + [allowed_surface] is {_list_or_none(self.allowed_surface)}",
            f"  + [blocked_surface] is {_list_or_none(self.blocked_surface)}",
            f"  + [block_reasons] is {_list_or_none(self.block_reasons)}",
            f"  + [outside] is {_list_or_none(self.outside)}",
            f"  + [created_utc] is {self.created_utc or _utc_now()}",
            "  = must: inspect launch_command before execution",
            "  = must: capture output before validation or integration",
            "  - never: infer launched, completed, or integrated from queue status",
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class TaskFrameLaunchQueue:
    queue_id: str
    candidates: tuple[TaskFrameLaunchCandidate, ...]
    launch_policy: str = "inspect_before_launch; no_silent_launch"
    outside: tuple[str, ...] = field(default_factory=tuple)
    created_utc: str = ""

    @property
    def safe_id(self) -> str:
        return _safe_key(self.queue_id)

    @property
    def ready_candidates(self) -> tuple[TaskFrameLaunchCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.ready_for_inspection)

    @property
    def blocked_candidates(self) -> tuple[TaskFrameLaunchCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.status == "blocked")

    @property
    def queue_status(self) -> str:
        if not self.candidates:
            return "empty"
        if self.ready_candidates:
            return "ready_for_inspection"
        if len(self.blocked_candidates) == len(self.candidates):
            return "blocked"
        return "queued"

    @property
    def ready(self) -> bool:
        return bool(self.queue_id and self.candidates)

    def render(self) -> str:
        lines = [
            "Subject: Task Frame Launch Queue Event",
            "",
            "Description: Inspectable launch queue for task-frame worker candidates.",
            "",
            f"& [TaskFrameLaunchQueue:{self.safe_id}] is a task-frame launch queue",
            f"  + [queue_id] is {self.queue_id}",
            f"  + [queue_status] is {self.queue_status}",
            f"  + [candidate_count] is {len(self.candidates)}",
            f"  + [ready_count] is {len(self.ready_candidates)}",
            f"  + [blocked_count] is {len(self.blocked_candidates)}",
            f"  + [launch_policy] is {self.launch_policy}",
            f"  + [created_utc] is {self.created_utc or _utc_now()}",
            f"  + [outside] is {_list_or_none(self.outside)}",
            "  = must: keep Codex as launch, validation, and integration authority",
            "  = must: keep ready candidates inspectable before launch",
            "  - never: launch silently from queue readiness",
            "",
        ]
        for candidate in self.candidates:
            lines.append(candidate.render())
            lines.append("")
        lines.extend(
            (
                "(task_frame_launch_queue) :task_frame_candidate: /gate_set and launch_policy/ |queue_outside|",
                f"  + [queue_status] is {self.queue_status}",
                f"  + [ready_candidates] is {_list_or_none(tuple(candidate.candidate_id for candidate in self.ready_candidates))}",
                f"  + [blocked_candidates] is {_list_or_none(tuple(candidate.candidate_id for candidate in self.blocked_candidates))}",
                f"  |queue_outside| {_list_or_none(self.outside)}",
            )
        )
        return "\n".join(lines)


def build_lmstudio_task_frame_candidate(
    *,
    candidate_id: str,
    task_frame_id: str,
    task_subject: str,
    objective: str,
    prompt_packet: str,
    capture_target: str,
    repo_root: str | Path = "C:\\Project\\Pinky",
    source_refs: tuple[str, ...] = (),
    required_gates: tuple[str, ...] = DEFAULT_LMSTUDIO_GATES,
    allowed_surface: tuple[str, ...] = ("prompt_packet", "scratch_workspace", "capture_target"),
    blocked_surface: tuple[str, ...] = ("repo_mutation", "credentials", "destructive_action", "project_root_authority"),
    outside: tuple[str, ...] = DEFAULT_LMSTUDIO_OUTSIDE,
    block_reasons: tuple[str, ...] = (),
    launch_mode: str = "isolated",
    timeout_seconds: int = 240,
) -> TaskFrameLaunchCandidate:
    resolved_block_reasons = tuple(block_reasons)
    if launch_mode not in {"isolated", "scratch_prompt_only"}:
        resolved_block_reasons = resolved_block_reasons + ("launch_mode_not_scratch_isolated",)
    command = _build_lmstudio_launch_command(
        repo_root=repo_root,
        prompt_packet=prompt_packet,
        capture_target=capture_target,
        launch_mode="isolated" if launch_mode == "scratch_prompt_only" else launch_mode,
        timeout_seconds=timeout_seconds,
    )
    return TaskFrameLaunchCandidate(
        candidate_id=candidate_id,
        task_frame_id=task_frame_id,
        task_subject=task_subject,
        objective=objective,
        lane_fit="lm_studio_cli",
        launch_mode=launch_mode,
        prompt_packet=prompt_packet,
        launch_command=command,
        capture_target=capture_target,
        required_gates=required_gates,
        source_refs=source_refs,
        allowed_surface=allowed_surface,
        blocked_surface=blocked_surface,
        block_reasons=resolved_block_reasons,
        outside=outside,
        status="blocked" if resolved_block_reasons else "queue_ready",
        created_utc=_utc_now(),
    )


def build_task_frame_launch_queue(
    *,
    queue_id: str,
    candidates: tuple[TaskFrameLaunchCandidate, ...],
    outside: tuple[str, ...] = (
        "automatic launch",
        "worker mutation authority",
        "hidden model state",
        "unrelated dirty files",
    ),
) -> TaskFrameLaunchQueue:
    return TaskFrameLaunchQueue(
        queue_id=queue_id,
        candidates=candidates,
        outside=outside,
        created_utc=_utc_now(),
    )


def write_task_frame_launch_queue(queue: TaskFrameLaunchQueue, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(queue.render() + "\n", encoding="ascii")
    return path


def _build_lmstudio_launch_command(
    *,
    repo_root: str | Path,
    prompt_packet: str,
    capture_target: str,
    launch_mode: str,
    timeout_seconds: int,
) -> str:
    return " ".join(
        (
            "python",
            ".sop\\runtime\\demos\\lm_studio_agent_benchmark.py",
            "--root",
            str(repo_root),
            "--codex-worker-prompt",
            prompt_packet,
            "--launch-mode",
            launch_mode,
            "--output",
            capture_target,
            "--timeout",
            str(timeout_seconds),
        )
    )


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _list_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
