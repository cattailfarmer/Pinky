from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


DEFAULT_OUTSIDE = (
    "hidden cognition",
    "exact hidden-state replay",
    "automatic branch creation",
    "remote synchronization",
    "merge without selection gate",
)


@dataclass(frozen=True)
class BranchRefinementFinding:
    finding_id: str
    finding_kind: str
    subject: str
    description: str
    route: str = "preserve_periphery"
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    @property
    def finding_key(self) -> str:
        return _safe_key(self.finding_id)

    def render(self, index: int) -> list[str]:
        lines = [
            f"  + [finding_{index:03d}_{self.finding_key}] is {self.finding_kind}",
            f"    = subject: {self.subject}",
            f"    = description: {self.description}",
            f"    = route: {self.route}",
        ]
        if self.evidence_refs:
            lines.append(f"    = evidence_refs: {', '.join(self.evidence_refs)}")
        return lines


@dataclass(frozen=True)
class BranchRefinementArtifact:
    artifact_id: str
    repo_root: str
    commit_bookend_start: str
    commit_bookend_end: str
    target_moment: str
    refinement_branch: str
    narrative_state_refs: tuple[str, ...] = field(default_factory=tuple)
    reconstructed_state_refs: tuple[str, ...] = field(default_factory=tuple)
    planned_specification_refs: tuple[str, ...] = field(default_factory=tuple)
    debug_inference: str = "not_declared"
    findings: tuple[BranchRefinementFinding, ...] = field(default_factory=tuple)
    selection_result: str = "preserve_periphery"
    selection_reason: str = "artifact emitted for review without merge authority"
    sync_status: str = "disabled_no_remote_policy"
    outside: tuple[str, ...] = DEFAULT_OUTSIDE

    @property
    def artifact_key(self) -> str:
        return _safe_key(self.artifact_id)

    @property
    def ready(self) -> bool:
        return bool(
            self.artifact_id
            and self.repo_root
            and self.commit_bookend_start
            and self.commit_bookend_end
            and self.target_moment
            and self.refinement_branch
            and self.selection_result
        )

    def render(self) -> str:
        lines = [
            "Subject: Branch Refinement Artifact",
            "",
            f"& [BranchRefinementArtifact:{self.artifact_key}] is a branch_refinement_artifact",
            f"  + [artifact_id] is {self.artifact_id}",
            f"  + [repo_root] is {self.repo_root}",
            f"  + [commit_bookend_start] is {self.commit_bookend_start}",
            f"  + [commit_bookend_end] is {self.commit_bookend_end}",
            f"  + [target_moment] is {self.target_moment}",
            f"  + [refinement_branch] is {self.refinement_branch}",
            "  + [branch_creation_status] is not_created_by_runtime",
            f"  + [selection_result] is {self.selection_result}",
            f"  + [selection_reason] is {self.selection_reason}",
            f"  + [sync_status] is {self.sync_status}",
            f"  + [debug_inference] is {self.debug_inference}",
        ]
        lines.extend(_render_refs("narrative_state_ref", self.narrative_state_refs))
        lines.extend(_render_refs("reconstructed_state_ref", self.reconstructed_state_refs))
        lines.extend(_render_refs("planned_specification_ref", self.planned_specification_refs))
        if self.findings:
            for index, finding in enumerate(self.findings, start=1):
                lines.extend(finding.render(index))
        else:
            lines.append("  + [finding_set] is empty")
        lines.append(f"  + [outside] is {', '.join(self.outside)}")
        lines.extend(
            [
                "",
                "(branch_refinement_artifact) :turn_moment_frame: /commit_bookends and branch_selection_gate/ |outside|",
                f"  + [turn_moment_frame] is {self.target_moment}",
                f"  + [commit_bookend_start] is {self.commit_bookend_start}",
                f"  + [commit_bookend_end] is {self.commit_bookend_end}",
                f"  + [branch_selection_gate] is {self.selection_result}",
                f"  |outside| {', '.join(self.outside)}",
            ]
        )
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = self.artifact_key
        artifact_node = HypergraphNode(
            f"N:artifact:{graph_id}",
            self.artifact_id,
            (("selection_result", self.selection_result), ("sync_status", self.sync_status)),
        )
        moment_node = HypergraphNode(f"N:event:{graph_id}_moment", self.target_moment)
        branch_node = HypergraphNode(
            f"N:branch:{_safe_key(self.refinement_branch)}",
            self.refinement_branch,
            (("creation_status", "not_created_by_runtime"),),
        )
        start_node = HypergraphNode(f"N:commit:{_safe_key(self.commit_bookend_start)}", self.commit_bookend_start)
        end_node = HypergraphNode(f"N:commit:{_safe_key(self.commit_bookend_end)}", self.commit_bookend_end)
        reentry_node = HypergraphNode(f"N:reentry:{graph_id}", "moment reconstruction packet")
        selection_node = HypergraphNode(
            f"N:policy:{graph_id}_selection_gate",
            self.selection_result,
            (("reason", self.selection_reason),),
        )
        outside_node = HypergraphNode("N:outside:moment_branch_refinement_boundary", ", ".join(self.outside))
        nodes: list[HypergraphNode] = [
            artifact_node,
            moment_node,
            branch_node,
            start_node,
            end_node,
            reentry_node,
            selection_node,
            outside_node,
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:span:{graph_id}",
                "span",
                (("moment", moment_node.key), ("start", start_node.key), ("end", end_node.key)),
            ),
            HypergraphEdge(
                f"E:branches:{graph_id}",
                "branches",
                (("reentry", reentry_node.key), ("branch", branch_node.key), ("artifact", artifact_node.key)),
                (("creation_status", "not_created_by_runtime"),),
            ),
            HypergraphEdge(
                f"E:captures:{graph_id}",
                "captures",
                (("artifact", artifact_node.key), ("moment", moment_node.key), ("reentry", reentry_node.key)),
            ),
            HypergraphEdge(
                f"E:selects:{graph_id}",
                "selects",
                (("artifact", artifact_node.key), ("gate", selection_node.key)),
            ),
            HypergraphEdge(
                f"E:blocks_sync:{graph_id}",
                "blocks_sync",
                (("branch", branch_node.key), ("outside", outside_node.key)),
                (("sync_status", self.sync_status),),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("artifact", artifact_node.key), ("outside", outside_node.key)),
            ),
        ]
        for index, ref in enumerate(self.narrative_state_refs, start=1):
            node = HypergraphNode(f"N:narrative:{_safe_key(ref)}", ref)
            nodes.append(node)
            edges.append(
                HypergraphEdge(
                    f"E:references:{graph_id}_narrative_{index:03d}",
                    "references",
                    (("artifact", artifact_node.key), ("narrative", node.key)),
                )
            )
        for index, ref in enumerate(self.reconstructed_state_refs, start=1):
            node = HypergraphNode(f"N:state:{_safe_key(ref)}", ref)
            nodes.append(node)
            edges.append(
                HypergraphEdge(
                    f"E:reconstructs:{graph_id}_state_{index:03d}",
                    "reconstructs",
                    (("reentry", reentry_node.key), ("state", node.key)),
                )
            )
        for index, ref in enumerate(self.planned_specification_refs, start=1):
            node = HypergraphNode(f"N:source:{_safe_key(ref)}", ref)
            nodes.append(node)
            edges.append(
                HypergraphEdge(
                    f"E:compares:{graph_id}_plan_{index:03d}",
                    "compares",
                    (("artifact", artifact_node.key), ("plan", node.key)),
                )
            )
        for index, finding in enumerate(self.findings, start=1):
            node = HypergraphNode(
                f"N:finding:{finding.finding_key}",
                finding.subject,
                (("finding_kind", finding.finding_kind), ("route", finding.route)),
            )
            nodes.append(node)
            edges.append(
                HypergraphEdge(
                    f"E:finds:{graph_id}_{index:03d}",
                    "finds",
                    (("artifact", artifact_node.key), ("finding", node.key)),
                    (("description", finding.description),),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.artifact_id} Branch Refinement Artifact",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG branch-refinement-artifact"),
                ("base_ref", self.commit_bookend_start),
                ("head_ref", self.commit_bookend_end),
                ("selection_result", self.selection_result),
            ),
            outside=self.outside,
        )


def build_branch_refinement_artifact(
    repo_root: str | Path,
    *,
    artifact_id: str,
    commit_bookend_start: str,
    commit_bookend_end: str,
    target_moment: str,
    refinement_branch: str | None = None,
    narrative_state_refs: Iterable[str] = (),
    reconstructed_state_refs: Iterable[str] = (),
    planned_specification_refs: Iterable[str] = (),
    debug_inference: str = "not_declared",
    findings: Iterable[BranchRefinementFinding] = (),
    selection_result: str = "preserve_periphery",
    selection_reason: str = "artifact emitted for review without merge authority",
    sync_status: str = "disabled_no_remote_policy",
    outside: Iterable[str] = DEFAULT_OUTSIDE,
) -> BranchRefinementArtifact:
    return BranchRefinementArtifact(
        artifact_id=artifact_id,
        repo_root=str(Path(repo_root)),
        commit_bookend_start=commit_bookend_start,
        commit_bookend_end=commit_bookend_end,
        target_moment=target_moment,
        refinement_branch=refinement_branch or f"codex/refine/{_safe_key(target_moment)}",
        narrative_state_refs=tuple(_parse_items(narrative_state_refs)),
        reconstructed_state_refs=tuple(_parse_items(reconstructed_state_refs)),
        planned_specification_refs=tuple(_parse_items(planned_specification_refs)),
        debug_inference=debug_inference,
        findings=tuple(findings),
        selection_result=selection_result,
        selection_reason=selection_reason,
        sync_status=sync_status,
        outside=tuple(_parse_items(outside)) or DEFAULT_OUTSIDE,
    )


def parse_branch_refinement_finding(value: str) -> BranchRefinementFinding:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 4:
        raise ValueError("finding must use id|kind|subject|description[|route][|evidence_refs]")
    evidence = parse_ref_list(parts[5]) if len(parts) > 5 else ()
    return BranchRefinementFinding(
        finding_id=parts[0],
        finding_kind=parts[1],
        subject=parts[2],
        description=parts[3],
        route=parts[4] if len(parts) > 4 and parts[4] else "preserve_periphery",
        evidence_refs=evidence,
    )


def parse_ref_list(value: str) -> tuple[str, ...]:
    return tuple(_parse_items((value,)))


def _render_refs(label: str, refs: tuple[str, ...]) -> list[str]:
    if not refs:
        return [f"  + [{label}_set] is empty"]
    return [f"  + [{label}_{index:03d}] is {ref}" for index, ref in enumerate(refs, start=1)]


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
