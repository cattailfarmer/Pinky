from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import WorkerJob, create_turn_spool, default_workers


def _worker(value: str) -> WorkerJob:
    parts = value.split(":", 3)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("worker must be id:lane:status:objective")
    return WorkerJob(parts[0], parts[1], parts[3], status=parts[2])


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a Codex-master turn spool and static hub tree.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--turn-id", default="spool_master_turn")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--narrative-token", required=True)
    parser.add_argument("--worker", action="append", type=_worker, default=None)
    args = parser.parse_args()

    spool = create_turn_spool(
        repo_root=args.root,
        turn_id=args.turn_id,
        objective=args.objective,
        narrative_token=args.narrative_token,
        workers=tuple(args.worker) if args.worker else default_workers(),
    )
    print(spool.render_sop())
    print("& [SpoolHubOutput] is the static worker hub")
    print(f"  + [turn_root] is {spool.root}")
    print(f"  + [index_html] is {Path(spool.root) / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
