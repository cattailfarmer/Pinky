from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.lambda_oscilloscope import lambda_oscilloscope_probe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit finite Lambda log-Fourier oscilloscope traces with explicit cutoff and window policy."
    )
    parser.add_argument("--sigma", action="append", help="Sigma value. May be repeated.")
    parser.add_argument("--t-min", default="0", help="Minimum nonnegative t.")
    parser.add_argument("--t-max", default="30", help="Maximum t.")
    parser.add_argument("--step", default="1", help="T step.")
    parser.add_argument("--prime-power-bound", type=int, default=100, help="Maximum prime power q <= N.")
    parser.add_argument("--window", choices=["hard", "fejer"], default="hard", help="Finite cutoff window.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--include-terms", action="store_true", help="Include per-prime-power phasor term rows.")
    parser.add_argument("--skip-comparison", action="store_true", help="Skip comparison to -zeta'(s)/zeta(s).")
    parser.add_argument("--max-samples", type=int, default=1000, help="Maximum t samples per sigma.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = lambda_oscilloscope_probe(
        sigmas=args.sigma,
        t_min=args.t_min,
        t_max=args.t_max,
        step=args.step,
        prime_power_bound=args.prime_power_bound,
        window=args.window,
        dps=args.dps,
        include_terms=args.include_terms,
        compare_exact=not args.skip_comparison,
        max_samples=args.max_samples,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
