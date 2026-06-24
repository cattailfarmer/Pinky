from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_compiled_attention_packet, parse_periphery_terms


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile a minimal SOP attention scaffold packet.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--packet-id", default="compiled_attention_packet", help="Stable packet id.")
    parser.add_argument("--job-need", required=True, help="Purpose, subject, risk, and output target for the job.")
    parser.add_argument("--output-target", default="inspectable SOP record", help="Expected output target.")
    parser.add_argument("--model-lane", default="codex", help="Actor or model lane that will use the packet.")
    parser.add_argument("--depth", default="slender", help="Attention depth such as slender, wide, deep, or explosive_controlled.")
    parser.add_argument("--periphery", default="", help="Comma-separated periphery terms.")
    parser.add_argument("--source-ref", action="append", default=[], help="Source reference to cite. Repeatable.")
    parser.add_argument("--output", help="Optional output .sop path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact packet.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    packet = build_compiled_attention_packet(
        packet_id=args.packet_id,
        job_need=args.job_need,
        output_target=args.output_target,
        model_lane=args.model_lane,
        depth=args.depth,
        periphery_terms=parse_periphery_terms(args.periphery),
        source_refs=tuple(args.source_ref),
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
