from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_branch_refinement_artifact, parse_branch_refinement_finding, parse_ref_list


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a local SOP branch refinement artifact without creating branches or syncing remotes.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--artifact-id", default="branch_refinement_artifact", help="Stable artifact id.")
    parser.add_argument("--base-ref", required=True, help="Start commit bookend.")
    parser.add_argument("--head-ref", required=True, help="End commit bookend.")
    parser.add_argument("--target-moment", required=True, help="Moment being reconstructed.")
    parser.add_argument("--refinement-branch", help="Candidate branch name. The runtime does not create it.")
    parser.add_argument("--narrative-ref", action="append", default=[], help="Narrative state reference. Repeatable.")
    parser.add_argument("--state-ref", action="append", default=[], help="Reconstructed state reference. Repeatable.")
    parser.add_argument("--planned-ref", action="append", default=[], help="Planned specification reference. Repeatable.")
    parser.add_argument("--debug-inference", default="not_declared", help="Evidence-bounded debug inference summary.")
    parser.add_argument("--finding", action="append", default=[], help="id|kind|subject|description[|route][|evidence_refs]")
    parser.add_argument("--selection-result", default="preserve_periphery", help="merge_candidate, revise, preserve_periphery, reject, or outside.")
    parser.add_argument("--selection-reason", default="artifact emitted for review without merge authority", help="Reason for selection result.")
    parser.add_argument("--sync-status", default="disabled_no_remote_policy", help="Remote sync status.")
    parser.add_argument("--outside", default="", help="Comma-separated outside terms. Defaults to branch-refinement runtime outside.")
    parser.add_argument("--output", help="Optional output .sop path.")
    parser.add_argument("--graph", action="store_true", help="Render SOP-HG graph instead of compact artifact.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    artifact = build_branch_refinement_artifact(
        root,
        artifact_id=args.artifact_id,
        commit_bookend_start=args.base_ref,
        commit_bookend_end=args.head_ref,
        target_moment=args.target_moment,
        refinement_branch=args.refinement_branch,
        narrative_state_refs=tuple(args.narrative_ref),
        reconstructed_state_refs=tuple(args.state_ref),
        planned_specification_refs=tuple(args.planned_ref),
        debug_inference=args.debug_inference,
        findings=tuple(parse_branch_refinement_finding(finding) for finding in args.finding),
        selection_result=args.selection_result,
        selection_reason=args.selection_reason,
        sync_status=args.sync_status,
        outside=parse_ref_list(args.outside) if args.outside else (),
    )
    rendered = artifact.to_hypergraph().render() if args.graph else artifact.render()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
