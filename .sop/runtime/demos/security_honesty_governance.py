from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import (
    build_security_honesty_governance_record,
    parse_candidate_action,
    parse_candidate_claim,
    parse_feedback_signal,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a SecurityHonestyGovernance SOP or SOP-HG record.")
    parser.add_argument("--governance-id", default="security_honesty_governance")
    parser.add_argument("--focal-subject", required=True)
    parser.add_argument("--return-anchor", required=True)
    parser.add_argument(
        "--claim",
        action="append",
        default=[],
        help="claim_id|claim|support[|assumption][|contradiction][|uncertainty][|truth_disposition]",
    )
    parser.add_argument(
        "--action",
        action="append",
        default=[],
        help="action_id|action|risk|admissible_path[|security_disposition]",
    )
    parser.add_argument(
        "--feedback",
        action="append",
        default=[],
        help="feedback_id|feedback_source|recursion_depth|return_anchor|evidence_refresh[|resonance_condition][|guard_disposition][|resonance_cap]",
    )
    parser.add_argument("--outside", action="append", default=[])
    parser.add_argument("--output", help="Optional output path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact frame.")
    args = parser.parse_args()

    record = build_security_honesty_governance_record(
        governance_id=args.governance_id,
        focal_subject=args.focal_subject,
        return_anchor=args.return_anchor,
        claims=tuple(parse_candidate_claim(value) for value in args.claim),
        actions=tuple(parse_candidate_action(value) for value in args.action),
        feedback=tuple(parse_feedback_signal(value) for value in args.feedback),
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
