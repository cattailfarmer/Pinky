from __future__ import annotations

import json
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rust_brace_scan() -> str:
    files = sorted((ROOT / "slm_rust" / "src").rglob("*.rs"))
    require(files, "no Rust source files found")
    for path in files:
        text = path.read_text(encoding="utf-8")
        stack: list[int] = []
        for index, char in enumerate(text):
            if char == "{":
                stack.append(index)
            elif char == "}":
                require(bool(stack), f"unmatched close brace: {path}:{index}")
                stack.pop()
        require(not stack, f"unmatched open brace: {path}:{stack[-1] if stack else 0}")
    return f"rust_brace_scan_ok files={len(files)}"


def python_compile() -> str:
    scripts = [
        ROOT / "slm_lexicon" / "scripts" / "download_open_english_wordnet.py",
        ROOT / "slm_lexicon" / "scripts" / "build_lexicon_db.py",
        ROOT / "slm_lexicon" / "scripts" / "export_lexicon_cache.py",
        ROOT / "slm_lexicon" / "scripts" / "build_lexical_substrate_pack.py",
        ROOT / "slm_lexicon" / "scripts" / "rebuild_lexical_substrate_workflow.py",
        ROOT / "slm_project" / "tools" / "slm_regression_harness.py",
        ROOT / "slm_project" / "tools" / "slm_golden_snapshot.py",
    ]
    for script in scripts:
        require(script.exists(), f"missing Python script: {script}")
        py_compile.compile(str(script), doraise=True)
    return f"python_compile_ok files={len(scripts)}"


def substrate_validation() -> str:
    substrate = ROOT / "slm_lexicon" / "data" / "slm_lexical_substrate"
    if not substrate.exists():
        return "substrate_validation_skipped missing_generated_substrate"

    manifest = json.loads((substrate / "manifest.json").read_text(encoding="utf-8"))
    index = json.loads((substrate / "term_role_sense_index.json").read_text(encoding="utf-8"))
    closed = json.loads((substrate / "closed_class_speed_table.json").read_text(encoding="utf-8"))

    entries = index["entries"]
    closed_terms = closed["terms"]
    expected = manifest["counts"]["substrate_entries"]
    require(index["format"] == "slm_lexical_substrate_index_v0", "unexpected substrate index format")
    require(expected == len(entries), f"substrate entry count mismatch: {expected} != {len(entries)}")
    for term in ["a", "for", "design", "compiler", "hardware"]:
        require(term in entries, f"missing substrate term: {term}")
    for_closed_rows = [row for item in closed_terms["for"] for row in item["closed_class"]]
    require(
        any(
            row["class"] == "preposition"
            and row["subclass"] == "purpose_or_beneficiary"
            for row in for_closed_rows
        ),
        "missing expected closed-class row for 'for'",
    )
    require(any(entry["roles"] for entry in entries["design"]), "design has no role evidence")
    require(any(entry["senses"] for entry in entries["compiler"]), "compiler has no sense evidence")
    return f"substrate_validation_ok {manifest['substrate_id']} entries={expected}"


def sidecar_prompt_contract_validation() -> str:
    path = ROOT / "slm_project" / "sidecar_prompts" / "sidecar_task_prompt_contracts_v0.json"
    prompt_contracts = json.loads(path.read_text(encoding="utf-8"))
    require(
        prompt_contracts["format"] == "slm_sidecar_task_prompt_contracts_v0",
        "unexpected sidecar prompt contract format",
    )
    required_tasks = {
        "rank_senses",
        "propose_spans",
        "object_to_parse",
        "answer_objection",
        "run_faculty_validation",
    }
    tasks = {task["task_kind"]: task for task in prompt_contracts["tasks"]}
    require(set(tasks) == required_tasks, f"sidecar task set mismatch: {set(tasks)}")
    for task_name, task in tasks.items():
        require(task["instruction"], f"{task_name} missing instruction")
        require(task["allowed_evidence"], f"{task_name} missing allowed evidence")
        require("provider_suggestions" in task["required_output"], f"{task_name} missing provider output")
        require(
            any("glyph" in rule for rule in task["forbidden_authority"]),
            f"{task_name} missing glyph authority ban",
        )
    return f"sidecar_prompt_contract_validation_ok tasks={len(tasks)}"


def provider_set_validation() -> str:
    path = ROOT / "slm_project" / "provider_sets" / "local_provider_set_v0.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    require(config["provider_set_id"] == "local_provider_set_v0", "unexpected provider set id")
    providers = {provider["provider_id"]: provider for provider in config["providers"]}
    for provider_id in ["mock-fixture", "local-lm-studio", "local-ollama"]:
        require(provider_id in providers, f"missing provider config: {provider_id}")
        require(providers[provider_id]["capabilities"], f"{provider_id} missing capabilities")
    for provider_id in ["local-lm-studio", "local-ollama"]:
        require(
            providers[provider_id]["prompt_contract"] == "sidecar_task_prompt_contracts_v0",
            f"{provider_id} missing sidecar prompt contract",
        )
        require(providers[provider_id]["endpoint"], f"{provider_id} missing endpoint")
    return f"provider_set_validation_ok providers={len(providers)}"


def target_absence() -> str:
    target = ROOT / "slm_rust" / "target"
    target_check = ROOT / "slm_rust" / "target-check"
    require(not target.exists(), f"Cargo target directory exists: {target}")
    require(not target_check.exists(), f"Cargo target-check directory exists: {target_check}")
    return "target_absence_ok"


def source_marker_scan() -> str:
    markers = {
        ROOT / "slm_rust" / "src" / "rules.rs": [
            "CLOSED_CLASS_SPAN_RULES",
            "PREPOSITION_RELATION_RULES",
            "SENSE_COHERENCE_RULES",
            "exclude_structural_hint_tokens",
        ],
        ROOT / "slm_rust" / "src" / "lexicon.rs": [
            "LexicalSenseRoutingPolicy",
            "DeferClosedClassTokenSenses",
            "EmitAllSenses",
        ],
        ROOT / "slm_rust" / "src" / "providers.rs": [
            "objection_with_class",
            "answer_with_kind",
            "ProviderFacultyReport",
            "HemispherePerspective",
            "ProviderCapability",
            "ProviderConfig",
            "ProviderSetConfig",
            "provider_set_from_json",
            "validate_provider_set",
        ],
        ROOT / "slm_rust" / "src" / "deliberation.rs": [
            "disagreement_class_from_payload",
            "faculty_report_refs",
            "JuryPanelMemberReview",
            "jury_panel_member_reviews",
            "aggregate_jury_measurement",
            "measurement_status",
        ],
        ROOT / "slm_rust" / "src" / "diffusion.rs": [
            "ensure_support_record",
            "ensure_contradiction_record",
            "contradiction_severity",
            "imperative_action_candidate",
            "propose_imperative_subject_uncertainty",
            "SupportPropagation",
            "LexicalSenseSupport",
        ],
        ROOT / "slm_rust" / "src" / "graph.rs": [
            "candidate_relation_ref",
            "endpoint_decision_refs",
            "relation_endpoint_stability",
        ],
        ROOT / "slm_rust" / "src" / "stabilization.rs": [
            "UncertaintyBoundaryCriteria",
            "uncertainty_boundary_criteria",
            "uncertainty_boundary_passes",
            "threshold_fixture_workspace",
        ],
        ROOT / "slm_rust" / "src" / "wobble.rs": [
            "WobbleFactor",
            "WobbleRoute",
            "WobbleRoutingDecision",
            "routing_decision",
            "target_kind",
            "push_factor",
            "subject_boundary_instability",
        ],
        ROOT / "slm_rust" / "src" / "primer.rs": [
            "provider_suggestion",
            "faculty_report_refs",
            "PrimerCompactionBudget",
            "compact_evidence_with_budget",
            "lexical_sense_top_k_per_token",
            "normalize_evidence_ref",
            "normalize_ref_list",
            "WobbleFactorPrimer",
            "routing_decision",
            "contradiction_refs",
            "PrimerSchemaInfo",
            "SLM_PRIMER_SCHEMA_ID",
            "SLM_PRIMER_SCHEMA_VERSION",
            "primer_schema_info",
        ],
        ROOT / "slm_rust" / "src" / "sidecar.rs": [
            "SidecarTaskPromptContract",
            "sidecar_task_prompt_contract",
            "task_instruction_text",
            "task_contract",
            "LmStudioSidecarConfig",
            "to_lm_studio_chat_request",
            "parse_lm_studio_provider_suggestions",
            "SidecarResponseValidationStatus",
            "SidecarValidatedParseOutcome",
            "parse_lm_studio_provider_suggestions_validated",
            "rejection_objection",
            "OllamaSidecarConfig",
            "OllamaChatRequest",
            "to_ollama_chat_request",
            "parse_ollama_provider_suggestions_validated",
        ],
        ROOT / "slm_rust" / "src" / "fixtures.rs": [
            "ProviderFacultyReport",
            "objection_with_class",
            "answer_with_kind",
        ],
        ROOT / "slm_rust" / "src" / "bin" / "slm_demo.rs": [
            "DemoOutputMode",
            "CompactDemoReport",
            "parse_demo_args",
            "render_demo_output",
        ],
    }
    for path, required_markers in markers.items():
        require(path.exists(), f"missing source file: {path}")
        text = path.read_text(encoding="utf-8")
        for marker in required_markers:
            require(marker in text, f"missing marker {marker} in {path}")
    return f"source_marker_scan_ok files={len(markers)}"


def main() -> None:
    checks = [
        rust_brace_scan,
        python_compile,
        substrate_validation,
        sidecar_prompt_contract_validation,
        provider_set_validation,
        target_absence,
        source_marker_scan,
    ]
    for check in checks:
        print(check())
    print("slm_source_gate_check_ok")


if __name__ == "__main__":
    main()
