from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import PeripheryImpression, build_semantic_hash_index, build_semantic_hash_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP-HG semantic hash table view.")
    parser.add_argument("--root", default=".", help="Repository root to index.")
    parser.add_argument("--index-id", default="semantic_hash_table", help="Stable index id.")
    parser.add_argument("--output", required=True, help="Output .hg.sop path.")
    parser.add_argument("--query-term", action="append", default=[], help="Term dimension for the rendered query.")
    parser.add_argument("--mode", default="permissive", choices=("exact", "strict", "permissive", "inclusive"))
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index = build_semantic_hash_index(
        root,
        index_id=args.index_id,
        impressions=(
            PeripheryImpression(
                narrative_subject="semantic_hash_table",
                periphery_term="permissive_lookup",
                relation_back="multi-dimensional semantic key retrieval",
                hiding_behind="exact hash pointer",
                turned_aspect="inclusive bucket intersection",
                nearby_association="semantic hash index",
                weight=4,
            ),
        ),
    )
    table = build_semantic_hash_table(index, table_id=f"{args.index_id}_table")
    query = {"term": tuple(args.query_term)} if args.query_term else {"term": ("periphery", "semantic")}
    graph = table.to_hypergraph(query=query, mode=args.mode)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(graph.render(), encoding="utf-8")
    print(graph.render())


if __name__ == "__main__":
    main()
