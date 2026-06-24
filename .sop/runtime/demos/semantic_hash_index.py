from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import PeripheryImpression, build_semantic_hash_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP-HG semantic hash index.")
    parser.add_argument("--root", default=".", help="Repository root to index.")
    parser.add_argument("--index-id", default="semantic_hash_index", help="Stable index id.")
    parser.add_argument("--output", required=True, help="Output .hg.sop path.")
    parser.add_argument("--narrative-subject", default="periphery_repository", help="Narrative subject for the optional impression.")
    parser.add_argument("--periphery-term", action="append", default=[], help="Peripheral term to record as an unstable impression.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    impressions = tuple(
        PeripheryImpression(
            narrative_subject=args.narrative_subject,
            periphery_term=term,
            relation_back="out-of-focus association around semantic hash indexing",
            hiding_behind="primary attention formation",
            turned_aspect="hash pointer plus semantic landscape",
            nearby_association="periphery repository",
            weight=3,
        )
        for term in args.periphery_term
    )
    index = build_semantic_hash_index(root, index_id=args.index_id, impressions=impressions)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(index.render(), encoding="utf-8")
    print(index.render())


if __name__ == "__main__":
    main()
