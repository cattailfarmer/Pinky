from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import (
    PeripheryImpression,
    build_semantic_correlation_graph,
    build_semantic_hash_index,
    build_semantic_hash_table,
    parse_directive,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP-HG semantic correlation graph.")
    parser.add_argument("--root", default=".", help="Repository root to index.")
    parser.add_argument("--graph-id", default="semantic_correlation_graph", help="Stable graph id.")
    parser.add_argument("--output", required=True, help="Output .hg.sop path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index = build_semantic_hash_index(
        root,
        index_id=f"{args.graph_id}_index",
        impressions=(
            PeripheryImpression(
                narrative_subject="semantic_correlation_graph",
                periphery_term="attention_directive",
                relation_back="directive tilts correlation through bucket graph",
                hiding_behind="semantic hash table",
                turned_aspect="weighted bucket overlap",
                nearby_association="attention rigging",
                weight=4,
            ),
        ),
    )
    table = build_semantic_hash_table(index, table_id=f"{args.graph_id}_table")
    directive = parse_directive(
        directive_id="attention_rigging_seed",
        purpose="Capture directive-shaped attention over semantic bucket correlations.",
        identified="attention_rigging",
        inside=("attention", "directive", "correlation"),
        boundary=("proof", "outside"),
        subject_a="semantic_hash_table",
        subject_b="attention_directive",
        tilt=(("term", "semantic"), ("term", "periphery")),
        boost=4,
    )
    graph = build_semantic_correlation_graph(
        table,
        graph_id=args.graph_id,
        directives=(directive,),
        max_correlations=32,
    )
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(graph.to_hypergraph(limit=16).render(), encoding="utf-8")
    print(graph.to_hypergraph(limit=16).render())


if __name__ == "__main__":
    main()
