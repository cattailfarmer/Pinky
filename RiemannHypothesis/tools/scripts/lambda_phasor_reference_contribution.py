from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.euler_product import REFERENCE_T_VALUES
from rh_math.lambda_oscilloscope import lambda_phasor_reference_contribution


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate finite Lambda phasor contributions near selected reference labels."
    )
    parser.add_argument("--sigma", action="append", help="Sigma value. May be repeated.")
    parser.add_argument(
        "--reference-label",
        action="append",
        choices=sorted(REFERENCE_T_VALUES),
        help="Reference label. May be repeated. Defaults to the first three reference labels.",
    )
    parser.add_argument("--offset", action="append", help="Offset from each reference t. May be repeated.")
    parser.add_argument(
        "--prime-power-bound",
        action="append",
        type=int,
        help="Maximum prime power q <= N. May be repeated.",
    )
    parser.add_argument("--window", action="append", choices=["hard", "fejer"], help="Window. May be repeated.")
    parser.add_argument("--top-terms", type=int, default=8, help="Top terms to include per row.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = lambda_phasor_reference_contribution(
        sigmas=args.sigma,
        reference_labels=args.reference_label,
        offsets=args.offset,
        prime_power_bounds=args.prime_power_bound,
        windows=args.window,
        dps=args.dps,
        top_terms=args.top_terms,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
