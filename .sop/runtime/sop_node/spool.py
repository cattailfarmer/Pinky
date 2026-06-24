from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


VALID_LANES = {"lm_studio_cli", "codex_cli", "manual"}
VALID_STATUSES = {"queued", "launch_ready", "launched", "completed", "blocked", "failed", "deferred"}


@dataclass(frozen=True)
class WorkerJob:
    worker_id: str
    lane: str
    objective: str
    status: str = "queued"
    prompt_packet: str = ""
    launch_command: str = ""
    result_file: str = "result.sop"
    attention_frame: str = ""

    def __post_init__(self) -> None:
        if self.lane not in VALID_LANES:
            raise ValueError(f"unknown worker lane: {self.lane}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"unknown worker status: {self.status}")

    @property
    def safe_id(self) -> str:
        return _safe_key(self.worker_id)

    def render_sop(self) -> str:
        return "\n".join(
            [
                "Subject: Worker Job",
                "",
                f"& [WorkerJob_{self.safe_id}] is a turn-spool worker record",
                f"  + [worker_id] is {self.worker_id}",
                f"  + [lane] is {self.lane}",
                f"  + [objective] is {self.objective}",
                f"  + [status] is {self.status}",
                f"  + [prompt_packet] is {self.prompt_packet or 'prompt.md'}",
                f"  + [launch_command] is {self.launch_command or 'not configured'}",
                f"  + [result_file] is {self.result_file}",
                f"  + [attention_frame] is {self.attention_frame or 'none'}",
                "  = must: inspect launch_command before execution",
                "  - never: infer completion from launch alone",
                "",
            ]
        )


@dataclass(frozen=True)
class TurnSpool:
    turn_id: str
    objective: str
    master: str
    narrative_token: str
    workers: tuple[WorkerJob, ...]
    created_utc: str
    root: str

    @property
    def safe_id(self) -> str:
        return _safe_key(self.turn_id)

    @property
    def ready(self) -> bool:
        return bool(self.turn_id and self.objective and self.master and self.workers)

    def render_sop(self) -> str:
        lines = [
            "Subject: Turn Spool",
            "",
            f"& [TurnSpool_{self.safe_id}] is a Codex-master turn spool",
            f"  + [turn_id] is {self.turn_id}",
            f"  + [objective] is {self.objective}",
            f"  + [master] is {self.master}",
            f"  + [narrative_token] is {self.narrative_token}",
            f"  + [created_utc] is {self.created_utc}",
            f"  + [root] is {self.root}",
            f"  + [worker_count] is {len(self.workers)}",
        ]
        for worker in self.workers:
            lines.append(f"  + [worker_{worker.safe_id}] is {worker.lane}:{worker.status}:{worker.objective}")
        lines.extend(
            [
                "",
                "  = must: render hub before launch",
                "  = must: keep launch policy explicit",
                "  - never: launch workers silently",
                "",
            ]
        )
        return "\n".join(lines)


def create_turn_spool(
    *,
    repo_root: str | Path,
    turn_id: str,
    objective: str,
    narrative_token: str,
    workers: tuple[WorkerJob, ...],
    master: str = "Codex",
) -> TurnSpool:
    root = Path(repo_root) / "spool" / "turns" / _safe_key(turn_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "workers").mkdir(exist_ok=True)
    (root / "artifacts").mkdir(exist_ok=True)
    created = datetime.now(UTC).isoformat()
    spool = TurnSpool(
        turn_id=turn_id,
        objective=objective,
        master=master,
        narrative_token=narrative_token,
        workers=workers,
        created_utc=created,
        root=str(root),
    )
    (root / "TurnSpool.sop").write_text(spool.render_sop(), encoding="utf-8")
    for worker in workers:
        worker_root = root / "workers" / worker.safe_id
        worker_root.mkdir(exist_ok=True)
        (worker_root / "WorkerJob.sop").write_text(worker.render_sop(), encoding="utf-8")
        (worker_root / (worker.prompt_packet or "prompt.md")).write_text(
            _render_prompt(spool, worker),
            encoding="utf-8",
        )
    render_hub(root, spool)
    return spool


def render_hub(root: str | Path, spool: TurnSpool) -> str:
    root_path = Path(root)
    rows = []
    for worker in spool.workers:
        worker_dir = f"workers/{worker.safe_id}"
        rows.append(
            "\n".join(
                [
                    "<li>",
                    f"<details open><summary><span class=\"badge {worker.status}\">{html.escape(worker.status)}</span> "
                    f"{html.escape(worker.worker_id)} <span class=\"lane\">{html.escape(worker.lane)}</span></summary>",
                    "<ul>",
                    f"<li><strong>Objective:</strong> {html.escape(worker.objective)}</li>",
                    f"<li><a href=\"{worker_dir}/WorkerJob.sop\">WorkerJob.sop</a></li>",
                    f"<li><a href=\"{worker_dir}/{html.escape(worker.prompt_packet or 'prompt.md')}\">Prompt packet</a></li>",
                    f"<li>Launch command: <code>{html.escape(worker.launch_command or 'not configured')}</code></li>",
                    f"<li>Result slot: <code>{html.escape(worker.result_file)}</code></li>",
                    "</ul>",
                    "</details>",
                    "</li>",
                ]
            )
        )
    html_text = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{html.escape(spool.turn_id)} Spool Hub</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 2rem; color: #20242a; background: #f7f7f4; }}
    main {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ font-size: 1.8rem; margin-bottom: .25rem; }}
    .meta {{ color: #5b626d; margin-bottom: 1.5rem; }}
    .tree {{ background: #fff; border: 1px solid #d8d8d0; padding: 1rem 1.25rem; border-radius: 6px; }}
    ul {{ line-height: 1.7; }}
    details {{ margin: .4rem 0; }}
    summary {{ cursor: pointer; }}
    .badge {{ display: inline-block; min-width: 5.5rem; text-align: center; border-radius: 999px; padding: .1rem .45rem; font-size: .78rem; margin-right: .4rem; background: #e4e7eb; }}
    .queued {{ background: #e7edf7; }}
    .launch_ready {{ background: #e7f5e8; }}
    .blocked, .failed {{ background: #f8e1df; }}
    .completed {{ background: #dff4ea; }}
    .deferred {{ background: #eee8f7; }}
    .lane {{ color: #6a4a00; font-size: .86rem; }}
    code {{ background: #f0f0ea; padding: .1rem .25rem; border-radius: 3px; }}
    a {{ color: #245f9c; }}
  </style>
</head>
<body>
<main>
  <h1>{html.escape(spool.turn_id)} Spool Hub</h1>
  <div class=\"meta\">Master: {html.escape(spool.master)} | Created: {html.escape(spool.created_utc)}</div>
  <section class=\"tree\">
    <h2>Turn</h2>
    <p>{html.escape(spool.objective)}</p>
    <p><strong>Narrative token:</strong> {html.escape(spool.narrative_token)}</p>
    <h2>Worker Tree</h2>
    <ul>
      {''.join(rows)}
    </ul>
  </section>
</main>
</body>
</html>
"""
    output = root_path / "index.html"
    output.write_text(html_text, encoding="utf-8")
    return str(output)


def default_workers() -> tuple[WorkerJob, ...]:
    return (
        WorkerJob(
            "lm_studio_local_model",
            "lm_studio_cli",
            "Local model reflection lane through LM Studio-compatible API.",
            status="blocked",
            launch_command="blocked: LM Studio launch policy not configured",
        ),
        WorkerJob(
            "codex_cli_worker",
            "codex_cli",
            "Additional Codex CLI worker lane for bounded job packets.",
            status="deferred",
            launch_command="deferred: explicit launch policy required",
        ),
        WorkerJob(
            "manual_review",
            "manual",
            "Human review lane for inspecting hub tree and launch commands.",
            status="queued",
        ),
    )


def _render_prompt(spool: TurnSpool, worker: WorkerJob) -> str:
    return "\n".join(
        [
            f"# {worker.worker_id}",
            "",
            f"Turn: {spool.turn_id}",
            f"Master: {spool.master}",
            f"Objective: {worker.objective}",
            f"Narrative token: {spool.narrative_token}",
            "",
            "Do not claim launch or completion unless the worker process actually ran and produced a captured result.",
            "",
        ]
    )


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"
