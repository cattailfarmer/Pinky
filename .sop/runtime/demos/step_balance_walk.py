from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_step_balance_walk, parse_step_balance_observation


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP step-balance walk record.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--walk-id", default="step_balance_walk", help="Stable walk id.")
    parser.add_argument("--focus-subject", required=True, help="Focus subject being walked.")
    parser.add_argument("--job-need", required=True, help="Purpose for the walk.")
    parser.add_argument("--impulse", default="", help="Visible impulse carried through the walk.")
    parser.add_argument(
        "--step",
        action="append",
        default=[],
        required=True,
        help=(
            "Step as step_id|action|balance_score|next_step[|signals][|correction][|settled][|evidence][|periphery]. "
            "Repeatable."
        ),
    )
    parser.add_argument("--output", help="Optional output .sop path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact walk record.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    walk = build_step_balance_walk(
        walk_id=args.walk_id,
        focus_subject=args.focus_subject,
        job_need=args.job_need,
        impulse=args.impulse,
        observations=tuple(parse_step_balance_observation(value) for value in args.step),
    )
    rendered = walk.to_hypergraph().render() if args.graph else walk.render()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
