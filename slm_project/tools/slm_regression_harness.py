from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SLM_RUST = ROOT / "slm_rust"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":/", 1)[-1]
    return f"/mnt/{drive}/{tail}"


def run_command(stage: str, command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode != 0:
        print(f"{stage}_failed exit_code={completed.returncode}", file=sys.stderr)
        if completed.stdout:
            print("--- stdout ---", file=sys.stderr)
            print(completed.stdout, file=sys.stderr)
        if completed.stderr:
            print("--- stderr ---", file=sys.stderr)
            print(completed.stderr, file=sys.stderr)
        completed.check_returncode()
    return completed


def run_wsl(stage: str, command: str) -> subprocess.CompletedProcess[str]:
    return run_command(stage, ["wsl", "--", "bash", "-lc", command])


def cargo_prefix() -> str:
    crate = to_wsl_path(SLM_RUST)
    return (
        'source "$HOME/.cargo/env"; '
        f'cd "{crate}"; '
        'env CARGO_TARGET_DIR="$HOME/slm_rust_target" '
        'CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER="$HOME/bin/zigcc"'
    )


def demo_command(mode: str, sentence: str) -> str:
    return f'{cargo_prefix()} cargo run --quiet --bin slm_demo -- --mode {mode} {sentence}'


def run_source_gate() -> None:
    script = ROOT / "slm_project" / "tools" / "slm_source_gate_check.py"
    completed = run_command("source_gate", [sys.executable, str(script)])
    require("slm_source_gate_check_ok" in completed.stdout, "source gate did not report ok")
    print("source_gate_ok")


def run_cargo_test() -> None:
    completed = run_wsl("cargo_test", f"{cargo_prefix()} cargo test")
    require("test result: ok" in completed.stdout, "cargo test did not report ok")
    print("cargo_test_ok")


def run_self_check() -> None:
    completed = run_wsl(
        "self_check",
        f"{cargo_prefix()} cargo run --quiet --bin slm_self_check",
    )
    require("slm_self_check: ok" in completed.stdout, "self-check did not report ok")
    print("self_check_ok")


def run_demo_compact() -> None:
    completed = run_wsl(
        "demo_compact",
        demo_command("compact", "Design a compiler for FPGA hardware."),
    )
    report = json.loads(completed.stdout)
    require(report["output_mode"] == "compact", "compact output mode mismatch")
    require("lexical_sense_candidates" not in report, "compact output leaked full sense array")
    require(
        report["primer_schema"]["schema_id"] == "slm_primer",
        "compact output missing primer schema",
    )
    require(
        report["wobble_route"] in {"ready", "continue_diffusion", "seek_sidecar", "route_to_deliberation"},
        "compact output has unknown wobble route",
    )
    print(
        "demo_compact_ok "
        f"lexical_sense_candidate_count={report['lexical_sense_candidate_count']} "
        f"wobble_route={report['wobble_route']}"
    )


def run_demo_primer_only() -> None:
    completed = run_wsl(
        "demo_primer_only",
        demo_command("primer-only", "Design a compiler for FPGA hardware."),
    )
    primer = json.loads(completed.stdout)
    require(primer["schema"]["schema_id"] == "slm_primer", "primer schema id mismatch")
    require(primer["schema"]["schema_version"] == "0.1.0", "primer schema version mismatch")
    require("compact_evidence" in primer, "primer-only output missing compact evidence")
    print(
        "demo_primer_only_ok "
        f"schema={primer['schema']['schema_id']}:{primer['schema']['schema_version']} "
        f"compact_evidence_count={len(primer['compact_evidence'])}"
    )


def run_demo_sop() -> None:
    completed = run_wsl(
        "demo_sop",
        demo_command("sop", "Design a compiler for FPGA hardware."),
    )
    require(completed.stdout.startswith("SLM_PRIMER_V0"), "SOP output missing primer prefix")
    require("Wobble:" in completed.stdout, "SOP output missing wobble line")
    print(f"demo_sop_ok first_line={completed.stdout.splitlines()[0]}")


def run_golden_snapshot_check() -> None:
    script = ROOT / "slm_project" / "tools" / "slm_golden_snapshot.py"
    completed = run_command("golden_snapshot_check", [sys.executable, str(script), "--check"])
    require(
        "slm_golden_snapshot_check_ok" in completed.stdout,
        "golden snapshot check did not report ok",
    )
    for line in completed.stdout.splitlines():
        if line.startswith("snapshot_ok") or line == "slm_golden_snapshot_check_ok":
            print(line)


def run_all() -> None:
    run_source_gate()
    run_cargo_test()
    run_self_check()
    run_demo_compact()
    run_demo_primer_only()
    run_demo_sop()
    run_golden_snapshot_check()
    print("slm_regression_harness_ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SLM trusted regression harness.")
    parser.parse_args()
    run_all()


if __name__ == "__main__":
    main()
