from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_viewfinder_snapshot, parse_reweighing


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a SOP-HG viewfinder snapshot.")
    parser.add_argument("narrative_token")
    parser.add_argument("--snapshot-id", default="viewfinder_snapshot")
    parser.add_argument("--shape", required=True)
    parser.add_argument("--commit-frame", default=None)
    parser.add_argument("--previous-reflection", action="append", default=None)
    parser.add_argument("--current-observation", action="append", default=None)
    parser.add_argument("--reweigh", action="append", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    commit_frame = args.commit_frame or _head_ref(Path(__file__).resolve().parents[2])
    snapshot = build_viewfinder_snapshot(
        snapshot_id=args.snapshot_id,
        narrative_token=args.narrative_token,
        desired_shape=args.shape,
        commit_frame=commit_frame,
        previous_reflections=tuple(args.previous_reflection or ()),
        current_observations=tuple(args.current_observation or ()),
        reweighings=tuple(parse_reweighing(value) for value in (args.reweigh or ())),
    )
    rendered = snapshot.render()
    print(rendered)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
        print("")
        print("& [ViewfinderSnapshotOutput] is the written SOP-HG viewfinder snapshot")
        print(f"  + [path] is {path}")
    return 0


def _head_ref(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return "WORKTREE"
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
