from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_hyperbolic_pants_topology_map, parse_pants_leg, parse_topology_cell


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a HyperbolicPantsAttentionMap SOP-HG topology record.")
    parser.add_argument("--map-id", default="hyperbolic_pants_topology_map")
    parser.add_argument("--focus-subject", required=True)
    parser.add_argument("--purpose", default="")
    parser.add_argument("--focal-term", action="append", default=[])
    parser.add_argument("--cell", action="append", default=[], help="cell_id|label|dimension|relation_to_focus|density[|salience][|source_ref]")
    parser.add_argument("--leg", action="append", default=[], help="leg_id|from_cell|to_cell|relation_type[|weight][|boundary]")
    parser.add_argument("--scale", default="")
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--output", help="Optional output path.")
    parser.add_argument("--compact", action="store_true", help="Render compact SOP source record instead of SOP-HG graph.")
    args = parser.parse_args()

    topology_map = build_hyperbolic_pants_topology_map(
        map_id=args.map_id,
        focus_subject=args.focus_subject,
        focal_terms=tuple(args.focal_term),
        periphery_cells=tuple(parse_topology_cell(value) for value in args.cell),
        pants_legs=tuple(parse_pants_leg(value) for value in args.leg),
        scale=args.scale,
        purpose=args.purpose,
        outside=tuple(args.outside),
    )
    rendered = topology_map.render() if args.compact else topology_map.to_hypergraph().render()
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
