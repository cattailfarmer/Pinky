from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import build_attention_tracking_record, parse_tracked_subject


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a SOP-HG attention tracker record.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--record-id", default="attention_tracker_seed", help="Stable tracking record id.")
    parser.add_argument("--current-session", type=int, default=2, help="Current session index.")
    parser.add_argument("--output", required=True, help="Output .hg.sop path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    record = build_attention_tracking_record(
        record_id=args.record_id,
        current_session=args.current_session,
        tracked_subjects=(
            parse_tracked_subject(
                tracker_id="track_that_semantics",
                subject_label="track that means attach an attention handle",
                reason="User clarified that tracking records being, relations, periphery, narrative, scan, and nearby correlations.",
                weight=6,
                session_id="2026-06-23",
                last_reaffirmed_session=2,
                native_context=("attention handle", "tracked subject", "session expiry"),
                periphery_context=("changelog review", "debug surface", "nearby correlations"),
                relations=("narrative layer", "sensitivity scan", "semantic correlation graph", "support balance"),
                narrative_refs=("current user clarification",),
                scan_refs=("events/scans/2026-06-23_attention_tracking_scan.hg.sop",),
                debug_refs=("platform/AttentionTracker.sop", "runtime/sop_node/attention_tracker.py"),
                open_questions=("how tracker reaffirmation should be surfaced in future manager turns",),
            ),
            parse_tracked_subject(
                tracker_id="unreaffirmed_worker_spool",
                subject_label="worker spool expansion while tracking support balance",
                reason="Useful nearby idea, but not reaffirmed for the active tracking subject.",
                weight=4,
                session_id="2026-06-23",
                last_reaffirmed_session=0,
                native_context=("worker spool",),
                periphery_context=("repo terminal", "manager hub"),
                relations=("spool master hub",),
                debug_refs=("platform/SpoolMasterHub.sop",),
            ),
            parse_tracked_subject(
                tracker_id="declared_period_changelog_review",
                subject_label="commit changelog review as tracking update source",
                reason="Declared longer watch because tracker updates should integrate with future commit-diff reflection.",
                weight=5,
                session_id="2026-06-23",
                last_reaffirmed_session=0,
                declared_period_sessions=4,
                native_context=("commit diff", "bookend reflection"),
                periphery_context=("narrative state", "tracked subject updates"),
                relations=("sensitivity scan", "meta-awareness repository"),
                scan_refs=("events/scans/2026-06-23_carried_support_balance_scan.hg.sop",),
            ),
        ),
    )
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = record.to_hypergraph().render()
    output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
