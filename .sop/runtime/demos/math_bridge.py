from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_math_bridge_map, parse_math_bridge_term


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a math bridge map for symbolic-to-formal inquiry.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--bridge-id", default="bsd_l_hand_r_hand_bridge", help="Stable bridge id.")
    parser.add_argument("--output", required=True, help="Output .sop path.")
    parser.add_argument("--hypergraph", action="store_true", help="Emit SOP-HG instead of prose SOP.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    bridge = build_math_bridge_map(
        bridge_id=args.bridge_id,
        problem_name="Birch and Swinnerton-Dyer",
        proposition=(
            "L-hand/R-hand language is useful only if it grounds analytic rank, algebraic rank, "
            "generator emergence, and leading-term data without circularly assuming BSD."
        ),
        terms=(
            parse_math_bridge_term(
                term_id="l_hand_collapse",
                symbolic_term="L-hand collapse",
                formal_object="order of vanishing of L(E,s) at the central point",
                problem_role="analytic-rank candidate",
                evidence_status="mapped_candidate",
                proof_obligations=(
                    "Define collapse without assuming analytic rank equals algebraic rank.",
                    "Show how multiplicity becomes usable information for the algebraic side.",
                ),
            ),
            parse_math_bridge_term(
                term_id="r_hand_growth",
                symbolic_term="R-hand growth",
                formal_object="Mordell-Weil generator structure of E(Q)",
                problem_role="algebraic-rank candidate",
                evidence_status="mapped_candidate",
                proof_obligations=(
                    "Define a generator-discovery or generator-accounting process.",
                    "Show why the process captures independent rational directions.",
                ),
            ),
            parse_math_bridge_term(
                term_id="surviving_rational_directions",
                symbolic_term="surviving rational directions",
                formal_object="rank of E(Q)",
                problem_role="rank bridge",
                evidence_status="mapped_candidate",
                proof_obligations=(
                    "Relate directions to independent points modulo torsion.",
                    "Avoid treating a visual direction metaphor as a rank proof.",
                ),
            ),
            parse_math_bridge_term(
                term_id="phase_corrected_field",
                symbolic_term="phase-corrected field",
                formal_object="unresolved bridge: regulator, height pairing, or leading coefficient data",
                problem_role="possible refined BSD bridge",
                evidence_status="unresolved_candidate",
                proof_obligations=(
                    "Decide whether this maps to heights, regulator, local factors, or should be retired.",
                ),
                caution="High meaning heat but not yet a defined arithmetic object.",
            ),
        ),
    )
    rendered = bridge.to_hypergraph().render() if args.hypergraph else bridge.render()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
