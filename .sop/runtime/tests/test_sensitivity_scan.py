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
    build_compiled_attention_packet,
    build_step_balance_walk,
    build_semantic_component,
    build_semantic_hash_index,
    build_semantic_hash_table,
    build_semantic_correlation_graph,
    build_support_balance,
    build_attention_tracking_record,
    build_lmstudio_task_frame_candidate,
    build_sensitivity_scan,
    build_sensitivity_scan_from_changes,
    build_task_frame_launch_queue,
    build_turn_bookmark_from_scan,
    build_inference_state_trace,
    build_operating_loop_tick,
    build_periphery_continuity_run,
    build_viewfinder_snapshot,
    classify_layer,
    create_turn_spool,
    parse_periphery_terms,
    parse_edge_participants,
    parse_directive,
    parse_faculty_field,
    parse_periphery_run_frame,
    parse_reflection_consumption,
    parse_support_probe,
    parse_step_balance_observation,
    parse_tracked_subject,
    scan_to_hypergraph,
    select_scaffold_profile,
)


class SensitivityScanTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
