from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_seven_fold_pants_frame, parse_correlation_cell, parse_fold_leg


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a SevenFoldPantsCorrelationFrame SOP or SOP-HG record.")
    parser.add_argument("--frame-id", default="seven_fold_pants_frame")
    parser.add_argument("--subject-surface", required=True)
    parser.add_argument("--purpose", default="")
    parser.add_argument("--shared-boundary", default="visible subject surface")
    parser.add_argument("--correlation", action="append", default=[], help="cell_id|label|heat|salience|confidence[|source_ref][|caution_load]")
    parser.add_argument("--fold-leg", action="append", default=[], help="leg_id|target_cell|relation_type|heat|confidence|source_anchor[|central_anchor][|dimension][|outside]")
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--output", help="Optional output path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact frame.")
    args = parser.parse_args()

    frame = build_seven_fold_pants_frame(
        frame_id=args.frame_id,
        subject_surface=args.subject_surface,
        purpose=args.purpose,
        shared_boundary=args.shared_boundary,
        correlations=tuple(parse_correlation_cell(value) for value in args.correlation),
        fold_legs=tuple(parse_fold_leg(value) for value in args.fold_leg),
        outside=tuple(args.outside),
    )
    rendered = frame.to_hypergraph().render() if args.graph else frame.render()
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
