from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.euler_product import t_axis_boundary_probe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slice finite Euler-product residuals along t at fixed sigma greater than 1."
    )
    parser.add_argument("--sigma", action="append", help="Sigma value greater than 1. May be repeated.")
    parser.add_argument("--t", action="append", help="Nonnegative imaginary ordinate t. May be repeated.")
    parser.add_argument("--prime-bound", type=int, action="append", help="Prime or prime-power bound. May be repeated.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = t_axis_boundary_probe(
        sigmas=args.sigma,
        t_values=args.t,
        prime_bounds=args.prime_bound,
        dps=args.dps,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
