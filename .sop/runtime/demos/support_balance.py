from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_support_balance, parse_support_probe


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP-HG carried support balance graph.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--balance-id", default="carried_support_balance", help="Stable balance id.")
    parser.add_argument("--output", required=True, help="Output .hg.sop path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    balance = build_support_balance(
        balance_id=args.balance_id,
        active_subject="carried support balance while implementing attention rails",
        subject_terms=("attention", "support", "balance", "native", "carried", "periphery", "association"),
        periphery_terms=("rails", "walking", "supports", "native", "perspective", "association", "balance"),
        probes=(
            parse_support_probe(
                support_id="periphery_fit_sensor",
                support_name="Periphery fit as support sensor",
                terms=("periphery", "native", "association", "support"),
            ),
            parse_support_probe(
                support_id="sjs_source_preservation",
                support_name="SJS and source preservation",
                terms=("specification", "governance", "source", "preservation"),
                carried_from="C:\\Project\\ReasoningFramework\\AGENTS.md",
            ),
            parse_support_probe(
                support_id="sop_hypergraph_record",
                support_name="SOP-HG support record shape",
                terms=("support", "hypergraph", "node", "edge", "balance"),
                carried_from="F:\\.sop\\platform\\SOPHypergraphRecord.sop",
            ),
            parse_support_probe(
                support_id="walking_rails_metaphor",
                support_name="Walking with rails metaphor",
                terms=("walking", "rails", "gait"),
            ),
            parse_support_probe(
                support_id="worker_spool_expansion",
                support_name="Worker spool expansion",
                terms=("worker", "spool", "repo", "terminal"),
            ),
            parse_support_probe(
                support_id="forced_framework_projection",
                support_name="Forced framework projection",
                terms=("framework", "projection", "override"),
                carried_from="agent habit risk",
                contradicts=True,
            ),
        ),
    )
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = balance.to_hypergraph().render()
    output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
