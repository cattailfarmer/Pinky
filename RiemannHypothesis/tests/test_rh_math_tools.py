from __future__ import annotations

import sys
from pathlib import Path

import mpmath as mp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.distribution import (
    chebyshev_psi,
    chebyshev_theta,
    prime_family_distribution,
    prime_family_interval_distribution,
    prime_power_decomposition,
)
from rh_math.euler_product import (
    euler_product_probe,
    sigma_boundary_probe,
    t_axis_boundary_probe,
    vertical_resonance_scan,
)
from rh_math.exponential_forms import (
    coefficient_power_shift_probe,
    exponential_power_shift_probe,
    exponential_shift_probe,
)
from rh_math.explicit_formula import (
    alpha_cesaro_kernel_weight,
    bias_tuned_kernel_bridge_atlas,
    cesaro_mellin_bridge_atlas,
    explicit_residual_movement_decomposition,
    explicit_formula_probe,
    lambda_mellin_bridge_atlas,
    n_domain_kernel_weight,
    partial_summation_bridge_atlas,
    scale_law_comparison_atlas,
    scale_tied_zero_height,
    scale_tied_zero_height_atlas,
    zero_height_cutoff_atlas,
    zero_height_window_weight,
    zero_window_probe,
    zero_window_stability_atlas,
    zero_window_weight,
)
from rh_math.irregular_primes import irregular_pairs_for_prime, irregular_prime_distribution, irregular_prime_scan
from rh_math.lambda_oscilloscope import (
    lambda_oscilloscope_probe,
    lambda_phasor_reference_contribution,
    lambda_window_cutoff_scan,
    lambda_window_weight,
)
from rh_math.primes import prime_count_compare
from rh_math.prime_families import scan_special_prime_families, special_prime_profile, special_prime_row
from rh_math.zeta import critical_line_scan, functional_equation_check, known_zero_probe, zeta_value


def test_zeta_eval_returns_small_value_near_first_zero() -> None:
    payload = zeta_value("0.5", "14.134725141734693790457251983562", dps=80)
    residual = mp.mpf(payload["row"]["zeta"]["abs"])
    assert residual < mp.mpf("1e-25")
    assert payload["metadata"]["proof_status"] == "numerical_zeta_value_not_proof"


def test_xi_functional_equation_residual_is_small() -> None:
    payload = functional_equation_check("2", "3", dps=80, equation="xi")
    residual = mp.mpf(payload["row"]["residual_abs"])
    assert residual < mp.mpf("1e-70")


def test_critical_line_scan_refines_first_sign_change() -> None:
    payload = critical_line_scan("14", "15", "0.1", dps=60, refine=True)
    assert payload["sign_changes"]
    estimate = mp.mpf(payload["refined_zero_estimates"][0]["root_t_estimate"])
    assert abs(estimate - mp.mpf("14.134725141734693790457251983562")) < mp.mpf("1e-20")
    assert payload["metadata"]["proof_status"] == "sign_change_probe_not_zero_certification"


def test_known_zero_probe_reports_first_zero_residual() -> None:
    payload = known_zero_probe(start=1, count=1, dps=80)
    row = payload["rows"][0]
    assert row["zero_index"] == 1
    assert abs(mp.mpf(row["zero"]["real"]) - mp.mpf("0.5")) < mp.mpf("1e-70")
    assert mp.mpf(row["zeta_abs_residual"]) < mp.mpf("1e-60")


def test_prime_count_compare_known_values() -> None:
    payload = prime_count_compare(points=[10, 100, 1000], terms=10, dps=60)
    observed = {row["x"]: row["prime_pi"] for row in payload["rows"]}
    assert observed == {10: 4, 100: 25, 1000: 168}
    assert payload["metadata"]["proof_status"] == "finite_prime_count_comparison_not_asymptotic_proof"


def test_fermat_prime_seed_identity_and_641_boundary() -> None:
    payload = special_prime_profile([3, 5, 17, 257, 65537, 641], max_fermat_n=6)
    rows = {row["p"]: row for row in payload["rows"]}
    assert [rows[p]["fermat_prime_index"] for p in [3, 5, 17, 257, 65537]] == [0, 1, 2, 3, 4]
    assert rows[641]["identity_scope"] == "fermat_number_factor_periphery"
    assert rows[641]["fermat_divisor_hits"] == [5]
    assert rows[641]["proth"]["is_proth_form"] is True


def test_neighbor_family_examples_are_detected() -> None:
    mersenne = special_prime_row(31)
    wieferich = special_prime_row(1093)
    assert mersenne["is_mersenne_prime"] is True
    assert mersenne["mersenne_prime_exponent"] == 5
    assert wieferich["is_base2_wieferich_prime"] is True


def test_special_prime_scan_finds_boundary_and_neighbor_sets() -> None:
    payload = scan_special_prime_families(limit=2000, max_fermat_n=6)
    families = {row["family"]: row["members"] for row in payload["rows"]}
    assert 641 in families["fermat_number_factor_periphery"]
    assert 31 in families["mersenne_prime"]
    assert 1093 in families["base2_wieferich_prime"]


def test_chebyshev_small_values() -> None:
    expected_theta = mp.log(2) + mp.log(3) + mp.log(5) + mp.log(7)
    expected_psi = (3 * mp.log(2)) + (2 * mp.log(3)) + mp.log(5) + mp.log(7)
    assert abs(chebyshev_theta(10) - expected_theta) < mp.mpf("1e-40")
    assert abs(chebyshev_psi(10) - expected_psi) < mp.mpf("1e-40")


def test_prime_family_distribution_returns_to_global_objects() -> None:
    payload = prime_family_distribution(
        points=[1000, 2000],
        families=["fermat_number_factor_periphery", "mersenne_prime", "base2_wieferich_prime"],
        max_fermat_n=6,
        dps=60,
    )
    global_rows = {row["x"]: row for row in payload["global_rows"]}
    assert global_rows[1000]["prime_pi"] == 168
    family_rows = {(row["x"], row["family"]): row for row in payload["rows"]}
    assert family_rows[(1000, "fermat_number_factor_periphery")]["family_count"] == 1
    assert family_rows[(1000, "mersenne_prime")]["family_count"] == 4
    assert family_rows[(2000, "base2_wieferich_prime")]["family_count"] == 1
    assert payload["metadata"]["proof_status"] == "finite_family_distribution_probe_not_rh_evidence"


def test_prime_family_interval_distribution_measures_increments() -> None:
    payload = prime_family_interval_distribution(
        points=[1000, 2000],
        families=["fermat_number_factor_periphery", "mersenne_prime", "base2_wieferich_prime"],
        max_fermat_n=6,
        dps=60,
    )
    global_rows = {(row["lower"], row["upper"]): row for row in payload["global_rows"]}
    assert global_rows[(0, 1000)]["prime_count_increment"] == 168
    assert global_rows[(1000, 2000)]["prime_count_increment"] == 135
    family_rows = {(row["lower"], row["upper"], row["family"]): row for row in payload["rows"]}
    assert family_rows[(0, 1000, "fermat_number_factor_periphery")]["family_count_increment"] == 1
    assert family_rows[(1000, 2000, "fermat_number_factor_periphery")]["family_count_increment"] == 0
    assert family_rows[(1000, 2000, "base2_wieferich_prime")]["family_count_increment"] == 1
    assert payload["metadata"]["proof_status"] == "finite_family_interval_probe_not_rh_evidence"


def test_prime_power_decomposition_splits_psi_layers() -> None:
    payload = prime_power_decomposition(points=[10], dps=60, include_events=True)
    row = payload["cumulative_rows"][0]
    expected_theta = mp.log(2) + mp.log(3) + mp.log(5) + mp.log(7)
    expected_higher = (2 * mp.log(2)) + mp.log(3)
    assert abs(mp.mpf(row["theta_x"]) - expected_theta) < mp.mpf("1e-40")
    assert abs(mp.mpf(row["higher_prime_power_sum"]) - expected_higher) < mp.mpf("1e-40")
    assert payload["summary"]["max_exponent_seen"] == 3
    events = {(event["prime"], event["exponent"], event["prime_power"]) for event in payload["event_rows"]}
    assert (2, 3, 8) in events
    assert payload["metadata"]["proof_status"] == "finite_prime_power_decomposition_not_rh_evidence"


def test_explicit_formula_probe_compares_finite_zero_terms_to_psi() -> None:
    payload = explicit_formula_probe(points=[100], zero_counts=[5], dps=60, include_zero_terms=True)
    row = payload["rows"][0]
    assert row["prime_pi"] == 25
    assert row["zero_pair_count"] == 5
    assert mp.mpf(row["residual_abs"]) < mp.mpf("2")
    assert len(payload["zero_term_rows"]) == 5
    assert payload["zero_term_rows"][0]["zero_index"] == 1
    assert payload["metadata"]["proof_status"] == "finite_explicit_formula_probe_not_zero_certification"


def test_zero_window_probe_applies_supported_smoothing_weights() -> None:
    assert zero_window_weight(1, 5, "sharp") == mp.mpf("1")
    assert zero_window_weight(1, 5, "fejer") == mp.mpf("5") / 6
    ratio = mp.mpf("1") / 6
    expected_lanczos = mp.sin(mp.pi * ratio) / (mp.pi * ratio)
    expected_hann = mp.mpf("0.5") * (mp.mpf("1") + mp.cos(mp.pi * ratio))
    assert abs(zero_window_weight(1, 5, "lanczos") - expected_lanczos) < mp.mpf("1e-50")
    assert abs(zero_window_weight(1, 5, "hann") - expected_hann) < mp.mpf("1e-50")
    payload = zero_window_probe(
        points=[100],
        zero_counts=[5],
        windows=["sharp", "fejer", "lanczos", "hann"],
        dps=60,
        include_zero_terms=True,
    )
    rows = {(row["window"], row["zero_pair_count"]): row for row in payload["rows"]}
    assert set(row["window"] for row in payload["rows"]) == {"sharp", "fejer", "lanczos", "hann"}
    assert rows[("sharp", 5)]["windowed_explicit_formula_estimate"] != rows[("fejer", 5)]["windowed_explicit_formula_estimate"]
    assert rows[("lanczos", 5)]["windowed_explicit_formula_estimate"] != rows[("hann", 5)]["windowed_explicit_formula_estimate"]
    first_fejer = next(row for row in payload["zero_term_rows"] if row["window"] == "fejer" and row["zero_index"] == 1)
    assert abs(mp.mpf(first_fejer["window_weight"]) - (mp.mpf("5") / 6)) < mp.mpf("1e-50")
    first_lanczos = next(row for row in payload["zero_term_rows"] if row["window"] == "lanczos" and row["zero_index"] == 1)
    first_hann = next(row for row in payload["zero_term_rows"] if row["window"] == "hann" and row["zero_index"] == 1)
    assert abs(mp.mpf(first_lanczos["window_weight"]) - expected_lanczos) < mp.mpf("1e-50")
    assert abs(mp.mpf(first_hann["window_weight"]) - expected_hann) < mp.mpf("1e-50")
    assert "lanczos" in payload["parameters"]["window_definitions"]
    assert "hann" in payload["parameters"]["window_definitions"]
    assert payload["metadata"]["proof_status"] == "finite_zero_window_probe_not_zero_certification"


def test_zero_window_stability_atlas_summarizes_window_cutoffs() -> None:
    payload = zero_window_stability_atlas(
        points=[100],
        zero_counts=[5, 10],
        windows=["sharp", "hann"],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 4
    assert payload["summary"]["best_window_row_count"] == 2
    assert payload["summary"]["window_summary_row_count"] == 2
    assert payload["summary"]["cutoff_transition_row_count"] == 2
    assert len(payload["sample_summary_rows"]) == 1
    assert set(row["window"] for row in payload["window_summary_rows"]) == {"sharp", "hann"}
    assert set(row["best_window"] for row in payload["best_window_rows"]) <= {"sharp", "hann"}
    assert payload["metadata"]["proof_status"] == "finite_explicit_residual_stability_atlas_not_zero_certification"


def test_zero_height_cutoff_atlas_uses_height_weighted_windows() -> None:
    assert zero_height_window_weight("10", "20", "sharp") == mp.mpf("1")
    assert zero_height_window_weight("10", "20", "fejer") == mp.mpf("0.5")
    ratio = mp.mpf("0.5")
    expected_lanczos = mp.sin(mp.pi * ratio) / (mp.pi * ratio)
    expected_hann = mp.mpf("0.5") * (mp.mpf("1") + mp.cos(mp.pi * ratio))
    assert abs(zero_height_window_weight("10", "20", "lanczos") - expected_lanczos) < mp.mpf("1e-50")
    assert abs(zero_height_window_weight("10", "20", "hann") - expected_hann) < mp.mpf("1e-50")
    payload = zero_height_cutoff_atlas(
        points=[100],
        zero_heights=["15", "25"],
        windows=["sharp", "fejer"],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 4
    assert payload["summary"]["best_window_row_count"] == 2
    assert payload["summary"]["height_transition_row_count"] == 2
    counts_by_height = {row["zero_height_cutoff"]: row["zero_pair_count"] for row in payload["rows"] if row["window"] == "sharp"}
    assert counts_by_height["15.0"] == 1
    assert counts_by_height["25.0"] == 2
    assert payload["metadata"]["proof_status"] == "finite_zero_height_cutoff_atlas_not_zero_certification"


def test_scale_tied_zero_height_atlas_uses_log_law() -> None:
    assert abs(scale_tied_zero_height(100, "4", "log") - (mp.mpf("4") * mp.log(100))) < mp.mpf("1e-50")
    assert abs(scale_tied_zero_height(100, "2", "sqrt") - (mp.mpf("2") * mp.sqrt(100))) < mp.mpf("1e-50")
    assert abs(scale_tied_zero_height(100, "0.5", "sqrt_log") - (mp.mpf("0.5") * mp.sqrt(100) * mp.log(100))) < mp.mpf("1e-50")
    payload = scale_tied_zero_height_atlas(
        points=[100],
        multipliers=["4", "8"],
        scale_law="log",
        windows=["sharp", "fejer"],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 4
    assert payload["summary"]["best_window_row_count"] == 2
    assert payload["summary"]["multiplier_transition_row_count"] == 2
    assert payload["parameters"]["scale_law"] == "log"
    ratios = {row["scale_multiplier"]: row["zero_height_over_log_x"] for row in payload["rows"] if row["window"] == "sharp"}
    assert abs(mp.mpf(ratios["4.0"]) - mp.mpf("4")) < mp.mpf("1e-50")
    assert abs(mp.mpf(ratios["8.0"]) - mp.mpf("8")) < mp.mpf("1e-50")
    assert payload["metadata"]["proof_status"] == "finite_scale_tied_zero_height_atlas_not_zero_certification"


def test_scale_law_comparison_atlas_summarizes_declared_laws() -> None:
    payload = scale_law_comparison_atlas(
        points=[100],
        scale_laws=["log", "sqrt_log"],
        windows=["sharp"],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 9
    assert payload["summary"]["law_summary_row_count"] == 2
    assert payload["summary"]["sample_best_law_row_count"] == 1
    assert {row["scale_law"] for row in payload["law_summary_rows"]} == {"log", "sqrt_log"}
    assert {row["scale_law"] for row in payload["multiplier_transition_rows"]} == {"log", "sqrt_log"}
    assert payload["sample_best_law_rows"][0]["best_scale_law"] in {"log", "sqrt_log"}
    assert payload["metadata"]["proof_status"] == "finite_scale_law_comparison_not_zero_certification"


def test_lambda_mellin_bridge_atlas_uses_shared_lambda_unit() -> None:
    payload = lambda_mellin_bridge_atlas(
        n_bounds=[10],
        samples=[("2", "0")],
        multipliers=["16"],
        windows=["sharp"],
        dps=60,
    )
    row = payload["rows"][0]
    assert payload["summary"]["row_count"] == 1
    assert payload["summary"]["best_bridge_row_count"] == 1
    assert row["n_bound"] == 10
    assert row["scale_law"] == "log"
    assert row["window"] == "sharp"
    assert abs(mp.mpf(row["exact_psi_n"]) - chebyshev_psi(10)) < mp.mpf("1e-50")
    assert "bridge_residual_abs" in row
    assert payload["metadata"]["proof_status"] == "finite_lambda_mellin_bridge_not_rh_evidence"


def test_partial_summation_bridge_atlas_reconstructs_exact_lambda_unit() -> None:
    payload = partial_summation_bridge_atlas(
        n_bounds=[10],
        samples=[("2", "0")],
        multipliers=["16"],
        windows=["sharp"],
        dps=60,
    )
    row = payload["rows"][0]
    assert payload["summary"]["row_count"] == 1
    assert payload["summary"]["best_partial_row_count"] == 1
    assert row["n_bound"] == 10
    assert row["scale_law"] == "log"
    assert row["window"] == "sharp"
    assert mp.mpf(row["exact_partial_summation_residual_abs"]) < mp.mpf("1e-50")
    assert "raw_bridge_residual_abs" in row
    assert "partial_over_raw_bridge_residual_abs" in row
    assert payload["metadata"]["proof_status"] == "finite_partial_summation_bridge_not_rh_evidence"


def test_cesaro_mellin_bridge_atlas_reports_kernel_against_raw_baseline() -> None:
    assert n_domain_kernel_weight(10, 10, "sharp") == 1
    assert n_domain_kernel_weight(10, 10, "cesaro") < 1
    payload = cesaro_mellin_bridge_atlas(
        n_bounds=[10],
        samples=[("2", "0")],
        multipliers=["16"],
        windows=["sharp"],
        kernels=["sharp", "cesaro"],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 2
    assert payload["summary"]["kernel_summary_row_count"] == 2
    rows_by_kernel = {row["n_domain_kernel"]: row for row in payload["rows"]}
    assert rows_by_kernel["sharp"]["smoothed_over_raw_bridge_residual_abs"] == "1.0"
    assert "exact_smoothed_cutoff_residual_abs" in rows_by_kernel["cesaro"]
    assert payload["metadata"]["proof_status"] == "finite_cesaro_mellin_bridge_not_rh_evidence"


def test_bias_tuned_kernel_bridge_atlas_scans_alpha_tradeoff() -> None:
    assert alpha_cesaro_kernel_weight(10, 10, "0") == 1
    assert alpha_cesaro_kernel_weight(10, 10, "1") == n_domain_kernel_weight(10, 10, "cesaro")
    payload = bias_tuned_kernel_bridge_atlas(
        n_bounds=[10],
        samples=[("2", "0")],
        multipliers=["16"],
        windows=["sharp"],
        alphas=["0", "1"],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 2
    assert payload["summary"]["alpha_summary_row_count"] == 2
    rows_by_alpha = {row["alpha"]: row for row in payload["rows"]}
    assert rows_by_alpha["0.0"]["bridge_over_sharp_residual_abs"] == "1.0"
    assert "cutoff_bias_increase_over_sharp_abs" in rows_by_alpha["1.0"]
    assert payload["pareto_rows"]
    assert payload["metadata"]["proof_status"] == "finite_bias_tuned_kernel_bridge_not_rh_evidence"


def test_explicit_residual_movement_decomposition_balances_layers() -> None:
    payload = explicit_residual_movement_decomposition(
        points=[100, 200, 300],
        multipliers=["16"],
        windows=["sharp"],
        dps=60,
    )
    assert payload["summary"]["point_row_count"] == 3
    assert payload["summary"]["movement_row_count"] == 2
    row = payload["movement_rows"][0]
    theta_error = mp.mpf(row["theta_error_movement"])
    higher = mp.mpf(row["higher_prime_power_movement"])
    psi_error = mp.mpf(row["psi_error_movement"])
    residual = mp.mpf(row["explicit_residual_movement"])
    estimate_movement = mp.mpf(row["explicit_psi_estimate_movement"])
    psi_increment = mp.mpf(row["psi_increment"])
    assert abs((theta_error + higher) - psi_error) < mp.mpf("1e-50")
    assert abs((estimate_movement - psi_increment) - residual) < mp.mpf("1e-50")
    assert row["dominant_exact_layer_by_abs_movement"] in {
        "theta_error_movement",
        "higher_prime_power_movement",
        "balanced_or_zero",
    }
    assert payload["metadata"]["proof_status"] == "finite_explicit_residual_movement_decomposition_not_rh_evidence"


def test_euler_product_probe_improves_in_convergent_half_plane() -> None:
    payload = euler_product_probe(samples=[("2", "0")], prime_bounds=[10, 100], dps=60, include_terms=True)
    rows = {row["prime_bound"]: row for row in payload["rows"]}
    product_small = mp.mpf(rows[10]["euler_product_residual_abs"])
    product_large = mp.mpf(rows[100]["euler_product_residual_abs"])
    log_small = mp.mpf(rows[10]["prime_factor_log_derivative_residual_abs"])
    log_large = mp.mpf(rows[100]["prime_factor_log_derivative_residual_abs"])
    assert product_large < product_small
    assert log_large < log_small
    assert rows[100]["prime_count"] == 25
    assert rows[100]["prime_power_term_count"] > rows[100]["prime_count"]
    assert payload["prime_factor_rows"]
    assert payload["prime_power_term_rows"]
    assert payload["metadata"]["proof_status"] == "finite_euler_product_log_derivative_probe_not_rh_evidence"


def test_sigma_boundary_probe_tracks_distance_and_transitions() -> None:
    payload = sigma_boundary_probe(sigmas=["2", "1.5", "1.1"], t_values=["0"], prime_bounds=[100], dps=60)
    assert payload["summary"]["minimum_sigma"] == "1.1"
    assert abs(mp.mpf(payload["summary"]["minimum_distance_to_sigma_1"]) - mp.mpf("0.1")) < mp.mpf("1e-25")
    rows = {(row["sigma"], row["prime_bound"]): row for row in payload["rows"]}
    assert abs(mp.mpf(rows[("1.1", 100)]["distance_to_sigma_1"]) - mp.mpf("0.1")) < mp.mpf("1e-25")
    assert len(payload["transition_rows"]) == 2
    assert payload["transition_rows"][0]["direction"] == "toward_sigma_1_from_above"
    assert payload["metadata"]["proof_status"] == "finite_sigma_boundary_probe_not_critical_line_evidence"


def test_t_axis_boundary_probe_marks_reference_landmarks() -> None:
    payload = t_axis_boundary_probe(
        sigmas=["1.5"],
        t_values=["0", "14.134725141734693790457251983562", "20"],
        prime_bounds=[100],
        dps=60,
    )
    rows_by_annotation = {row["t_axis_annotation"]: row for row in payload["rows"]}
    assert mp.mpf(rows_by_annotation["pole_axis_reference"]["t"]) == mp.mpf("0")
    assert rows_by_annotation["known_zero_ordinate_landmark"]["nearest_reference_label"] == "first_zero_ordinate_reference"
    assert mp.mpf(rows_by_annotation["ordinary_vertical_sample"]["t"]) == mp.mpf("20")
    assert len(payload["transition_rows"]) == 2
    assert payload["summary"]["landmark_row_count"] == 1
    assert payload["metadata"]["proof_status"] == "finite_t_axis_boundary_probe_not_zero_line_evidence"


def test_vertical_resonance_scan_returns_candidates() -> None:
    payload = vertical_resonance_scan(
        sigmas=["1.5"],
        t_min="0",
        t_max="30",
        step="5",
        prime_bounds=[100],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 7
    assert payload["summary"]["candidate_count"] >= 1
    candidate = payload["candidate_rows"][0]
    assert candidate["extremum_type"] in {"local_minimum", "local_maximum"}
    assert candidate["metric"] in payload["parameters"]["metrics"]
    assert payload["metadata"]["proof_status"] == "finite_vertical_resonance_scan_not_zero_line_evidence"


def test_lambda_oscilloscope_includes_prime_powers_and_hard_window() -> None:
    payload = lambda_oscilloscope_probe(
        sigmas=["2"],
        t_min="0",
        t_max="0",
        step="1",
        prime_power_bound=10,
        dps=60,
        include_terms=True,
    )
    term_powers = [row["prime_power"] for row in payload["term_rows"]]
    assert term_powers == [2, 3, 4, 5, 7, 8, 9]
    assert {row["window_weight"] for row in payload["term_rows"]} == {"1.0"}
    assert payload["summary"]["term_count_per_trace"] == 7
    assert payload["metadata"]["proof_status"] == "finite_lambda_oscilloscope_trace_not_rh_evidence"


def test_lambda_oscilloscope_fejer_window_and_comparison_boundary() -> None:
    assert abs(lambda_window_weight(2, 10, "fejer") - (mp.mpf("1") - (mp.mpf("2") / 11))) < mp.mpf("1e-50")
    payload = lambda_oscilloscope_probe(
        sigmas=["2", "0.5"],
        t_min="0",
        t_max="0",
        step="1",
        prime_power_bound=10,
        window="fejer",
        dps=60,
        include_terms=True,
    )
    rows = {row["sigma"]: row for row in payload["rows"]}
    assert rows["2.0"]["comparison_status"] == "compared_to_negative_zeta_prime_over_zeta"
    assert mp.mpf(rows["2.0"]["finite_trace_residual_abs"]) > 0
    assert rows["0.5"]["comparison_status"] == "not_compared_sigma_not_greater_than_one"
    first_sigma_terms = [row for row in payload["term_rows"] if row["sigma"] == "2.0"]
    first_term = next(row for row in first_sigma_terms if row["prime_power"] == 2)
    assert abs(mp.mpf(first_term["window_weight"]) - (mp.mpf("1") - (mp.mpf("2") / 11))) < mp.mpf("1e-50")


def test_lambda_window_cutoff_scan_reports_candidates_and_stability() -> None:
    payload = lambda_window_cutoff_scan(
        sigmas=["1.5"],
        t_min="0",
        t_max="30",
        step="5",
        prime_power_bounds=[50, 100],
        windows=["hard", "fejer"],
        dps=60,
    )
    assert payload["summary"]["row_count"] == 28
    assert payload["summary"]["candidate_count"] > 0
    assert payload["summary"]["cutoff_stability_row_count"] > 0
    assert payload["summary"]["cross_window_row_count"] > 0
    candidate = payload["candidate_rows"][0]
    assert candidate["metric"] in {"lambda_trace_abs", "finite_trace_residual_abs"}
    assert candidate["extremum_type"] in {"local_minimum", "local_maximum"}
    assert payload["metadata"]["proof_status"] == "finite_lambda_window_cutoff_scan_not_rh_evidence"


def test_lambda_phasor_reference_contribution_separates_layers() -> None:
    payload = lambda_phasor_reference_contribution(
        sigmas=["1.5"],
        reference_labels=["first_zero_ordinate_reference"],
        offsets=["0"],
        prime_power_bounds=[10],
        windows=["hard"],
        dps=60,
        top_terms=3,
    )
    assert payload["summary"]["row_count"] == 1
    row = payload["rows"][0]
    assert row["reference_label"] == "first_zero_ordinate_reference"
    assert row["comparison_status"] == "compared_to_negative_zeta_prime_over_zeta"
    layer_rows = {layer["layer_id"]: layer for layer in payload["layer_rows"]}
    assert layer_rows["prime_terms"]["term_count"] == 4
    assert layer_rows["higher_prime_power_terms"]["term_count"] == 3
    assert payload["top_projection_rows"]
    assert payload["metadata"]["proof_status"] == "finite_lambda_phasor_reference_contribution_not_rh_evidence"


def test_exponential_shift_probe_detects_shift_two_small_factors() -> None:
    payload = exponential_shift_probe(
        base=65537,
        exponents=[641 * 3, 641 * 5, 641 * 17],
        shifts=[2, -2],
        small_factor_limit=100000,
        dps=60,
    )
    rows = {(row["exponent"], row["shift"]): row for row in payload["rows"]}
    assert 5 in rows[(641 * 3, 2)]["small_divisors"]
    assert 17 in rows[(641 * 5, 2)]["small_divisors"]
    assert rows[(641 * 17, 2)]["bounded_result"] == "no_small_divisor_found_within_bound"
    assert 257 in rows[(641 * 17, -2)]["small_divisors"]
    assert payload["metadata"]["proof_status"] == "bounded_exponential_shift_probe_not_primality_proof"


def test_exponential_power_shift_probe_handles_huge_exponents_modularly() -> None:
    payload = exponential_power_shift_probe(
        base=65537,
        exponent_base=641,
        exponent_powers=[3, 5, 17],
        shifts=[1, 2, 4],
        small_factor_limit=1000000,
        dps=60,
    )
    rows = {(row["exponent_power"], row["shift"]): row for row in payload["rows"]}
    assert 3 in rows[(3, 1)]["small_divisors"]
    assert 3 in rows[(3, 4)]["small_divisors"]
    assert 7 in rows[(3, 2)]["small_divisors"]
    assert 7 in rows[(5, 2)]["small_divisors"]
    assert 7 in rows[(17, 2)]["small_divisors"]
    assert payload["metadata"]["proof_status"] == "bounded_power_exponent_shift_probe_not_primality_proof"


def test_coefficient_power_shift_probe_tracks_n_dependent_shifts() -> None:
    payload = coefficient_power_shift_probe(
        coefficient=65537,
        power_base=641,
        powers=[3, 5, 17],
        fixed_shifts=[1, -1],
        shift_modes=["plus_n", "minus_n", "n_plus_1", "one_minus_n", "minus_n_minus_1"],
        small_factor_limit=1000000,
        dps=60,
    )
    rows = {(row["power"], row["shift_label"]): row for row in payload["rows"]}
    assert 2 in rows[(3, "fixed_+1")]["small_divisors"]
    assert 2 in rows[(5, "fixed_-1")]["small_divisors"]
    assert 5 in rows[(3, "plus_n")]["small_divisors"]
    assert rows[(5, "n_plus_1")]["bounded_result"] == "no_small_divisor_found_within_bound"
    assert rows[(17, "minus_n_minus_1")]["bounded_result"] == "no_small_divisor_found_within_bound"
    assert payload["metadata"]["proof_status"] == "bounded_coefficient_power_shift_probe_not_primality_proof"


def test_irregular_prime_scan_finds_first_irregular_primes() -> None:
    pairs_37 = irregular_pairs_for_prime(37)
    assert [pair["bernoulli_index"] for pair in pairs_37] == [32]
    payload = irregular_prime_scan(limit=70, dps=60)
    assert payload["summary"]["irregular_primes"] == [37, 59, 67]
    assert payload["summary"]["first_irregular_prime"] == 37
    assert payload["metadata"]["proof_status"] == "finite_irregular_prime_scan_not_zero_line_evidence"


def test_irregular_prime_distribution_returns_to_global_objects() -> None:
    payload = irregular_prime_distribution(points=[100, 200], dps=60, include_members=True)
    global_rows = {row["x"]: row for row in payload["global_rows"]}
    assert global_rows[100]["prime_pi"] == 25
    assert global_rows[200]["odd_prime_count"] == 45
    rows = {row["x"]: row for row in payload["rows"]}
    assert rows[100]["irregular_prime_count"] == 3
    assert rows[100]["irregular_primes_up_to_x"] == [37, 59, 67]
    assert rows[200]["irregular_prime_count"] == 8
    assert rows[200]["last_irregular_prime"] == 157
    assert payload["metadata"]["proof_status"] == "finite_irregular_prime_distribution_not_zero_line_evidence"
