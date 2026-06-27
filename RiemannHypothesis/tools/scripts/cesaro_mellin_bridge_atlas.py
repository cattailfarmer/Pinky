from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.explicit_formula import SUPPORTED_N_DOMAIN_KERNELS, SUPPORTED_ZERO_WINDOWS, cesaro_mellin_bridge_atlas


def parse_sample(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise argparse.ArgumentTypeError("sample must use the form sigma,t")
    return parts[0], parts[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare n-domain smoothed Lambda-Mellin bridge projections."
    )
    parser.add_argument("--n-bound", type=int, action="append", help="Finite N cutoff. May be repeated.")
    parser.add_argument("--sample", type=parse_sample, action="append", help="Sample point as sigma,t. May be repeated.")
    parser.add_argument("--scale-law", default="log", help="Scale law for zero-height cutoff.")
    parser.add_argument("--multiplier", action="append", help="Scale multiplier. May be repeated.")
    parser.add_argument("--window", choices=list(SUPPORTED_ZERO_WINDOWS), action="append", help="Zero-height window mode. May be repeated.")
    parser.add_argument("--kernel", choices=list(SUPPORTED_N_DOMAIN_KERNELS), action="append", help="N-domain smoothing kernel. May be repeated.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = cesaro_mellin_bridge_atlas(
        n_bounds=args.n_bound,
        samples=args.sample,
        scale_law=args.scale_law,
        multipliers=args.multiplier,
        windows=args.window,
        kernels=args.kernel,
        dps=args.dps,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
