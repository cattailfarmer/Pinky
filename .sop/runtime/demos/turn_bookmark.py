from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_turn_bookmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP-HG turn bookmark from Git bookends.")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--base-ref", default="HEAD", help="Starting Git ref.")
    parser.add_argument("--head-ref", default="WORKTREE", help="Ending Git ref or WORKTREE.")
    parser.add_argument("--bookmark-id", default="turn_bookmark", help="Stable bookmark id.")
    parser.add_argument("--planned-term", action="append", default=[], help="Planned term to compare against changed signals.")
    parser.add_argument("--narrative-term", action="append", default=[], help="Narrative term that may open new-potential findings.")
    parser.add_argument("--pathspec", action="append", default=None, help="Git pathspec to include in the bookmark scan.")
    parser.add_argument("--output", required=True, help="Output .hg.sop path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    bookmark = build_turn_bookmark(
        root,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        planned_terms=tuple(args.planned_term),
        narrative_terms=tuple(args.narrative_term),
        pathspecs=tuple(args.pathspec) if args.pathspec else ("*.sop", ":(glob)**/*.sop", "*.py", ":(glob)**/*.py"),
        bookmark_id=args.bookmark_id,
    )
    graph = bookmark.to_hypergraph()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(graph.render() + "\n", encoding="utf-8")
    print(graph.render())


if __name__ == "__main__":
    main()
