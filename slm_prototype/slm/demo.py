"""Command-line demo for the SLM prototype."""

from __future__ import annotations

import argparse
import json

from slm.diffusion import analyze


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Semantic Logic Model prototype.")
    parser.add_argument("text", nargs="?", default="Design a compiler for FPGA hardware.")
    args = parser.parse_args()

    result = analyze(args.text)

    print("TOKENS")
    for token in result.tokens:
        print(f"  {token.index}: {token.text!r}")

    print("\nCANDIDATE ROLES")
    for token in result.tokens:
        roles = ", ".join(f"{candidate.role}:{candidate.activation:.2f}" for candidate in result.candidates[token.index])
        print(f"  {token.text}: {roles}")

    print("\nSTRUCTURAL RELATION HINTS")
    for hint in result.structural_hints:
        print(f"  token={hint.source_token} relation={hint.relation} scope={hint.target_scope} activation={hint.activation:.2f}")

    print("\nDIFFUSION SNAPSHOTS")
    for snapshot in result.snapshots:
        print(f"  {snapshot.pass_name}: {snapshot.summary} glyphs={len(snapshot.graph.glyphs)} edges={len(snapshot.graph.edges)}")

    print("\nWOBBLE")
    print(f"  score={result.wobble.score:.3f}")
    for factor in result.wobble.factors:
        print(f"  - {factor}")

    print("\nFINAL SLM PRIMER")
    print(json.dumps(result.primer, indent=2))


if __name__ == "__main__":
    main()
