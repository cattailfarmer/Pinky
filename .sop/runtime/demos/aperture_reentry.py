from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_aperture_reentry_springboard, parse_aperture_support, support_from_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit an aperture reentry springboard from a focal point and support draws.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--cycle-id", default="aperture_reentry_springboard")
    parser.add_argument("--focal-point", default=".sop/state/CurrentFocalPoint.sop")
    parser.add_argument("--support", action="append", default=[], help="support_id|label|source_ref|relation[|heat][|prompt_hint]")
    parser.add_argument("--support-file", action="append", default=[], help="Support source file to read as a source_anchor support.")
    parser.add_argument("--support-file-relation", default="source_anchor")
    parser.add_argument("--support-file-heat", type=int, default=4)
    parser.add_argument("--depth-adjustment", default="")
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--output", help="Optional output .sop path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact springboard.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    focal_path = Path(args.focal_point)
    if not focal_path.is_absolute():
        focal_path = root / focal_path
    supports = [parse_aperture_support(value) for value in args.support]
    for support_file in args.support_file:
        support_path = Path(support_file)
        if not support_path.is_absolute():
            support_path = root / support_path
        supports.append(
            support_from_file(
                support_path,
                relation=args.support_file_relation,
                heat=args.support_file_heat,
            )
        )
    springboard = build_aperture_reentry_springboard(
        focal_point_path=focal_path,
        supports=supports,
        cycle_id=args.cycle_id,
        depth_adjustment=args.depth_adjustment,
        outside=tuple(args.outside),
    )
    rendered = springboard.to_hypergraph().render() if args.graph else springboard.render()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
