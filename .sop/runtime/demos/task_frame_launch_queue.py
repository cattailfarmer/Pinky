from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_lmstudio_task_frame_candidate, build_task_frame_launch_queue, write_task_frame_launch_queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit an inspectable task-frame launch queue.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--queue-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--task-frame-id", required=True)
    parser.add_argument("--task-subject", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--prompt-packet", required=True)
    parser.add_argument("--capture-target", required=True)
    parser.add_argument("--source-ref", action="append", default=[])
    parser.add_argument("--block-reason", action="append", default=[])
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    candidate_kwargs = {}
    if args.outside:
        candidate_kwargs["outside"] = tuple(args.outside)
    candidate = build_lmstudio_task_frame_candidate(
        candidate_id=args.candidate_id,
        task_frame_id=args.task_frame_id,
        task_subject=args.task_subject,
        objective=args.objective,
        prompt_packet=args.prompt_packet,
        capture_target=args.capture_target,
        repo_root=root,
        source_refs=tuple(args.source_ref),
        block_reasons=tuple(args.block_reason),
        **candidate_kwargs,
    )
    queue = build_task_frame_launch_queue(queue_id=args.queue_id, candidates=(candidate,))
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    write_task_frame_launch_queue(queue, output)
    print(queue.render())
    print("")
    print(f"wrote: {output}")
    return 0 if queue.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
