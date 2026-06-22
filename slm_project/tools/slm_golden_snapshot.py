from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SLM_RUST = ROOT / "slm_rust"
SNAPSHOT_DIR = ROOT / "slm_project" / "fixtures" / "golden"


@dataclass(frozen=True)
class GoldenFixture:
    fixture_id: str
    sentence: str
    file_name: str


FIXTURES = [
    GoldenFixture(
        fixture_id="design_compiler",
        sentence="Design a compiler for FPGA hardware.",
        file_name="compact_design_compiler.json",
    ),
    GoldenFixture(
        fixture_id="fish_swim",
        sentence="The fish swim.",
        file_name="compact_fish_swim.json",
    ),
    GoldenFixture(
        fixture_id="time_flies",
        sentence="Time flies like an arrow.",
        file_name="compact_time_flies.json",
    ),
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":/", 1)[-1]
    return f"/mnt/{drive}/{tail}"


def cargo_prefix() -> str:
    crate = to_wsl_path(SLM_RUST)
    return (
        'source "$HOME/.cargo/env"; '
        f'cd "{crate}"; '
        'env CARGO_TARGET_DIR="$HOME/slm_rust_target" '
        'CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER="$HOME/bin/zigcc"'
    )


def run_demo_compact(fixture: GoldenFixture) -> dict:
    command = (
        f"{cargo_prefix()} cargo run --quiet --bin slm_demo -- "
        f"--mode compact {fixture.sentence}"
    )
    completed = subprocess.run(
        ["wsl", "--", "bash", "-lc", command],
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        print(f"snapshot_demo_failed fixture={fixture.fixture_id}", file=sys.stderr)
        print(completed.stdout, file=sys.stderr)
        print(completed.stderr, file=sys.stderr)
        completed.check_returncode()

    report = json.loads(completed.stdout)
    validate_compact_snapshot(fixture, report)
    return report


def validate_compact_snapshot(fixture: GoldenFixture, report: dict) -> None:
    require(report["input"] == fixture.sentence, f"{fixture.fixture_id} input mismatch")
    require(report["output_mode"] == "compact", f"{fixture.fixture_id} mode mismatch")
    require("lexical_sense_candidates" not in report, "compact snapshot leaked sense array")
    require("graph_summary" in report, f"{fixture.fixture_id} missing graph summary")
    require("wobble_route" in report, f"{fixture.fixture_id} missing wobble route")
    require("primer_schema" in report, f"{fixture.fixture_id} missing primer schema")
    require(
        report["primer_schema"]["schema_id"] == "slm_primer",
        f"{fixture.fixture_id} primer schema mismatch",
    )
    require(
        "compaction_omitted_item_count" in report,
        f"{fixture.fixture_id} missing compaction omitted count",
    )


def canonical_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def update_snapshots() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for fixture in FIXTURES:
        report = run_demo_compact(fixture)
        path = SNAPSHOT_DIR / fixture.file_name
        path.write_text(canonical_json(report), encoding="utf-8")
        print(
            f"snapshot_updated fixture={fixture.fixture_id} "
            f"wobble_route={report['wobble_route']} path={path}"
        )


def check_snapshots() -> None:
    for fixture in FIXTURES:
        path = SNAPSHOT_DIR / fixture.file_name
        require(path.exists(), f"missing snapshot file: {path}")
        current = canonical_json(run_demo_compact(fixture))
        expected = path.read_text(encoding="utf-8")
        if current != expected:
            diff = difflib.unified_diff(
                expected.splitlines(),
                current.splitlines(),
                fromfile=f"expected/{fixture.file_name}",
                tofile=f"current/{fixture.file_name}",
                lineterm="",
            )
            print("\n".join(diff), file=sys.stderr)
            raise AssertionError(f"snapshot mismatch for {fixture.fixture_id}")
        print(f"snapshot_ok fixture={fixture.fixture_id} path={path}")
    print("slm_golden_snapshot_check_ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update or check SLM compact golden snapshots.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--update", action="store_true", help="Regenerate golden snapshots.")
    action.add_argument("--check", action="store_true", help="Compare current output to snapshots.")
    args = parser.parse_args()

    if args.update:
        update_snapshots()
    else:
        check_snapshots()


if __name__ == "__main__":
    main()
