from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.zeta import critical_line_scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample Hardy Z(t) on the critical line.")
    parser.add_argument("--t-min", required=True, help="Start ordinate.")
    parser.add_argument("--t-max", required=True, help="End ordinate.")
    parser.add_argument("--step", required=True, help="Sample step.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--refine", action="store_true", help="Refine sign-change brackets by bisection.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()
    payload = critical_line_scan(args.t_min, args.t_max, args.step, args.dps, args.refine)
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
