from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEXICON = ROOT / "slm_lexicon"


@dataclass(frozen=True)
class RebuildStep:
    name: str
    command: list[str]
    modifies_source: bool = False


WATCHED_ARTIFACTS = [
    LEXICON / "data" / "raw" / "open_english_wordnet" / "manifest.json",
    LEXICON / "data" / "slm_lexicon.sqlite",
    LEXICON / "data" / "slm_lexical_substrate" / "manifest.json",
    LEXICON / "data" / "slm_lexical_substrate" / "term_role_sense_index.json",
    LEXICON / "data" / "slm_lexical_substrate" / "closed_class_speed_table.json",
    LEXICON / "data" / "slm_lexical_substrate" / "source_provenance.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def planned_steps(include_download: bool) -> list[RebuildStep]:
    steps = []
    if include_download:
        steps.append(
            RebuildStep(
                "download_open_english_wordnet",
                [sys.executable, str(LEXICON / "scripts" / "download_open_english_wordnet.py")],
                modifies_source=True,
            )
        )
    steps.extend(
        [
            RebuildStep(
                "build_lexicon_db",
                [sys.executable, str(LEXICON / "scripts" / "build_lexicon_db.py")],
            ),
            RebuildStep(
                "export_lexicon_cache",
                [sys.executable, str(LEXICON / "scripts" / "export_lexicon_cache.py")],
            ),
            RebuildStep(
                "build_lexical_substrate_pack",
                [sys.executable, str(LEXICON / "scripts" / "build_lexical_substrate_pack.py")],
            ),
            RebuildStep(
                "source_gate",
                [sys.executable, str(ROOT / "slm_project" / "tools" / "slm_source_gate_check.py")],
            ),
        ]
    )
    return steps


def print_artifact_checksums(label: str) -> None:
    print(f"{label}:")
    for path in WATCHED_ARTIFACTS:
        if path.exists():
            print(f"  sha256 {path.relative_to(ROOT)} {sha256(path)}")
        else:
            print(f"  missing {path.relative_to(ROOT)}")


def print_plan(steps: list[RebuildStep]) -> None:
    print("planned_steps:")
    for step in steps:
        source_note = " modifies_source=true" if step.modifies_source else ""
        print(f"  {step.name}{source_note}: {' '.join(step.command)}")


def run_steps(steps: list[RebuildStep]) -> None:
    for step in steps:
        print(f"running_step={step.name}")
        completed = subprocess.run(step.command, text=True, capture_output=True)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.returncode != 0:
            if completed.stderr:
                print(completed.stderr, file=sys.stderr, end="")
            completed.check_returncode()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run or execute the SLM lexical substrate rebuild workflow."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print plan and checksums only.")
    mode.add_argument(
        "--execute-local",
        action="store_true",
        help="Run local rebuild steps against already preserved source files.",
    )
    parser.add_argument(
        "--include-download",
        action="store_true",
        help="Include source download step. Requires --execute-local.",
    )
    args = parser.parse_args()

    if args.include_download and not args.execute_local:
        raise SystemExit("--include-download requires --execute-local")

    steps = planned_steps(include_download=args.include_download)
    print_artifact_checksums("current_artifacts")
    print_plan(steps)
    if args.execute_local:
        run_steps(steps)
        print_artifact_checksums("rebuilt_artifacts")
        print("slm_lexical_rebuild_workflow_ok mode=execute_local")
    else:
        print("slm_lexical_rebuild_workflow_ok mode=dry_run")


if __name__ == "__main__":
    main()
