from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.prime_families import DEFAULT_SPECIAL_PRIME_SEEDS, special_prime_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile special-prime family facts for finite periphery inquiry.")
    parser.add_argument(
        "--prime",
        "-p",
        type=int,
        action="append",
        help="Prime or integer to profile. May be repeated. Defaults to the Fermat-prime/641 seed set.",
    )
    parser.add_argument("--max-fermat-n", type=int, default=8, help="Largest Fermat number index to test divisibility against.")
    parser.add_argument("--dps", type=int, default=80, help="Recorded decimal precision metadata.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    primes = args.prime if args.prime else DEFAULT_SPECIAL_PRIME_SEEDS
    payload = special_prime_profile(primes=primes, max_fermat_n=args.max_fermat_n, dps=args.dps)
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
