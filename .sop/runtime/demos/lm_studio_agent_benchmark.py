from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import (
    DEFAULT_LM_STUDIO_ENDPOINT,
    run_lm_studio_benchmark,
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
    parser.add_argument(
        "--output",
        default="",
        help="Optional output report path. Defaults to .sop/events/benchmarks/<report_id>.sop under root.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
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
