from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.exponential_forms import exponential_power_shift_probe


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded modular probe for base^(exponent_base^power) + shift forms.")
    parser.add_argument("--base", type=int, required=True, help="Integer base.")
    parser.add_argument("--exponent-base", type=int, required=True, help="Base of the exponent power.")
    parser.add_argument("--exponent-power", type=int, action="append", required=True, help="Exponent power. May be repeated.")
    parser.add_argument("--shift", type=int, action="append", default=None, help="Additive shift. May be repeated.")
    parser.add_argument("--small-factor-limit", type=int, default=100000, help="Bound for small prime divisor search.")
    parser.add_argument("--max-hits", type=int, default=10, help="Max divisors reported per expression.")
    parser.add_argument("--dps", type=int, default=80, help="Recorded decimal precision metadata.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = exponential_power_shift_probe(
        base=args.base,
        exponent_base=args.exponent_base,
        exponent_powers=args.exponent_power,
        shifts=args.shift or [1, 2, 4],
        small_factor_limit=args.small_factor_limit,
        max_hits=args.max_hits,
        dps=args.dps,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
