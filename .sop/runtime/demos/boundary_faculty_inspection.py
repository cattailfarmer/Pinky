from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_boundary_faculty_inspection_record, parse_boundary_term


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a BoundaryFacultyInspection SOP or SOP-HG record.")
    parser.add_argument("--inspection-id", default="boundary_faculty_inspection")
    parser.add_argument("--attention-subject", required=True)
    parser.add_argument("--identity-boundary", required=True)
    parser.add_argument("--protected-identity", required=True)
    parser.add_argument("--purpose", default="")
    parser.add_argument("--periphery", action="append", default=[], help="Boundary periphery term or comma-list.")
    parser.add_argument(
        "--term",
        action="append",
        default=[],
        help=(
            "term_id|term|boundary_role|subject_vector|boundary_vector|orthogonality_result|honesty_load|security_load|"
            "representation_claim|support_surface|protected_identity[|misdirection_vector][|weak_boundary_fault][|honesty_disposition][|security_alert]"
        ),
    )
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--output", help="Optional output path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact frame.")
    args = parser.parse_args()

    record = build_boundary_faculty_inspection_record(
        inspection_id=args.inspection_id,
        attention_subject=args.attention_subject,
        identity_boundary=args.identity_boundary,
        boundary_periphery=tuple(args.periphery),
        protected_identity=args.protected_identity,
        terms=tuple(parse_boundary_term(value) for value in args.term),
        purpose=args.purpose,
        outside=tuple(args.outside),
    )
    rendered = record.to_hypergraph().render() if args.graph else record.render()
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
