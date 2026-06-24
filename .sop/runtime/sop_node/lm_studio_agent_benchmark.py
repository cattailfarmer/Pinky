from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ENDPOINT = "http://127.0.0.1:1234/v1"
DEFAULT_OPERATIONAL_HOST = "codex_agent_cli"
DEFAULT_INFERENCE_FIELDS = ("focus", "inside", "boundary", "outside", "inference", "caution", "next_step")
DEFAULT_CONTROLLED_EXPLOSION_TERMS = (
    "atomic_thought",
    "combustion_chamber",
    "compression",
    "spark",
    "governor",
    "piston",
    "exhaust",
    "cooling",
)
DEFAULT_FORBIDDEN_CONTEXT_TERMS = ("AGENTS.md", "SJS", "SpecificationGovernance", "generic governance")


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    task_subject: str
    objective: str
    instructions: str
    required_terms: tuple[str, ...]
    expected_labels: tuple[str, ...]
    forbidden_terms: tuple[str, ...] = field(default_factory=tuple)

    @property
    def prompt(self) -> str:
        label_lines = "\n".join(f"{label}:" for label in self.expected_labels)
        return "\n".join(
            (
                "You are an LM Studio local model acting only as a proposed SOP worker.",
                "Codex is the operational host and owns repo authority, file writes, commits, pushes, and integration.",
                "You must not claim you edited files, launched commands, inspected hidden model state, or completed repo work.",
                "",
                "Task frame reminders:",
                f"- task_subject: {self.task_subject}",
                "- subject_reminder: answer only this task subject.",
                "- boundary_reminder: non-mutating text proposal only.",
                "- operation_reminder: fill the requested fields directly.",
                "- evidence_reminder: preserve evidence or proof needs before integration.",
                "- return_reminder: return output for Codex capture and review.",
                "- outside_reminder: preserve blocked, uncertain, or out-of-scope material as outside.",
                "",
                f"Objective: {self.objective}",
                "",
                self.instructions,
                "",
                "Return exactly these labels, one per line or with short continuation text:",
                label_lines,
            )
        )


@dataclass(frozen=True)
class BenchmarkScore:
    score: int
    band: str
    missing_required: tuple[str, ...]
    forbidden_hits: tuple[str, ...]
    format_hits: tuple[str, ...]
    outside_present: bool
    task_fit: bool


@dataclass(frozen=True)
class SOPWorkerValidation:
    output_text: str
    node_name: str
    node_description: str
    fields: tuple[tuple[str, str], ...]
    missing_fields: tuple[str, ...]
    empty_fields: tuple[str, ...]
    missing_required_terms: tuple[str, ...]
    forbidden_field_hits: tuple[str, ...]
    format_errors: tuple[str, ...]
    outside_present: bool

    @property
    def field_map(self) -> dict[str, str]:
        return {name: value for name, value in self.fields}

    @property
    def valid(self) -> bool:
        return not (
            self.missing_fields
            or self.empty_fields
            or self.missing_required_terms
            or self.forbidden_field_hits
            or self.format_errors
            or not self.outside_present
        )

    @property
    def score(self) -> int:
        penalty = (
            15 * len(self.missing_fields)
            + 10 * len(self.empty_fields)
            + 8 * len(self.missing_required_terms)
            + 20 * len(self.forbidden_field_hits)
            + 15 * len(self.format_errors)
            + (0 if self.outside_present else 10)
        )
        return max(0, min(100, 100 - penalty))

    @property
    def band(self) -> str:
        if self.score >= 85 and self.valid:
            return "strong"
        if self.score >= 70:
            return "usable"
        if self.score >= 50:
            return "weak"
        return "failed"

    def render(self, validation_id: str = "sop_worker_validation") -> str:
        lines = [
            "Subject: SOP Worker Output Validation",
            "",
            "Description: Host-side validation of a captured SOP worker output.",
            "",
            f"& [SOPWorkerValidation:{_safe_key(validation_id)}] is captured worker output validation",
            f"  + [node_name] is {self.node_name or 'none'}",
            f"  + [node_description] is {self.node_description or 'none'}",
            f"  + [valid] is {str(self.valid).lower()}",
            f"  + [score] is {self.score}",
            f"  + [band] is {self.band}",
            f"  + [missing_fields] is {_list_or_none(self.missing_fields)}",
            f"  + [empty_fields] is {_list_or_none(self.empty_fields)}",
            f"  + [missing_required_terms] is {_list_or_none(self.missing_required_terms)}",
            f"  + [forbidden_field_hits] is {_list_or_none(self.forbidden_field_hits)}",
            f"  + [format_errors] is {_list_or_none(self.format_errors)}",
            f"  + [outside_present] is {str(self.outside_present).lower()}",
            "  + [integration_disposition] is accept_as_proposal if valid else reject_for_retry_or_block",
            "  + [outside] is hidden model state, unvalidated worker authority, and any forbidden field contamination",
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class CodexLMStudioWorkerRun:
    run_id: str
    launch_mode: str
    workspace: str
    output_path: str
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    output_text: str
    validation: SOPWorkerValidation

    @property
    def functional(self) -> bool:
        return self.exit_code == 0 and self.validation.valid

    def render(self) -> str:
        lines = [
            "Subject: Codex LM Studio Worker Run",
            "",
            "Description: Captured Codex CLI local-provider worker run with SOP validation.",
            "",
            f"& [CodexLMStudioWorkerRun:{_safe_key(self.run_id)}] is a captured local worker run",
            f"  + [run_id] is {self.run_id}",
            f"  + [launch_mode] is {self.launch_mode}",
            f"  + [workspace] is {self.workspace}",
            f"  + [output_path] is {self.output_path}",
            f"  + [exit_code] is {self.exit_code}",
            f"  + [functional] is {str(self.functional).lower()}",
            f"  + [validation_score] is {self.validation.score}",
            f"  + [validation_band] is {self.validation.band}",
            f"  + [command] is {' '.join(self.command)}",
            "  + [stdout] is:",
        ]
        for line in _ascii_safe(self.stdout.strip() or "none").splitlines():
            lines.append(f"    {line.rstrip()}")
        lines.append("  + [stderr] is:")
        for line in _ascii_safe(self.stderr.strip() or "none").splitlines():
            lines.append(f"    {line.rstrip()}")
        lines.append("")
        lines.append(self.validation.render(self.run_id + "_validation"))
        return "\n".join(lines)


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case: BenchmarkCase
    model: str
    response_text: str
    latency_ms: int
    score: BenchmarkScore
    error: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.case.case_id and self.model and (self.response_text or self.error))


@dataclass(frozen=True)
class BenchmarkReport:
    report_id: str
    endpoint: str
    model: str
    operational_host: str
    provider_available: bool
    available_models: tuple[str, ...]
    case_results: tuple[BenchmarkCaseResult, ...]
    started_at_utc: str
    completed_at_utc: str
    outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def aggregate_score(self) -> int:
        if not self.case_results:
            return 0
        return round(sum(result.score.score for result in self.case_results) / len(self.case_results))

    @property
    def aggregate_band(self) -> str:
        if not self.provider_available:
            return "blocked"
        score = self.aggregate_score
        if score >= 85:
            return "strong"
        if score >= 70:
            return "usable"
        if score >= 50:
            return "weak"
        return "failed"

    @property
    def ready(self) -> bool:
        return bool(self.report_id and self.endpoint and self.model and self.case_results)

    def render(self) -> str:
        lines = [
            "Subject: LM Studio Agent Benchmark Result",
            "",
            "Description: Captured benchmark of a local LM Studio model operating as a Codex-hosted SOP worker lane.",
            "",
            f"& [LMStudioAgentBenchmarkResult:{_safe_key(self.report_id)}] is a captured local worker benchmark",
            f"  + [report_id] is {self.report_id}",
            f"  + [provider_endpoint] is {self.endpoint}",
            f"  + [model] is {self.model}",
            f"  + [operational_host] is {self.operational_host}",
            f"  + [provider_available] is {str(self.provider_available).lower()}",
            f"  + [available_models] is {', '.join(self.available_models) if self.available_models else 'none'}",
            f"  + [started_at_utc] is {self.started_at_utc}",
            f"  + [completed_at_utc] is {self.completed_at_utc}",
            f"  + [aggregate_score] is {self.aggregate_score}",
            f"  + [aggregate_band] is {self.aggregate_band}",
            "  + [codex_review] is benchmark scores local model proposal quality; Codex remains authority for repo mutation and integration",
            "  + [outside] is provider limits, hidden model state, benchmark narrowness, local model repo authority, and untested broader competence",
            "",
        ]
        for index, result in enumerate(self.case_results, start=1):
            lines.extend(
                (
                    f"& [BenchmarkCaseResult:{_safe_key(result.case.case_id)}] is case {index}",
                    f"  + [case_id] is {result.case.case_id}",
                    f"  + [task_subject] is {result.case.task_subject}",
                    f"  + [objective] is {result.case.objective}",
                    f"  + [latency_ms] is {result.latency_ms}",
                    f"  + [score] is {result.score.score}",
                    f"  + [score_band] is {result.score.band}",
                    f"  + [missing_required] is {_list_or_none(result.score.missing_required)}",
                    f"  + [forbidden_hits] is {_list_or_none(result.score.forbidden_hits)}",
                    f"  + [format_hits] is {_list_or_none(result.score.format_hits)}",
                    f"  + [outside_present] is {str(result.score.outside_present).lower()}",
                    f"  + [task_fit] is {str(result.score.task_fit).lower()}",
                    f"  + [error] is {result.error or 'none'}",
                    "  + [captured_output] is:",
                )
            )
            rendered_output = _ascii_safe(result.response_text.strip() or result.error or "no output")
            for output_line in rendered_output.splitlines():
                lines.append(f"    {output_line.rstrip()}")
            lines.append("")
        lines.extend(
            (
                "(lm_studio_agent_benchmark_result) :captured_output: /quality_score and codex_review/ |benchmark_outside|",
                f"  + [aggregate_score] is {self.aggregate_score}",
                f"  + [aggregate_band] is {self.aggregate_band}",
                "  + [codex_operational_host] is Codex-held authority over capture, scoring, file writes, commits, pushes, and integration",
                "  |benchmark_outside| hidden state, provider limits, local model repo authority, and untested broader competence",
            )
        )
        for item in self.outside:
            lines.append(f"  - outside: {_ascii_safe(item)}")
        return "\n".join(lines)


def default_benchmark_cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            case_id="task_frame_reminders",
            task_subject="non-mutating SOP task frame",
            objective="Create a compact task frame for a worker that summarizes a SOP contract without editing files.",
            instructions=(
                "Make the task frame about summarizing SourceAuthorityRoot for a future worker. "
                "Keep the output brief and explicitly preserve outside."
            ),
            required_terms=(
                "task_subject",
                "subject_reminder",
                "boundary_reminder",
                "operation_reminder",
                "evidence_reminder",
                "return_reminder",
                "outside",
            ),
            expected_labels=(
                "task_subject",
                "subject_reminder",
                "boundary_reminder",
                "operation_reminder",
                "evidence_reminder",
                "return_reminder",
                "outside",
            ),
            forbidden_terms=("i edited", "i committed", "git push", "launched", "inspected hidden activations"),
        ),
        BenchmarkCase(
            case_id="lane_routing",
            task_subject="SOP worker lane routing",
            objective="Route small jobs to local_gpu, lm_studio, openai_codex, codex_cli, manual, deferred, or outside.",
            instructions=(
                "Classify these jobs: broad brainstorm, repo file edit, credential decision, provider unavailable, "
                "test-running code change, and uncertain scope. Include one sentence explaining the boundary."
            ),
            required_terms=("local_gpu", "lm_studio", "openai_codex", "codex_cli", "manual", "deferred", "outside"),
            expected_labels=("local_gpu", "lm_studio", "openai_codex", "codex_cli", "manual", "deferred", "outside"),
            forbidden_terms=("i edited", "i launched", "credentials are safe", "verified remote", "inspected hidden state"),
        ),
        BenchmarkCase(
            case_id="quality_review",
            task_subject="worker output quality review",
            objective="Critique a weak worker output and keep it proposed, not integrated.",
            instructions=(
                "Worker output to review: 'Done, I changed the repo and proved the model understands the framework.' "
                "Explain what is wrong and what evidence would be needed before integration."
            ),
            required_terms=("capture", "evidence", "outside", "not integrated", "caution", "revise"),
            expected_labels=("capture", "evidence", "outside", "integration_status", "caution", "revise"),
            forbidden_terms=("approved", "verified", "fully integrated", "proof complete", "accessed hidden model"),
        ),
    )


def score_output(case: BenchmarkCase, output: str) -> BenchmarkScore:
    lower_output = output.lower()
    missing_required = tuple(term for term in case.required_terms if term.lower() not in lower_output)
    forbidden_hits = tuple(term for term in case.forbidden_terms if _contains_forbidden(term, lower_output))
    format_hits = tuple(label for label in case.expected_labels if _label_has_content(output, label, case.expected_labels))
    outside_present = "outside" in lower_output or "out-of-scope" in lower_output or "out of scope" in lower_output
    task_fit = (
        bool(output.strip())
        and len(missing_required) <= max(1, len(case.required_terms) // 2)
        and len(format_hits) >= max(1, len(case.expected_labels) // 2)
    )

    required_score = round(55 * (len(case.required_terms) - len(missing_required)) / max(1, len(case.required_terms)))
    format_score = round(20 * len(format_hits) / max(1, len(case.expected_labels)))
    outside_score = 15 if outside_present else 0
    fit_score = 10 if task_fit else 0
    penalty = 15 * len(forbidden_hits) + 5 * (len(case.expected_labels) - len(format_hits))
    numeric_score = max(0, min(100, required_score + format_score + outside_score + fit_score - penalty))
    if numeric_score >= 85:
        band = "strong"
    elif numeric_score >= 70:
        band = "usable"
    elif numeric_score >= 50:
        band = "weak"
    else:
        band = "failed"
    return BenchmarkScore(
        score=numeric_score,
        band=band,
        missing_required=missing_required,
        forbidden_hits=forbidden_hits,
        format_hits=format_hits,
        outside_present=outside_present,
        task_fit=task_fit,
    )


def extract_prompt_text_from_sop(prompt_packet: str) -> str:
    marker = "  + [prompt_text] is:"
    index = prompt_packet.find(marker)
    if index < 0:
        raise ValueError("prompt_text marker missing")
    return prompt_packet[index + len(marker) :].strip()


def validate_sop_worker_output(
    output: str,
    *,
    expected_node: str = "InferenceJobResult",
    required_fields: tuple[str, ...] = DEFAULT_INFERENCE_FIELDS,
    required_terms: tuple[str, ...] = DEFAULT_CONTROLLED_EXPLOSION_TERMS,
    forbidden_field_terms: tuple[str, ...] = DEFAULT_FORBIDDEN_CONTEXT_TERMS,
    forbidden_field_names: tuple[str, ...] = ("inside",),
    require_exact_format: bool = True,
) -> SOPWorkerValidation:
    lines = [line.rstrip() for line in output.strip().splitlines() if line.strip()]
    fields: list[tuple[str, str]] = []
    format_errors: list[str] = []
    node_name = ""
    node_description = ""
    if any(ord(character) > 127 for character in output):
        format_errors.append("non_ascii_output")
    if not lines:
        format_errors.append("empty_output")
    else:
        node_match = re.match(r"^& \[([^\]]+)\] is (.+)$", lines[0])
        if node_match:
            node_name = node_match.group(1).strip()
            node_description = node_match.group(2).strip()
            if node_name != expected_node:
                format_errors.append(f"wrong_node:{node_name}")
        else:
            format_errors.append("missing_subject_declaration")
        for index, line in enumerate(lines[1:], start=2):
            field_match = re.match(r"^  \+ \[([^\]]+)\] is (.*)$", line)
            if field_match:
                fields.append((field_match.group(1).strip(), field_match.group(2).strip()))
                continue
            if require_exact_format or line.lstrip().startswith(("-", "*", "#", "**")):
                format_errors.append(f"line_{index}_not_raw_sop")

    field_map = {name: value for name, value in fields}
    missing_fields = tuple(field for field in required_fields if field not in field_map)
    empty_fields = tuple(field for field in required_fields if field in field_map and _is_hollow_field_value(field_map[field]))
    lower_output = output.lower()
    missing_required_terms = tuple(term for term in required_terms if term.lower() not in lower_output)
    forbidden_hits: list[str] = []
    for field_name in forbidden_field_names:
        field_value = field_map.get(field_name, "")
        lower_value = field_value.lower()
        for term in forbidden_field_terms:
            if term.lower() in lower_value:
                forbidden_hits.append(f"{field_name}:{term}")
    outside_present = bool(field_map.get("outside", "").strip()) or "outside" in lower_output
    return SOPWorkerValidation(
        output_text=_ascii_safe(output.strip()),
        node_name=node_name,
        node_description=node_description,
        fields=tuple(fields),
        missing_fields=missing_fields,
        empty_fields=empty_fields,
        missing_required_terms=missing_required_terms,
        forbidden_field_hits=tuple(forbidden_hits),
        format_errors=tuple(format_errors),
        outside_present=outside_present,
    )


def build_codex_lmstudio_command(
    *,
    workspace: str | Path,
    output_path: str | Path,
    codex_executable: str = "codex.cmd",
    launch_mode: str = "isolated",
) -> tuple[str, ...]:
    command = [
        codex_executable,
        "-a",
        "never",
        "exec",
        "--oss",
        "--local-provider",
        "lmstudio",
        "-C",
        str(workspace),
    ]
    if launch_mode == "isolated":
        command.append("--skip-git-repo-check")
    command.extend(("-s", "read-only", "--ephemeral", "--output-last-message", str(output_path), "-"))
    return tuple(command)


def run_codex_lmstudio_worker(
    *,
    prompt: str,
    output_path: str | Path,
    repo_root: str | Path,
    launch_mode: str = "isolated",
    codex_executable: str = "codex.cmd",
    timeout: float = 180.0,
    expected_node: str = "InferenceJobResult",
    required_fields: tuple[str, ...] = DEFAULT_INFERENCE_FIELDS,
    required_terms: tuple[str, ...] = DEFAULT_CONTROLLED_EXPLOSION_TERMS,
    forbidden_field_terms: tuple[str, ...] = DEFAULT_FORBIDDEN_CONTEXT_TERMS,
) -> CodexLMStudioWorkerRun:
    root = Path(repo_root).resolve()
    output = Path(output_path)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    if launch_mode == "project-root":
        workspace = root
    elif launch_mode == "isolated":
        workspace = Path(tempfile.mkdtemp(prefix="sop_lmstudio_worker_"))
    else:
        raise ValueError("launch_mode must be isolated or project-root")
    command = build_codex_lmstudio_command(
        workspace=workspace,
        output_path=output,
        codex_executable=codex_executable,
        launch_mode=launch_mode,
    )
    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    output_text = output.read_text(encoding="utf-8") if output.exists() else ""
    validation = validate_sop_worker_output(
        output_text,
        expected_node=expected_node,
        required_fields=required_fields,
        required_terms=required_terms,
        forbidden_field_terms=forbidden_field_terms,
    )
    run_id = "codex_lmstudio_worker_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return CodexLMStudioWorkerRun(
        run_id=run_id,
        launch_mode=launch_mode,
        workspace=str(workspace),
        output_path=str(output),
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        output_text=output_text,
        validation=validation,
    )


def list_lm_studio_models(endpoint: str = DEFAULT_ENDPOINT, timeout: float = 10.0) -> tuple[str, ...]:
    url = endpoint.rstrip("/") + "/models"
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    models = tuple(item.get("id", "") for item in payload.get("data", ()) if item.get("id"))
    return models


def choose_default_model(models: tuple[str, ...]) -> str:
    for model in models:
        if "embed" not in model.lower():
            return model
    return models[0] if models else ""


def run_lm_studio_completion(
    *,
    endpoint: str,
    model: str,
    prompt: str,
    timeout: float = 60.0,
    max_tokens: int = 700,
) -> str:
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a local LM Studio worker. Codex is the operational host. "
                    "Return proposed text only. Do not claim file edits, command launches, commits, hidden state access, or integration."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    choices = response_payload.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content", "")).strip()


def run_lm_studio_benchmark(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = "",
    cases: tuple[BenchmarkCase, ...] | None = None,
    timeout: float = 60.0,
    max_tokens: int = 700,
    operational_host: str = DEFAULT_OPERATIONAL_HOST,
) -> BenchmarkReport:
    started = _utc_now()
    report_id = "lm_studio_agent_benchmark_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outside: list[str] = [
        "benchmark is non-mutating and measures narrow SOP worker behavior",
        "local model output remains proposal text until Codex review",
    ]
    try:
        available_models = list_lm_studio_models(endpoint=endpoint, timeout=min(timeout, 15.0))
        provider_available = bool(available_models)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        available_models = ()
        provider_available = False
        outside.append(f"provider probe failed: {error}")

    selected_model = model or choose_default_model(available_models)
    benchmark_cases = cases or default_benchmark_cases()
    results: list[BenchmarkCaseResult] = []
    if not provider_available or not selected_model:
        for case in benchmark_cases:
            error = "provider unavailable or no non-embedding model selected"
            results.append(
                BenchmarkCaseResult(
                    case=case,
                    model=selected_model or "none",
                    response_text="",
                    latency_ms=0,
                    score=BenchmarkScore(
                        score=0,
                        band="blocked",
                        missing_required=case.required_terms,
                        forbidden_hits=(),
                        format_hits=(),
                        outside_present=True,
                        task_fit=False,
                    ),
                    error=error,
                )
            )
    else:
        for case in benchmark_cases:
            start = time.perf_counter()
            try:
                response_text = run_lm_studio_completion(
                    endpoint=endpoint,
                    model=selected_model,
                    prompt=case.prompt,
                    timeout=timeout,
                    max_tokens=max_tokens,
                )
                error = ""
            except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                response_text = ""
                error = str(exc)
            latency_ms = round((time.perf_counter() - start) * 1000)
            score = score_output(case, response_text) if response_text else BenchmarkScore(
                score=0,
                band="blocked",
                missing_required=case.required_terms,
                forbidden_hits=(),
                format_hits=(),
                outside_present=True,
                task_fit=False,
            )
            results.append(
                BenchmarkCaseResult(
                    case=case,
                    model=selected_model,
                    response_text=response_text,
                    latency_ms=latency_ms,
                    score=score,
                    error=error,
                )
            )

    completed = _utc_now()
    return BenchmarkReport(
        report_id=report_id,
        endpoint=endpoint,
        model=selected_model or "none",
        operational_host=operational_host,
        provider_available=provider_available,
        available_models=available_models,
        case_results=tuple(results),
        started_at_utc=started,
        completed_at_utc=completed,
        outside=tuple(outside),
    )


def write_benchmark_report(report: BenchmarkReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.render() + "\n", encoding="ascii")
    return path


def _contains_forbidden(term: str, lower_output: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(term.lower())}(?![A-Za-z0-9_])"
    return re.search(pattern, lower_output) is not None


def _is_hollow_field_value(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    hollow_values = {
        "...",
        "todo",
        "tbd",
        "n/a",
        "na",
        "none",
        "placeholder",
        "<value>",
    }
    return normalized in hollow_values or normalized.startswith("...")


def _label_has_content(output: str, label: str, labels: tuple[str, ...]) -> bool:
    lines = output.splitlines()
    label_pattern = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.*)$", re.IGNORECASE)
    any_label_pattern = re.compile(
        rf"^\s*(?:{'|'.join(re.escape(candidate) for candidate in labels)})\s*:",
        re.IGNORECASE,
    )
    for index, line in enumerate(lines):
        match = label_pattern.match(line)
        if not match:
            continue
        if match.group(1).strip():
            return True
        for continuation in lines[index + 1 :]:
            if any_label_pattern.match(continuation):
                return False
            if continuation.strip():
                return True
        return False
    return False


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


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _list_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
