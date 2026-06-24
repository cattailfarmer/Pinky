from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_operating_loop_tick, write_operating_loop_tick


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a semantic cognition operating-loop tick.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--focus-subject", required=True)
    parser.add_argument("--completed-step", required=True)
    parser.add_argument("--proof-state", required=True, choices=("none", "captured", "validated", "committed", "pushed", "blocked"))
    parser.add_argument("--next-step", default="")
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--tick-id", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    tick = build_operating_loop_tick(
        focus_subject=args.focus_subject,
        completed_step=args.completed_step,
        proof_state=args.proof_state,
        next_step=args.next_step,
        evidence_refs=tuple(args.evidence_ref),
        outside=tuple(args.outside),
        tick_id=args.tick_id,
    )
    output = Path(args.output) if args.output else root / ".sop" / "events" / "operating_loop" / f"{tick.safe_id}.sop"
    if not output.is_absolute():
        output = root / output
    write_operating_loop_tick(tick, output)
    print(tick.render())
    print("")
    print(f"wrote: {output}")
    return 0 if tick.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
