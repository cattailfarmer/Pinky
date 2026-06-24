from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_trailing_checksum_review, parse_terms


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a trailing checksum review over a direct-focus commit.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--review-id", default="trailing_checksum_review", help="Stable review id.")
    parser.add_argument("--direct-focus-ref", default="HEAD", help="Direct-focus commit or ref to review.")
    parser.add_argument("--base-ref", help="Optional start bookend. Defaults to direct-focus-ref parent.")
    parser.add_argument("--review-turn", default="current_review_turn", help="Review turn label.")
    parser.add_argument("--planned-term", action="append", default=[], help="Planned term to compare against the commit.")
    parser.add_argument("--narrative-term", action="append", default=[], help="Narrative term to keep warm in the checksum.")
    parser.add_argument("--pathspec", action="append", default=None, help="Git pathspec to include.")
    parser.add_argument("--outside", default="", help="Comma-separated outside terms.")
    parser.add_argument("--output", help="Optional output .sop path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact review.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    review = build_trailing_checksum_review(
        root,
        review_id=args.review_id,
        direct_focus_ref=args.direct_focus_ref,
        base_ref=args.base_ref,
        review_turn=args.review_turn,
        planned_terms=tuple(args.planned_term),
        narrative_terms=tuple(args.narrative_term),
        pathspecs=tuple(args.pathspec) if args.pathspec else None,
        outside=parse_terms(args.outside) if args.outside else (),
    )
    rendered = review.to_hypergraph().render() if args.graph else review.render()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
