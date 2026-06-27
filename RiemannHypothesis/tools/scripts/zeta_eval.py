from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.zeta import zeta_value


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate zeta(s) at s=sigma+i*t.")
    parser.add_argument("--sigma", required=True, help="Real part of s.")
    parser.add_argument("--t", required=True, help="Imaginary part of s.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()
    emit_payload(zeta_value(args.sigma, args.t, args.dps), args.format, args.output)


if __name__ == "__main__":
    main()
