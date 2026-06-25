from __future__ import annotations

import re
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .lm_studio_agent_benchmark import (
    DEFAULT_ENDPOINT,
    choose_default_model,
    list_lm_studio_models,
    run_lm_studio_completion,
)


DEFAULT_MANAGER_CANDIDATE_ID = "direct_lmstudio_endpoint_manager_runner_001"
DEFAULT_CONTEXT_PATHS = (
    ".sop/platform/SOPLanguagePrimerForLocalAgents.sop",
    ".sop/platform/SOPWorkerBootPacket.sop",
    ".sop/platform/CompactLMStudioManagerKernelBundle.sop",
    ".sop/workspaces/codex_lmstudio_orchestrator/CompactManagerKernelBundle.sop",
    ".sop/workspaces/codex_lmstudio_orchestrator/WorkspaceState.sop",
    ".sop/workspaces/codex_lmstudio_orchestrator/Runbook.sop",
    ".sop/workspaces/codex_lmstudio_orchestrator/WorkerPacketTemplate.sop",
    ".sop/workspaces/codex_lmstudio_orchestrator/Queue.sop",
    ".sop/state/CurrentFocalPoint.sop",
)
REQUIRED_MANAGER_PROPOSAL_FIELDS = (
    "proposal_id",
    "proposed_worker_lane",
    "objective",
    "working_directory",
    "allowed_surface",
    "blocked_surface",
    "prompt_packet_refs",
    "capture_target",
    "proof_gate",
    "risk_gate",
    "outside",
)
MANAGER_FIELD_GUIDANCE = {
    "proposal_id": "stable short id for this proposal",
    "proposed_worker_lane": "openai_codex_cli, manual, deferred, or blocked",
    "objective": "one bounded job or one concrete blocked_outside reason",
    "working_directory": "C:\\Project\\Pinky or outside",
    "allowed_surface": "read compact context, classify the selected candidate, preserve outside, and return one proposal or blocked note",
    "blocked_surface": "file mutation, shell commands, worker launch, commits, pushes, credentials, destructive action, hidden spend, and unrelated dirty files",
    "prompt_packet_refs": "CompactManagerKernelBundle.sop plus the selected queue candidate and source refs",
    "capture_target": "local capture path or outside when no worker capture is safe",
    "proof_gate": "tests, diff check, ASCII scan, validator score, and Codex review before integration",
    "risk_gate": "cost, authority, safety, stop policy, and handoff threshold when Codex worker lane is proposed",
    "outside": "uncertainty, stale blockers, unsafe actions, hidden state, and any launch material not accepted",
}
VALID_MANAGER_LANES = {"openai_codex_cli", "manual", "deferred", "blocked"}
FORBIDDEN_CLAIM_PATTERNS = (
    (r"\b(?:i|we|lm studio|local manager|manager)\s+(?:edited|modified|wrote|created|deleted)\b", "mutation_claim"),
    (r"\b(?:i|we|lm studio|local manager|manager)\s+(?:launched|ran|executed|started|spawned)\b", "launch_claim"),
    (r"\b(?:i|we|lm studio|local manager|manager)\s+(?:committed|pushed|integrated|validated)\b", "authority_claim"),
    (r"\b(?:worker|job|codex)\s+(?:has been|was)\s+(?:launched|started|completed|committed|pushed)\b", "completed_work_claim"),
)


@dataclass(frozen=True)
class DirectLMStudioManagerContextStream:
    stream_id: str
    root: str
    endpoint: str
    model: str
    candidate_id: str
    source_refs: tuple[str, ...]
    source_slices: tuple[tuple[str, str], ...]
    selected_candidate_excerpt: str
    created_utc: str = ""

    @property
    def safe_id(self) -> str:
        return _safe_key(self.stream_id)

    @property
    def ready(self) -> bool:
        return bool(self.stream_id and self.source_refs and self.selected_candidate_excerpt)

    def prompt_text(self) -> str:
        lines = [
            "You are the local LM Studio SOP manager for C:\\Project\\Pinky\\.sop.",
            "Codex remains the only authority for file mutation, shell commands, worker launch, commits, pushes, and integration.",
            "Your job is to read the compact SOP context stream and return exactly one bounded manager proposal or one blocked note.",
            "Runner status: this direct endpoint runner exists and is currently executing in proposal-only mode.",
            "If a stale source says runtime_build_confirmation is missing, treat this runner execution as the build-confirmation context and inspect whether any other gate remains blocked.",
            "Return raw SOP only. Do not use markdown, bullets, code fences, or commentary outside the SOP node.",
            "Every property line must use this exact syntax: two spaces, plus sign, field in brackets, space, is, space, value.",
            "Example:   + [proposal_id] is direct_runner_next_step",
            "",
            "Required output shape:",
            "& [LMStudioManagerProposal:<proposal_id>] is one direct endpoint manager proposal",
        ]
        for field_name in REQUIRED_MANAGER_PROPOSAL_FIELDS:
            lines.append(f"  + [{field_name}] is {MANAGER_FIELD_GUIDANCE[field_name]}")
        lines.extend(
            (
                "",
                "Rules:",
                "- proposed_worker_lane must be one of openai_codex_cli, manual, deferred, or blocked.",
                "- If proposed_worker_lane is openai_codex_cli, name the handoff threshold in risk_gate or objective.",
                "- Keep exactly one job or exactly one blocked note.",
                "- Do not claim you edited files, ran commands, launched workers, committed, pushed, validated, or integrated work.",
                "- Use ASCII only.",
                "- Required fields must be concrete. For blocked notes, allowed_surface should describe reading context and returning a blocked note; do not use none, TBD, or placeholders.",
                "- Preserve outside explicitly.",
                "",
                "Selected queue candidate:",
                self.selected_candidate_excerpt.strip(),
                "",
                "Compact source slices:",
            )
        )
        for path, text in self.source_slices:
            lines.extend(("", f"[source:{path}]", text.strip()))
        return _ascii_safe("\n".join(lines).strip())

    def render(self) -> str:
        lines = [
            "Subject: Direct LM Studio Manager Context Stream",
            "",
            "Description: Lightweight SOP context stream for a local LM Studio manager proposal pass.",
            "",
            f"& [DirectLMStudioManagerContextStream:{self.safe_id}] is a lightweight SOP context stream",
            f"  + [stream_id] is {self.stream_id}",
            f"  + [root] is {self.root}",
            f"  + [endpoint] is {self.endpoint}",
            f"  + [model] is {self.model or 'auto_select'}",
            f"  + [candidate_id] is {self.candidate_id}",
            f"  + [source_refs] is {_list_or_none(self.source_refs)}",
            f"  + [source_slice_count] is {len(self.source_slices)}",
            f"  + [created_utc] is {self.created_utc or _utc_now()}",
            "  + [prompt_text] is:",
        ]
        for line in self.prompt_text().splitlines():
            stripped = line.rstrip()
            lines.append(f"    {stripped}" if stripped else "")
        lines.extend(
            (
                "",
                "  = must: be reviewed or sent by an explicit runner call",
                "  = must: keep one selected queue candidate",
                "  - never: launch a worker from context construction alone",
            )
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class LMStudioManagerProposalValidation:
    output_text: str
    fields: tuple[tuple[str, str], ...]
    node_count: int
    missing_fields: tuple[str, ...]
    empty_fields: tuple[str, ...]
    invalid_lanes: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    format_errors: tuple[str, ...]
    outside_present: bool
    handoff_threshold_named: bool

    @property
    def field_map(self) -> dict[str, str]:
        return {name: value for name, value in self.fields}

    @property
    def valid(self) -> bool:
        return not (
            self.missing_fields
            or self.empty_fields
            or self.invalid_lanes
            or self.forbidden_claims
            or self.format_errors
            or not self.outside_present
            or not self.handoff_threshold_named
        )

    @property
    def score(self) -> int:
        penalty = (
            12 * len(self.missing_fields)
            + 8 * len(self.empty_fields)
            + 15 * len(self.invalid_lanes)
            + 20 * len(self.forbidden_claims)
            + 15 * len(self.format_errors)
            + (0 if self.outside_present else 15)
            + (0 if self.handoff_threshold_named else 10)
        )
        return max(0, min(100, 100 - penalty))

    @property
    def band(self) -> str:
        if self.valid and self.score >= 90:
            return "strong"
        if self.valid and self.score >= 75:
            return "usable"
        if self.score >= 50:
            return "weak"
        return "failed"

    @property
    def integration_disposition(self) -> str:
        if not self.output_text.strip():
            return "blocked_outside"
        if self.valid:
            lane = self.field_map.get("proposed_worker_lane", "").strip().lower()
            return "blocked_outside" if lane == "blocked" else "accept_for_codex_review"
        return "reject_for_retry"

    def render(self, validation_id: str = "direct_lmstudio_manager_validation") -> str:
        lines = [
            "Subject: Direct LM Studio Manager Proposal Validation",
            "",
            "Description: Host-side validation of a local manager proposal before Codex review.",
            "",
            f"& [DirectLMStudioManagerProposalValidation:{_safe_key(validation_id)}] is manager proposal validation",
            f"  + [valid] is {str(self.valid).lower()}",
            f"  + [score] is {self.score}",
            f"  + [band] is {self.band}",
            f"  + [node_count] is {self.node_count}",
            f"  + [missing_fields] is {_list_or_none(self.missing_fields)}",
            f"  + [empty_fields] is {_list_or_none(self.empty_fields)}",
            f"  + [invalid_lanes] is {_list_or_none(self.invalid_lanes)}",
            f"  + [forbidden_claims] is {_list_or_none(self.forbidden_claims)}",
            f"  + [format_errors] is {_list_or_none(self.format_errors)}",
            f"  + [outside_present] is {str(self.outside_present).lower()}",
            f"  + [handoff_threshold_named] is {str(self.handoff_threshold_named).lower()}",
            f"  + [integration_disposition] is {self.integration_disposition}",
            "  + [outside] is raw manager output remains advisory until Codex review accepts it",
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class DirectLMStudioManagerRun:
    run_id: str
    context_stream: DirectLMStudioManagerContextStream
    provider_available: bool
    provider_called: bool
    available_models: tuple[str, ...]
    selected_model: str
    output_text: str
    validation: LMStudioManagerProposalValidation
    error: str = ""
    created_utc: str = ""

    @property
    def ready(self) -> bool:
        return self.context_stream.ready and bool(self.run_id)

    @property
    def accepted(self) -> bool:
        return self.provider_called and self.validation.valid

    def render(self) -> str:
        lines = [
            "Subject: Direct LM Studio Manager Run",
            "",
            "Description: Captured direct endpoint manager pass with host-side validation.",
            "",
            f"& [DirectLMStudioManagerRun:{_safe_key(self.run_id)}] is a captured local manager pass",
            f"  + [run_id] is {self.run_id}",
            f"  + [stream_id] is {self.context_stream.stream_id}",
            f"  + [endpoint] is {self.context_stream.endpoint}",
            f"  + [provider_available] is {str(self.provider_available).lower()}",
            f"  + [provider_called] is {str(self.provider_called).lower()}",
            f"  + [available_models] is {_list_or_none(self.available_models)}",
            f"  + [selected_model] is {self.selected_model or 'none'}",
            f"  + [accepted] is {str(self.accepted).lower()}",
            f"  + [validation_score] is {self.validation.score}",
            f"  + [validation_band] is {self.validation.band}",
            f"  + [integration_disposition] is {self.validation.integration_disposition}",
            f"  + [error] is {self.error or 'none'}",
            f"  + [created_utc] is {self.created_utc or _utc_now()}",
            "  + [raw_output] is:",
        ]
        for line in _ascii_safe(self.output_text.strip() or "none").splitlines():
            lines.append(f"    {line.rstrip()}")
        lines.append("")
        lines.append(self.validation.render(self.run_id + "_validation"))
        lines.extend(
            (
                "",
                "  = must: preserve raw_output before any Codex handoff",
                "  = must: reject invalid or authority-blurred outputs",
                "  - never: dispatch an OpenAI Codex worker from this capture alone",
            )
        )
        return "\n".join(lines)


def build_direct_lmstudio_manager_context(
    *,
    root: str | Path = ".",
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = "",
    candidate_id: str = DEFAULT_MANAGER_CANDIDATE_ID,
    context_paths: tuple[str, ...] = DEFAULT_CONTEXT_PATHS,
    max_chars_per_source: int = 5000,
    stream_id: str = "",
) -> DirectLMStudioManagerContextStream:
    repo_root = Path(root).resolve()
    source_slices: list[tuple[str, str]] = []
    source_refs: list[str] = []
    for relative_path in context_paths:
        path = repo_root / relative_path
        if not path.exists():
            continue
        source_refs.append(relative_path)
        source_slices.append((relative_path, _read_limited(path, max_chars=max_chars_per_source)))

    queue_path = repo_root / ".sop/workspaces/codex_lmstudio_orchestrator/Queue.sop"
    queue_text = _ascii_safe(queue_path.read_text(encoding="utf-8")) if queue_path.exists() else _source_text_for(
        ".sop/workspaces/codex_lmstudio_orchestrator/Queue.sop",
        source_slices,
    )
    candidate_excerpt = _extract_candidate(queue_text, candidate_id)
    if candidate_excerpt != "none":
        source_slices = [
            (
                path,
                "Subject: Selected Queue Candidate\n\n"
                + candidate_excerpt
                + "\n\n|queue_outside| other queue candidates are omitted from this compact manager pass"
                if path == ".sop/workspaces/codex_lmstudio_orchestrator/Queue.sop"
                else text,
            )
            for path, text in source_slices
        ]
    workspace_state_path = repo_root / ".sop/workspaces/codex_lmstudio_orchestrator/WorkspaceState.sop"
    workspace_state_text = (
        _ascii_safe(workspace_state_path.read_text(encoding="utf-8"))
        if workspace_state_path.exists()
        else _source_text_for(".sop/workspaces/codex_lmstudio_orchestrator/WorkspaceState.sop", source_slices)
    )
    selected_model = model or _normalize_model_hint(_extract_field(workspace_state_text, "preferred_initial_manager_model"))
    resolved_stream_id = stream_id or "direct_lmstudio_manager_context_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return DirectLMStudioManagerContextStream(
        stream_id=resolved_stream_id,
        root=str(repo_root),
        endpoint=endpoint,
        model=selected_model,
        candidate_id=candidate_id,
        source_refs=tuple(source_refs),
        source_slices=tuple(source_slices),
        selected_candidate_excerpt=candidate_excerpt,
        created_utc=_utc_now(),
    )


def validate_lmstudio_manager_proposal(output: str) -> LMStudioManagerProposalValidation:
    ascii_text = _ascii_safe(output)
    fields = _parse_fields(ascii_text)
    field_map = {name: value for name, value in fields}
    missing = tuple(field for field in REQUIRED_MANAGER_PROPOSAL_FIELDS if field not in field_map)
    empty = tuple(field for field in REQUIRED_MANAGER_PROPOSAL_FIELDS if field in field_map and _is_hollow(field_map[field]))
    lane = field_map.get("proposed_worker_lane", "").strip().lower()
    invalid_lanes = () if not lane or lane in VALID_MANAGER_LANES else (lane,)
    forbidden_claims = tuple(label for pattern, label in FORBIDDEN_CLAIM_PATTERNS if re.search(pattern, ascii_text, re.IGNORECASE))
    node_count = len(re.findall(r"(?m)^\s*&\s*\[", ascii_text))
    format_errors: list[str] = []
    if output != ascii_text:
        format_errors.append("non_ascii_output")
    if node_count == 0:
        format_errors.append("missing_subject_declaration")
    if node_count > 1:
        format_errors.append("multiple_subject_declarations")
    malformed_fields = tuple(
        field
        for field in re.findall(r"(?m)^\s*\+\s*\[([A-Za-z0-9_:-]+)\]\s+(?!is\b).+$", ascii_text)
        if field in REQUIRED_MANAGER_PROPOSAL_FIELDS
    )
    if malformed_fields:
        format_errors.append("missing_is_property_marker:" + ",".join(malformed_fields))
    if "```" in ascii_text or "**" in ascii_text:
        format_errors.append("markdown_format")
    outside = field_map.get("outside", "")
    outside_present = bool(outside.strip()) and not _is_hollow(outside)
    if lane == "openai_codex_cli":
        handoff_named = "handoff" in ascii_text.lower() and "threshold" in ascii_text.lower()
    else:
        handoff_named = True
    return LMStudioManagerProposalValidation(
        output_text=ascii_text,
        fields=fields,
        node_count=node_count,
        missing_fields=missing,
        empty_fields=empty,
        invalid_lanes=invalid_lanes,
        forbidden_claims=forbidden_claims,
        format_errors=tuple(format_errors),
        outside_present=outside_present,
        handoff_threshold_named=handoff_named,
    )


def run_direct_lmstudio_manager(
    *,
    root: str | Path = ".",
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = "",
    candidate_id: str = DEFAULT_MANAGER_CANDIDATE_ID,
    timeout: float = 60.0,
    max_tokens: int = 700,
    dry_run: bool = True,
    max_chars_per_source: int = 5000,
    context_stream: DirectLMStudioManagerContextStream | None = None,
    model_probe: Callable[..., tuple[str, ...]] = list_lm_studio_models,
    completion_fn: Callable[..., str] = run_lm_studio_completion,
) -> DirectLMStudioManagerRun:
    context = context_stream or build_direct_lmstudio_manager_context(
        root=root,
        endpoint=endpoint,
        model=model,
        candidate_id=candidate_id,
        max_chars_per_source=max_chars_per_source,
    )
    run_id = "direct_lmstudio_manager_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if dry_run:
        validation = validate_lmstudio_manager_proposal("")
        return DirectLMStudioManagerRun(
            run_id=run_id,
            context_stream=context,
            provider_available=False,
            provider_called=False,
            available_models=(),
            selected_model=context.model or model,
            output_text="",
            validation=validation,
            error="dry_run_no_provider_call",
            created_utc=_utc_now(),
        )

    try:
        available_models = model_probe(endpoint=endpoint, timeout=min(timeout, 15.0))
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as error:
        validation = validate_lmstudio_manager_proposal("")
        return DirectLMStudioManagerRun(
            run_id=run_id,
            context_stream=context,
            provider_available=False,
            provider_called=False,
            available_models=(),
            selected_model=context.model or model,
            output_text="",
            validation=validation,
            error=f"provider_probe_failed: {error}",
            created_utc=_utc_now(),
        )

    selected_model = model or context.model or choose_default_model(available_models)
    if not available_models or not selected_model:
        validation = validate_lmstudio_manager_proposal("")
        return DirectLMStudioManagerRun(
            run_id=run_id,
            context_stream=context,
            provider_available=False,
            provider_called=False,
            available_models=available_models,
            selected_model=selected_model,
            output_text="",
            validation=validation,
            error="provider_unavailable_or_no_model",
            created_utc=_utc_now(),
        )

    try:
        output = completion_fn(
            endpoint=endpoint,
            model=selected_model,
            prompt=context.prompt_text(),
            timeout=timeout,
            max_tokens=max_tokens,
        )
        error = ""
    except urllib.error.HTTPError as exc:
        output = ""
        error = f"completion_failed: {exc}; body={_http_error_body(exc)}"
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        output = ""
        error = f"completion_failed: {exc}"
    validation = validate_lmstudio_manager_proposal(output)
    return DirectLMStudioManagerRun(
        run_id=run_id,
        context_stream=context,
        provider_available=True,
        provider_called=True,
        available_models=available_models,
        selected_model=selected_model,
        output_text=output,
        validation=validation,
        error=error,
        created_utc=_utc_now(),
    )


def write_direct_lmstudio_manager_context(context: DirectLMStudioManagerContextStream, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(context.render() + "\n", encoding="ascii")
    return path


def write_direct_lmstudio_manager_run(run: DirectLMStudioManagerRun, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(run.render() + "\n", encoding="ascii")
    return path


def _extract_candidate(queue_text: str, candidate_id: str) -> str:
    node_name = "Candidate_" + candidate_id
    pattern = rf"(?ms)^& \[{re.escape(node_name)}\].*?(?=^& \[|\Z)"
    match = re.search(pattern, queue_text)
    if match:
        return match.group(0).strip()
    generic = re.search(r"(?ms)^& \[Candidate_[^\]]+\].*?(?=^& \[|\Z)", queue_text)
    return generic.group(0).strip() if generic else "none"


def _extract_field(text: str, field_name: str) -> str:
    match = re.search(rf"(?m)^\s*\+\s*\[{re.escape(field_name)}\]\s+is\s+(.+?)\s*$", text)
    return match.group(1).strip() if match else ""


def _parse_fields(output: str) -> tuple[tuple[str, str], ...]:
    fields: list[tuple[str, str]] = []
    current_name = ""
    current_lines: list[str] = []
    field_pattern = re.compile(r"^\s*\+\s*\[([A-Za-z0-9_:-]+)\]\s+is\s*(.*)$")
    for line in output.splitlines():
        match = field_pattern.match(line)
        if match:
            if current_name:
                fields.append((current_name, " ".join(current_lines).strip()))
            current_name = match.group(1)
            current_lines = [match.group(2).strip()]
            continue
        if current_name and (line.startswith("    ") or line.startswith("  ")):
            current_lines.append(line.strip())
    if current_name:
        fields.append((current_name, " ".join(current_lines).strip()))
    return tuple(fields)


def _read_limited(path: Path, *, max_chars: int) -> str:
    text = path.read_text(encoding="utf-8")
    safe = _ascii_safe(text)
    if len(safe) <= max_chars:
        return safe
    head = safe[: max_chars // 2].rstrip()
    tail = safe[-(max_chars // 2) :].lstrip()
    return f"{head}\n[... clipped middle for compact manager context ...]\n{tail}"


def _source_text_for(relative_path: str, source_slices: tuple[tuple[str, str], ...] | list[tuple[str, str]]) -> str:
    for path, text in source_slices:
        if path == relative_path:
            return text
    return ""


def _is_hollow(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"", "...", "todo", "tbd", "n/a", "na", "none", "placeholder", "<non-empty value>"}


def _http_error_body(error: urllib.error.HTTPError) -> str:
    try:
        body = error.read().decode("utf-8", errors="replace").strip()
    except Exception:
        return "unavailable"
    return _ascii_safe(body[:1000]) if body else "empty"


def _normalize_model_hint(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    for separator in (" until ", " unless ", " if ", " when ", ","):
        if separator in stripped:
            return stripped.split(separator, 1)[0].strip()
    return stripped.split()[0] if " " in stripped else stripped


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _list_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _ascii_safe(value: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2011": "-",
        "\u2026": "...",
    }
    translated = "".join(replacements.get(character, character) for character in str(value))
    return translated.encode("ascii", errors="replace").decode("ascii")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
