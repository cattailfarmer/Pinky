from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_hyperbolic_corridor_navigation, parse_corridor_frame, parse_curving_association


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a HyperbolicCorridorNavigator SOP or SOP-HG record.")
    parser.add_argument("--navigator-id", default="hyperbolic_corridor_navigator")
    parser.add_argument("--focal-subject", required=True)
    parser.add_argument("--identity-target", required=True)
    parser.add_argument("--advance-step", default="")
    parser.add_argument("--depth-budget", default="")
    parser.add_argument("--frame", action="append", default=[], help="frame_id|label|relation_role|heat|confidence|return_anchor[|source_ref][|distinctness]")
    parser.add_argument(
        "--association",
        action="append",
        default=[],
        help="association_id|source_frame|target_frame|relation_hint|heat|confidence[|status][|evidence_ref][|outside]",
    )
    parser.add_argument("--extension", action="append", default=[], help="Local awareness extension term or comma-list.")
    parser.add_argument("--entanglement", action="append", default=[], help="Entanglement field term or comma-list.")
    parser.add_argument("--identity-candidate", default="")
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--output", help="Optional output path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact frame.")
    args = parser.parse_args()

    navigation = build_hyperbolic_corridor_navigation(
        navigator_id=args.navigator_id,
        focal_subject=args.focal_subject,
        identity_resolution_target=args.identity_target,
        frames=tuple(parse_corridor_frame(value) for value in args.frame),
        associations=tuple(parse_curving_association(value) for value in args.association),
        advance_step=args.advance_step,
        depth_budget=args.depth_budget,
        local_awareness_extension=tuple(args.extension),
        entanglement_terms=tuple(args.entanglement),
        identity_clarity_candidate=args.identity_candidate,
        outside=tuple(args.outside),
    )
    rendered = navigation.to_hypergraph().render() if args.graph else navigation.render()
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
