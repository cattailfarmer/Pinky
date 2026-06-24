from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord
from .turn_bookmark import TurnBookmark, build_turn_bookmark


DEFAULT_OUTSIDE = (
    "hidden cognition",
    "exact hidden-state replay",
    "unsupported causation",
    "claim that later reflection was original awareness",
    "automatic branch creation",
    "remote synchronization",
)

CHECKSUM_SIGNAL_STOP_WORDS = {
    "without",
}


@dataclass(frozen=True)
class ChecksumZone:
    zone_id: str
    zone_kind: str
    signal_key: str
    heat: int
    confidence: str
    disposition: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    latent_depth_candidate: str = ""

    @property
    def zone_key(self) -> str:
        return _safe_key(self.zone_id)

    def render(self, index: int) -> list[str]:
        lines = [
            f"  + [zone_{index:03d}_{self.zone_key}] is {self.zone_kind}",
            f"    = signal_key: {self.signal_key}",
            f"    = heat: {self.heat}",
            f"    = confidence: {self.confidence}",
            f"    = disposition: {self.disposition}",
        ]
        if self.latent_depth_candidate:
            lines.append(f"    = latent_depth_candidate: {self.latent_depth_candidate}")
        if self.evidence_refs:
            lines.append(f"    = evidence_refs: {', '.join(self.evidence_refs)}")
        return lines


@dataclass(frozen=True)
class TrailingChecksumReview:
    review_id: str
    repo_root: str
    direct_focus_turn: str
    review_turn: str
    commit_bookend_start: str
    commit_bookend_end: str
    one_turn_lag: str
    bookmark: TurnBookmark
    zones: tuple[ChecksumZone, ...]
    checksum_disposition: str
    inquiry_preparation: str
    outside: tuple[str, ...] = DEFAULT_OUTSIDE

    @property
    def review_key(self) -> str:
        return _safe_key(self.review_id)

    @property
    def ready(self) -> bool:
        return bool(
            self.review_id
            and self.repo_root
            and self.direct_focus_turn
            and self.commit_bookend_start
            and self.commit_bookend_end
            and self.bookmark.ready
            and self.checksum_disposition
        )

    def render(self) -> str:
        lines = [
            "Subject: Trailing Checksum Review",
            "",
            f"& [TrailingChecksumReview:{self.review_key}] is a trailing_checksum_review",
            f"  + [review_id] is {self.review_id}",
            f"  + [repo_root] is {self.repo_root}",
            f"  + [direct_focus_turn] is {self.direct_focus_turn}",
            f"  + [review_turn] is {self.review_turn}",
            f"  + [one_turn_lag] is {self.one_turn_lag}",
            "  + [insight_timing] is trailing_reflection",
            f"  + [commit_bookend_start] is {self.commit_bookend_start}",
            f"  + [commit_bookend_end] is {self.commit_bookend_end}",
            f"  + [changed_file_count] is {len(self.bookmark.scan.changes)}",
            f"  + [signal_count] is {len(self.bookmark.scan.signals)}",
            f"  + [checksum_disposition] is {self.checksum_disposition}",
            f"  + [inquiry_preparation] is {self.inquiry_preparation}",
        ]
        if self.zones:
            for index, zone in enumerate(self.zones, start=1):
                lines.extend(zone.render(index))
        else:
            lines.append("  + [zone_set] is empty")
        if self.bookmark.findings:
            for index, finding in enumerate(self.bookmark.findings[:8], start=1):
                lines.extend(finding.render(index))
        else:
            lines.append("  + [finding_set] is empty")
        lines.append(f"  + [outside] is {', '.join(self.outside)}")
        lines.extend(
            [
                "",
                "(trailing_checksum_review) :direct_focus_turn: /one_turn_lag and checksum_disposition/ |outside|",
                f"  + [direct_focus_turn] is {self.direct_focus_turn}",
                f"  + [review_turn] is {self.review_turn}",
                f"  + [one_turn_lag] is {self.one_turn_lag}",
                f"  + [checksum_disposition] is {self.checksum_disposition}",
                f"  |outside| {', '.join(self.outside)}",
            ]
        )
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.review_key
        review_node = HypergraphNode(
            f"N:bookmark:{graph_id}",
            self.review_id,
            (("checksum_disposition", self.checksum_disposition), ("one_turn_lag", self.one_turn_lag)),
        )
        direct_focus_node = HypergraphNode(f"N:event:{_safe_key(self.direct_focus_turn)}", self.direct_focus_turn)
        review_turn_node = HypergraphNode(f"N:event:{_safe_key(self.review_turn)}", self.review_turn)
        start_node = HypergraphNode(f"N:commit:{_safe_key(self.commit_bookend_start)}", self.commit_bookend_start)
        end_node = HypergraphNode(f"N:commit:{_safe_key(self.commit_bookend_end)}", self.commit_bookend_end)
        disposition_node = HypergraphNode(
            f"N:policy:{_safe_key(self.checksum_disposition)}",
            self.checksum_disposition,
        )
        outside_node = HypergraphNode("N:outside:trailing_checksum_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [
            review_node,
            direct_focus_node,
            review_turn_node,
            start_node,
            end_node,
            disposition_node,
            outside_node,
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:span:{graph_id}",
                "span",
                (("review", review_node.key), ("start", start_node.key), ("end", end_node.key)),
            ),
            HypergraphEdge(
                f"E:trails:{_safe_key(self.direct_focus_turn)}",
                "trails",
                (("direct_focus", direct_focus_node.key), ("review", review_turn_node.key)),
                (("lag", self.one_turn_lag),),
            ),
            HypergraphEdge(
                f"E:checksums:{graph_id}",
                "checksums",
                (("review", review_node.key), ("direct_focus", direct_focus_node.key), ("disposition", disposition_node.key)),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("review", review_node.key), ("outside", outside_node.key)),
            ),
        ]
        for zone in self.zones:
            zone_node = HypergraphNode(
                f"N:zone:{zone.zone_key}",
                zone.zone_kind,
                (("signal_key", zone.signal_key), ("heat", str(zone.heat)), ("confidence", zone.confidence)),
            )
            signal_node = HypergraphNode(f"N:signal:{_safe_key(zone.signal_key)}", zone.signal_key)
            nodes.extend((zone_node, signal_node))
            edge_kind = "heats" if zone.zone_kind in {"hot_zone", "impact_zone"} else "warms"
            edges.append(
                HypergraphEdge(
                    f"E:{edge_kind}:{zone.zone_key}",
                    edge_kind,
                    (("zone", zone_node.key), ("signal", signal_node.key), ("review", review_node.key)),
                    (("weight", str(zone.heat)),),
                )
            )
            if zone.latent_depth_candidate:
                latent_node = HypergraphNode(
                    f"N:finding:{_safe_key(zone.latent_depth_candidate)}",
                    zone.latent_depth_candidate,
                    (("disposition", zone.disposition),),
                )
                nodes.append(latent_node)
                edges.append(
                    HypergraphEdge(
                        f"E:inquires:{_safe_key(zone.latent_depth_candidate)}",
                        "inquires",
                        (("finding", latent_node.key), ("disposition", disposition_node.key), ("review", review_node.key)),
                    )
                )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.review_id} Trailing Checksum Review",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG trailing-checksum-review"),
                ("base_ref", self.commit_bookend_start),
                ("head_ref", self.commit_bookend_end),
                ("one_turn_lag", self.one_turn_lag),
                ("checksum_disposition", self.checksum_disposition),
            ),
            outside=self.outside,
        )


def build_trailing_checksum_review(
    repo_root: str | Path,
    *,
    review_id: str,
    direct_focus_ref: str = "HEAD",
    base_ref: str | None = None,
    review_turn: str = "current_review_turn",
    planned_terms: Iterable[str] = (),
    narrative_terms: Iterable[str] = (),
    pathspecs: Iterable[str] | None = None,
    outside: Iterable[str] = DEFAULT_OUTSIDE,
) -> TrailingChecksumReview:
    root = Path(repo_root)
    start_ref, end_ref = detect_direct_focus_bookends(root, direct_focus_ref=direct_focus_ref, base_ref=base_ref)
    bookmark = build_turn_bookmark(
        root,
        base_ref=start_ref,
        head_ref=end_ref,
        planned_terms=tuple(planned_terms),
        narrative_terms=tuple(narrative_terms),
        pathspecs=tuple(pathspecs) if pathspecs else ("*.sop", ":(glob)**/*.sop", "*.py", ":(glob)**/*.py"),
        bookmark_id=f"{review_id}_turn_bookmark",
    )
    zones = classify_checksum_zones(bookmark)
    disposition = _select_disposition(zones, bookmark)
    inquiry = _build_inquiry_preparation(zones, bookmark)
    return TrailingChecksumReview(
        review_id=review_id,
        repo_root=str(root),
        direct_focus_turn=end_ref,
        review_turn=review_turn,
        commit_bookend_start=start_ref,
        commit_bookend_end=end_ref,
        one_turn_lag="one_turn",
        bookmark=bookmark,
        zones=zones,
        checksum_disposition=disposition,
        inquiry_preparation=inquiry,
        outside=tuple(_parse_items(outside)) or DEFAULT_OUTSIDE,
    )


def detect_direct_focus_bookends(
    repo_root: str | Path,
    *,
    direct_focus_ref: str = "HEAD",
    base_ref: str | None = None,
) -> tuple[str, str]:
    root = Path(repo_root)
    end_ref = _git_rev_parse(root, "--short", direct_focus_ref)
    start_ref = base_ref or _git_rev_parse(root, "--short", f"{direct_focus_ref}~1")
    return start_ref, end_ref


def classify_checksum_zones(bookmark: TurnBookmark, *, limit: int = 8) -> tuple[ChecksumZone, ...]:
    zones: list[ChecksumZone] = []
    for signal in bookmark.scan.signals[:limit]:
        if signal.subject_key in CHECKSUM_SIGNAL_STOP_WORDS:
            continue
        zone_kind = _zone_kind(signal.layer, signal.heat)
        if zone_kind == "cold_zone":
            continue
        disposition = _disposition_for_zone(zone_kind, signal.subject_key)
        latent = signal.subject_key if zone_kind in {"hot_zone", "impact_zone"} else ""
        zones.append(
            ChecksumZone(
                zone_id=f"{zone_kind}_{signal.subject_key}",
                zone_kind=zone_kind,
                signal_key=signal.subject_key,
                heat=signal.heat,
                confidence=_confidence_for_signal(signal.touch_count, signal.layer),
                disposition=disposition,
                evidence_refs=signal.evidence_paths,
                latent_depth_candidate=latent,
            )
        )
    if not zones and bookmark.scan.signals:
        signal = bookmark.scan.signals[0]
        zones.append(
            ChecksumZone(
                zone_id=f"cold_{signal.subject_key}",
                zone_kind="cold_zone",
                signal_key=signal.subject_key,
                heat=signal.heat,
                confidence="low",
                disposition="no_action",
                evidence_refs=signal.evidence_paths,
            )
        )
    return tuple(zones)


def parse_terms(value: str) -> tuple[str, ...]:
    return tuple(_parse_items((value,)))


def _zone_kind(layer: str, heat: int) -> str:
    if layer == "impact" or heat >= 80:
        return "impact_zone"
    if layer == "pressure" or heat >= 24:
        return "hot_zone"
    if layer in {"hair", "skin"} or heat >= 4:
        return "warmth_zone"
    return "cold_zone"


def _disposition_for_zone(zone_kind: str, signal_key: str) -> str:
    if zone_kind == "impact_zone":
        if any(term in signal_key for term in ("security", "honesty", "boundary", "proof")):
            return "caution"
        return "deep_probe"
    if zone_kind == "hot_zone":
        if "branch" in signal_key:
            return "branch_refinement"
        return "track"
    if zone_kind == "warmth_zone":
        return "note_warmth"
    return "no_action"


def _confidence_for_signal(touch_count: int, layer: str) -> str:
    if layer in {"pressure", "impact"} and touch_count >= 3:
        return "high"
    if touch_count >= 2:
        return "medium"
    return "low"


def _select_disposition(zones: tuple[ChecksumZone, ...], bookmark: TurnBookmark) -> str:
    dispositions = {zone.disposition for zone in zones}
    if "caution" in dispositions:
        return "caution"
    if "deep_probe" in dispositions:
        return "deep_probe"
    if "branch_refinement" in dispositions:
        return "branch_refinement"
    if "track" in dispositions:
        return "track"
    if any(finding.route in {"focus", "state_trace", "branch_refinement"} for finding in bookmark.findings):
        return "track"
    if "note_warmth" in dispositions:
        return "note_warmth"
    return "no_action"


def _build_inquiry_preparation(zones: tuple[ChecksumZone, ...], bookmark: TurnBookmark) -> str:
    latent = [zone.latent_depth_candidate for zone in zones if zone.latent_depth_candidate]
    if latent:
        return "prepare inquiry over " + ", ".join(latent[:5])
    if bookmark.findings:
        return "preserve bookmark findings as periphery"
    return "no additional inquiry prepared"


def _git_rev_parse(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _parse_items(values: Iterable[str]) -> tuple[str, ...]:
    items: list[str] = []
    for value in values:
        for item in str(value).split(","):
            stripped = item.strip()
            if stripped and _normalize(stripped) not in {"none", "not_supplied"}:
                items.append(stripped)
    return tuple(items)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
