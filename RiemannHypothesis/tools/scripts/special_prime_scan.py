from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.prime_families import scan_special_prime_families


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan bounded primes for selected special-prime families.")
    parser.add_argument("--limit", type=int, default=10000, help="Inclusive integer bound for prime scan.")
    parser.add_argument("--max-fermat-n", type=int, default=8, help="Largest Fermat number index to test divisibility against.")
    parser.add_argument("--include-profiles", action="store_true", help="Include per-prime profile rows in JSON output.")
    parser.add_argument("--dps", type=int, default=80, help="Recorded decimal precision metadata.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = scan_special_prime_families(
        limit=args.limit,
        max_fermat_n=args.max_fermat_n,
        include_profiles=args.include_profiles,
        dps=args.dps,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
