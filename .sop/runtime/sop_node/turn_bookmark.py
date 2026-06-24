from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord
from .sensitivity_scan import SensitivityScan, build_sensitivity_scan


DEFAULT_BOOKMARK_PATHSPECS = ("*.sop", ":(glob)**/*.sop", "*.py", ":(glob)**/*.py")


@dataclass(frozen=True)
class TurnBookmarkFinding:
    finding_kind: str
    subject_key: str
    reason: str
    weight: int
    resolution_band: str
    plan_relation: str
    route: str
    evidence_paths: tuple[str, ...] = field(default_factory=tuple)

    def render(self, index: int) -> list[str]:
        lines = [
            f"  + [finding_{index:03d}_{_safe_key(self.subject_key)}] is {self.finding_kind}",
            f"    = subject_key: {self.subject_key}",
            f"    = reason: {self.reason}",
            f"    = weight: {self.weight}",
            f"    = resolution_band: {self.resolution_band}",
            f"    = plan_relation: {self.plan_relation}",
            f"    = route: {self.route}",
        ]
        if self.evidence_paths:
            lines.append(f"    = evidence_paths: {', '.join(self.evidence_paths)}")
        return lines


@dataclass(frozen=True)
class TurnBookmark:
    bookmark_id: str
    repo_root: str
    base_ref: str
    head_ref: str
    planned_terms: tuple[str, ...]
    narrative_terms: tuple[str, ...]
    scan: SensitivityScan
    findings: tuple[TurnBookmarkFinding, ...]
    residual_outside: str

    @property
    def ready(self) -> bool:
        return bool(self.bookmark_id and self.repo_root and self.base_ref and self.head_ref and self.scan.ready)

    def render(self) -> str:
        lines = [
            "Subject: Turn Bookmark Event",
            "",
            f"& [{self.bookmark_id}] is a turn bookmark over Git bookends",
            f"  + [repo_root] is {self.repo_root}",
            f"  + [base_ref] is {self.base_ref}",
            f"  + [head_ref] is {self.head_ref}",
            f"  + [planned_terms] is {', '.join(self.planned_terms) if self.planned_terms else 'not_supplied'}",
            f"  + [narrative_terms] is {', '.join(self.narrative_terms) if self.narrative_terms else 'not_supplied'}",
            f"  + [changed_file_count] is {len(self.scan.changes)}",
            f"  + [signal_count] is {len(self.scan.signals)}",
        ]
        if self.findings:
            for index, finding in enumerate(self.findings, start=1):
                lines.extend(finding.render(index))
        else:
            lines.append("  + [no_findings] is true")
        lines.append(f"  + [residual_outside] is {self.residual_outside}")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = _safe_key(self.bookmark_id)
        bookmark_key = f"N:bookmark:{graph_id}"
        outside_key = "N:outside:turn_bookmark_boundary"
        nodes: list[HypergraphNode] = [
            HypergraphNode(bookmark_key, self.bookmark_id, (("repo_root", self.repo_root),)),
            HypergraphNode(f"N:commit:{_safe_key(self.base_ref)}", self.base_ref),
            HypergraphNode(f"N:commit:{_safe_key(self.head_ref)}", self.head_ref),
            HypergraphNode(outside_key, "hidden cognition and semantic proof outside bookmark evidence"),
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:span:{graph_id}",
                "span",
                (
                    ("bookmark", bookmark_key),
                    ("start", f"N:commit:{_safe_key(self.base_ref)}"),
                    ("end", f"N:commit:{_safe_key(self.head_ref)}"),
                ),
            )
        ]

        for term in self.planned_terms:
            term_key = f"N:term:{_safe_key(term)}"
            nodes.append(HypergraphNode(term_key, term, (("term_role", "planned"),)))
            edges.append(
                HypergraphEdge(
                    f"E:compares:{graph_id}_{_safe_key(term)}",
                    "compares",
                    (("bookmark", bookmark_key), ("plan", term_key)),
                )
            )

        for signal in self.scan.signals[:8]:
            signal_key = f"N:signal:{_safe_key(signal.subject_key)}"
            nodes.append(
                HypergraphNode(
                    signal_key,
                    signal.subject_key,
                    (("heat", str(signal.heat)), ("layer", signal.layer), ("touch_count", str(signal.touch_count))),
                )
            )
            edges.append(
                HypergraphEdge(
                    f"E:weighs:{graph_id}_{_safe_key(signal.subject_key)}",
                    "weighs",
                    (("bookmark", bookmark_key), ("signal", signal_key)),
                    (("weight", str(signal.heat)), ("resolution_band", signal.layer)),
                )
            )

        for index, finding in enumerate(self.findings, start=1):
            finding_key = f"N:finding:{index:03d}_{_safe_key(finding.subject_key)}"
            nodes.append(
                HypergraphNode(
                    finding_key,
                    finding.subject_key,
                    (
                        ("finding_kind", finding.finding_kind),
                        ("weight", str(finding.weight)),
                        ("resolution_band", finding.resolution_band),
                        ("plan_relation", finding.plan_relation),
                        ("route", finding.route),
                    ),
                )
            )
            edge_kind = _edge_kind_for_finding(finding.finding_kind)
            edges.append(
                HypergraphEdge(
                    f"E:{edge_kind}:{graph_id}_{index:03d}",
                    edge_kind,
                    (("bookmark", bookmark_key), ("finding", finding_key)),
                    (("reason", finding.reason),),
                )
            )

        edges.append(
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("bookmark", bookmark_key), ("outside", outside_key)),
            )
        )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.bookmark_id} Turn Bookmark",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG turn-bookmark"),
                ("base_ref", self.base_ref),
                ("head_ref", self.head_ref),
            ),
            outside=(self.residual_outside,),
        )


def build_turn_bookmark(
    repo_root: str | Path,
    *,
    base_ref: str = "HEAD",
    head_ref: str = "WORKTREE",
    planned_terms: tuple[str, ...] = (),
    narrative_terms: tuple[str, ...] = (),
    pathspecs: tuple[str, ...] = DEFAULT_BOOKMARK_PATHSPECS,
    bookmark_id: str | None = None,
) -> TurnBookmark:
    scan = build_sensitivity_scan(
        repo_root,
        base_ref=base_ref,
        head_ref=head_ref,
        pathspecs=pathspecs,
        scan_id=(bookmark_id or _make_bookmark_id()) + "_scan",
    )
    return build_turn_bookmark_from_scan(
        repo_root,
        scan=scan,
        planned_terms=planned_terms,
        narrative_terms=narrative_terms,
        bookmark_id=bookmark_id,
    )


def build_turn_bookmark_from_scan(
    repo_root: str | Path,
    *,
    scan: SensitivityScan,
    planned_terms: tuple[str, ...] = (),
    narrative_terms: tuple[str, ...] = (),
    bookmark_id: str | None = None,
) -> TurnBookmark:
    normalized_planned = _unique(_normalize(term) for term in planned_terms)
    normalized_narrative = _unique(_normalize(term) for term in narrative_terms)
    signal_by_key = {signal.subject_key: signal for signal in scan.signals}
    findings: list[TurnBookmarkFinding] = []

    for term in normalized_planned:
        signal = signal_by_key.get(term)
        if signal is None:
            direct_evidence = _planned_term_evidence_paths(Path(repo_root), scan, term)
            if direct_evidence:
                findings.append(
                    TurnBookmarkFinding(
                        "unique_accomplishment",
                        term,
                        "planned term appears in changed work but did not reach top signal salience",
                        max(4, len(direct_evidence) * 4),
                        "skin",
                        "satisfied",
                        "close",
                        direct_evidence,
                    )
                )
            else:
                findings.append(
                    TurnBookmarkFinding(
                        "missed_work",
                        term,
                        "planned term did not appear in scan signals or direct changed-file evidence",
                        3,
                        "hair",
                        "missing",
                        "track",
                    )
                )
        else:
            findings.append(
                TurnBookmarkFinding(
                    "unique_accomplishment",
                    term,
                    "planned term appears in changed work signals",
                    signal.heat,
                    signal.layer,
                    "satisfied",
                    "close" if signal.layer in {"hair", "skin"} else "focus",
                    signal.evidence_paths,
                )
            )

    planned_set = set(normalized_planned)
    narrative_set = set(normalized_narrative)
    for signal in scan.signals[:12]:
        if signal.subject_key in planned_set:
            continue
        if signal.subject_key in narrative_set or signal.layer in {"pressure", "impact"}:
            findings.append(
                TurnBookmarkFinding(
                    "new_potential",
                    signal.subject_key,
                    "strong or narrative-adjacent signal opened a future attention route",
                    signal.heat,
                    signal.layer,
                    "opened",
                    "periphery" if signal.layer != "impact" else "focus",
                    signal.evidence_paths,
                )
            )

    generated_pressure = _generated_artifact_pressure(scan)
    if generated_pressure > 0:
        findings.append(
            TurnBookmarkFinding(
                "mistake",
                "generated_artifact_inflation",
                "generated or index artifact pressure may distort semantic weight",
                generated_pressure,
                "pressure" if generated_pressure < 128 else "impact",
                "surprising",
                "caution",
                tuple(change.path for change in scan.changes if _is_generated_artifact(change.path)),
            )
        )

    residual = (
        "bookmark compares visible repo signals against planned and narrative terms; hidden motive and semantic proof remain outside"
    )
    return TurnBookmark(
        bookmark_id=bookmark_id or _make_bookmark_id(),
        repo_root=str(Path(repo_root)),
        base_ref=scan.base_ref,
        head_ref=scan.head_ref,
        planned_terms=normalized_planned,
        narrative_terms=normalized_narrative,
        scan=scan,
        findings=tuple(findings),
        residual_outside=residual,
    )


def _generated_artifact_pressure(scan: SensitivityScan) -> int:
    return sum(change.line_pressure for change in scan.changes if _is_generated_artifact(change.path))


def _planned_term_evidence_paths(root: Path, scan: SensitivityScan, term: str) -> tuple[str, ...]:
    hits: list[str] = []
    normalized_term = _normalize(term)
    for change in scan.changes:
        path_text = _normalize(Path(change.path).stem.replace("_", " "))
        if normalized_term and normalized_term in path_text:
            hits.append(change.path)
            continue
        text = _text_for_change(root, scan.head_ref, change.path)
        if normalized_term and normalized_term in _normalize(text):
            hits.append(change.path)
    return tuple(hits)


def _text_for_change(root: Path, head_ref: str, path: str) -> str:
    if head_ref.upper() == "WORKTREE":
        file_path = root / path
        if file_path.exists():
            return file_path.read_text(encoding="utf-8", errors="ignore")
        return ""
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{head_ref}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else ""


def _is_generated_artifact(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return "/indexes/" in normalized or normalized.endswith("_scan.hg.sop")


def _edge_kind_for_finding(finding_kind: str) -> str:
    if finding_kind == "missed_work":
        return "misses"
    if finding_kind == "mistake":
        return "flags"
    if finding_kind == "unique_accomplishment":
        return "accomplishes"
    if finding_kind == "new_potential":
        return "opens"
    return "realizes"


def _unique(values) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())


def _make_bookmark_id() -> str:
    return "TurnBookmark_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
