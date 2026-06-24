from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_sensitivity_scan, scan_to_hypergraph, write_scan


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an SOP sensitivity scan over Git bookends.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--head-ref", default="WORKTREE")
    parser.add_argument("--scan-id", default=None)
    parser.add_argument("--pathspec", action="append", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--hypergraph-output", default=None)
    parser.add_argument("--hypergraph", action="store_true")
    args = parser.parse_args()

    scan = build_sensitivity_scan(
        args.root,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        pathspecs=tuple(args.pathspec) if args.pathspec else ("*.sop", ":(glob)**/*.sop"),
        scan_id=args.scan_id,
    )
    if args.hypergraph:
        print(scan_to_hypergraph(scan).render())
    else:
        print(scan.render())
    if args.output:
        output_path = write_scan(args.output, scan)
        print("")
        print("& [SensitivityScanOutput] is the written scan record")
        print(f"  + [path] is {output_path}")
    if args.hypergraph_output:
        graph_path = write_scan(args.hypergraph_output, scan_to_hypergraph(scan))
        print("")
        print("& [SOPHypergraphOutput] is the written SOP-HG graph record")
        print(f"  + [path] is {graph_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
