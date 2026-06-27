from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.euler_product import euler_product_probe


def parse_sample(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise argparse.ArgumentTypeError("sample must use the form sigma,t")
    return parts[0], parts[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare finite Euler products and logarithmic-derivative weighting in Re(s) > 1."
    )
    parser.add_argument("--sample", type=parse_sample, action="append", help="Sample point as sigma,t. May be repeated.")
    parser.add_argument("--prime-bound", type=int, action="append", help="Prime or prime-power bound. May be repeated.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--include-terms", action="store_true", help="Include per-prime and per-prime-power term rows.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = euler_product_probe(
        samples=args.sample,
        prime_bounds=args.prime_bound,
        dps=args.dps,
        include_terms=args.include_terms,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
