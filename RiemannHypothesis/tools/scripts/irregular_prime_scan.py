from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.irregular_primes import irregular_prime_scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan bounded primes for irregular-prime Bernoulli numerator divisibility.")
    parser.add_argument("--limit", type=int, default=200, help="Inclusive prime bound.")
    parser.add_argument("--include-regular", action="store_true", help="Include regular odd primes in the output rows.")
    parser.add_argument("--dps", type=int, default=80, help="Recorded decimal precision metadata.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = irregular_prime_scan(limit=args.limit, include_regular=args.include_regular, dps=args.dps)
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
