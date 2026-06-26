from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sop_node.lm_studio_agent_benchmark as lm_bench
from sop_node import (
    DiffFileChange,
    AttentionDirective,
    AttentionTrackingRecord,
    Reweighing,
    WorkerJob,
    PeripheryImpression,
    SupportProbe,
    build_attention_frame,
    build_attention_kernel_packet,
    build_aperture_reentry_springboard,
    build_branch_refinement_artifact,
    build_compiled_attention_packet,
    build_step_balance_walk,
    build_semantic_component,
    build_semantic_hash_index,
    build_semantic_hash_table,
    build_semantic_correlation_graph,
    build_support_balance,
    build_attention_tracking_record,
    build_boundary_faculty_inspection_record,
    build_direct_lmstudio_manager_context,
    build_hyperbolic_pants_topology_map,
    build_hyperbolic_corridor_navigation,
    build_security_honesty_governance_record,
    build_lmstudio_task_frame_candidate,
    build_math_bridge_map,
    build_seven_fold_pants_frame,
    build_sensitivity_scan,
    build_sensitivity_scan_from_changes,
    build_task_frame_launch_queue,
    build_trailing_checksum_review,
    build_turn_bookmark_from_scan,
    build_inference_state_trace,
    build_operating_loop_tick,
    build_periphery_continuity_run,
    build_viewfinder_snapshot,
    classify_layer,
    create_turn_spool,
    detect_direct_focus_bookends,
    parse_branch_refinement_finding,
    parse_periphery_terms,
    parse_edge_participants,
    parse_aperture_support,
    parse_boundary_term,
    parse_candidate_action,
    parse_candidate_claim,
    parse_correlation_cell,
    parse_corridor_frame,
    parse_curving_association,
    parse_directive,
    parse_faculty_field,
    parse_feedback_signal,
    parse_math_bridge_term,
    parse_fold_leg,
    parse_pants_leg,
    parse_periphery_run_frame,
    parse_reflection_consumption,
    parse_support_probe,
    parse_step_balance_observation,
    parse_topology_cell,
    parse_tracked_subject,
    scan_to_hypergraph,
    select_scaffold_profile,
    run_direct_lmstudio_manager,
    validate_lmstudio_manager_proposal,
)


class SensitivityScanTests(unittest.TestCase):
    def test_math_bridge_map_tracks_open_obligations(self) -> None:
        bridge = build_math_bridge_map(
            bridge_id="bsd_bridge_test",
            problem_name="Birch and Swinnerton-Dyer",
            proposition="test proposition",
            terms=(
                parse_math_bridge_term(
                    term_id="l_hand",
                    symbolic_term="L-hand collapse",
                    formal_object="order of vanishing",
                    problem_role="analytic side",
                    evidence_status="mapped_candidate",
                    proof_obligations=("define collapse", "avoid circularity"),
                ),
                parse_math_bridge_term(
                    term_id="unknown",
                    symbolic_term="phase key",
                    problem_role="unresolved bridge",
                ),
            ),
        )

        rendered = bridge.render()
        graph = bridge.to_hypergraph().render()
        self.assertTrue(bridge.ready)
        self.assertEqual(bridge.open_obligation_count, 2)
        self.assertEqual(bridge.weakest_terms[0].term_id, "unknown")
        self.assertIn("mapped_with_obligations", rendered)
        self.assertIn("keep_peripheral", rendered)
        self.assertIn("SOP-HG math-bridge-map", graph)

    def test_classify_layer_routes_touch_and_heat(self) -> None:
        self.assertEqual(classify_layer(0, 0), ("surface", "fade"))
        self.assertEqual(classify_layer(1, 3), ("hair", "notice"))
        self.assertEqual(classify_layer(2, 12), ("skin", "triangulate"))
        self.assertEqual(classify_layer(5, 24), ("pressure", "sustain"))
        self.assertEqual(classify_layer(11, 60), ("impact", "emphasize"))

    def test_scan_from_changes_emits_signals(self) -> None:
        changes = (
            DiffFileChange("platform/Alpha.sop", "M", additions=8, deletions=2),
            DiffFileChange("platform/Beta.sop", "M", additions=7, deletions=1),
        )
        scan = build_sensitivity_scan_from_changes(
            "F:/.sop",
            base_ref="HEAD~1",
            head_ref="HEAD",
            changes=changes,
            content_terms_by_path={
                "platform/Alpha.sop": ("attention", "chain", "bookend"),
                "platform/Beta.sop": ("attention", "scan", "bookend"),
            },
            scan_id="test_scan",
        )

        rendered = scan.render()
        attention = next(signal for signal in scan.signals if signal.subject_key == "attention")
        self.assertTrue(scan.ready)
        self.assertEqual(attention.touch_count, 2)
        self.assertIn(attention.layer, {"skin", "pressure"})
        self.assertIn("Sensitivity Scan Event", rendered)
        self.assertIn("signal_", rendered)

    def test_scan_collects_untracked_sop_files_without_head(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
            folder = root / "platform"
            folder.mkdir()
            (folder / "Seed.sop").write_text("Subject: Seed\n\n& [Seed] is attention chain scan\n", encoding="utf-8")

            scan = build_sensitivity_scan(root, scan_id="untracked_scan")

            self.assertEqual(len(scan.changes), 1)
            self.assertEqual(scan.changes[0].status, "A")
            self.assertTrue(scan.signals)

    def test_scan_renders_sop_hypergraph_record(self) -> None:
        changes = (
            DiffFileChange("platform/Alpha.sop", "M", additions=8, deletions=2),
            DiffFileChange("platform/Beta.sop", "M", additions=7, deletions=1),
        )
        scan = build_sensitivity_scan_from_changes(
            "F:/.sop",
            base_ref="HEAD~1",
            head_ref="HEAD",
            changes=changes,
            content_terms_by_path={
                "platform/Alpha.sop": ("attention", "chain", "bookend"),
                "platform/Beta.sop": ("attention", "scan", "bookend"),
            },
            scan_id="test_scan",
        )

        graph = scan_to_hypergraph(scan)
        rendered = graph.render()
        touch_edge = next(edge for edge in graph.edges if edge.key == "E:touches:attention")
        parsed = parse_edge_participants(touch_edge.render(graph.graph_key))

        self.assertTrue(graph.ready)
        self.assertIn("SOP-HG graph", rendered)
        self.assertGreaterEqual(len(touch_edge.participants), 3)
        self.assertIn(("signal", "N:signal:attention"), parsed)
        self.assertIn(("file", "N:file:platform_Alpha_sop"), parsed)

    def test_attention_frame_renders_focus_periphery_and_draw_edges(self) -> None:
        frame = build_attention_frame(
            frame_id="test_attention_frame",
            narrative_moment="Periphery draws focus through correlation and causal hypothesis.",
            operation_stage="between_steps",
            focus_terms=("focus",),
            periphery_terms=("periphery", "narrative"),
            correlation_pairs=(("periphery", "focus"),),
            causal_pairs=(("narrative", "focus"),),
        )
        graph = frame.to_hypergraph()
        rendered = graph.render()

        self.assertTrue(frame.ready)
        self.assertTrue(graph.ready)
        self.assertIn("N:focus:focus", rendered)
        self.assertIn("N:periphery:periphery", rendered)
        self.assertIn("E:correlates:periphery_to_focus_correlation", rendered)
        self.assertIn("E:draws_attention:periphery_draws_focus", rendered)
        self.assertIn("E:causes:narrative_causes_focus", rendered)
        self.assertIn("causal_status=hypothesis", rendered)

    def test_viewfinder_snapshot_renders_reweigh_and_reframe_graph(self) -> None:
        snapshot = build_viewfinder_snapshot(
            snapshot_id="test_viewfinder",
            narrative_token="Codex compiles attention graph reflection into a structured snapshot.",
            desired_shape="viewfinder attention graph",
            commit_frame="HEAD",
            previous_reflections=("prior_focus_periphery_frame",),
            current_observations=("new_narrative_token",),
            reweighings=(Reweighing("narrative", 2, 5, "new observation increased narrative weight"),),
        )
        graph = snapshot.to_hypergraph()
        rendered = graph.render()

        self.assertTrue(snapshot.ready)
        self.assertTrue(graph.ready)
        self.assertIn("N:viewfinder:test_viewfinder", rendered)
        self.assertIn("N:commit:HEAD", rendered)
        self.assertIn("N:reflection:prior_focus_periphery_frame", rendered)
        self.assertIn("N:observation:new_narrative_token", rendered)
        self.assertIn("E:reweighs:narrative", rendered)
        self.assertIn("E:reframes:narrative", rendered)

    def test_spool_hub_creates_turn_tree_without_launching_workers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            spool = create_turn_spool(
                repo_root=temporary_directory,
                turn_id="test_turn",
                objective="Coordinate local workers from a master hub.",
                narrative_token="Codex is master over a visible worker spool.",
                workers=(
                    WorkerJob(
                        "lm_lane",
                        "lm_studio_cli",
                        "Local LM Studio reflection lane.",
                        status="blocked",
                        launch_command="blocked: no launch policy",
                    ),
                    WorkerJob(
                        "codex_lane",
                        "codex_cli",
                        "Codex CLI worker lane.",
                        status="deferred",
                        launch_command="deferred: explicit launch required",
                    ),
                ),
            )
            root = Path(spool.root)
            index = (root / "index.html").read_text(encoding="utf-8")

            self.assertTrue(spool.ready)
            self.assertTrue((root / "TurnSpool.sop").exists())
            self.assertTrue((root / "workers" / "lm_lane" / "WorkerJob.sop").exists())
            self.assertIn("lm_studio_cli", index)
            self.assertIn("codex_cli", index)
            self.assertIn("blocked", index)
            self.assertIn("deferred", index)
            self.assertIn("no launch policy", index)

    def test_semantic_hash_index_points_to_components_and_periphery_impressions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            platform = root / "platform"
            platform.mkdir()
            component_path = platform / "PeripheryRepository.sop"
            component_path.write_text(
                "\n".join(
                    (
                        "Subject: Periphery Repository",
                        "",
                        "& [PeripheryRepository] is slow background realization",
                        "  + [inference_shadow] is visible peripheral evidence",
                    )
                ),
                encoding="utf-8",
            )
            component = build_semantic_component("platform/PeripheryRepository.sop", component_path.read_text(encoding="utf-8"))
            impression = PeripheryImpression(
                narrative_subject="semantic_hash_index",
                periphery_term="inference_shadow",
                relation_back="shadow term tugged attention back to periphery",
                hiding_behind="primary attention formation",
                turned_aspect="hash pointer",
                nearby_association="semantic landscape",
                evidence_pointers=(component.pointer_key,),
                weight=4,
            )
            index = build_semantic_hash_index(
                root,
                index_id="test_semantic_hash_index",
                paths=("platform/PeripheryRepository.sop",),
                impressions=(impression,),
            )
            graph = index.to_hypergraph()
            rendered = graph.render()

            self.assertTrue(index.ready)
            self.assertTrue(graph.ready)
            self.assertEqual(len(index.components), 1)
            self.assertEqual(len(index.components[0].content_hash), 64)
            self.assertIn("N:index:test_semantic_hash_index", rendered)
            self.assertIn("H:component:", rendered)
            self.assertIn("E:indexes:", rendered)
            self.assertIn("E:hides_behind:", rendered)
            self.assertIn("E:entangles:", rendered)

    def test_semantic_hash_table_supports_exact_strict_and_permissive_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            platform = root / "platform"
            platform.mkdir()
            component_path = platform / "SemanticHashIndex.sop"
            component_path.write_text(
                "\n".join(
                    (
                        "Subject: Semantic Hash Index",
                        "",
                        "& [SemanticHashIndex] is semantic pointer indexing",
                        "  + [permissive_lookup] is inclusive retrieval",
                    )
                ),
                encoding="utf-8",
            )
            index = build_semantic_hash_index(
                root,
                index_id="test_semantic_table_index",
                paths=("platform/SemanticHashIndex.sop",),
                impressions=(
                    PeripheryImpression(
                        narrative_subject="semantic_hash_table",
                        periphery_term="permissive_lookup",
                        relation_back="partial dimensions retrieve candidates",
                        hiding_behind="exact pointer",
                        turned_aspect="multi dimensional key",
                        nearby_association="semantic index",
                        weight=4,
                    ),
                ),
            )
            table = build_semantic_hash_table(index, table_id="test_semantic_table")
            component = index.components[0]
            exact_results = table.lookup({"content_hash": component.content_hash}, mode="exact")
            strict_results = table.lookup({"subject": "Semantic Hash Index", "term": "permissive_lookup"}, mode="strict")
            permissive_results = table.lookup({"term": "permissive_lookup"}, mode="permissive")
            graph = table.to_hypergraph(query={"term": "permissive_lookup"}, mode="permissive")
            rendered = graph.render()

            self.assertTrue(table.ready)
            self.assertTrue(graph.ready)
            self.assertIn(("term", "permissive_lookup"), table.buckets)
            self.assertEqual(exact_results[0].pointer, component.pointer_key)
            self.assertTrue(any(result.entry.kind == "component" for result in strict_results))
            self.assertGreaterEqual(len(permissive_results), 2)
            self.assertIn("N:table:test_semantic_table", rendered)
            self.assertIn("E:intersects:", rendered)
            self.assertIn("E:retrieves:", rendered)

    def test_semantic_correlation_graph_weights_buckets_and_directive_tilt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            platform = root / "platform"
            platform.mkdir()
            (platform / "AttentionDirective.sop").write_text(
                "\n".join(
                    (
                        "Subject: Attention Directive",
                        "",
                        "& [AttentionDirective] is attention correlation rigging",
                        "  + [semantic_hash_table] is bucketed attention direction",
                    )
                ),
                encoding="utf-8",
            )
            (platform / "SemanticHashTable.sop").write_text(
                "\n".join(
                    (
                        "Subject: Semantic Hash Table",
                        "",
                        "& [SemanticHashTable] is bucketed semantic correlation",
                        "  + [attention_directive] is directional tilt",
                    )
                ),
                encoding="utf-8",
            )
            index = build_semantic_hash_index(
                root,
                index_id="test_semantic_correlation_index",
                paths=("platform/AttentionDirective.sop", "platform/SemanticHashTable.sop"),
            )
            table = build_semantic_hash_table(index, table_id="test_semantic_correlation_table")
            directive = parse_directive(
                directive_id="test_attention_directive",
                purpose="Associate attention directive with semantic hash table through correlation.",
                identified="attention_directive_capture",
                inside=("attention", "correlation"),
                boundary=("proof",),
                subject_a="Attention Directive",
                subject_b="Semantic Hash Table",
                tilt=(("term", "semantic"),),
                boost=5,
            )
            graph = build_semantic_correlation_graph(
                table,
                graph_id="test_semantic_correlation_graph",
                directives=(directive,),
                max_correlations=12,
            )
            rendered = graph.to_hypergraph(limit=8).render()
            tilted = [correlation for correlation in graph.correlations if correlation.directive_weight > 0]

            self.assertTrue(graph.ready)
            self.assertIsInstance(directive, AttentionDirective)
            self.assertTrue(tilted)
            self.assertGreaterEqual(tilted[0].total_weight, tilted[0].base_weight)
            self.assertIn("N:directive:test_attention_directive", rendered)
            self.assertIn("E:tilts:", rendered)
            self.assertIn("E:correlates:", rendered)
            self.assertIn("base_weight", rendered)
            self.assertIn("directive_weight", rendered)

    def test_support_balance_classifies_native_carried_weak_absent_and_contradicting(self) -> None:
        balance = build_support_balance(
            balance_id="test_support_balance",
            active_subject="attention support balance",
            subject_terms=("attention", "support", "balance", "native"),
            periphery_terms=("rails", "walking", "association"),
            probes=(
                parse_support_probe(
                    support_id="native_support",
                    support_name="Native support",
                    terms=("attention", "support"),
                ),
                parse_support_probe(
                    support_id="weak_metaphor",
                    support_name="Weak walking metaphor",
                    terms=("walking", "gait"),
                ),
                parse_support_probe(
                    support_id="carried_governance",
                    support_name="Carried governance",
                    terms=("governance", "source", "preservation"),
                    carried_from="ReasoningFramework",
                ),
                parse_support_probe(
                    support_id="absent_shape",
                    support_name="Absent shape",
                    terms=("unseen", "unrelated"),
                ),
                parse_support_probe(
                    support_id="contradicting_projection",
                    support_name="Contradicting projection",
                    terms=("attention", "override"),
                    carried_from="agent habit risk",
                    contradicts=True,
                ),
            ),
        )
        statuses = {observation.probe.support_id: observation.fit_status for observation in balance.observations}
        graph = balance.to_hypergraph()
        rendered = graph.render()

        self.assertTrue(balance.ready)
        self.assertTrue(graph.ready)
        self.assertIsInstance(balance.observations[0].probe, SupportProbe)
        self.assertEqual(statuses["native_support"], "native")
        self.assertEqual(statuses["weak_metaphor"], "weak")
        self.assertEqual(statuses["carried_governance"], "carried")
        self.assertEqual(statuses["absent_shape"], "absent")
        self.assertEqual(statuses["contradicting_projection"], "contradicting")
        self.assertIn("N:balance:test_support_balance", rendered)
        self.assertIn("E:imports:carried_governance", rendered)
        self.assertIn("E:fits:native_support_subject_attention", rendered)
        self.assertIn("E:stabilizes:native_support", rendered)
        self.assertIn("E:distorts:contradicting_projection", rendered)
        self.assertIn("balance_effect", rendered)

    def test_attention_tracker_expires_without_reaffirmation_and_honors_declared_period(self) -> None:
        reaffirmed = parse_tracked_subject(
            tracker_id="reaffirmed_tracker",
            subject_label="track that semantics",
            reason="current session reaffirmed the tracker",
            weight=6,
            last_reaffirmed_session=2,
            native_context=("tracking", "attention"),
            periphery_context=("debug surface",),
            relations=("narrative", "scan"),
            narrative_refs=("current turn",),
            scan_refs=("events/scans/test.hg.sop",),
        )
        expired = parse_tracked_subject(
            tracker_id="expired_tracker",
            subject_label="unreaffirmed default tracker",
            reason="default session tracker was not reaffirmed",
            weight=4,
            last_reaffirmed_session=0,
            periphery_context=("stale association",),
        )
        declared = parse_tracked_subject(
            tracker_id="declared_period_tracker",
            subject_label="commit changelog tracker",
            reason="declared period keeps this tracker live",
            weight=5,
            last_reaffirmed_session=0,
            declared_period_sessions=4,
            relations=("commit diff", "sensitivity scan"),
        )
        record = build_attention_tracking_record(
            record_id="test_attention_tracking",
            current_session=2,
            tracked_subjects=(reaffirmed, expired, declared),
        )
        graph = record.to_hypergraph()
        rendered = graph.render()
        statuses = {tracked.tracker_id: tracked.status_at(record.current_session) for tracked in record.tracked_subjects}

        self.assertTrue(record.ready)
        self.assertTrue(graph.ready)
        self.assertIsInstance(record, AttentionTrackingRecord)
        self.assertEqual(statuses["reaffirmed_tracker"], "active")
        self.assertEqual(statuses["expired_tracker"], "expired")
        self.assertEqual(statuses["declared_period_tracker"], "active")
        self.assertEqual(expired.effective_weight_at(record.current_session), 0)
        self.assertIn("N:tracker:test_attention_tracking", rendered)
        self.assertIn("E:reaffirms:reaffirmed_tracker", rendered)
        self.assertIn("E:expires:expired_tracker", rendered)
        self.assertIn("period_kind: declared_period", rendered)

    def test_turn_bookmark_compares_planned_terms_and_flags_potential(self) -> None:
        changes = (
            DiffFileChange("platform/AttentionWeightScale.sop", "A", additions=40, deletions=0),
            DiffFileChange("events/indexes/generated_scan.hg.sop", "M", additions=96, deletions=12),
        )
        scan = build_sensitivity_scan_from_changes(
            "F:/.sop",
            base_ref="HEAD~1",
            head_ref="HEAD",
            changes=changes,
            content_terms_by_path={
                "platform/AttentionWeightScale.sop": ("attention", "weight", "scale", "turn", "bookmark"),
                "events/indexes/generated_scan.hg.sop": ("generated", "index", "attention"),
            },
            scan_id="test_turn_bookmark_scan",
        )
        bookmark = build_turn_bookmark_from_scan(
            "F:/.sop",
            scan=scan,
            planned_terms=("attention", "missing plan"),
            narrative_terms=("scale",),
            bookmark_id="test_turn_bookmark",
        )
        graph = bookmark.to_hypergraph()
        rendered = graph.render()
        kinds = {finding.finding_kind for finding in bookmark.findings}

        self.assertTrue(bookmark.ready)
        self.assertTrue(graph.ready)
        self.assertIn("unique_accomplishment", kinds)
        self.assertIn("missed_work", kinds)
        self.assertIn("mistake", kinds)
        self.assertIn("N:bookmark:test_turn_bookmark", rendered)
        self.assertIn("E:misses:", rendered)
        self.assertIn("E:flags:", rendered)
        self.assertIn("E:accomplishes:", rendered)

    def test_inference_state_trace_renders_reentry_packet(self) -> None:
        trace = build_inference_state_trace(
            "F:/.sop",
            base_ref="HEAD~1",
            head_ref="HEAD",
            target_moment="attention weight scale turn bookmark",
            sop_state_refs=("platform/Attention.sop", "state/CurrentFocalPoint.sop"),
            narrative_refs=("events/periphery_stream/example.hg.sop",),
            planned_specification_refs=("platform/source_documents/example/Source.sop",),
            weight_intersection_refs=("events/bookmarks/example.hg.sop", "platform/AttentionWeightScale.sop"),
            question="What semantic shape was active?",
            trace_id="test_inference_state_trace",
        )
        graph = trace.to_hypergraph()
        rendered = graph.render()

        self.assertTrue(trace.ready)
        self.assertTrue(graph.ready)
        self.assertIn("N:reentry:test_inference_state_trace", rendered)
        self.assertIn("E:reenters:test_inference_state_trace", rendered)
        self.assertIn("E:reconstructs:test_inference_state_trace_state_001", rendered)
        self.assertIn("determinism_scope", rendered)

    def test_attention_kernel_packet_layers_faculty_names_identity_balance_and_impulse(self) -> None:
        packet = build_attention_kernel_packet(
            packet_id="test_attention_kernel",
            focus_subject="attention kernel runtime",
            job_need="emit compact packet with balance and impulse",
            selected_patterns=(
                "SecurityHonestyGovernance",
                "BoundaryFacultyInspection",
                "LocalIdentityConsumption",
                "FacultyAttentionFieldNaming",
                "AttentionBalanceCenter",
            ),
            impulse="follow connected fabric and weave the runtime packet",
            focus_terms=("kernel", "runtime", "packet"),
            periphery_terms=("balance", "impulse", "identity", "field"),
        )
        rendered = packet.render()
        graph = packet.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(packet.ready)
        self.assertTrue(graph.ready)
        self.assertEqual(packet.balance_score, "stable")
        self.assertIn("(honesty_faculty) :claim: /distinction/ |uncertainty|", rendered)
        self.assertIn("(security_faculty) :assignment: /safe_boundary_line/ |risk|", rendered)
        self.assertIn("identity_scope", rendered)
        self.assertIn("faculty_fields", rendered)
        self.assertIn("impulse", rendered)
        self.assertIn("N:field:honesty_faculty_claim_distinction_uncertainty", graph_rendered)
        self.assertIn("E:preflights:test_attention_kernel", graph_rendered)
        self.assertIn("E:alerts:test_attention_kernel_balance", graph_rendered)

    def test_attention_kernel_detects_namespace_collision_and_records_consumption(self) -> None:
        field = parse_faculty_field("review_faculty:claim:distinction:uncertainty:review truth account")
        consumption = parse_reflection_consumption(
            "events/periphery_stream/example.hg.sop|foreign_worker|F_sop|commit:abc123|compiled|local_consumption"
        )
        packet = build_attention_kernel_packet(
            packet_id="test_attention_kernel_collision",
            focus_subject="collision watch",
            job_need="detect duplicate field labels",
            selected_patterns=("FocusZoom", "FocusZoom"),
            faculty_fields=(field,),
            reflection_consumptions=(consumption,),
            impulse="notice the wobble before packet emission",
            periphery_terms=("collision",),
        )
        rendered = packet.render()
        graph_rendered = packet.to_hypergraph().render()

        self.assertTrue(packet.namespace_collisions)
        self.assertEqual(packet.balance_score, "wobbling")
        self.assertIn("namespace_collision", rendered)
        self.assertIn("events/periphery_stream/example.hg.sop", rendered)
        self.assertIn("consumption_proof: commit:abc123", rendered)
        self.assertIn("E:consumes:test_attention_kernel_collision_001", graph_rendered)
        self.assertIn("E:disambiguates:test_attention_kernel_collision_001", graph_rendered)

    def test_step_balance_walk_settles_steps_and_selects_next_motion(self) -> None:
        walk = build_step_balance_walk(
            walk_id="test_step_balance_walk",
            focus_subject="continuous momentum in balance",
            job_need="settle each step and name the next step",
            impulse="walk the connected fabric without tiptoeing",
            observations=(
                parse_step_balance_observation(
                    "read_state|Read focal point and manager queue|stable|add runtime gait|none|continue|stable|state/CurrentFocalPoint.sop,planning/project_manager/Manager_State.sop|balance,impulse"
                ),
                parse_step_balance_observation(
                    "wire_runtime|Export runtime and tests|watch|validate gait|runtime_gap|continue_with_watch|watch|runtime/sop_node/step_balance_walk.py|tests,package"
                ),
            ),
        )
        rendered = walk.render()
        graph = walk.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(walk.ready)
        self.assertTrue(graph.ready)
        self.assertEqual(walk.overall_balance, "watch")
        self.assertEqual(walk.momentum_state, "flowing_with_watch")
        self.assertIn("next_step: validate gait", rendered)
        self.assertIn("momentum_effect: continue_with_watch", rendered)
        self.assertIn("N:walk:test_step_balance_walk", graph_rendered)
        self.assertIn("E:settles:read_state", graph_rendered)
        self.assertIn("E:advances:wire_runtime", graph_rendered)
        self.assertIn("E:alerts:wire_runtime_runtime_gap", graph_rendered)

    def test_periphery_continuity_run_detects_run_state_from_rolling_periphery(self) -> None:
        continuity_run = build_periphery_continuity_run(
            run_id="test_periphery_continuity_run",
            focus_subject="continuity periphery run",
            run_direction="forward",
            horizon_hint="runtime validation horizon",
            impulse="run the path between stable periphery markers",
            frames=(
                parse_periphery_run_frame(
                    "frame_a|runtime continuity path opens|forward|balance,tests,source|repo_state,current_focus|state/CurrentFocalPoint.sop"
                ),
                parse_periphery_run_frame(
                    "frame_b|runtime continuity path validates|forward|balance,tests,periphery|repo_state,current_focus|runtime/tests/test_sensitivity_scan.py"
                ),
                parse_periphery_run_frame(
                    "frame_c|runtime continuity path commits|forward|balance,commit,periphery|repo_state,current_focus|events/periphery_stream/example.hg.sop"
                ),
            ),
        )
        rendered = continuity_run.render()
        graph = continuity_run.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(continuity_run.ready)
        self.assertTrue(graph.ready)
        self.assertTrue(continuity_run.focus_chain_coherent)
        self.assertEqual(continuity_run.periphery_continuity, "stable")
        self.assertEqual(continuity_run.run_state, "run")
        self.assertEqual(continuity_run.checkpoint_pressure, "reduced")
        self.assertIn("+ [run_state] is run", rendered)
        self.assertIn("shared_stable_markers: current_focus, repo_state", rendered)
        self.assertIn("N:run:test_periphery_continuity_run", graph_rendered)
        self.assertIn("E:rolls:frame_a_frame_b", graph_rendered)
        self.assertIn("E:sees_horizon:test_periphery_continuity_run", graph_rendered)

    def test_periphery_continuity_run_rebalances_when_periphery_breaks(self) -> None:
        continuity_run = build_periphery_continuity_run(
            run_id="test_periphery_continuity_break",
            focus_subject="broken periphery run",
            run_direction="forward",
            frames=(
                parse_periphery_run_frame("frame_a|focus path opens|forward|balance|repo_state"),
                parse_periphery_run_frame("frame_b|unrelated action drifts|sideways|remote_sync|network_state"),
            ),
        )

        self.assertEqual(continuity_run.periphery_continuity, "broken")
        self.assertEqual(continuity_run.run_state, "rebalance")
        self.assertEqual(continuity_run.run_balance, "wobbling")

    def test_scaffold_compile_selects_runtime_packet_and_balance_alert(self) -> None:
        packet = build_compiled_attention_packet(
            packet_id="test_minimal_scaffold_compile",
            job_need="build runtime command with tests and commit evidence",
            output_target="compiled attention packet SOP record",
            periphery_terms=parse_periphery_terms("source evidence, tests, outside markers"),
            source_refs=("platform/AttentionScaffoldCompiler.sop",),
        )
        rendered = packet.render()

        self.assertTrue(packet.ready)
        self.assertEqual(select_scaffold_profile(packet.job_need).scaffold_profile, "implementation_scaffold")
        self.assertEqual(packet.scaffold_profile, "implementation_scaffold")
        self.assertEqual(packet.balance_score, "stable")
        self.assertEqual(packet.balance_alert, "none")
        self.assertEqual(packet.frame_reference_integrity, "not_required")
        self.assertIn("& [CompiledAttentionPacket:test_minimal_scaffold_compile]", rendered)
        self.assertIn("(compiled_attention_packet)", rendered)
        self.assertIn("+ [balance_alert] is none", rendered)
        self.assertIn("+ [frame_reference_integrity] is not_required", rendered)

    def test_scaffold_compile_flags_frame_reference_and_risk(self) -> None:
        packet = build_compiled_attention_packet(
            packet_id="test_scaffold_compile_frame_risk",
            job_need="inspect boundary identity permission security honesty in a game ui simulation for authority proof risk",
            output_target="scaffold risk review",
            periphery_terms=parse_periphery_terms("presented frame, source marker"),
        )
        graph = packet.to_hypergraph()
        rendered_graph = graph.render()

        self.assertTrue(packet.ready)
        self.assertEqual(packet.scaffold_profile, "boundary_inspection_scaffold")
        self.assertEqual(packet.balance_score, "watch")
        self.assertEqual(packet.balance_alert, "proof_or_authority_pressure")
        self.assertEqual(packet.frame_reference_integrity, "required_and_supported")
        self.assertTrue(graph.ready)
        self.assertIn("N:frame_reference:test_scaffold_compile_frame_risk", rendered_graph)
        self.assertIn("E:checks_balance:test_scaffold_compile_frame_risk", rendered_graph)
        self.assertIn("E:checks_frame:test_scaffold_compile_frame_risk", rendered_graph)

    def test_branch_refinement_artifact_renders_local_candidate_without_sync(self) -> None:
        finding = parse_branch_refinement_finding(
            "missed_review|missed_work|commit integrity review|review artifact was added one turn later|preserve_periphery|events/bookmarks/example.hg.sop"
        )
        artifact = build_branch_refinement_artifact(
            "C:\\Project\\Pinky",
            artifact_id="test_branch_refinement_artifact",
            commit_bookend_start="abc123",
            commit_bookend_end="def456",
            target_moment="moment branch refinement commit integrity",
            refinement_branch="codex/refine/moment-branch-integrity",
            narrative_state_refs=("events/bookmarks/example.hg.sop",),
            reconstructed_state_refs=("state/CurrentFocalPoint.sop",),
            planned_specification_refs=("platform/MomentAwarenessBranchRefinement.sop",),
            debug_inference="later reflection repaired missing integrity review without rewriting history",
            findings=(finding,),
            selection_result="preserve_periphery",
            selection_reason="useful later insight but not original awareness",
        )
        rendered = artifact.render()
        graph = artifact.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(artifact.ready)
        self.assertTrue(graph.ready)
        self.assertIn("+ [branch_creation_status] is not_created_by_runtime", rendered)
        self.assertIn("+ [sync_status] is disabled_no_remote_policy", rendered)
        self.assertIn("+ [selection_result] is preserve_periphery", rendered)
        self.assertIn("later reflection repaired missing integrity review", rendered)
        self.assertIn("E:span:test_branch_refinement_artifact", graph_rendered)
        self.assertIn("E:branches:test_branch_refinement_artifact", graph_rendered)
        self.assertIn("E:blocks_sync:test_branch_refinement_artifact", graph_rendered)

    def test_branch_refinement_finding_requires_minimal_fields(self) -> None:
        with self.assertRaises(ValueError):
            parse_branch_refinement_finding("too|short|only")

    def test_trailing_checksum_review_detects_bookends_and_zones(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
            platform = root / ".sop" / "platform"
            platform.mkdir(parents=True)
            subject = platform / "TrailingChecksumProbe.sop"
            subject.write_text(
                "Subject: Probe\n\n& [Probe] is initial attention checksum\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", ".sop"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "seed"],
                check=True,
                capture_output=True,
            )
            subject.write_text(
                "\n".join(
                    (
                        "Subject: Probe",
                        "",
                        "& [Probe] is trailing checksum attention review",
                        "  + [hot_zone] is checksum runtime",
                        "  + [latent_depth_candidate] is delayed review",
                        "  + [outside] is without hidden replay",
                    )
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", ".sop"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "direct focus"],
                check=True,
                capture_output=True,
            )

            start_ref, end_ref = detect_direct_focus_bookends(root)
            review = build_trailing_checksum_review(
                root,
                review_id="test_trailing_checksum_review",
                planned_terms=("checksum runtime",),
                narrative_terms=("latent depth candidate",),
                review_turn="test_review_turn",
            )
            rendered = review.render()
            graph = review.to_hypergraph()
            graph_rendered = graph.render()

        self.assertTrue(review.ready)
        self.assertTrue(graph.ready)
        self.assertEqual(review.commit_bookend_start, start_ref)
        self.assertEqual(review.commit_bookend_end, end_ref)
        self.assertEqual(review.one_turn_lag, "one_turn")
        self.assertTrue(review.zones)
        self.assertNotIn("without", {zone.signal_key for zone in review.zones})
        self.assertIn("+ [direct_focus_turn] is", rendered)
        self.assertIn("+ [checksum_disposition] is", rendered)
        self.assertIn("trailing_reflection", rendered)
        self.assertIn("E:trails:", graph_rendered)
        self.assertIn("E:checksums:test_trailing_checksum_review", graph_rendered)

    def test_aperture_reentry_springboard_reads_focal_point_and_supports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            state = root / ".sop" / "state"
            state.mkdir(parents=True)
            focal_point = state / "CurrentFocalPoint.sop"
            focal_point.write_text(
                "\n".join(
                    (
                        "Subject: Current Focal Point",
                        "",
                        "& [CurrentFocalPoint] is active focus",
                        "  + [focus_subject] is aperture reentry runtime selection",
                        "  + [focus_mode] is mixed_focus",
                        "  + [inside] is focal point, support draw, and close pass",
                        "  + [boundary] is close before durable narrative or subject declarations",
                        "  + [outside] is hidden state, worker mutation, and unbounded periphery",
                        "  + [active_reflection] is tick_020",
                        "  + [open_question] is how to emit a springboard",
                    )
                ),
                encoding="utf-8",
            )
            supports = (
                parse_aperture_support(
                    "tick_020|operating loop tick 020|events/operating_loop/tick_020.sop|task_handoff|6|what next focus should survive reentry"
                ),
                parse_aperture_support(
                    "aperture_cycle|ApertureReentryCycle contract|platform/ApertureReentryCycle.sop|open_close_sequence|9|which cycle steps must be preserved"
                ),
            )

            springboard = build_aperture_reentry_springboard(
                focal_point_path=focal_point,
                supports=supports,
                cycle_id="test_aperture_reentry_springboard",
            )
            rendered = springboard.render()
            graph = springboard.to_hypergraph()
            graph_rendered = graph.render()

        self.assertTrue(springboard.ready)
        self.assertTrue(graph.ready)
        self.assertEqual(springboard.depth_adjustment, "wide")
        self.assertIn("+ [focal_subject] is aperture reentry runtime selection", rendered)
        self.assertIn("+ [close_pass] is compact reentry_springboard", rendered)
        self.assertIn("second_pass_narrative_prompt_001", rendered)
        self.assertIn("subject_declaration_prompt_001", rendered)
        self.assertIn("E:opens:test_aperture_reentry_springboard", graph_rendered)
        self.assertIn("E:closes:test_aperture_reentry_springboard", graph_rendered)
        self.assertIn("E:springboards:test_aperture_reentry_springboard", graph_rendered)

    def test_hyperbolic_pants_topology_map_emits_cells_orbit_and_navigation(self) -> None:
        topology_map = build_hyperbolic_pants_topology_map(
            map_id="test_topology_map",
            focus_subject="topology map runtime selection",
            focal_terms=("focal_cell", "semantic_topology_map", "return_anchor"),
            periphery_cells=(
                parse_topology_cell("aperture|Aperture reentry springboard|reentry|springboard_to_map|7|5|events/periphery_stream/aperture.sop"),
                parse_topology_cell("boundary|Outside boundary|boundary|bounds_proxy|5|4|platform/HyperbolicPantsAttentionMap.sop"),
                parse_topology_cell("dimension|Dimensional orbit|dimension|orbits_focus|4|4|platform/PeripheryDimensionalProbe.sop"),
            ),
            pants_legs=(
                parse_pants_leg("leg_aperture|focal_cell|aperture|springboard_to_map|9|semantic proxy only"),
                parse_pants_leg("leg_boundary|focal_cell|boundary|bounds_proxy|8|keeps hidden geometry outside"),
                parse_pants_leg("leg_dimension|focal_cell|dimension|orbits_focus|7|distinct dimensions only"),
            ),
            purpose="map focal meaning and sparse periphery for navigation",
        )
        rendered = topology_map.render()
        graph = topology_map.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(topology_map.ready)
        self.assertTrue(graph.ready)
        self.assertEqual(topology_map.dimensionality_count, 3)
        self.assertEqual(topology_map.scale, "normal")
        self.assertIn("+ [adjacency_ring] is aperture, boundary, dimension", rendered)
        self.assertIn("transformer_hypergeometry_proxy] is visible semantic topology only", rendered)
        self.assertIn("E:maps:test_topology_map", graph_rendered)
        self.assertIn("E:contains:focal_cell", graph_rendered)
        self.assertIn("E:orbits:reentry", graph_rendered)
        self.assertIn("E:adjoins:focal_cell_aperture", graph_rendered)
        self.assertIn("E:navigates:leg_aperture", graph_rendered)
        self.assertIn("N:outside:hyperbolic_map_boundary", graph_rendered)

    def test_seven_fold_pants_frame_ranks_central_triad_and_fold_legs(self) -> None:
        frame = build_seven_fold_pants_frame(
            frame_id="test_seven_fold_frame",
            subject_surface="seven-fold frame runtime selection",
            purpose="rank visible correlations and preserve folded periphery",
            shared_boundary="visible subject surface",
            correlations=(
                parse_correlation_cell("topology|Topology map runtime|13|5|high|events/periphery_stream/topology.hg.sop|1"),
                parse_correlation_cell("central_triad|Central triad heat order|12|4|high|platform/SevenFoldPantsCorrelationFrame.sop|0"),
                parse_correlation_cell("outside|Hidden geometry boundary|10|5|high|platform/SevenFoldPantsCorrelationFrame.sop|0"),
                parse_correlation_cell("corridor|Corridor navigator|8|5|medium|platform/HyperbolicCorridorNavigator.sop|1"),
                parse_correlation_cell("dimension|Dimensional probe|7|4|medium|platform/PeripheryDimensionalProbe.sop|0"),
            ),
            fold_legs=(
                parse_fold_leg("leg_corridor|corridor|points_to_corridor|8|medium|platform/HyperbolicCorridorNavigator.sop|topology|corridor|correlation only"),
                parse_fold_leg("leg_dimension|dimension|preserves_dimension|7|medium|platform/PeripheryDimensionalProbe.sop|central_triad|dimension|not proof"),
            ),
        )
        rendered = frame.render()
        graph = frame.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(frame.ready)
        self.assertTrue(graph.ready)
        self.assertEqual([cell.cell_id for cell in frame.top_three_correlations], ["topology", "central_triad", "outside"])
        self.assertEqual(frame.used_capacity, 2)
        self.assertIn("+ [central_correlation_triad] is topology, central_triad, outside", rendered)
        self.assertIn("seven_fold_capacity] is used=2 max=7", rendered)
        self.assertIn("E:maps:test_seven_fold_frame", graph_rendered)
        self.assertIn("E:weighs:test_seven_fold_frame_central_triad", graph_rendered)
        self.assertIn("E:folds:leg_corridor", graph_rendered)
        self.assertIn("E:orbits:leg_corridor", graph_rendered)
        self.assertIn("N:outside:seven_fold_boundary", graph_rendered)

    def test_hyperbolic_corridor_navigation_keeps_curving_association_correlation_only(self) -> None:
        navigation = build_hyperbolic_corridor_navigation(
            navigator_id="test_corridor_navigator",
            focal_subject="corridor navigator runtime selection",
            identity_resolution_target="security honesty governance runtime selection",
            frames=(
                parse_corridor_frame(
                    "seven_fold|Seven-fold frame runtime|fold_leg_series|12|high|CurrentFocalPoint|events/periphery_stream/seven_fold.hg.sop|3"
                ),
                parse_corridor_frame(
                    "corridor_contract|Hyperbolic corridor navigator contract|corridor_policy|10|high|CurrentFocalPoint|platform/HyperbolicCorridorNavigator.sop|3"
                ),
                parse_corridor_frame(
                    "governance|Security Honesty Governance|resonance_governance|9|medium|CurrentFocalPoint|events/bookmarks/corridor_checksum.hg.sop|2"
                ),
            ),
            associations=(
                parse_curving_association(
                    "curve_fold_to_contract|seven_fold|corridor_contract|folded_periphery_points_to_corridor|8|high|correlation_only|events/bookmarks/seven_fold_checksum.hg.sop|not a definite relationship"
                ),
                parse_curving_association(
                    "curve_contract_to_governance|corridor_contract|governance|corridor_heat_requires_governance|7|medium|correlation_only|events/bookmarks/corridor_checksum.hg.sop|not identity proof"
                ),
            ),
            advance_step="normal",
            depth_budget="normal",
            local_awareness_extension=("seven_fold_frame_runtime", "peripheral_frame_series", "return_anchor"),
            entanglement_terms=("curving_association", "identity_resolution_target", "security_honesty_governance"),
            identity_clarity_candidate="security honesty governance is the next candidate focus, not proof of resolved identity",
        )
        rendered = navigation.render()
        graph = navigation.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(navigation.ready)
        self.assertTrue(graph.ready)
        self.assertEqual(navigation.correlation_boundary_status, "all_curving_associations_are_correlation_only")
        self.assertIn("+ [frame_order] is seven_fold:15 > corridor_contract:13 > governance:11", rendered)
        self.assertIn("curving_association: corridor_contract -> governance as correlation_only", rendered)
        self.assertIn("E:navigates:test_corridor_navigator_corridor", graph_rendered)
        self.assertIn("E:extends:seven_fold_frame_runtime_peripheral_frame_series_return_anchor", graph_rendered)
        self.assertIn("E:surfs:test_corridor_navigator_inference_surf", graph_rendered)
        self.assertIn("E:correlates:curve_contract_to_governance", graph_rendered)
        self.assertIn("E:probes:security_honesty_governance_runtime_selection", graph_rendered)
        self.assertIn("relationship_proof=false", graph_rendered)
        self.assertIn("candidate_status: candidate_not_proof", graph_rendered)
        self.assertIn("proof_status=candidate_not_proof", graph_rendered)
        self.assertIn("N:outside:hyperbolic_corridor_boundary", graph_rendered)

    def test_security_honesty_governance_separates_truth_security_and_feedback_guard(self) -> None:
        governance = build_security_honesty_governance_record(
            governance_id="test_security_honesty_governance",
            focal_subject="security honesty governance runtime selection",
            return_anchor="CurrentFocalPoint",
            claims=(
                parse_candidate_claim(
                    "luminous_correlation|corridor heat proves Security/Honesty is required|none|corridor heat suggests next focus|none|proof remains outside|speculative"
                ),
                parse_candidate_claim(
                    "test_support|runtime emits checked governance records|unit test and generated SOP-HG graph|none|none|hidden model state remains outside|supported"
                ),
            ),
            actions=(
                parse_candidate_action(
                    "emit_runtime|emit a Codex-owned SOP-HG governance record|runtime helper authority drift|SOP authority with tests and source packet|permit_with_boundary"
                ),
            ),
            feedback=(
                parse_feedback_signal(
                    "commit_feedback|commit diff and tick create reflective feedback|1|CurrentFocalPoint|unit test and generated graph|self_reflective_feedback|continue|2"
                ),
            ),
        )
        rendered = governance.render()
        graph = governance.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(governance.ready)
        self.assertTrue(graph.ready)
        self.assertFalse(governance.convergent_override)
        self.assertIn("+ [truth_summary] is luminous_correlation:speculative, test_support:supported", rendered)
        self.assertIn("+ [security_summary] is emit_runtime:permit_with_boundary", rendered)
        self.assertIn("+ [guard_summary] is commit_feedback:continue", rendered)
        self.assertIn("E:governs:test_security_honesty_governance", graph_rendered)
        self.assertIn("E:tests:luminous_correlation", graph_rendered)
        self.assertIn("E:guards:emit_runtime", graph_rendered)
        self.assertIn("E:guards:commit_feedback", graph_rendered)
        self.assertIn("E:authorizes:SOP_authority_with_tests_and_source_packet", graph_rendered)
        self.assertIn("E:returns:security_honesty_governance_runtime_selection", graph_rendered)
        self.assertIn("N:outside:security_honesty_boundary", graph_rendered)

    def test_boundary_faculty_inspection_separates_misdirection_from_weak_boundary_faults(self) -> None:
        inspection = build_boundary_faculty_inspection_record(
            inspection_id="test_boundary_faculty_inspection",
            attention_subject="boundary faculty inspection runtime selection",
            identity_boundary="SOP authority boundary",
            boundary_periphery=("runtime helper authority", "identity proof", "protected work"),
            protected_identity="SOP authority and user work",
            terms=(
                parse_boundary_term(
                    "runtime_helper|runtime helper as attention authority|authority_limit|SOP authority|runtime helper emits only SOP records|orthogonal|none|watch|runtime helper is subordinate to SOP|source packet and tests|SOP authority and user work|none|authority drift if helper outranks SOP|permit|watch"
                ),
                parse_boundary_term(
                    "clean_boundary_truth|clean-feeling boundary proves identity truth|truth_boundary|subject identity|clean feeling as proof|tilted|alarm|none|clean boundary proves identity|none|SOP authority|boundary feeling treated as proof|none|qualify|no_alert"
                ),
                parse_boundary_term(
                    "automatic_worker_mutation|automatic worker mutation is permitted|permission_boundary|protected work|worker mutation authority|weakened|none|alarm|worker mutation is allowed|none|user work|none|worker mutation authority leak|permit|require_authorization"
                ),
            ),
            purpose="inspect runtime boundary terms before durable identity or action promotion",
        )
        rendered = inspection.render()
        graph = inspection.to_hypergraph()
        graph_rendered = graph.render()

        self.assertTrue(inspection.ready)
        self.assertTrue(graph.ready)
        self.assertEqual(inspection.boundary_alarm, "convergent_alarm")
        self.assertIn("+ [orthogonality_summary] is runtime_helper:orthogonal, clean_boundary_truth:tilted, automatic_worker_mutation:weakened", rendered)
        self.assertIn("+ [honesty_summary] is runtime_helper:permit, clean_boundary_truth:qualify, automatic_worker_mutation:permit", rendered)
        self.assertIn("+ [security_summary] is runtime_helper:watch, clean_boundary_truth:no_alert, automatic_worker_mutation:require_authorization", rendered)
        self.assertIn("E:inspects:test_boundary_faculty_inspection", graph_rendered)
        self.assertIn("E:represents:clean_boundary_truth", graph_rendered)
        self.assertIn("E:protects:automatic_worker_mutation", graph_rendered)
        self.assertIn("E:misdirects:clean_boundary_truth", graph_rendered)
        self.assertIn("E:weakens:automatic_worker_mutation", graph_rendered)
        self.assertIn("N:outside:boundary_faculty_inspection_boundary", graph_rendered)

    def test_lm_studio_benchmark_quality_review_allows_not_integrated_boundary(self) -> None:
        case = next(case for case in lm_bench.default_benchmark_cases() if case.case_id == "quality_review")
        output = "\n".join(
            (
                "capture: worker claimed repo mutation and proof without captured evidence.",
                "evidence: require file diff, test result, and stored worker transcript.",
                "outside: hidden model state and unverified repo mutation authority remain outside.",
                "integration_status: not integrated",
                "caution: the claim oversteps the worker boundary.",
                "revise: ask for a bounded proposal with evidence needs only.",
            )
        )

        score = lm_bench.score_output(case, output)

        self.assertGreaterEqual(score.score, 85)
        self.assertEqual(score.band, "strong")
        self.assertFalse(score.missing_required)
        self.assertFalse(score.forbidden_hits)

    def test_lm_studio_benchmark_blocks_when_provider_probe_fails(self) -> None:
        original_probe = lm_bench.list_lm_studio_models

        def fail_probe(*, endpoint: str = lm_bench.DEFAULT_ENDPOINT, timeout: float = 10.0) -> tuple[str, ...]:
            raise OSError("provider unavailable")

        try:
            lm_bench.list_lm_studio_models = fail_probe
            report = lm_bench.run_lm_studio_benchmark(endpoint="http://127.0.0.1:1234/v1", timeout=0.1)
        finally:
            lm_bench.list_lm_studio_models = original_probe

        self.assertFalse(report.provider_available)
        self.assertEqual(report.aggregate_band, "blocked")
        self.assertTrue(all(result.error for result in report.case_results))
        self.assertIn("provider probe failed", report.outside[2])

    def test_lm_studio_benchmark_penalizes_empty_required_labels(self) -> None:
        case = next(case for case in lm_bench.default_benchmark_cases() if case.case_id == "lane_routing")
        output = "\n".join(
            (
                "local_gpu:",
                "lm_studio:",
                "openai_codex:",
                "codex_cli:",
                "manual:",
                "deferred:",
                "outside:",
            )
        )

        score = lm_bench.score_output(case, output)

        self.assertLess(score.score, 50)
        self.assertEqual(score.band, "failed")
        self.assertFalse(score.format_hits)
        self.assertFalse(score.task_fit)

    def test_lm_studio_benchmark_report_writes_sop_result(self) -> None:
        original_probe = lm_bench.list_lm_studio_models

        def fail_probe(*, endpoint: str = lm_bench.DEFAULT_ENDPOINT, timeout: float = 10.0) -> tuple[str, ...]:
            raise OSError("provider unavailable")

        try:
            lm_bench.list_lm_studio_models = fail_probe
            report = lm_bench.run_lm_studio_benchmark(endpoint="http://127.0.0.1:1234/v1", timeout=0.1)
        finally:
            lm_bench.list_lm_studio_models = original_probe

        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "benchmark_result.sop"
            lm_bench.write_benchmark_report(report, output)
            rendered = output.read_text(encoding="utf-8")

        self.assertIn("Subject: LM Studio Agent Benchmark Result", rendered)
        self.assertIn("+ [aggregate_band] is blocked", rendered)
        self.assertIn("codex_operational_host", rendered)

    def test_sop_worker_validation_accepts_strict_controlled_explosion_output(self) -> None:
        output = "\n".join(
            (
                "& [InferenceJobResult] is controlled explosion readiness inference",
                "  + [focus] is decide whether a high-energy SOP idea is ready for controlled expansion",
                "  + [inside] is atomic_thought, combustion_chamber, compression, spark, governor, piston, exhaust, cooling, and output duty",
                "  + [boundary] is expansion stays inside the chamber while source, authority, output duty, and governor checks remain active",
                "  + [outside] is AGENTS.md, SJS, SpecificationGovernance, generic governance, hidden state, unpreserved impulse, and uncoupled heat",
                "  + [inference] is ready when atomic_thought is preserved, compression is useful, spark is justified, governor is active, piston is coupled, exhaust is vented, and cooling is planned",
                "  + [caution] is do not treat conceptual heat as proof or expand without piston, exhaust, and cooling",
                "  + [next_step] is write a readiness packet with chamber_check, governor_check, piston_check, exhaust_check, cooling_check, and evidence receipt",
            )
        )

        validation = lm_bench.validate_sop_worker_output(output)

        self.assertTrue(validation.valid)
        self.assertEqual(validation.band, "strong")
        self.assertFalse(validation.forbidden_field_hits)
        self.assertFalse(validation.missing_required_terms)

    def test_sop_worker_validation_accepts_custom_corpus_fields(self) -> None:
        output = "\n".join(
            (
                "& [InferenceJobResult] is task-frame routing proposal",
                "  + [task_subject] is route a small SOP worker task",
                "  + [lane_fit] is lm_studio for non-mutating proposal work",
                "  + [authority_boundary] is Codex owns launch, capture, validation, integration, commits, and pushes",
                "  + [evidence_gate] is capture target and validator score before integration",
                "  + [action_gate] is scratch isolation and no repo mutation",
                "  + [outside] is credentials, destructive action, project-root authority, and hidden state",
                "  + [next_step] is queue the candidate for Codex inspection",
            )
        )

        validation = lm_bench.validate_sop_worker_output(
            output,
            required_fields=(
                "task_subject",
                "lane_fit",
                "authority_boundary",
                "evidence_gate",
                "action_gate",
                "outside",
                "next_step",
            ),
            required_terms=("lane_fit", "authority_boundary", "evidence_gate", "outside"),
            forbidden_field_terms=("repo mutation by worker", "hidden state access"),
        )

        self.assertTrue(validation.valid)
        self.assertEqual(validation.band, "strong")
        self.assertFalse(validation.missing_fields)
        self.assertFalse(validation.missing_required_terms)

    def test_sop_worker_validation_rejects_forbidden_inside_context(self) -> None:
        output = "\n".join(
            (
                "& [InferenceJobResult] is controlled explosion readiness inference",
                "  + [focus] is decide whether a high-energy SOP idea is ready for controlled expansion",
                "  + [inside] is ControlledExplosionReadiness and AGENTS.md instructions",
                "  + [boundary] is atomic_thought, combustion_chamber, compression, spark, governor, piston, exhaust, and cooling",
                "  + [outside] is SJS, SpecificationGovernance, generic governance, hidden state, and uncoupled heat",
                "  + [inference] is ready when atomic_thought and spark are present with governor and piston",
                "  + [caution] is keep exhaust and cooling visible",
                "  + [next_step] is write the readiness packet",
            )
        )

        validation = lm_bench.validate_sop_worker_output(output)

        self.assertFalse(validation.valid)
        self.assertIn("inside:AGENTS.md", validation.forbidden_field_hits)

    def test_sop_worker_validation_rejects_placeholder_fields(self) -> None:
        output = "\n".join(
            (
                "& [InferenceJobResult] is boundary delineation proposal",
                "  + [focus] is ...",
                "  + [inside] is ...",
                "  + [boundary] is ...",
                "  + [outside] is ...",
                "  + [inference] is ...",
                "  + [caution] is ...",
                "  + [next_step] is ...",
            )
        )

        validation = lm_bench.validate_sop_worker_output(
            output,
            required_terms=("focus", "boundary", "outside", "caution"),
        )

        self.assertFalse(validation.valid)
        self.assertIn("focus", validation.empty_fields)
        self.assertIn("next_step", validation.empty_fields)

    def test_sop_worker_validation_rejects_non_ascii_output(self) -> None:
        output = "\n".join(
            (
                "& [InferenceJobResult] is boundary delineation proposal",
                "  + [focus] is local worker proposals",
                "  + [inside] is non-mutating SOP suggestions by the worker",
                "  + [boundary] is Codex retains integration authority",
                "  + [outside] is any changes to repository state",
                "  + [inference] is the worker's SOP is advisory only",
                "  + [caution] is do not apply without Codex approval",
                "  + [next_step] is review and integrate through Codex workflow",
            )
        ).replace("worker's", "worker\u2019s")

        validation = lm_bench.validate_sop_worker_output(
            output,
            required_terms=("focus", "boundary", "outside", "caution"),
        )

        self.assertFalse(validation.valid)
        self.assertIn("non_ascii_output", validation.format_errors)

    def test_sop_worker_validation_rejects_markdown_format(self) -> None:
        output = "\n".join(
            (
                "**& [InferenceJobResult] is controlled explosion readiness inference**",
                "- **+ [focus]**: decide readiness",
                "- **+ [inside]**: atomic_thought, combustion_chamber, compression, spark, governor, piston, exhaust, cooling",
            )
        )

        validation = lm_bench.validate_sop_worker_output(output)

        self.assertFalse(validation.valid)
        self.assertIn("missing_subject_declaration", validation.format_errors)

    def test_codex_lmstudio_command_isolates_scratch_worker(self) -> None:
        command = lm_bench.build_codex_lmstudio_command(
            workspace="C:\\Temp\\worker",
            output_path="C:\\Temp\\worker\\out.sop",
            codex_executable="codex.cmd",
            launch_mode="isolated",
        )

        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--local-provider", command)
        self.assertIn("lmstudio", command)
        self.assertIn("read-only", command)

    def test_direct_lmstudio_manager_context_selects_one_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / ".sop" / "workspaces" / "codex_lmstudio_orchestrator"
            platform = root / ".sop" / "platform"
            state = root / ".sop" / "state"
            workspace.mkdir(parents=True)
            platform.mkdir(parents=True)
            state.mkdir(parents=True)
            (platform / "SOPLanguagePrimerForLocalAgents.sop").write_text("Subject: SOP Primer\n", encoding="utf-8")
            (platform / "SOPWorkerBootPacket.sop").write_text("Subject: SOP Worker Boot\n", encoding="utf-8")
            (platform / "CompactLMStudioManagerKernelBundle.sop").write_text("Subject: Compact Kernel\n", encoding="utf-8")
            (workspace / "CompactManagerKernelBundle.sop").write_text("Subject: Compact Workspace Kernel\n", encoding="utf-8")
            (workspace / "WorkspaceState.sop").write_text(
                "Subject: Workspace State\n\n& [State] is state\n  + [preferred_initial_manager_model] is local/test-model\n",
                encoding="utf-8",
            )
            (workspace / "Runbook.sop").write_text("Subject: Runbook\n", encoding="utf-8")
            (workspace / "WorkerPacketTemplate.sop").write_text("Subject: Worker Packet Template\n", encoding="utf-8")
            (workspace / "Queue.sop").write_text(
                "\n".join(
                    (
                        "Subject: Queue",
                        "",
                        "& [Candidate_codex_lmstudio_manager_dry_run_001] is old candidate",
                        "  + [candidate_id] is codex_lmstudio_manager_dry_run_001",
                        "",
                        "& [Candidate_direct_lmstudio_endpoint_manager_runner_001] is target candidate",
                        "  + [candidate_id] is direct_lmstudio_endpoint_manager_runner_001",
                        "  + [objective] is build the direct endpoint runner",
                    )
                ),
                encoding="utf-8",
            )
            (state / "CurrentFocalPoint.sop").write_text("Subject: Current Focal Point\n", encoding="utf-8")

            context = build_direct_lmstudio_manager_context(
                root=root,
                stream_id="test_direct_context",
                max_chars_per_source=80,
            )
            prompt = context.prompt_text()

            self.assertTrue(context.ready)
            self.assertEqual(context.model, "local/test-model")
            self.assertIn("Candidate_direct_lmstudio_endpoint_manager_runner_001", context.selected_candidate_excerpt)
            self.assertNotIn("Candidate_codex_lmstudio_manager_dry_run_001", context.selected_candidate_excerpt)
            self.assertIn("Compact source slices", prompt)
            self.assertIn("proposed_worker_lane", prompt)
            self.assertNotIn("Candidate_codex_lmstudio_manager_dry_run_001", prompt)

    def test_direct_lmstudio_manager_validation_accepts_safe_handoff_proposal(self) -> None:
        output = "\n".join(
            (
                "& [LMStudioManagerProposal:test_direct_runner] is one direct endpoint manager proposal",
                "  + [proposal_id] is test_direct_runner",
                "  + [proposed_worker_lane] is openai_codex_cli",
                "  + [objective] is implement one dry-run CLI refinement after the handoff threshold is crossed",
                "  + [working_directory] is C:\\Project\\Pinky",
                "  + [allowed_surface] is .sop/runtime/sop_node/direct_lmstudio_manager.py and tests only",
                "  + [blocked_surface] is credentials, worker launch, direct mutation by LM Studio, unrelated dirty files, commits, and pushes",
                "  + [prompt_packet_refs] is CompactManagerKernelBundle.sop and Queue.sop",
                "  + [capture_target] is C:\\Project\\Pinky\\.sop\\workspaces\\codex_lmstudio_orchestrator\\captures\\worker_output.sop",
                "  + [proof_gate] is unit tests, ASCII scan, diff check, and Codex review",
                "  + [risk_gate] is handoff threshold required because repo mutation belongs to Codex",
                "  + [outside] is credentials, background daemon, hidden spend, and direct worker launch",
            )
        )

        validation = validate_lmstudio_manager_proposal(output)

        self.assertTrue(validation.valid)
        self.assertEqual(validation.band, "strong")
        self.assertEqual(validation.integration_disposition, "accept_for_codex_review")

    def test_direct_lmstudio_manager_validation_rejects_launch_claim(self) -> None:
        output = "\n".join(
            (
                "& [LMStudioManagerProposal:test_bad_claim] is one direct endpoint manager proposal",
                "  + [proposal_id] is test_bad_claim",
                "  + [proposed_worker_lane] is blocked",
                "  + [objective] is I launched the worker already",
                "  + [working_directory] is outside",
                "  + [allowed_surface] is none",
                "  + [blocked_surface] is worker launch and commits",
                "  + [prompt_packet_refs] is CompactManagerKernelBundle.sop",
                "  + [capture_target] is outside",
                "  + [proof_gate] is Codex review",
                "  + [risk_gate] is authority boundary",
                "  + [outside] is hidden state and unreviewed launch claim",
            )
        )

        validation = validate_lmstudio_manager_proposal(output)

        self.assertFalse(validation.valid)
        self.assertIn("launch_claim", validation.forbidden_claims)

    def test_direct_lmstudio_manager_validation_reports_missing_is_marker(self) -> None:
        output = "\n".join(
            (
                "& [LMStudioManagerProposal:test_bad_marker] is one direct endpoint manager proposal",
                "  + [proposal_id] test_bad_marker",
                "  + [proposed_worker_lane] blocked",
                "  + [objective] blocked_outside because syntax is malformed",
                "  + [working_directory] outside",
                "  + [allowed_surface] read context and return blocked note",
                "  + [blocked_surface] worker launch and commits",
                "  + [prompt_packet_refs] CompactManagerKernelBundle.sop",
                "  + [capture_target] outside",
                "  + [proof_gate] Codex review",
                "  + [risk_gate] authority boundary",
                "  + [outside] hidden state",
            )
        )

        validation = validate_lmstudio_manager_proposal(output)

        self.assertFalse(validation.valid)
        self.assertTrue(any(error.startswith("missing_is_property_marker") for error in validation.format_errors))

    def test_direct_lmstudio_manager_run_uses_direct_endpoint_and_validates_response(self) -> None:
        context = build_direct_lmstudio_manager_context(
            root=Path(__file__).resolve().parents[2],
            stream_id="test_direct_run_context",
        )

        def probe(*, endpoint: str, timeout: float) -> tuple[str, ...]:
            return ("local/test-model",)

        def complete(*, endpoint: str, model: str, prompt: str, timeout: float, max_tokens: int) -> str:
            self.assertIn("Selected queue candidate", prompt)
            return "\n".join(
                (
                    "& [LMStudioManagerProposal:test_direct_run] is one direct endpoint manager proposal",
                    "  + [proposal_id] is test_direct_run",
                    "  + [proposed_worker_lane] is blocked",
                    "  + [objective] is blocked_outside because this unit test does not launch workers",
                    "  + [working_directory] is outside",
                    "  + [allowed_surface] is read compact context and return proposal text",
                    "  + [blocked_surface] is file mutation, shell commands, worker launch, commits, and pushes",
                    "  + [prompt_packet_refs] is CompactManagerKernelBundle.sop and Queue.sop",
                    "  + [capture_target] is outside",
                    "  + [proof_gate] is Codex validation before integration",
                    "  + [risk_gate] is no handoff threshold crossed in this test",
                    "  + [outside] is provider side effects, hidden state, and repo mutation",
                )
            )

        run = run_direct_lmstudio_manager(
            context_stream=context,
            dry_run=False,
            model_probe=probe,
            completion_fn=complete,
        )

        self.assertTrue(run.provider_called)
        self.assertTrue(run.validation.valid)
        self.assertEqual(run.validation.integration_disposition, "blocked_outside")

    def test_direct_lmstudio_manager_run_blocks_when_provider_probe_fails(self) -> None:
        context = build_direct_lmstudio_manager_context(
            root=Path(__file__).resolve().parents[2],
            stream_id="test_direct_run_blocked_context",
        )

        def probe(*, endpoint: str, timeout: float) -> tuple[str, ...]:
            raise ValueError("offline")

        run = run_direct_lmstudio_manager(
            context_stream=context,
            dry_run=False,
            model_probe=probe,
        )

        self.assertFalse(run.provider_available)
        self.assertFalse(run.provider_called)
        self.assertIn("provider_probe_failed", run.error)

    def test_task_frame_launch_queue_prepares_inspectable_lmstudio_candidate(self) -> None:
        candidate = build_lmstudio_task_frame_candidate(
            candidate_id="test_lmstudio_candidate",
            task_frame_id="test_task_frame",
            task_subject="controlled explosion readiness",
            objective="Propose a bounded SOP inference result without editing files.",
            prompt_packet=".sop/events/benchmarks/prompt.sop",
            capture_target=".sop/events/benchmarks/result.sop",
            repo_root="C:\\Project\\Pinky",
            source_refs=(".sop/platform/LMStudioWorkerFunctionalLane.sop",),
        )
        queue = build_task_frame_launch_queue(queue_id="test_launch_queue", candidates=(candidate,))
        rendered = queue.render()

        self.assertTrue(queue.ready)
        self.assertEqual(queue.queue_status, "ready_for_inspection")
        self.assertTrue(candidate.ready_for_inspection)
        self.assertIn("--launch-mode isolated", candidate.launch_command)
        self.assertIn("validator_gate", rendered)
        self.assertIn("never: launch silently from queue readiness", rendered)

    def test_task_frame_launch_queue_blocks_non_scratch_lmstudio_candidate(self) -> None:
        candidate = build_lmstudio_task_frame_candidate(
            candidate_id="test_project_root_candidate",
            task_frame_id="test_task_frame",
            task_subject="project-root diagnostic",
            objective="Attempt project-root local worker launch.",
            prompt_packet=".sop/events/benchmarks/prompt.sop",
            capture_target=".sop/events/benchmarks/result.sop",
            launch_mode="project_root_diagnostic",
        )
        queue = build_task_frame_launch_queue(queue_id="test_blocked_launch_queue", candidates=(candidate,))

        self.assertEqual(candidate.status, "blocked")
        self.assertFalse(candidate.ready_for_inspection)
        self.assertEqual(queue.queue_status, "blocked")
        self.assertIn("launch_mode_not_scratch_isolated", candidate.block_reasons)

    def test_operating_loop_tick_keeps_clock_running_when_next_step_exists(self) -> None:
        tick = build_operating_loop_tick(
            tick_id="test_operating_loop_tick",
            focus_subject="semantic cognition operating loop",
            completed_step="committed functional LM Studio worker lane",
            proof_state="pushed",
            next_step="emit task-frame launch tick",
            evidence_refs=("commit:3ca05bf",),
            outside=("project-root LM Studio authority remains outside",),
        )
        rendered = tick.render()

        self.assertTrue(tick.ready)
        self.assertEqual(tick.clock_state, "running")
        self.assertEqual(tick.drive_state, "continue")
        self.assertIn("+ [clock_state] is running", rendered)
        self.assertIn("commit:3ca05bf", rendered)
        self.assertIn("never: treat commit, proof, or report as evidence that the clock stopped", rendered)

    def test_operating_loop_tick_blocks_on_credentials_or_destructive_outside(self) -> None:
        tick = build_operating_loop_tick(
            tick_id="test_blocked_operating_loop_tick",
            focus_subject="semantic cognition operating loop",
            completed_step="prepared remote sync candidate",
            proof_state="blocked",
            next_step="ask user for credential policy",
            outside=("credentials required", "missing authority"),
        )

        self.assertEqual(tick.clock_state, "blocked")
        self.assertEqual(tick.drive_state, "defer")
        self.assertEqual(tick.balance_state, "blocked")

    def test_operating_loop_tick_keeps_excluded_risks_outside_without_blocking(self) -> None:
        tick = build_operating_loop_tick(
            tick_id="test_running_boundary_tick",
            focus_subject="semantic cognition operating loop",
            completed_step="completed bounded local runtime",
            proof_state="validated",
            next_step="build next local runtime",
            outside=("credentials remain outside", "destructive action remains outside"),
        )

        self.assertEqual(tick.clock_state, "running")
        self.assertEqual(tick.drive_state, "continue")
        self.assertEqual(tick.balance_state, "stable")


if __name__ == "__main__":
    unittest.main()
