from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.primes import prime_count_compare


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare finite prime counts with li(x) and truncated Riemann R.")
    parser.add_argument("--x", type=int, action="append", help="Sample point. May be repeated.")
    parser.add_argument("--max-x", type=int, default=1000, help="Max generated sample point when --x is omitted.")
    parser.add_argument("--count", type=int, default=8, help="Generated sample count when --x is omitted.")
    parser.add_argument("--terms", type=int, default=20, help="Riemann R truncation terms.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()
    payload = prime_count_compare(args.x, args.max_x, args.count, args.terms, args.dps)
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
