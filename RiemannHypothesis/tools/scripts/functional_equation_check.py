from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.zeta import functional_equation_check


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute finite residuals for zeta/xi functional equations.")
    parser.add_argument("--sigma", required=True, help="Real part of s.")
    parser.add_argument("--t", required=True, help="Imaginary part of s.")
    parser.add_argument("--equation", choices=["xi", "zeta"], default="xi")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()
    payload = functional_equation_check(args.sigma, args.t, args.dps, args.equation)
    payload["rows"] = [payload["row"]]
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
