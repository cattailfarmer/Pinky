from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_periphery_continuity_run, parse_periphery_run_frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP periphery-continuity run record.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--run-id", default="periphery_continuity_run", help="Stable run id.")
    parser.add_argument("--focus-subject", required=True, help="Focus subject being run.")
    parser.add_argument("--direction", required=True, help="Visible forward direction of the focus path.")
    parser.add_argument("--horizon", default="", help="Visible horizon hint for the path.")
    parser.add_argument("--impulse", default="", help="Visible impulse carried through the run.")
    parser.add_argument(
        "--frame",
        action="append",
        default=[],
        required=True,
        help="Frame as frame_id|focus_observation|direction[|periphery][|stable_markers][|evidence]. Repeatable.",
    )
    parser.add_argument("--output", help="Optional output .sop path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact run record.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    run = build_periphery_continuity_run(
        run_id=args.run_id,
        focus_subject=args.focus_subject,
        run_direction=args.direction,
        frames=tuple(parse_periphery_run_frame(value) for value in args.frame),
        impulse=args.impulse,
        horizon_hint=args.horizon,
    )
    rendered = run.to_hypergraph().render() if args.graph else run.render()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
