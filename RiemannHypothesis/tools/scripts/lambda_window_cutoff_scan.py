from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.lambda_oscilloscope import lambda_window_cutoff_scan


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan Lambda Oscilloscope extrema across window policy and cutoff growth."
    )
    parser.add_argument("--sigma", action="append", help="Sigma value greater than or equal to 0. May be repeated.")
    parser.add_argument("--t-min", default="0", help="Minimum nonnegative t.")
    parser.add_argument("--t-max", default="30", help="Maximum t.")
    parser.add_argument("--step", default="0.5", help="T step.")
    parser.add_argument("--prime-power-bound", type=int, action="append", help="Prime-power cutoff N. May be repeated.")
    parser.add_argument("--window", choices=["hard", "fejer"], action="append", help="Window policy. May be repeated.")
    parser.add_argument("--stability-tolerance", help="T tolerance for stable candidate matching. Defaults to step.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--max-samples", type=int, default=1000, help="Maximum t samples per sigma.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = lambda_window_cutoff_scan(
        sigmas=args.sigma,
        t_min=args.t_min,
        t_max=args.t_max,
        step=args.step,
        prime_power_bounds=args.prime_power_bound,
        windows=args.window,
        dps=args.dps,
        max_samples=args.max_samples,
        stability_tolerance=args.stability_tolerance,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
