from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import (
    DEFAULT_LM_STUDIO_ENDPOINT,
    extract_prompt_text_from_sop,
    run_codex_lmstudio_worker,
    run_lm_studio_benchmark,
    validate_sop_worker_output,
    write_benchmark_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark LM Studio as a Codex-hosted SOP worker lane.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--endpoint", default=DEFAULT_LM_STUDIO_ENDPOINT, help="LM Studio OpenAI-compatible endpoint.")
    parser.add_argument("--model", default="", help="Model id. Defaults to the first non-embedding model.")
    parser.add_argument("--operational-host", default="codex_agent_cli", help="Operational host recorded in the report.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds.")
    parser.add_argument("--max-tokens", type=int, default=700, help="Maximum response tokens per benchmark case.")
    parser.add_argument("--validate-output", default="", help="Validate an existing captured SOP worker output file.")
    parser.add_argument("--codex-worker-prompt", default="", help="Run Codex CLI over LM Studio with this SOP prompt packet.")
    parser.add_argument(
        "--launch-mode",
        choices=("isolated", "project-root"),
        default="isolated",
        help="Launch mode for --codex-worker-prompt.",
    )
    parser.add_argument("--codex-executable", default="codex.cmd", help="Codex executable for worker launches.")
    parser.add_argument(
        "--output",
        default="",
        help="Optional output report or captured worker path. Defaults to .sop/events/benchmarks/<report_id>.sop under root.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.validate_output:
        validation = validate_sop_worker_output(Path(args.validate_output).read_text(encoding="utf-8"))
        print(validation.render(Path(args.validate_output).stem))
        raise SystemExit(0 if validation.valid else 2)

    if args.codex_worker_prompt:
        prompt_packet = Path(args.codex_worker_prompt).read_text(encoding="utf-8")
        prompt = extract_prompt_text_from_sop(prompt_packet)
        output = Path(args.output) if args.output else root / ".sop" / "events" / "benchmarks" / "codex_lmstudio_worker_output.sop"
        if not output.is_absolute():
            output = root / output
        worker_run = run_codex_lmstudio_worker(
            prompt=prompt,
            output_path=output,
            repo_root=root,
            launch_mode=args.launch_mode,
            codex_executable=args.codex_executable,
            timeout=args.timeout,
        )
        print(worker_run.render())
        raise SystemExit(0 if worker_run.functional else 2)

    report = run_lm_studio_benchmark(
        endpoint=args.endpoint,
        model=args.model,
        operational_host=args.operational_host,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
    )
    output = Path(args.output) if args.output else root / ".sop" / "events" / "benchmarks" / f"{report.report_id}.sop"
    if not output.is_absolute():
        output = root / output
    write_benchmark_report(report, output)
    print(report.render())
    print("")
    print(f"wrote: {output}")


if __name__ == "__main__":
    main()
