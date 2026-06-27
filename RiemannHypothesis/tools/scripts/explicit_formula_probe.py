from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.explicit_formula import explicit_formula_probe


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare psi(x) with bounded explicit-formula zero-pair sums.")
    parser.add_argument("--x", type=int, action="append", help="Sample point. May be repeated.")
    parser.add_argument("--max-x", type=int, default=1000, help="Max generated sample point when --x is omitted.")
    parser.add_argument("--count", type=int, default=6, help="Generated sample count when --x is omitted.")
    parser.add_argument("--zero-count", type=int, action="append", help="Zero pair count. May be repeated.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--include-zero-terms", action="store_true", help="Include individual zero-pair term rows.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = explicit_formula_probe(
        points=args.x,
        max_x=args.max_x,
        count=args.count,
        zero_counts=args.zero_count,
        dps=args.dps,
        include_zero_terms=args.include_zero_terms,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
