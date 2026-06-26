from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sop_node import FlowStateCounts, score_delta, score_state


class SymbolicRicciFlowTests(unittest.TestCase):
    def test_bsd_replay_before_state_keeps_high_irregularity_visible(self) -> None:
        before = FlowStateCounts(
            active_claims=1,
            source_linked_claims=1,
            claims_with_explicit_boundary=0,
            distinction_loss=3,
            authority_leak_count=1,
            unresolved_locks={
                "source_count": 1.0,
                "independence": 1.0,
                "upper_control": 1.0,
            },
            edges={
                "unsupported_analogizes": 1,
                "overbroad_transfers_to": 1,
                "depends_on_open_lock": 3,
                "supports_with_source_trace": 1,
            },
        )

        score = score_state(before)

        self.assertEqual(score.irregularity_total, 11.0)
        self.assertEqual(score.unresolved_lock_mass, 3.0)
        self.assertEqual(score.boundary_clarity, 0.0)
        self.assertEqual(score.source_coverage, 1.0)
        self.assertEqual(score.distinction_loss, 3)
        self.assertEqual(score.authority_leak_count, 1)

    def test_bsd_replay_after_state_separates_boundary_cleanup_from_lock_resolution(self) -> None:
        after = FlowStateCounts(
            active_claims=5,
            source_linked_claims=5,
            claims_with_explicit_boundary=5,
            unresolved_locks={
                "source_count": 1.0,
                "independence": 1.0,
                "upper_control": 1.0,
            },
            edges={
                "depends_on_open_lock": 3,
                "supports_with_source_trace": 5,
                "refines_distinction": 4,
                "blocks_proof_promotion": 1,
            },
        )

        score = score_state(after)

        self.assertEqual(score.irregularity_total, 0.0)
        self.assertEqual(score.unresolved_lock_mass, 3.0)
        self.assertEqual(score.boundary_clarity, 1.0)
        self.assertEqual(score.source_coverage, 1.0)
        self.assertEqual(score.distinction_loss, 0)
        self.assertEqual(score.authority_leak_count, 0)

    def test_delta_reports_cleanup_without_claiming_lock_mass_reduction(self) -> None:
        before = FlowStateCounts(
            active_claims=1,
            source_linked_claims=1,
            distinction_loss=3,
            authority_leak_count=1,
            unresolved_locks={"lock": 3.0},
            edges={
                "unsupported_analogizes": 1,
                "overbroad_transfers_to": 1,
                "depends_on_open_lock": 3,
                "supports_with_source_trace": 1,
            },
        )
        after = FlowStateCounts(
            active_claims=5,
            source_linked_claims=5,
            claims_with_explicit_boundary=5,
            unresolved_locks={"lock": 3.0},
            edges={
                "depends_on_open_lock": 3,
                "supports_with_source_trace": 5,
                "refines_distinction": 4,
                "blocks_proof_promotion": 1,
            },
        )

        delta = score_delta(before, after)

        self.assertEqual(delta.irregularity_delta, -11.0)
        self.assertEqual(delta.unresolved_lock_mass_delta, 0.0)
        self.assertEqual(delta.boundary_clarity_delta, 1.0)
        self.assertEqual(delta.source_coverage_delta, 0.0)
        self.assertEqual(delta.distinction_loss_delta, -3)
        self.assertEqual(delta.authority_leak_delta, -1)

    def test_zero_claim_state_has_zero_ratios(self) -> None:
        score = score_state(FlowStateCounts())

        self.assertEqual(score.boundary_clarity, 0.0)
        self.assertEqual(score.source_coverage, 0.0)

    def test_unknown_edge_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown Symbolic Ricci Flow edge"):
            score_state(FlowStateCounts(edges={"invented_edge": 1}))

    def test_negative_lock_weight_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unresolved lock weight cannot be negative"):
            score_state(FlowStateCounts(unresolved_locks={"bad_lock": -0.5}))


if __name__ == "__main__":
    unittest.main()
