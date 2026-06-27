from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.exponential_forms import coefficient_power_shift_probe


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded modular probe for coefficient * power_base^N + shift(N) forms.")
    parser.add_argument("--coefficient", type=int, required=True, help="Multiplicative coefficient.")
    parser.add_argument("--power-base", type=int, required=True, help="Base being raised to each power.")
    parser.add_argument("--power", type=int, action="append", required=True, help="Power N. May be repeated.")
    parser.add_argument("--fixed-shift", type=int, action="append", default=None, help="Fixed additive shift. May be repeated.")
    parser.add_argument(
        "--shift-mode",
        choices=["plus_n", "minus_n", "n_plus_1", "one_minus_n", "minus_n_minus_1"],
        action="append",
        default=None,
        help="N-dependent shift mode. May be repeated.",
    )
    parser.add_argument("--small-factor-limit", type=int, default=100000, help="Bound for small prime divisor search.")
    parser.add_argument("--max-hits", type=int, default=10, help="Max divisors reported per expression.")
    parser.add_argument("--dps", type=int, default=80, help="Recorded decimal precision metadata.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = coefficient_power_shift_probe(
        coefficient=args.coefficient,
        power_base=args.power_base,
        powers=args.power,
        fixed_shifts=args.fixed_shift,
        shift_modes=args.shift_mode,
        small_factor_limit=args.small_factor_limit,
        max_hits=args.max_hits,
        dps=args.dps,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
