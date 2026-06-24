from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
DEFAULT_PATHSPECS = ("*.sop", ":(glob)**/*.sop")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")
_STOP_WORDS = {
    "and",
    "are",
    "but",
    "for",
    "from",
    "into",
    "not",
    "the",
    "that",
    "this",
    "with",
    "description",
    "empty",
    "false",
    "manifest",
    "must",
    "never",
    "request",
    "should",
    "sop",
    "source",
    "subject",
    "true",
}


@dataclass(frozen=True)
class DiffFileChange:
    path: str
    status: str
    additions: int = 0
    deletions: int = 0

    @property
    def line_pressure(self) -> int:
        return self.additions + self.deletions


@dataclass(frozen=True)
class SensitivitySignal:
    subject_key: str
    touch_count: int
    heat: int
    layer: str
    retention_policy: str
    evidence_paths: tuple[str, ...]
    residual_outside: str

    def render(self, index: int) -> list[str]:
        return [
            f"  + [signal_{index:03d}_{self.subject_key}] is {self.layer}",
            f"    = touch_count: {self.touch_count}",
            f"    = heat: {self.heat}",
            f"    = retention_policy: {self.retention_policy}",
            f"    = evidence_paths: {', '.join(self.evidence_paths)}",
            f"    = residual_outside: {self.residual_outside}",
        ]


@dataclass(frozen=True)
class SensitivityScan:
    scan_id: str
    repo_root: str
    base_ref: str
    head_ref: str
    changes: tuple[DiffFileChange, ...]
    signals: tuple[SensitivitySignal, ...]
    residual_outside: str

    @property
    def ready(self) -> bool:
        return bool(self.scan_id and self.repo_root and self.base_ref and self.head_ref)

    def render(self) -> str:
        lines = [
            "Subject: Sensitivity Scan Event",
            "",
            f"& [{self.scan_id}] is a sensitivity scan over Git bookends",
            f"  + [repo_root] is {self.repo_root}",
            f"  + [base_ref] is {self.base_ref}",
            f"  + [head_ref] is {self.head_ref}",
            f"  + [changed_file_count] is {len(self.changes)}",
        ]
        if self.changes:
            for index, change in enumerate(self.changes, start=1):
                lines.append(f"  + [change_{index:03d}] is {change.status}:{change.path}")
                lines.append(f"    = additions: {change.additions}")
                lines.append(f"    = deletions: {change.deletions}")
        else:
            lines.append("  + [no_changed_sop_files] is true")
        if self.signals:
            for index, signal in enumerate(self.signals, start=1):
                lines.extend(signal.render(index))
        else:
            lines.append("  + [no_sensitivity_signals] is true")
        lines.append(f"  + [residual_outside] is {self.residual_outside}")
        return "\n".join(lines)


def build_sensitivity_scan(
    repo_root: str | Path,
    *,
    base_ref: str = "HEAD",
    head_ref: str = "WORKTREE",
    pathspecs: tuple[str, ...] = DEFAULT_PATHSPECS,
    include_untracked: bool = True,
    scan_id: str | None = None,
) -> SensitivityScan:
    root = Path(repo_root)
    changes = _collect_git_changes(root, base_ref, head_ref, pathspecs)
    if include_untracked and head_ref.upper() == "WORKTREE":
        changes = _merge_changes(changes, _collect_untracked_sop_changes(root))
    return build_sensitivity_scan_from_changes(
        root,
        base_ref=base_ref,
        head_ref=head_ref,
        changes=changes,
        scan_id=scan_id,
    )


def build_sensitivity_scan_from_changes(
    repo_root: str | Path,
    *,
    base_ref: str,
    head_ref: str,
    changes: tuple[DiffFileChange, ...],
    content_terms_by_path: dict[str, tuple[str, ...]] | None = None,
    scan_id: str | None = None,
) -> SensitivityScan:
    root = Path(repo_root)
    term_paths: dict[str, set[str]] = {}
    term_heat: dict[str, int] = {}
    supplied_terms = content_terms_by_path or {}
    for change in changes:
        terms = supplied_terms.get(change.path)
        if terms is None:
            terms = _terms_for_change(root, change, head_ref)
        for term in terms:
            normalized = _normalize(term)
            if not normalized:
                continue
            term_paths.setdefault(normalized, set()).add(change.path)
            term_heat[normalized] = term_heat.get(normalized, 0) + max(1, change.line_pressure)

    signals = tuple(
        sorted(
            (
                _build_signal(term, paths, term_heat[term])
                for term, paths in term_paths.items()
            ),
            key=lambda signal: (-signal.heat, -signal.touch_count, signal.subject_key),
        )
    )[:24]
    residual = (
        "scan measures changed SOP paths, terms, and line pressure; narrative why and semantic truth require deeper review"
    )
    return SensitivityScan(
        scan_id=scan_id or _make_scan_id(),
        repo_root=str(root),
        base_ref=base_ref,
        head_ref=head_ref,
        changes=changes,
        signals=signals,
        residual_outside=residual,
    )


def classify_layer(touch_count: int, heat: int) -> tuple[str, str]:
    if touch_count > 10 or heat >= 96:
        return ("impact", "emphasize")
    if 4 <= touch_count <= 10 or heat >= 48:
        return ("pressure", "sustain")
    if touch_count >= 2 or heat >= 16:
        return ("skin", "triangulate")
    if touch_count == 1 or heat > 0:
        return ("hair", "notice")
    return ("surface", "fade")


def write_scan(output_path: str | Path, scan: SensitivityScan) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(scan.render() + "\n", encoding="utf-8")
    return str(path)


def _collect_git_changes(
    root: Path,
    base_ref: str,
    head_ref: str,
    pathspecs: tuple[str, ...],
) -> tuple[DiffFileChange, ...]:
    if base_ref == "HEAD" and not _has_head(root):
        return ()
    left = EMPTY_TREE if base_ref.upper() in {"EMPTY", "EMPTY_TREE"} else base_ref
    name_status = _run_git(root, _diff_args(left, head_ref, "--name-status", pathspecs))
    numstat = _run_git(root, _diff_args(left, head_ref, "--numstat", pathspecs))
    status_changes = _parse_name_status(name_status)
    stats = _parse_numstat(numstat)
    return tuple(
        DiffFileChange(
            path=change.path,
            status=change.status,
            additions=stats.get(change.path, (change.additions, change.deletions))[0],
            deletions=stats.get(change.path, (change.additions, change.deletions))[1],
        )
        for change in status_changes
    )


def _collect_untracked_sop_changes(root: Path) -> tuple[DiffFileChange, ...]:
    output = _run_git(root, ["ls-files", "--others", "--exclude-standard", "--", *DEFAULT_PATHSPECS])
    changes = []
    for raw_path in output.splitlines():
        path = raw_path.strip()
        if not path:
            continue
        full_path = root / path
        additions = len(full_path.read_text(encoding="utf-8", errors="ignore").splitlines()) if full_path.exists() else 0
        changes.append(DiffFileChange(path=path.replace("\\", "/"), status="A", additions=additions, deletions=0))
    return tuple(changes)


def _merge_changes(
    primary: tuple[DiffFileChange, ...],
    secondary: tuple[DiffFileChange, ...],
) -> tuple[DiffFileChange, ...]:
    by_path = {change.path: change for change in primary}
    for change in secondary:
        by_path.setdefault(change.path, change)
    return tuple(sorted(by_path.values(), key=lambda change: change.path))


def _diff_args(base_ref: str, head_ref: str, mode: str, pathspecs: tuple[str, ...]) -> list[str]:
    if head_ref.upper() == "WORKTREE":
        args = ["diff", mode, base_ref]
    else:
        args = ["diff", mode, base_ref, head_ref]
    if pathspecs:
        args.extend(["--", *pathspecs])
    return args


def _parse_name_status(text: str) -> tuple[DiffFileChange, ...]:
    changes = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = parts[-1]
        changes.append(DiffFileChange(path=path, status=status))
    return tuple(changes)


def _parse_numstat(text: str) -> dict[str, tuple[int, int]]:
    stats = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        stats[parts[-1]] = (_parse_int(parts[0]), _parse_int(parts[1]))
    return stats


def _parse_int(value: str) -> int:
    return 0 if value == "-" else int(value)


def _terms_for_change(root: Path, change: DiffFileChange, head_ref: str) -> tuple[str, ...]:
    path_terms = _extract_terms(Path(change.path).stem.replace("_", " "))
    text = ""
    if head_ref.upper() == "WORKTREE":
        file_path = root / change.path
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8", errors="ignore")
    elif change.status != "D":
        completed = subprocess.run(
            ["git", "-C", str(root), "show", f"{head_ref}:{change.path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            text = completed.stdout
    return _unique_terms(path_terms + _extract_terms(text))


def _build_signal(term: str, paths: Iterable[str], heat: int) -> SensitivitySignal:
    evidence_paths = tuple(sorted(paths))
    layer, retention = classify_layer(len(evidence_paths), heat)
    return SensitivitySignal(
        subject_key=term,
        touch_count=len(evidence_paths),
        heat=heat,
        layer=layer,
        retention_policy=retention,
        evidence_paths=evidence_paths,
        residual_outside="term correlation is a sensitivity signal, not a proof claim",
    )


def _extract_terms(text: str) -> tuple[str, ...]:
    return _unique_terms(
        word
        for word in _WORD_RE.findall(text)
        if word.lower() not in _STOP_WORDS
    )


def _unique_terms(values: Iterable[str]) -> tuple[str, ...]:
    seen = set()
    terms = []
    for value in values:
        normalized = _normalize(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(normalized)
    return tuple(terms)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _has_head(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def _make_scan_id() -> str:
    return "SensitivityScan_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
