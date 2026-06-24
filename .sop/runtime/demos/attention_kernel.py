from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_attention_kernel_packet, parse_faculty_field, parse_reflection_consumption


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compiled SOP attention kernel packet.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--packet-id", default="attention_kernel_packet", help="Stable packet id.")
    parser.add_argument("--focus-subject", required=True, help="Focus subject for the packet.")
    parser.add_argument("--job-need", required=True, help="Purpose and output target for the packet.")
    parser.add_argument("--impulse", default="", help="Visible impulse or drive carried into the packet.")
    parser.add_argument("--pattern", action="append", default=[], help="Selected SOP pattern name. Repeatable.")
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        help="Faculty field as system:field:boundary:residual:feature_account. Repeatable.",
    )
    parser.add_argument(
        "--consume",
        action="append",
        default=[],
        help="Reflection consumption as artifact|origin|consumer[|proof|mode|local_status]. Repeatable.",
    )
    parser.add_argument("--focus-term", action="append", default=[], help="Focus term used for balance context.")
    parser.add_argument("--periphery-term", action="append", default=[], help="Periphery term used for balance context.")
    parser.add_argument("--output", help="Optional output .sop path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact packet.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    packet = build_attention_kernel_packet(
        packet_id=args.packet_id,
        focus_subject=args.focus_subject,
        job_need=args.job_need,
        selected_patterns=tuple(args.pattern),
        faculty_fields=tuple(parse_faculty_field(value) for value in args.field),
        reflection_consumptions=tuple(parse_reflection_consumption(value) for value in args.consume),
        impulse=args.impulse,
        focus_terms=tuple(args.focus_term),
        periphery_terms=tuple(args.periphery_term),
    )
    rendered = packet.to_hypergraph().render() if args.graph else packet.render()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
