from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_inference_state_trace


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP-HG inference state trace re-entry packet.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--base-ref", default="HEAD", help="Starting Git ref.")
    parser.add_argument("--head-ref", default="WORKTREE", help="Ending Git ref or WORKTREE.")
    parser.add_argument("--trace-id", default="inference_state_trace", help="Stable trace id.")
    parser.add_argument("--target-moment", required=True, help="Moment or turn being reconstructed.")
    parser.add_argument("--question", default="", help="Question the re-entry packet should resolve.")
    parser.add_argument("--model-key", default="model_service_unspecified", help="Model or service key for determinism boundary.")
    parser.add_argument("--sop-state-ref", action="append", default=[], help="SOP state file to load for re-entry.")
    parser.add_argument("--narrative-ref", action="append", default=[], help="Narrative or periphery record for re-entry.")
    parser.add_argument("--planned-ref", action="append", default=[], help="Planned specification or task reference.")
    parser.add_argument("--weight-ref", action="append", default=[], help="Weight intersection, bookmark, or scale reference.")
    parser.add_argument("--missing-input", action="append", default=None, help="Known missing input that blocks exact hidden replay.")
    parser.add_argument("--output", required=True, help="Output .hg.sop path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    trace = build_inference_state_trace(
        root,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        target_moment=args.target_moment,
        sop_state_refs=tuple(args.sop_state_ref),
        narrative_refs=tuple(args.narrative_ref),
        planned_specification_refs=tuple(args.planned_ref),
        weight_intersection_refs=tuple(args.weight_ref),
        question=args.question,
        model_key=args.model_key,
        known_missing_inputs=tuple(args.missing_input) if args.missing_input is not None else (
            "hidden activations",
            "sampling seed",
            "unlogged system context",
        ),
        trace_id=args.trace_id,
    )
    graph = trace.to_hypergraph()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(graph.render() + "\n", encoding="utf-8")
    print(graph.render())


if __name__ == "__main__":
    main()
