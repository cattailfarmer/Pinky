from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_attention_frame


def _pair(value: str) -> tuple[str, str]:
    if ":" in value:
        left, right = value.split(":", 1)
    elif "->" in value:
        left, right = value.split("->", 1)
    else:
        raise argparse.ArgumentTypeError("relation pairs must use left:right or left->right")
    return (left.strip(), right.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a SOP-HG attention layer frame.")
    parser.add_argument("narrative_moment")
    parser.add_argument("--frame-id", default="attention_frame")
    parser.add_argument("--stage", default="work_turn")
    parser.add_argument("--focus", nargs="+", required=True)
    parser.add_argument("--periphery", nargs="*", default=())
    parser.add_argument("--correlates", action="append", type=_pair, default=None)
    parser.add_argument("--causes", action="append", type=_pair, default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    frame = build_attention_frame(
        frame_id=args.frame_id,
        narrative_moment=args.narrative_moment,
        operation_stage=args.stage,
        focus_terms=tuple(args.focus),
        periphery_terms=tuple(args.periphery),
        correlation_pairs=tuple(args.correlates or ()),
        causal_pairs=tuple(args.causes or ()),
    )
    rendered = frame.render()
    print(rendered)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
        print("")
        print("& [AttentionFrameOutput] is the written SOP-HG attention frame")
        print(f"  + [path] is {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
