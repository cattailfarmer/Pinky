from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.distribution import prime_emergence_shell_signature
from rh_math.prime_families import special_prime_family_names


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure prime-emergence shell surface signatures.")
    parser.add_argument("--x", type=int, action="append", help="Shell endpoint. May be repeated.")
    parser.add_argument("--max-x", type=int, default=5000, help="Max generated endpoint when --x is omitted.")
    parser.add_argument("--count", type=int, default=6, help="Generated endpoint count when --x is omitted.")
    parser.add_argument("--family", choices=special_prime_family_names(), action="append", help="Family to include. May be repeated.")
    parser.add_argument("--max-fermat-n", type=int, default=8, help="Largest Fermat number index to test divisibility against.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--include-members", action="store_true", help="Include prime and family members in each shell.")
    parser.add_argument("--no-layers", action="store_true", help="Omit Lambda layer rows.")
    parser.add_argument("--max-examples", type=int, default=12, help="Maximum sieve examples per shell.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = prime_emergence_shell_signature(
        points=args.x,
        max_x=args.max_x,
        count=args.count,
        families=args.family,
        max_fermat_n=args.max_fermat_n,
        dps=args.dps,
        include_members=args.include_members,
        include_layers=not args.no_layers,
        max_examples=args.max_examples,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
