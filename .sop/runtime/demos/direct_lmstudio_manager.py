from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import (
    DEFAULT_LM_STUDIO_ENDPOINT,
    build_direct_lmstudio_manager_context,
    run_direct_lmstudio_manager,
    write_direct_lmstudio_manager_context,
    write_direct_lmstudio_manager_run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or dry-run the direct LM Studio SOP manager lane.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--endpoint", default=DEFAULT_LM_STUDIO_ENDPOINT, help="LM Studio OpenAI-compatible endpoint.")
    parser.add_argument("--model", default="", help="Model id. Defaults to WorkspaceState or provider default.")
    parser.add_argument("--candidate-id", default="direct_lmstudio_endpoint_manager_runner_001")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--max-chars-per-source", type=int, default=5000)
    parser.add_argument("--send", action="store_true", help="Call LM Studio. Without this flag only writes the context stream.")
    parser.add_argument("--context-output", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    capture_root = root / ".sop" / "workspaces" / "codex_lmstudio_orchestrator" / "captures"
    context_output = Path(args.context_output) if args.context_output else capture_root / "direct_lmstudio_endpoint_manager_runner_001_context.sop"
    output = Path(args.output) if args.output else capture_root / "direct_lmstudio_endpoint_manager_runner_001_output.sop"
    if not context_output.is_absolute():
        context_output = root / context_output
    if not output.is_absolute():
        output = root / output

    context = build_direct_lmstudio_manager_context(
        root=root,
        endpoint=args.endpoint,
        model=args.model,
        candidate_id=args.candidate_id,
        max_chars_per_source=args.max_chars_per_source,
    )
    write_direct_lmstudio_manager_context(context, context_output)
    run = run_direct_lmstudio_manager(
        root=root,
        endpoint=args.endpoint,
        model=args.model,
        candidate_id=args.candidate_id,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
        dry_run=not args.send,
        max_chars_per_source=args.max_chars_per_source,
        context_stream=context,
    )
    write_direct_lmstudio_manager_run(run, output)
    print(run.render())
    print("")
    print(f"wrote context: {context_output}")
    print(f"wrote capture: {output}")
    return 0 if (not args.send or run.accepted or run.validation.integration_disposition == "blocked_outside") else 2


if __name__ == "__main__":
    raise SystemExit(main())
