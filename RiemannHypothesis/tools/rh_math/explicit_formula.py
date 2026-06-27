"""Finite explicit-formula probes for psi(x) and nontrivial zero terms."""

from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp

from .common import complex_record, metadata, mp_str, set_precision
from .distribution import chebyshev_psi, chebyshev_theta
from .euler_product import REFERENCE_T_VALUES, negative_zeta_log_derivative
from .primes import generated_sample_points

SUPPORTED_ZERO_WINDOWS = ("sharp", "fejer", "lanczos", "hann")
SUPPORTED_SCALE_LAWS = ("log", "sqrt", "sqrt_log")
SUPPORTED_N_DOMAIN_KERNELS = ("sharp", "cesaro", "hann")
DEFAULT_LAMBDA_MELLIN_SAMPLES = (
    ("2", "0"),
    ("2", REFERENCE_T_VALUES["first_zero_ordinate_reference"]),
    ("1.5", REFERENCE_T_VALUES["first_zero_ordinate_reference"]),
)
DEFAULT_SCALE_LAW_MULTIPLIERS = {
    "log": ("8", "12", "16", "24", "32"),
    "sqrt": ("1", "2", "3", "4", "6"),
    "sqrt_log": ("0.25", "0.5", "0.75", "1"),
}


def _selected_sample_points(points: list[int] | None, max_x: int | None, count: int) -> list[int]:
    if points:
        sample_points = sorted(set(int(x) for x in points))
    else:
        sample_points = generated_sample_points(int(max_x or 1000), int(count))
    if not sample_points:
        raise ValueError("at least one sample point is required")
    if sample_points[0] <= 1:
        raise ValueError("explicit-formula sample points must be greater than 1")
    return sample_points


def _selected_zero_counts(zero_counts: list[int] | None) -> list[int]:
    selected = sorted(set(int(value) for value in (zero_counts or [5, 10, 20])))
    if not selected or selected[0] < 1:
        raise ValueError("zero pair counts must be positive")
    return selected


def _selected_windows(windows: list[str] | None) -> list[str]:
    selected = [value.lower() for value in (windows or ["sharp", "fejer"])]
    allowed = set(SUPPORTED_ZERO_WINDOWS)
    unsupported = sorted(set(selected) - allowed)
    if unsupported:
        raise ValueError(f"unsupported windows: {', '.join(unsupported)}")
    return list(dict.fromkeys(selected))


def zero_window_weight(zero_index: int, zero_pair_count: int, window: str) -> mp.mpf:
    if zero_index < 1:
        raise ValueError("zero_index must be positive")
    if zero_pair_count < 1:
        raise ValueError("zero_pair_count must be positive")
    window = window.lower()
    if window == "sharp":
        return mp.mpf("1")
    if window == "fejer":
        return mp.mpf(1) - (mp.mpf(zero_index) / (zero_pair_count + 1))
    ratio = mp.mpf(zero_index) / (zero_pair_count + 1)
    if window == "lanczos":
        return mp.sin(mp.pi * ratio) / (mp.pi * ratio)
    if window == "hann":
        return mp.mpf("0.5") * (mp.mpf("1") + mp.cos(mp.pi * ratio))
    raise ValueError(f"unsupported window: {window}")


def zero_height_window_weight(zero_height: mp.mpf | str | float, cutoff_height: mp.mpf | str | float, window: str) -> mp.mpf:
    gamma = mp.mpf(zero_height)
    cutoff = mp.mpf(cutoff_height)
    if gamma <= 0:
        raise ValueError("zero_height must be positive")
    if cutoff <= 0:
        raise ValueError("cutoff_height must be positive")
    if gamma > cutoff:
        raise ValueError("zero_height must be less than or equal to cutoff_height")
    window = window.lower()
    if window == "sharp":
        return mp.mpf("1")
    ratio = gamma / cutoff
    if window == "fejer":
        return mp.mpf("1") - ratio
    if window == "lanczos":
        return mp.sin(mp.pi * ratio) / (mp.pi * ratio)
    if window == "hann":
        return mp.mpf("0.5") * (mp.mpf("1") + mp.cos(mp.pi * ratio))
    raise ValueError(f"unsupported window: {window}")


def _zero_pair_terms(x: int, zero_pair_count: int) -> list[dict[str, Any]]:
    xx = mp.mpf(x)
    terms: list[dict[str, Any]] = []
    cumulative = mp.mpc("0")
    for zero_index in range(1, zero_pair_count + 1):
        rho = mp.zetazero(zero_index)
        conjugate = mp.conj(rho)
        pair_term = mp.power(xx, rho) / rho + mp.power(xx, conjugate) / conjugate
        cumulative += pair_term
        terms.append(
            {
                "x": int(x),
                "zero_index": zero_index,
                "zero": complex_record(rho),
                "pair_contribution": mp_str(mp.re(pair_term)),
                "pair_contribution_imag": mp_str(mp.im(pair_term)),
                "cumulative_zero_pair_sum": mp_str(mp.re(cumulative)),
            }
        )
    return terms


def _zero_pair_terms_until_height(x: int, zero_height: mp.mpf) -> list[dict[str, Any]]:
    xx = mp.mpf(x)
    terms: list[dict[str, Any]] = []
    cumulative = mp.mpc("0")
    zero_index = 1
    while True:
        rho = mp.zetazero(zero_index)
        gamma = abs(mp.im(rho))
        if gamma > zero_height:
            break
        conjugate = mp.conj(rho)
        pair_term = mp.power(xx, rho) / rho + mp.power(xx, conjugate) / conjugate
        cumulative += pair_term
        terms.append(
            {
                "x": int(x),
                "zero_index": zero_index,
                "zero_height": mp_str(gamma),
                "zero": complex_record(rho),
                "pair_contribution": mp_str(mp.re(pair_term)),
                "pair_contribution_imag": mp_str(mp.im(pair_term)),
                "cumulative_zero_pair_sum": mp_str(mp.re(cumulative)),
            }
        )
        zero_index += 1
    return terms


def _windowed_zero_pair_terms(x: int, zero_pair_count: int, window: str) -> list[dict[str, Any]]:
    terms = _zero_pair_terms(x, zero_pair_count)
    cumulative = mp.mpf("0")
    for term in terms:
        weight = zero_window_weight(int(term["zero_index"]), zero_pair_count, window)
        weighted = weight * mp.mpf(term["pair_contribution"])
        cumulative += weighted
        term["window"] = window
        term["window_weight"] = mp_str(weight)
        term["weighted_pair_contribution"] = mp_str(weighted)
        term["cumulative_weighted_zero_pair_sum"] = mp_str(cumulative)
    return terms


def _windowed_zero_pair_sum_from_terms(terms: list[dict[str, Any]], zero_pair_count: int, window: str) -> mp.mpf:
    if zero_pair_count > len(terms):
        raise ValueError("not enough zero-pair terms for requested count")
    return mp.fsum(
        zero_window_weight(zero_index, zero_pair_count, window) * mp.mpf(terms[zero_index - 1]["pair_contribution"])
        for zero_index in range(1, zero_pair_count + 1)
    )


def _selected_zero_heights(zero_heights: list[str] | list[float] | None) -> list[mp.mpf]:
    selected = sorted(set(mp.mpf(value) for value in (zero_heights or ["20", "40", "80", "120", "160"])))
    if not selected or selected[0] <= 0:
        raise ValueError("zero-height cutoffs must be positive")
    return selected


def _selected_scale_multipliers(multipliers: list[str] | list[float] | None) -> list[mp.mpf]:
    selected = sorted(set(mp.mpf(value) for value in (multipliers or ["4", "6", "8", "12", "16", "24", "32"])))
    if not selected or selected[0] <= 0:
        raise ValueError("scale multipliers must be positive")
    return selected


def _selected_scale_laws(scale_laws: list[str] | None) -> list[str]:
    selected = [value.lower() for value in (scale_laws or list(SUPPORTED_SCALE_LAWS))]
    unsupported = sorted(set(selected) - set(SUPPORTED_SCALE_LAWS))
    if unsupported:
        raise ValueError(f"unsupported scale laws: {', '.join(unsupported)}")
    return list(dict.fromkeys(selected))


def _selected_bridge_n_bounds(n_bounds: list[int] | None) -> list[int]:
    selected = sorted(set(int(value) for value in (n_bounds or [50, 100, 200])))
    if not selected or selected[0] < 2:
        raise ValueError("bridge N bounds must be at least 2")
    return selected


def _selected_bridge_samples(
    samples: list[tuple[str | float, str | float]] | None,
) -> list[tuple[mp.mpf, mp.mpf]]:
    selected = samples or list(DEFAULT_LAMBDA_MELLIN_SAMPLES)
    if not selected:
        raise ValueError("at least one bridge s sample is required")
    parsed: list[tuple[mp.mpf, mp.mpf]] = []
    for sigma_value, t_value in selected:
        sigma = mp.mpf(str(sigma_value))
        t = mp.mpf(str(t_value))
        if sigma <= 1:
            raise ValueError("Lambda-Mellin bridge samples require sigma greater than 1")
        parsed.append((sigma, t))
    return parsed


def _selected_n_domain_kernels(kernels: list[str] | None) -> list[str]:
    selected = [value.lower() for value in (kernels or list(SUPPORTED_N_DOMAIN_KERNELS))]
    unsupported = sorted(set(selected) - set(SUPPORTED_N_DOMAIN_KERNELS))
    if unsupported:
        raise ValueError(f"unsupported n-domain kernels: {', '.join(unsupported)}")
    return list(dict.fromkeys(selected))


def _selected_kernel_alphas(alphas: list[str] | list[float] | None) -> list[mp.mpf]:
    selected = sorted(set(mp.mpf(value) for value in (alphas or ["0", "0.25", "0.5", "0.75", "1"])))
    if not selected:
        raise ValueError("at least one kernel alpha is required")
    if selected[0] < 0 or selected[-1] > 1:
        raise ValueError("kernel alpha values must be in [0, 1]")
    return selected


def scale_tied_zero_height(x: int, multiplier: mp.mpf | str | float, law: str) -> mp.mpf:
    if x <= 1:
        raise ValueError("x must be greater than 1")
    c = mp.mpf(multiplier)
    if c <= 0:
        raise ValueError("scale multiplier must be positive")
    law = law.lower()
    if law == "log":
        return c * mp.log(x)
    if law == "sqrt":
        return c * mp.sqrt(x)
    if law == "sqrt_log":
        return c * mp.sqrt(x) * mp.log(x)
    raise ValueError(f"unsupported scale law: {law}")


def _height_windowed_zero_pair_sum_from_terms(
    terms: list[dict[str, Any]],
    cutoff_height: mp.mpf,
    window: str,
) -> tuple[mp.mpf, int, str | None]:
    selected_terms = [term for term in terms if mp.mpf(term["zero_height"]) <= cutoff_height]
    zero_pair_sum = mp.fsum(
        zero_height_window_weight(term["zero_height"], cutoff_height, window) * mp.mpf(term["pair_contribution"])
        for term in selected_terms
    )
    max_height_used = selected_terms[-1]["zero_height"] if selected_terms else None
    return zero_pair_sum, len(selected_terms), max_height_used


def explicit_formula_estimate(x: int, zero_pair_count: int, dps: int = 80) -> dict[str, Any]:
    if x <= 1:
        raise ValueError("x must be greater than 1")
    if zero_pair_count < 1:
        raise ValueError("zero_pair_count must be positive")
    set_precision(dps)
    xx = mp.mpf(x)
    terms = _zero_pair_terms(int(x), int(zero_pair_count))
    zero_pair_sum = mp.fsum(mp.mpf(term["pair_contribution"]) for term in terms)
    constant_log_2pi = mp.log(2 * mp.pi)
    trivial_zero_correction = mp.mpf("0.5") * mp.log(1 - xx ** -2)
    estimate = xx - zero_pair_sum - constant_log_2pi - trivial_zero_correction
    return {
        "x": int(x),
        "zero_pair_count": int(zero_pair_count),
        "zero_pair_sum": zero_pair_sum,
        "constant_log_2pi": constant_log_2pi,
        "trivial_zero_correction": trivial_zero_correction,
        "estimate": estimate,
        "zero_term_rows": terms,
    }


def explicit_formula_probe(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 6,
    zero_counts: list[int] | None = None,
    dps: int = 80,
    include_zero_terms: bool = False,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_zero_counts = _selected_zero_counts(zero_counts)
    rows: list[dict[str, Any]] = []
    zero_term_rows: list[dict[str, Any]] = []

    for x in sample_points:
        prime_pi = int(sp.primepi(x))
        theta_x = chebyshev_theta(x)
        psi_x = chebyshev_psi(x)
        sqrt_x = mp.sqrt(x)
        scale = sqrt_x * mp.log(x)
        for zero_pair_count in selected_zero_counts:
            estimate_record = explicit_formula_estimate(x, zero_pair_count, dps=dps)
            estimate = mp.mpf(estimate_record["estimate"])
            residual = estimate - psi_x
            row = {
                "x": x,
                "zero_pair_count": zero_pair_count,
                "prime_pi": prime_pi,
                "theta_x": mp_str(theta_x),
                "theta_minus_x": mp_str(theta_x - x),
                "psi_x": mp_str(psi_x),
                "psi_minus_x": mp_str(psi_x - x),
                "explicit_formula_estimate": mp_str(estimate),
                "estimate_minus_psi": mp_str(residual),
                "estimate_minus_x": mp_str(estimate - x),
                "residual_abs": mp_str(abs(residual)),
                "residual_over_sqrt_x": mp_str(residual / sqrt_x if sqrt_x else 0),
                "residual_over_sqrt_x_log_x": mp_str(residual / scale if scale else 0),
                "zero_pair_sum": mp_str(estimate_record["zero_pair_sum"]),
                "constant_log_2pi": mp_str(estimate_record["constant_log_2pi"]),
                "trivial_zero_correction": mp_str(estimate_record["trivial_zero_correction"]),
            }
            rows.append(row)
            if include_zero_terms:
                for term in estimate_record["zero_term_rows"]:
                    zero_term_rows.append({**term, "zero_pair_count": zero_pair_count})

    return {
        "metadata": metadata(
            "explicit_formula_probe",
            dps,
            "finite_explicit_formula_probe_not_zero_certification",
        ),
        "parameters": {
            "points": sample_points,
            "zero_counts": selected_zero_counts,
            "include_zero_terms": include_zero_terms,
            "formula": "psi(x) ~= x - sum_rho x^rho/rho - log(2*pi) - 1/2*log(1 - x^-2)",
        },
        "summary": {
            "max_sample": max(sample_points),
            "max_zero_pair_count": max(selected_zero_counts),
            "row_count": len(rows),
        },
        "rows": rows,
        "zero_term_rows": zero_term_rows,
    }


def zero_window_estimate(x: int, zero_pair_count: int, window: str, dps: int = 80) -> dict[str, Any]:
    if x <= 1:
        raise ValueError("x must be greater than 1")
    if zero_pair_count < 1:
        raise ValueError("zero_pair_count must be positive")
    set_precision(dps)
    window = window.lower()
    xx = mp.mpf(x)
    terms = _windowed_zero_pair_terms(int(x), int(zero_pair_count), window)
    zero_pair_sum = mp.fsum(mp.mpf(term["weighted_pair_contribution"]) for term in terms)
    constant_log_2pi = mp.log(2 * mp.pi)
    trivial_zero_correction = mp.mpf("0.5") * mp.log(1 - xx ** -2)
    estimate = xx - zero_pair_sum - constant_log_2pi - trivial_zero_correction
    return {
        "x": int(x),
        "zero_pair_count": int(zero_pair_count),
        "window": window,
        "zero_pair_sum": zero_pair_sum,
        "constant_log_2pi": constant_log_2pi,
        "trivial_zero_correction": trivial_zero_correction,
        "estimate": estimate,
        "zero_term_rows": terms,
    }


def zero_window_probe(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 6,
    zero_counts: list[int] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
    include_zero_terms: bool = False,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_zero_counts = _selected_zero_counts(zero_counts)
    selected_windows = _selected_windows(windows)
    rows: list[dict[str, Any]] = []
    zero_term_rows: list[dict[str, Any]] = []

    for x in sample_points:
        prime_pi = int(sp.primepi(x))
        theta_x = chebyshev_theta(x)
        psi_x = chebyshev_psi(x)
        sqrt_x = mp.sqrt(x)
        scale = sqrt_x * mp.log(x)
        for zero_pair_count in selected_zero_counts:
            for window in selected_windows:
                estimate_record = zero_window_estimate(x, zero_pair_count, window, dps=dps)
                estimate = mp.mpf(estimate_record["estimate"])
                residual = estimate - psi_x
                row = {
                    "x": x,
                    "zero_pair_count": zero_pair_count,
                    "window": window,
                    "prime_pi": prime_pi,
                    "theta_x": mp_str(theta_x),
                    "psi_x": mp_str(psi_x),
                    "windowed_explicit_formula_estimate": mp_str(estimate),
                    "estimate_minus_psi": mp_str(residual),
                    "residual_abs": mp_str(abs(residual)),
                    "residual_over_sqrt_x": mp_str(residual / sqrt_x if sqrt_x else 0),
                    "residual_over_sqrt_x_log_x": mp_str(residual / scale if scale else 0),
                    "windowed_zero_pair_sum": mp_str(estimate_record["zero_pair_sum"]),
                    "constant_log_2pi": mp_str(estimate_record["constant_log_2pi"]),
                    "trivial_zero_correction": mp_str(estimate_record["trivial_zero_correction"]),
                }
                rows.append(row)
                if include_zero_terms:
                    for term in estimate_record["zero_term_rows"]:
                        zero_term_rows.append({**term, "zero_pair_count": zero_pair_count})

    return {
        "metadata": metadata(
            "zero_window_probe",
            dps,
            "finite_zero_window_probe_not_zero_certification",
        ),
        "parameters": {
            "points": sample_points,
            "zero_counts": selected_zero_counts,
            "windows": selected_windows,
            "include_zero_terms": include_zero_terms,
            "formula": "psi(x) ~= x - windowed_sum_rho x^rho/rho - log(2*pi) - 1/2*log(1 - x^-2)",
            "window_definitions": {
                "sharp": "weight(k, N) = 1",
                "fejer": "weight(k, N) = 1 - k/(N + 1)",
                "lanczos": "weight(k, N) = sin(pi*k/(N + 1))/(pi*k/(N + 1))",
                "hann": "weight(k, N) = 0.5*(1 + cos(pi*k/(N + 1)))",
            },
        },
        "summary": {
            "max_sample": max(sample_points),
            "max_zero_pair_count": max(selected_zero_counts),
            "windows": selected_windows,
            "row_count": len(rows),
        },
        "rows": rows,
        "zero_term_rows": zero_term_rows,
    }


def zero_window_stability_atlas(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 8,
    zero_counts: list[int] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_zero_counts = _selected_zero_counts(zero_counts or [10, 20, 40, 80, 120])
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    max_zero_count = max(selected_zero_counts)
    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for x in sample_points:
        prime_pi = int(sp.primepi(x))
        theta_x = chebyshev_theta(x)
        psi_x = chebyshev_psi(x)
        sqrt_x = mp.sqrt(x)
        scale = sqrt_x * mp.log(x)
        constant_log_2pi = mp.log(2 * mp.pi)
        trivial_zero_correction = mp.mpf("0.5") * mp.log(1 - mp.mpf(x) ** -2)
        zero_terms = _zero_pair_terms(int(x), max_zero_count)

        for zero_pair_count in selected_zero_counts:
            for window in selected_windows:
                zero_pair_sum = _windowed_zero_pair_sum_from_terms(zero_terms, zero_pair_count, window)
                estimate = mp.mpf(x) - zero_pair_sum - constant_log_2pi - trivial_zero_correction
                residual = estimate - psi_x
                residual_abs = abs(residual)
                record = {
                    "x": x,
                    "zero_pair_count": zero_pair_count,
                    "window": window,
                    "residual": residual,
                    "residual_abs": residual_abs,
                    "estimate": estimate,
                    "zero_pair_sum": zero_pair_sum,
                }
                records.append(record)
                rows.append(
                    {
                        "x": x,
                        "zero_pair_count": zero_pair_count,
                        "window": window,
                        "prime_pi": prime_pi,
                        "theta_x": mp_str(theta_x),
                        "theta_minus_x": mp_str(theta_x - x),
                        "psi_x": mp_str(psi_x),
                        "psi_minus_x": mp_str(psi_x - x),
                        "windowed_explicit_formula_estimate": mp_str(estimate),
                        "estimate_minus_psi": mp_str(residual),
                        "residual_abs": mp_str(residual_abs),
                        "residual_over_sqrt_x": mp_str(residual / sqrt_x if sqrt_x else 0),
                        "residual_over_sqrt_x_log_x": mp_str(residual / scale if scale else 0),
                        "windowed_zero_pair_sum": mp_str(zero_pair_sum),
                        "constant_log_2pi": mp_str(constant_log_2pi),
                        "trivial_zero_correction": mp_str(trivial_zero_correction),
                    }
                )

    best_window_rows: list[dict[str, Any]] = []
    sample_summary_rows: list[dict[str, Any]] = []
    cutoff_transition_rows: list[dict[str, Any]] = []

    for x in sample_points:
        best_sequence: list[str] = []
        x_records = [record for record in records if record["x"] == x]
        best_overall = min(x_records, key=lambda record: record["residual_abs"])
        max_cutoff_records = [record for record in x_records if record["zero_pair_count"] == max_zero_count]
        best_at_max_cutoff = min(max_cutoff_records, key=lambda record: record["residual_abs"])

        for zero_pair_count in selected_zero_counts:
            candidates = [record for record in x_records if record["zero_pair_count"] == zero_pair_count]
            best = min(candidates, key=lambda record: record["residual_abs"])
            best_sequence.append(str(best["window"]))
            best_window_rows.append(
                {
                    "x": x,
                    "zero_pair_count": zero_pair_count,
                    "best_window": best["window"],
                    "best_residual_abs": mp_str(best["residual_abs"]),
                    "best_estimate_minus_psi": mp_str(best["residual"]),
                }
            )

        switch_count = sum(1 for left, right in zip(best_sequence, best_sequence[1:]) if left != right)
        sample_summary_rows.append(
            {
                "x": x,
                "best_overall_zero_pair_count": best_overall["zero_pair_count"],
                "best_overall_window": best_overall["window"],
                "best_overall_residual_abs": mp_str(best_overall["residual_abs"]),
                "best_at_max_zero_count_window": best_at_max_cutoff["window"],
                "best_at_max_zero_count_residual_abs": mp_str(best_at_max_cutoff["residual_abs"]),
                "best_window_sequence_by_cutoff": ",".join(best_sequence),
                "best_window_switch_count": switch_count,
            }
        )

        for window in selected_windows:
            previous: dict[str, Any] | None = None
            ordered = [
                record
                for record in sorted(x_records, key=lambda record: record["zero_pair_count"])
                if record["window"] == window
            ]
            for current in ordered:
                if previous is not None:
                    delta = current["residual_abs"] - previous["residual_abs"]
                    if delta < 0:
                        direction = "improved"
                    elif delta > 0:
                        direction = "worsened"
                    else:
                        direction = "unchanged"
                    cutoff_transition_rows.append(
                        {
                            "x": x,
                            "window": window,
                            "previous_zero_pair_count": previous["zero_pair_count"],
                            "current_zero_pair_count": current["zero_pair_count"],
                            "previous_residual_abs": mp_str(previous["residual_abs"]),
                            "current_residual_abs": mp_str(current["residual_abs"]),
                            "residual_abs_delta": mp_str(delta),
                            "transition_direction": direction,
                        }
                    )
                previous = current

    window_summary_rows: list[dict[str, Any]] = []
    win_counts = {window: 0 for window in selected_windows}
    for row in best_window_rows:
        win_counts[str(row["best_window"])] += 1
    for window in selected_windows:
        window_records = [record for record in records if record["window"] == window]
        residuals = [record["residual_abs"] for record in window_records]
        average_residual = mp.fsum(residuals) / len(residuals)
        window_summary_rows.append(
            {
                "window": window,
                "best_window_win_count": win_counts[window],
                "average_residual_abs": mp_str(average_residual),
                "min_residual_abs": mp_str(min(residuals)),
                "max_residual_abs": mp_str(max(residuals)),
            }
        )

    return {
        "metadata": metadata(
            "zero_window_stability_atlas",
            dps,
            "finite_explicit_residual_stability_atlas_not_zero_certification",
        ),
        "parameters": {
            "points": sample_points,
            "zero_counts": selected_zero_counts,
            "windows": selected_windows,
            "formula": "psi(x) ~= x - windowed_sum_rho x^rho/rho - log(2*pi) - 1/2*log(1 - x^-2)",
            "window_definitions": {
                "sharp": "weight(k, N) = 1",
                "fejer": "weight(k, N) = 1 - k/(N + 1)",
                "lanczos": "weight(k, N) = sin(pi*k/(N + 1))/(pi*k/(N + 1))",
                "hann": "weight(k, N) = 0.5*(1 + cos(pi*k/(N + 1)))",
            },
        },
        "summary": {
            "max_sample": max(sample_points),
            "sample_count": len(sample_points),
            "max_zero_pair_count": max_zero_count,
            "zero_count_count": len(selected_zero_counts),
            "windows": selected_windows,
            "row_count": len(rows),
            "best_window_row_count": len(best_window_rows),
            "window_summary_row_count": len(window_summary_rows),
            "cutoff_transition_row_count": len(cutoff_transition_rows),
            "best_window_win_counts": win_counts,
        },
        "rows": rows,
        "best_window_rows": best_window_rows,
        "sample_summary_rows": sample_summary_rows,
        "window_summary_rows": window_summary_rows,
        "cutoff_transition_rows": cutoff_transition_rows,
    }


def zero_height_cutoff_atlas(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 8,
    zero_heights: list[str] | list[float] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_zero_heights = _selected_zero_heights(zero_heights)
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    max_zero_height = max(selected_zero_heights)
    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for x in sample_points:
        prime_pi = int(sp.primepi(x))
        theta_x = chebyshev_theta(x)
        psi_x = chebyshev_psi(x)
        sqrt_x = mp.sqrt(x)
        log_x = mp.log(x)
        scale = sqrt_x * log_x
        constant_log_2pi = mp.log(2 * mp.pi)
        trivial_zero_correction = mp.mpf("0.5") * mp.log(1 - mp.mpf(x) ** -2)
        zero_terms = _zero_pair_terms_until_height(int(x), max_zero_height)

        for zero_height in selected_zero_heights:
            for window in selected_windows:
                zero_pair_sum, zero_pair_count, max_height_used = _height_windowed_zero_pair_sum_from_terms(
                    zero_terms,
                    zero_height,
                    window,
                )
                estimate = mp.mpf(x) - zero_pair_sum - constant_log_2pi - trivial_zero_correction
                residual = estimate - psi_x
                residual_abs = abs(residual)
                record = {
                    "x": x,
                    "zero_height_cutoff": zero_height,
                    "window": window,
                    "zero_pair_count": zero_pair_count,
                    "residual": residual,
                    "residual_abs": residual_abs,
                    "estimate": estimate,
                    "zero_pair_sum": zero_pair_sum,
                }
                records.append(record)
                rows.append(
                    {
                        "x": x,
                        "zero_height_cutoff": mp_str(zero_height),
                        "zero_height_over_log_x": mp_str(zero_height / log_x if log_x else 0),
                        "zero_height_over_sqrt_x": mp_str(zero_height / sqrt_x if sqrt_x else 0),
                        "zero_pair_count": zero_pair_count,
                        "max_zero_height_used": max_height_used,
                        "window": window,
                        "prime_pi": prime_pi,
                        "theta_x": mp_str(theta_x),
                        "theta_minus_x": mp_str(theta_x - x),
                        "psi_x": mp_str(psi_x),
                        "psi_minus_x": mp_str(psi_x - x),
                        "windowed_explicit_formula_estimate": mp_str(estimate),
                        "estimate_minus_psi": mp_str(residual),
                        "residual_abs": mp_str(residual_abs),
                        "residual_over_sqrt_x": mp_str(residual / sqrt_x if sqrt_x else 0),
                        "residual_over_sqrt_x_log_x": mp_str(residual / scale if scale else 0),
                        "height_windowed_zero_pair_sum": mp_str(zero_pair_sum),
                        "constant_log_2pi": mp_str(constant_log_2pi),
                        "trivial_zero_correction": mp_str(trivial_zero_correction),
                    }
                )

    best_window_rows: list[dict[str, Any]] = []
    sample_summary_rows: list[dict[str, Any]] = []
    height_transition_rows: list[dict[str, Any]] = []

    for x in sample_points:
        best_sequence: list[str] = []
        x_records = [record for record in records if record["x"] == x]
        best_overall = min(x_records, key=lambda record: record["residual_abs"])
        max_height_records = [record for record in x_records if record["zero_height_cutoff"] == max_zero_height]
        best_at_max_height = min(max_height_records, key=lambda record: record["residual_abs"])

        for zero_height in selected_zero_heights:
            candidates = [record for record in x_records if record["zero_height_cutoff"] == zero_height]
            best = min(candidates, key=lambda record: record["residual_abs"])
            best_sequence.append(str(best["window"]))
            best_window_rows.append(
                {
                    "x": x,
                    "zero_height_cutoff": mp_str(zero_height),
                    "zero_pair_count": best["zero_pair_count"],
                    "best_window": best["window"],
                    "best_residual_abs": mp_str(best["residual_abs"]),
                    "best_estimate_minus_psi": mp_str(best["residual"]),
                }
            )

        switch_count = sum(1 for left, right in zip(best_sequence, best_sequence[1:]) if left != right)
        sample_summary_rows.append(
            {
                "x": x,
                "best_overall_zero_height_cutoff": mp_str(best_overall["zero_height_cutoff"]),
                "best_overall_zero_pair_count": best_overall["zero_pair_count"],
                "best_overall_window": best_overall["window"],
                "best_overall_residual_abs": mp_str(best_overall["residual_abs"]),
                "best_at_max_zero_height_window": best_at_max_height["window"],
                "best_at_max_zero_height_residual_abs": mp_str(best_at_max_height["residual_abs"]),
                "best_window_sequence_by_height": ",".join(best_sequence),
                "best_window_switch_count": switch_count,
            }
        )

        for window in selected_windows:
            previous: dict[str, Any] | None = None
            ordered = [
                record
                for record in sorted(x_records, key=lambda record: record["zero_height_cutoff"])
                if record["window"] == window
            ]
            for current in ordered:
                if previous is not None:
                    delta = current["residual_abs"] - previous["residual_abs"]
                    if delta < 0:
                        direction = "improved"
                    elif delta > 0:
                        direction = "worsened"
                    else:
                        direction = "unchanged"
                    height_transition_rows.append(
                        {
                            "x": x,
                            "window": window,
                            "previous_zero_height_cutoff": mp_str(previous["zero_height_cutoff"]),
                            "current_zero_height_cutoff": mp_str(current["zero_height_cutoff"]),
                            "previous_zero_pair_count": previous["zero_pair_count"],
                            "current_zero_pair_count": current["zero_pair_count"],
                            "previous_residual_abs": mp_str(previous["residual_abs"]),
                            "current_residual_abs": mp_str(current["residual_abs"]),
                            "residual_abs_delta": mp_str(delta),
                            "transition_direction": direction,
                        }
                    )
                previous = current

    window_summary_rows: list[dict[str, Any]] = []
    win_counts = {window: 0 for window in selected_windows}
    for row in best_window_rows:
        win_counts[str(row["best_window"])] += 1
    for window in selected_windows:
        window_records = [record for record in records if record["window"] == window]
        residuals = [record["residual_abs"] for record in window_records]
        average_residual = mp.fsum(residuals) / len(residuals)
        window_summary_rows.append(
            {
                "window": window,
                "best_window_win_count": win_counts[window],
                "average_residual_abs": mp_str(average_residual),
                "min_residual_abs": mp_str(min(residuals)),
                "max_residual_abs": mp_str(max(residuals)),
            }
        )

    return {
        "metadata": metadata(
            "zero_height_cutoff_atlas",
            dps,
            "finite_zero_height_cutoff_atlas_not_zero_certification",
        ),
        "parameters": {
            "points": sample_points,
            "zero_heights": [mp_str(value) for value in selected_zero_heights],
            "windows": selected_windows,
            "formula": "psi(x) ~= x - sum_{0 < gamma <= T} w(gamma,T)*x^rho/rho - log(2*pi) - 1/2*log(1 - x^-2)",
            "window_definitions": {
                "sharp": "weight(gamma, T) = 1",
                "fejer": "weight(gamma, T) = 1 - gamma/T",
                "lanczos": "weight(gamma, T) = sin(pi*gamma/T)/(pi*gamma/T)",
                "hann": "weight(gamma, T) = 0.5*(1 + cos(pi*gamma/T))",
            },
        },
        "summary": {
            "max_sample": max(sample_points),
            "sample_count": len(sample_points),
            "max_zero_height": mp_str(max_zero_height),
            "zero_height_count": len(selected_zero_heights),
            "windows": selected_windows,
            "row_count": len(rows),
            "best_window_row_count": len(best_window_rows),
            "window_summary_row_count": len(window_summary_rows),
            "height_transition_row_count": len(height_transition_rows),
            "best_window_win_counts": win_counts,
        },
        "rows": rows,
        "best_window_rows": best_window_rows,
        "sample_summary_rows": sample_summary_rows,
        "window_summary_rows": window_summary_rows,
        "height_transition_rows": height_transition_rows,
    }


def scale_tied_zero_height_atlas(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 8,
    multipliers: list[str] | list[float] | None = None,
    scale_law: str = "log",
    windows: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_multipliers = _selected_scale_multipliers(multipliers)
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    scale_law = scale_law.lower()
    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    max_zero_height = max(scale_tied_zero_height(x, multiplier, scale_law) for x in sample_points for multiplier in selected_multipliers)

    for x in sample_points:
        prime_pi = int(sp.primepi(x))
        theta_x = chebyshev_theta(x)
        psi_x = chebyshev_psi(x)
        sqrt_x = mp.sqrt(x)
        log_x = mp.log(x)
        residual_scale = sqrt_x * log_x
        constant_log_2pi = mp.log(2 * mp.pi)
        trivial_zero_correction = mp.mpf("0.5") * mp.log(1 - mp.mpf(x) ** -2)
        zero_terms = _zero_pair_terms_until_height(int(x), max_zero_height)

        for multiplier in selected_multipliers:
            zero_height = scale_tied_zero_height(x, multiplier, scale_law)
            for window in selected_windows:
                zero_pair_sum, zero_pair_count, max_height_used = _height_windowed_zero_pair_sum_from_terms(
                    zero_terms,
                    zero_height,
                    window,
                )
                estimate = mp.mpf(x) - zero_pair_sum - constant_log_2pi - trivial_zero_correction
                residual = estimate - psi_x
                residual_abs = abs(residual)
                record = {
                    "x": x,
                    "scale_multiplier": multiplier,
                    "scale_law": scale_law,
                    "zero_height_cutoff": zero_height,
                    "window": window,
                    "zero_pair_count": zero_pair_count,
                    "residual": residual,
                    "residual_abs": residual_abs,
                    "estimate": estimate,
                    "zero_pair_sum": zero_pair_sum,
                }
                records.append(record)
                rows.append(
                    {
                        "x": x,
                        "scale_law": scale_law,
                        "scale_multiplier": mp_str(multiplier),
                        "zero_height_cutoff": mp_str(zero_height),
                        "zero_height_over_log_x": mp_str(zero_height / log_x if log_x else 0),
                        "zero_height_over_sqrt_x": mp_str(zero_height / sqrt_x if sqrt_x else 0),
                        "zero_pair_count": zero_pair_count,
                        "max_zero_height_used": max_height_used,
                        "window": window,
                        "prime_pi": prime_pi,
                        "theta_x": mp_str(theta_x),
                        "theta_minus_x": mp_str(theta_x - x),
                        "psi_x": mp_str(psi_x),
                        "psi_minus_x": mp_str(psi_x - x),
                        "windowed_explicit_formula_estimate": mp_str(estimate),
                        "estimate_minus_psi": mp_str(residual),
                        "residual_abs": mp_str(residual_abs),
                        "residual_over_sqrt_x": mp_str(residual / sqrt_x if sqrt_x else 0),
                        "residual_over_sqrt_x_log_x": mp_str(residual / residual_scale if residual_scale else 0),
                        "height_windowed_zero_pair_sum": mp_str(zero_pair_sum),
                        "constant_log_2pi": mp_str(constant_log_2pi),
                        "trivial_zero_correction": mp_str(trivial_zero_correction),
                    }
                )

    best_window_rows: list[dict[str, Any]] = []
    sample_summary_rows: list[dict[str, Any]] = []
    multiplier_transition_rows: list[dict[str, Any]] = []

    for x in sample_points:
        best_sequence: list[str] = []
        x_records = [record for record in records if record["x"] == x]
        best_overall = min(x_records, key=lambda record: record["residual_abs"])
        max_multiplier = max(selected_multipliers)
        max_multiplier_records = [record for record in x_records if record["scale_multiplier"] == max_multiplier]
        best_at_max_multiplier = min(max_multiplier_records, key=lambda record: record["residual_abs"])

        for multiplier in selected_multipliers:
            candidates = [record for record in x_records if record["scale_multiplier"] == multiplier]
            best = min(candidates, key=lambda record: record["residual_abs"])
            best_sequence.append(str(best["window"]))
            best_window_rows.append(
                {
                    "x": x,
                    "scale_law": scale_law,
                    "scale_multiplier": mp_str(multiplier),
                    "zero_height_cutoff": mp_str(best["zero_height_cutoff"]),
                    "zero_pair_count": best["zero_pair_count"],
                    "best_window": best["window"],
                    "best_residual_abs": mp_str(best["residual_abs"]),
                    "best_estimate_minus_psi": mp_str(best["residual"]),
                }
            )

        switch_count = sum(1 for left, right in zip(best_sequence, best_sequence[1:]) if left != right)
        sample_summary_rows.append(
            {
                "x": x,
                "best_overall_scale_multiplier": mp_str(best_overall["scale_multiplier"]),
                "best_overall_zero_height_cutoff": mp_str(best_overall["zero_height_cutoff"]),
                "best_overall_zero_pair_count": best_overall["zero_pair_count"],
                "best_overall_window": best_overall["window"],
                "best_overall_residual_abs": mp_str(best_overall["residual_abs"]),
                "best_at_max_multiplier_window": best_at_max_multiplier["window"],
                "best_at_max_multiplier_residual_abs": mp_str(best_at_max_multiplier["residual_abs"]),
                "best_window_sequence_by_multiplier": ",".join(best_sequence),
                "best_window_switch_count": switch_count,
            }
        )

        for window in selected_windows:
            previous: dict[str, Any] | None = None
            ordered = [
                record
                for record in sorted(x_records, key=lambda record: record["scale_multiplier"])
                if record["window"] == window
            ]
            for current in ordered:
                if previous is not None:
                    delta = current["residual_abs"] - previous["residual_abs"]
                    if delta < 0:
                        direction = "improved"
                    elif delta > 0:
                        direction = "worsened"
                    else:
                        direction = "unchanged"
                    multiplier_transition_rows.append(
                        {
                            "x": x,
                            "scale_law": scale_law,
                            "window": window,
                            "previous_scale_multiplier": mp_str(previous["scale_multiplier"]),
                            "current_scale_multiplier": mp_str(current["scale_multiplier"]),
                            "previous_zero_height_cutoff": mp_str(previous["zero_height_cutoff"]),
                            "current_zero_height_cutoff": mp_str(current["zero_height_cutoff"]),
                            "previous_zero_pair_count": previous["zero_pair_count"],
                            "current_zero_pair_count": current["zero_pair_count"],
                            "previous_residual_abs": mp_str(previous["residual_abs"]),
                            "current_residual_abs": mp_str(current["residual_abs"]),
                            "residual_abs_delta": mp_str(delta),
                            "transition_direction": direction,
                        }
                    )
                previous = current

    window_summary_rows: list[dict[str, Any]] = []
    win_counts = {window: 0 for window in selected_windows}
    for row in best_window_rows:
        win_counts[str(row["best_window"])] += 1
    for window in selected_windows:
        window_records = [record for record in records if record["window"] == window]
        residuals = [record["residual_abs"] for record in window_records]
        average_residual = mp.fsum(residuals) / len(residuals)
        window_summary_rows.append(
            {
                "window": window,
                "best_window_win_count": win_counts[window],
                "average_residual_abs": mp_str(average_residual),
                "min_residual_abs": mp_str(min(residuals)),
                "max_residual_abs": mp_str(max(residuals)),
            }
        )

    return {
        "metadata": metadata(
            "scale_tied_zero_height_atlas",
            dps,
            "finite_scale_tied_zero_height_atlas_not_zero_certification",
        ),
        "parameters": {
            "points": sample_points,
            "scale_law": scale_law,
            "scale_multipliers": [mp_str(value) for value in selected_multipliers],
            "windows": selected_windows,
            "formula": "psi(x) ~= x - sum_{0 < gamma <= T(x)} w(gamma,T)*x^rho/rho - log(2*pi) - 1/2*log(1 - x^-2)",
            "window_definitions": {
                "sharp": "weight(gamma, T) = 1",
                "fejer": "weight(gamma, T) = 1 - gamma/T",
                "lanczos": "weight(gamma, T) = sin(pi*gamma/T)/(pi*gamma/T)",
                "hann": "weight(gamma, T) = 0.5*(1 + cos(pi*gamma/T))",
            },
        },
        "summary": {
            "max_sample": max(sample_points),
            "sample_count": len(sample_points),
            "scale_law": scale_law,
            "scale_multiplier_count": len(selected_multipliers),
            "max_zero_height": mp_str(max_zero_height),
            "windows": selected_windows,
            "row_count": len(rows),
            "best_window_row_count": len(best_window_rows),
            "window_summary_row_count": len(window_summary_rows),
            "multiplier_transition_row_count": len(multiplier_transition_rows),
            "best_window_win_counts": win_counts,
        },
        "rows": rows,
        "best_window_rows": best_window_rows,
        "sample_summary_rows": sample_summary_rows,
        "window_summary_rows": window_summary_rows,
        "multiplier_transition_rows": multiplier_transition_rows,
    }


def scale_law_comparison_atlas(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 8,
    scale_laws: list[str] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_scale_laws = _selected_scale_laws(scale_laws)
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    rows: list[dict[str, Any]] = []
    best_window_rows: list[dict[str, Any]] = []
    multiplier_transition_rows: list[dict[str, Any]] = []
    law_summary_rows: list[dict[str, Any]] = []
    window_summary_rows: list[dict[str, Any]] = []

    for law in selected_scale_laws:
        payload = scale_tied_zero_height_atlas(
            points=sample_points,
            multipliers=list(DEFAULT_SCALE_LAW_MULTIPLIERS[law]),
            scale_law=law,
            windows=selected_windows,
            dps=dps,
        )
        rows.extend(payload["rows"])
        best_window_rows.extend(payload["best_window_rows"])
        multiplier_transition_rows.extend(payload["multiplier_transition_rows"])
        for row in payload["window_summary_rows"]:
            window_summary_rows.append({**row, "scale_law": law})

    sample_best_law_rows: list[dict[str, Any]] = []
    law_best_counts = {law: 0 for law in selected_scale_laws}
    for x in sample_points:
        x_rows = [row for row in rows if row["x"] == x]
        best = min(x_rows, key=lambda row: mp.mpf(row["residual_abs"]))
        law_best_counts[str(best["scale_law"])] += 1
        sample_best_law_rows.append(
            {
                "x": x,
                "best_scale_law": best["scale_law"],
                "best_scale_multiplier": best["scale_multiplier"],
                "best_zero_height_cutoff": best["zero_height_cutoff"],
                "best_zero_pair_count": best["zero_pair_count"],
                "best_window": best["window"],
                "best_residual_abs": best["residual_abs"],
                "best_estimate_minus_psi": best["estimate_minus_psi"],
            }
        )

    for law in selected_scale_laws:
        law_rows = [row for row in rows if row["scale_law"] == law]
        residuals = [mp.mpf(row["residual_abs"]) for row in law_rows]
        average_residual = mp.fsum(residuals) / len(residuals)
        min_row = min(law_rows, key=lambda row: mp.mpf(row["residual_abs"]))
        max_row = max(law_rows, key=lambda row: mp.mpf(row["residual_abs"]))
        law_summary_rows.append(
            {
                "scale_law": law,
                "sample_best_law_count": law_best_counts[law],
                "row_count": len(law_rows),
                "average_residual_abs": mp_str(average_residual),
                "min_residual_abs": min_row["residual_abs"],
                "min_residual_x": min_row["x"],
                "min_residual_multiplier": min_row["scale_multiplier"],
                "min_residual_window": min_row["window"],
                "max_residual_abs": max_row["residual_abs"],
            }
        )

    return {
        "metadata": metadata(
            "scale_law_comparison_atlas",
            dps,
            "finite_scale_law_comparison_not_zero_certification",
        ),
        "parameters": {
            "points": sample_points,
            "scale_laws": selected_scale_laws,
            "default_scale_law_multipliers": DEFAULT_SCALE_LAW_MULTIPLIERS,
            "windows": selected_windows,
            "formula": "psi(x) ~= x - sum_{0 < gamma <= T_law(x)} w(gamma,T)*x^rho/rho - log(2*pi) - 1/2*log(1 - x^-2)",
            "window_definitions": {
                "sharp": "weight(gamma, T) = 1",
                "fejer": "weight(gamma, T) = 1 - gamma/T",
                "lanczos": "weight(gamma, T) = sin(pi*gamma/T)/(pi*gamma/T)",
                "hann": "weight(gamma, T) = 0.5*(1 + cos(pi*gamma/T))",
            },
        },
        "summary": {
            "max_sample": max(sample_points),
            "sample_count": len(sample_points),
            "scale_laws": selected_scale_laws,
            "scale_law_count": len(selected_scale_laws),
            "windows": selected_windows,
            "row_count": len(rows),
            "best_window_row_count": len(best_window_rows),
            "law_summary_row_count": len(law_summary_rows),
            "sample_best_law_row_count": len(sample_best_law_rows),
            "multiplier_transition_row_count": len(multiplier_transition_rows),
            "sample_best_law_counts": law_best_counts,
        },
        "rows": rows,
        "best_window_rows": best_window_rows,
        "sample_best_law_rows": sample_best_law_rows,
        "law_summary_rows": law_summary_rows,
        "window_summary_rows": window_summary_rows,
        "multiplier_transition_rows": multiplier_transition_rows,
    }


def _zero_values_until_height(zero_height: mp.mpf) -> list[tuple[mp.mpf, mp.mpc]]:
    zero_values: list[tuple[mp.mpf, mp.mpc]] = []
    zero_index = 1
    while True:
        rho = mp.zetazero(zero_index)
        gamma = abs(mp.im(rho))
        if gamma > zero_height:
            break
        zero_values.append((gamma, rho))
        zero_index += 1
    return zero_values


def _height_windowed_zero_pair_sum_from_zero_values(
    x: int,
    zero_values: list[tuple[mp.mpf, mp.mpc]],
    cutoff_height: mp.mpf,
    window: str,
) -> tuple[mp.mpf, int, str | None]:
    xx = mp.mpf(x)
    total = mp.mpf("0")
    count = 0
    max_height_used: str | None = None
    for gamma, rho in zero_values:
        if gamma > cutoff_height:
            break
        conjugate = mp.conj(rho)
        pair_term = mp.power(xx, rho) / rho + mp.power(xx, conjugate) / conjugate
        total += zero_height_window_weight(gamma, cutoff_height, window) * mp.re(pair_term)
        count += 1
        max_height_used = mp_str(gamma)
    return total, count, max_height_used


def _von_mangoldt_values(max_n: int) -> list[mp.mpf]:
    values = [mp.mpf("0") for _ in range(max_n + 1)]
    for prime in sp.primerange(2, max_n + 1):
        p = int(prime)
        log_prime = mp.log(p)
        power = p
        while power <= max_n:
            values[power] = log_prime
            power *= p
    return values


def _relative_abs(residual: mp.mpc | mp.mpf, target: mp.mpc | mp.mpf) -> mp.mpf:
    return abs(residual) / max(abs(target), mp.mpf("1"))


def _safe_ratio(numerator: mp.mpf, denominator: mp.mpf) -> str | None:
    if denominator == 0:
        return None
    return mp_str(numerator / denominator)


def _sign_label(value: mp.mpf) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def _sign_relation(left: mp.mpf, right: mp.mpf) -> str:
    if left == 0 or right == 0:
        return "zero_involved"
    if (left > 0 and right > 0) or (left < 0 and right < 0):
        return "same_sign"
    return "opposite_sign"


def _explicit_psi_estimates_up_to(
    max_n: int,
    scale_law: str,
    multiplier: mp.mpf,
    window: str,
    zero_values: list[tuple[mp.mpf, mp.mpc]],
) -> tuple[list[mp.mpf], list[int], list[str | None], list[mp.mpf]]:
    estimates = [mp.mpf("0") for _ in range(max_n + 1)]
    zero_pair_counts = [0 for _ in range(max_n + 1)]
    max_heights_used: list[str | None] = [None for _ in range(max_n + 1)]
    zero_heights = [mp.mpf("0") for _ in range(max_n + 1)]
    constant_log_2pi = mp.log(2 * mp.pi)
    for n in range(2, max_n + 1):
        zero_height = scale_tied_zero_height(n, multiplier, scale_law)
        zero_pair_sum, zero_pair_count, max_height_used = _height_windowed_zero_pair_sum_from_zero_values(
            n,
            zero_values,
            zero_height,
            window,
        )
        trivial_zero_correction = mp.mpf("0.5") * mp.log(1 - mp.mpf(n) ** -2)
        estimates[n] = mp.mpf(n) - zero_pair_sum - constant_log_2pi - trivial_zero_correction
        zero_pair_counts[n] = zero_pair_count
        max_heights_used[n] = max_height_used
        zero_heights[n] = zero_height
    return estimates, zero_pair_counts, max_heights_used, zero_heights


def explicit_residual_movement_decomposition(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 8,
    scale_law: str = "log",
    multipliers: list[str] | list[float] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_multipliers = _selected_scale_multipliers(multipliers)
    selected_windows = _selected_windows(windows or ["sharp"])
    scale_law = scale_law.lower()
    if scale_law not in SUPPORTED_SCALE_LAWS:
        raise ValueError(f"unsupported scale law: {scale_law}")

    max_zero_height = max(
        scale_tied_zero_height(x, multiplier, scale_law)
        for x in sample_points
        for multiplier in selected_multipliers
    )
    zero_values = _zero_values_until_height(max_zero_height)
    point_rows: list[dict[str, Any]] = []
    movement_rows: list[dict[str, Any]] = []
    records_by_configuration: dict[tuple[str, str], list[dict[str, Any]]] = {}

    exact_rows: dict[int, dict[str, mp.mpf]] = {}
    for x in sample_points:
        theta_x = chebyshev_theta(x)
        psi_x = chebyshev_psi(x)
        exact_rows[x] = {
            "theta_x": theta_x,
            "psi_x": psi_x,
            "higher_prime_power_sum": psi_x - theta_x,
            "theta_minus_x": theta_x - x,
            "psi_minus_x": psi_x - x,
        }

    for multiplier in selected_multipliers:
        for window in selected_windows:
            config_key = (mp_str(multiplier), window)
            config_records: list[dict[str, Any]] = []
            records_by_configuration[config_key] = config_records

            for x in sample_points:
                xx = mp.mpf(x)
                exact = exact_rows[x]
                log_x = mp.log(xx)
                sqrt_x = mp.sqrt(xx)
                residual_scale = sqrt_x * log_x
                zero_height = scale_tied_zero_height(x, multiplier, scale_law)
                zero_pair_sum, zero_pair_count, max_height_used = _height_windowed_zero_pair_sum_from_zero_values(
                    x,
                    zero_values,
                    zero_height,
                    window,
                )
                constant_log_2pi = mp.log(2 * mp.pi)
                trivial_zero_correction = mp.mpf("0.5") * mp.log(1 - xx ** -2)
                estimate = xx - zero_pair_sum - constant_log_2pi - trivial_zero_correction
                residual = estimate - exact["psi_x"]
                record = {
                    "x": x,
                    "scale_multiplier": multiplier,
                    "window": window,
                    "zero_height_cutoff": zero_height,
                    "zero_pair_count": zero_pair_count,
                    "max_zero_height_used": max_height_used,
                    "explicit_psi_estimate": estimate,
                    "explicit_residual": residual,
                }
                config_records.append(record)
                point_rows.append(
                    {
                        "x": x,
                        "scale_law": scale_law,
                        "scale_multiplier": mp_str(multiplier),
                        "zero_height_cutoff": mp_str(zero_height),
                        "zero_height_over_log_x": mp_str(zero_height / log_x if log_x else 0),
                        "zero_pair_count": zero_pair_count,
                        "max_zero_height_used": max_height_used,
                        "window": window,
                        "theta_x": mp_str(exact["theta_x"]),
                        "theta_minus_x": mp_str(exact["theta_minus_x"]),
                        "psi_x": mp_str(exact["psi_x"]),
                        "psi_minus_x": mp_str(exact["psi_minus_x"]),
                        "higher_prime_power_sum": mp_str(exact["higher_prime_power_sum"]),
                        "higher_prime_power_share_of_psi": _safe_ratio(
                            exact["higher_prime_power_sum"],
                            exact["psi_x"],
                        ),
                        "explicit_psi_estimate": mp_str(estimate),
                        "explicit_residual": mp_str(residual),
                        "explicit_residual_abs": mp_str(abs(residual)),
                        "explicit_residual_over_sqrt_x_log_x": mp_str(
                            residual / residual_scale if residual_scale else 0
                        ),
                    }
                )

            for lower_record, upper_record in zip(config_records, config_records[1:]):
                lower = int(lower_record["x"])
                upper = int(upper_record["x"])
                lower_exact = exact_rows[lower]
                upper_exact = exact_rows[upper]
                interval_length = mp.mpf(upper - lower)
                theta_increment = upper_exact["theta_x"] - lower_exact["theta_x"]
                psi_increment = upper_exact["psi_x"] - lower_exact["psi_x"]
                higher_movement = upper_exact["higher_prime_power_sum"] - lower_exact["higher_prime_power_sum"]
                theta_error_movement = upper_exact["theta_minus_x"] - lower_exact["theta_minus_x"]
                psi_error_movement = upper_exact["psi_minus_x"] - lower_exact["psi_minus_x"]
                estimate_movement = upper_record["explicit_psi_estimate"] - lower_record["explicit_psi_estimate"]
                residual_movement = upper_record["explicit_residual"] - lower_record["explicit_residual"]
                residual_minus_psi_error = residual_movement - psi_error_movement
                residual_minus_theta_error = residual_movement - theta_error_movement
                residual_minus_higher = residual_movement - higher_movement
                if abs(theta_error_movement) > abs(higher_movement):
                    dominant_layer = "theta_error_movement"
                elif abs(theta_error_movement) < abs(higher_movement):
                    dominant_layer = "higher_prime_power_movement"
                else:
                    dominant_layer = "balanced_or_zero"

                movement_row = {
                    "lower_x": lower,
                    "upper_x": upper,
                    "interval_length": mp_str(interval_length),
                    "scale_law": scale_law,
                    "scale_multiplier": mp_str(multiplier),
                    "window": window,
                    "lower_zero_height_cutoff": mp_str(lower_record["zero_height_cutoff"]),
                    "upper_zero_height_cutoff": mp_str(upper_record["zero_height_cutoff"]),
                    "lower_zero_pair_count": lower_record["zero_pair_count"],
                    "upper_zero_pair_count": upper_record["zero_pair_count"],
                    "theta_increment": mp_str(theta_increment),
                    "theta_error_movement": mp_str(theta_error_movement),
                    "higher_prime_power_movement": mp_str(higher_movement),
                    "psi_increment": mp_str(psi_increment),
                    "psi_error_movement": mp_str(psi_error_movement),
                    "explicit_psi_estimate_movement": mp_str(estimate_movement),
                    "explicit_residual_movement": mp_str(residual_movement),
                    "explicit_residual_movement_abs": mp_str(abs(residual_movement)),
                    "residual_minus_psi_error_movement": mp_str(residual_minus_psi_error),
                    "residual_minus_theta_error_movement": mp_str(residual_minus_theta_error),
                    "residual_minus_higher_prime_power_movement": mp_str(residual_minus_higher),
                    "residual_over_psi_error_movement": _safe_ratio(residual_movement, psi_error_movement),
                    "residual_over_theta_error_movement": _safe_ratio(residual_movement, theta_error_movement),
                    "residual_over_higher_prime_power_movement": _safe_ratio(residual_movement, higher_movement),
                    "residual_movement_sign": _sign_label(residual_movement),
                    "theta_error_movement_sign": _sign_label(theta_error_movement),
                    "higher_prime_power_movement_sign": _sign_label(higher_movement),
                    "psi_error_movement_sign": _sign_label(psi_error_movement),
                    "residual_to_psi_error_sign_relation": _sign_relation(residual_movement, psi_error_movement),
                    "residual_to_theta_error_sign_relation": _sign_relation(residual_movement, theta_error_movement),
                    "residual_to_higher_prime_power_sign_relation": _sign_relation(
                        residual_movement,
                        higher_movement,
                    ),
                    "dominant_exact_layer_by_abs_movement": dominant_layer,
                }
                movement_rows.append(movement_row)

    configuration_summary_rows: list[dict[str, Any]] = []
    for multiplier_text, window in records_by_configuration:
        config_movements = [
            row
            for row in movement_rows
            if row["scale_multiplier"] == multiplier_text and row["window"] == window
        ]
        residual_movements = [mp.mpf(row["explicit_residual_movement_abs"]) for row in config_movements]
        residual_minus_psi = [abs(mp.mpf(row["residual_minus_psi_error_movement"])) for row in config_movements]
        same_sign_count = sum(
            1 for row in config_movements if row["residual_to_psi_error_sign_relation"] == "same_sign"
        )
        opposite_sign_count = sum(
            1 for row in config_movements if row["residual_to_psi_error_sign_relation"] == "opposite_sign"
        )
        configuration_summary_rows.append(
            {
                "scale_law": scale_law,
                "scale_multiplier": multiplier_text,
                "window": window,
                "movement_row_count": len(config_movements),
                "average_explicit_residual_movement_abs": mp_str(
                    mp.fsum(residual_movements) / len(residual_movements) if residual_movements else 0
                ),
                "average_abs_residual_minus_psi_error_movement": mp_str(
                    mp.fsum(residual_minus_psi) / len(residual_minus_psi) if residual_minus_psi else 0
                ),
                "residual_psi_error_same_sign_count": same_sign_count,
                "residual_psi_error_opposite_sign_count": opposite_sign_count,
            }
        )

    dominant_layer_counts = {
        "theta_error_movement": 0,
        "higher_prime_power_movement": 0,
        "balanced_or_zero": 0,
    }
    sign_relation_counts = {
        "same_sign": 0,
        "opposite_sign": 0,
        "zero_involved": 0,
    }
    for row in movement_rows:
        dominant_layer_counts[row["dominant_exact_layer_by_abs_movement"]] += 1
        sign_relation_counts[row["residual_to_psi_error_sign_relation"]] += 1

    return {
        "metadata": metadata(
            "explicit_residual_movement_decomposition",
            dps,
            "finite_explicit_residual_movement_decomposition_not_rh_evidence",
        ),
        "parameters": {
            "points": sample_points,
            "scale_law": scale_law,
            "scale_multipliers": [mp_str(value) for value in selected_multipliers],
            "windows": selected_windows,
            "max_zero_height": mp_str(max_zero_height),
            "zero_count_available_to_max_height": len(zero_values),
            "explicit_residual_definition": "R(x)=psi_hat(x)-psi(x)",
            "movement_definition": "Delta R(a,b)=R(b)-R(a) over adjacent sampled intervals",
            "theta_error_movement_definition": "Delta(theta(x)-x)",
            "higher_prime_power_movement_definition": "Delta(psi(x)-theta(x))",
            "psi_error_movement_definition": "Delta(psi(x)-x)",
            "policy_boundary": "reuses existing zero-height/window policies; introduces no new kernel, window, or cutoff law",
        },
        "summary": {
            "max_sample": max(sample_points),
            "sample_count": len(sample_points),
            "scale_multiplier_count": len(selected_multipliers),
            "window_count": len(selected_windows),
            "point_row_count": len(point_rows),
            "movement_row_count": len(movement_rows),
            "configuration_summary_row_count": len(configuration_summary_rows),
            "dominant_exact_layer_counts": dominant_layer_counts,
            "residual_psi_error_sign_relation_counts": sign_relation_counts,
        },
        "rows": movement_rows,
        "point_rows": point_rows,
        "movement_rows": movement_rows,
        "configuration_summary_rows": configuration_summary_rows,
    }


def _finite_difference_projection(values: list[mp.mpf], n_bound: int, s: mp.mpc) -> mp.mpc:
    return mp.fsum((values[n] - values[n - 1]) * mp.power(n, -s) for n in range(2, n_bound + 1))


def _partial_summation_projection(values: list[mp.mpf], n_bound: int, s: mp.mpc) -> mp.mpc:
    total = values[n_bound] * mp.power(n_bound, -s)
    for k in range(2, n_bound):
        total += values[k] * (mp.power(k, -s) - mp.power(k + 1, -s))
    return total


def n_domain_kernel_weight(n: int, n_bound: int, kernel: str) -> mp.mpf:
    if n < 1:
        raise ValueError("n must be positive")
    if n_bound < 1:
        raise ValueError("n_bound must be positive")
    if n > n_bound:
        raise ValueError("n must be less than or equal to n_bound")
    kernel = kernel.lower()
    if kernel == "sharp":
        return mp.mpf("1")
    ratio = mp.mpf(n) / (mp.mpf(n_bound) + 1)
    if kernel == "cesaro":
        return mp.mpf("1") - ratio
    if kernel == "hann":
        return mp.mpf("0.5") * (mp.mpf("1") + mp.cos(mp.pi * ratio))
    raise ValueError(f"unsupported n-domain kernel: {kernel}")


def alpha_cesaro_kernel_weight(n: int, n_bound: int, alpha: mp.mpf | str | float) -> mp.mpf:
    if n < 1:
        raise ValueError("n must be positive")
    if n_bound < 1:
        raise ValueError("n_bound must be positive")
    if n > n_bound:
        raise ValueError("n must be less than or equal to n_bound")
    a = mp.mpf(alpha)
    if a < 0 or a > 1:
        raise ValueError("alpha must be in [0, 1]")
    return mp.mpf("1") - a * (mp.mpf(n) / (mp.mpf(n_bound) + 1))


def _kernel_weighted_projection(values: list[mp.mpf], n_bound: int, s: mp.mpc, kernel: str) -> mp.mpc:
    return mp.fsum(
        n_domain_kernel_weight(n, n_bound, kernel) * (values[n] - values[n - 1]) * mp.power(n, -s)
        for n in range(2, n_bound + 1)
    )


def _kernel_weighted_lambda_projection(lambda_values: list[mp.mpf], n_bound: int, s: mp.mpc, kernel: str) -> mp.mpc:
    return mp.fsum(
        n_domain_kernel_weight(n, n_bound, kernel) * lambda_values[n] * mp.power(n, -s)
        for n in range(2, n_bound + 1)
    )


def _alpha_weighted_projection(values: list[mp.mpf], n_bound: int, s: mp.mpc, alpha: mp.mpf) -> mp.mpc:
    return mp.fsum(
        alpha_cesaro_kernel_weight(n, n_bound, alpha) * (values[n] - values[n - 1]) * mp.power(n, -s)
        for n in range(2, n_bound + 1)
    )


def _alpha_weighted_lambda_projection(lambda_values: list[mp.mpf], n_bound: int, s: mp.mpc, alpha: mp.mpf) -> mp.mpc:
    return mp.fsum(
        alpha_cesaro_kernel_weight(n, n_bound, alpha) * lambda_values[n] * mp.power(n, -s)
        for n in range(2, n_bound + 1)
    )


def lambda_mellin_bridge_atlas(
    n_bounds: list[int] | None = None,
    samples: list[tuple[str | float, str | float]] | None = None,
    scale_law: str = "log",
    multipliers: list[str] | list[float] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    selected_n_bounds = _selected_bridge_n_bounds(n_bounds)
    selected_samples = _selected_bridge_samples(samples)
    selected_multipliers = _selected_scale_multipliers(multipliers or ["16", "32"])
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    scale_law = scale_law.lower()
    if scale_law not in SUPPORTED_SCALE_LAWS:
        raise ValueError(f"unsupported scale law: {scale_law}")

    max_n = max(selected_n_bounds)
    max_zero_height = max(scale_tied_zero_height(max_n, multiplier, scale_law) for multiplier in selected_multipliers)
    zero_values = _zero_values_until_height(max_zero_height)
    lambda_values = _von_mangoldt_values(max_n)
    exact_psi_values = [mp.mpf("0") for _ in range(max_n + 1)]
    running_psi = mp.mpf("0")
    for n in range(2, max_n + 1):
        running_psi += lambda_values[n]
        exact_psi_values[n] = running_psi

    exact_targets = {
        (mp_str(sigma), mp_str(t)): negative_zeta_log_derivative(mp.mpc(sigma, t))
        for sigma, t in selected_samples
    }

    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    increment_rows: list[dict[str, Any]] = []

    for multiplier in selected_multipliers:
        for window in selected_windows:
            estimates, zero_pair_counts, max_heights_used, zero_heights = _explicit_psi_estimates_up_to(
                max_n,
                scale_law,
                multiplier,
                window,
                zero_values,
            )
            increment_residual_prefix = [mp.mpf("0") for _ in range(max_n + 1)]
            explicit_increments = [mp.mpf("0") for _ in range(max_n + 1)]
            running_increment_l1 = mp.mpf("0")
            for n in range(2, max_n + 1):
                explicit_increment = estimates[n] - estimates[n - 1]
                explicit_increments[n] = explicit_increment
                increment_residual = explicit_increment - lambda_values[n]
                running_increment_l1 += abs(increment_residual)
                increment_residual_prefix[n] = running_increment_l1
                if n in selected_n_bounds:
                    increment_rows.append(
                        {
                            "n": n,
                            "scale_law": scale_law,
                            "scale_multiplier": mp_str(multiplier),
                            "window": window,
                            "exact_lambda": mp_str(lambda_values[n]),
                            "explicit_lambda_like_increment": mp_str(explicit_increment),
                            "increment_residual": mp_str(increment_residual),
                            "increment_residual_abs": mp_str(abs(increment_residual)),
                        }
                    )

            for sigma, t in selected_samples:
                s = mp.mpc(sigma, t)
                exact_target = exact_targets[(mp_str(sigma), mp_str(t))]
                for n_bound in selected_n_bounds:
                    exact_finite_sum = mp.fsum(lambda_values[n] * mp.power(n, -s) for n in range(2, n_bound + 1))
                    explicit_projected_sum = mp.fsum(
                        explicit_increments[n] * mp.power(n, -s) for n in range(2, n_bound + 1)
                    )
                    bridge_residual = explicit_projected_sum - exact_finite_sum
                    exact_cutoff_residual = exact_finite_sum - exact_target
                    combined_residual = explicit_projected_sum - exact_target
                    endpoint_psi_residual = estimates[n_bound] - exact_psi_values[n_bound]
                    bridge_residual_abs = abs(bridge_residual)
                    exact_cutoff_residual_abs = abs(exact_cutoff_residual)
                    combined_residual_abs = abs(combined_residual)
                    record = {
                        "n_bound": n_bound,
                        "sigma": sigma,
                        "t": t,
                        "scale_law": scale_law,
                        "scale_multiplier": multiplier,
                        "window": window,
                        "bridge_residual_abs": bridge_residual_abs,
                        "combined_residual_abs": combined_residual_abs,
                        "exact_cutoff_residual_abs": exact_cutoff_residual_abs,
                    }
                    records.append(record)
                    rows.append(
                        {
                            "n_bound": n_bound,
                            "sigma": mp_str(sigma),
                            "t": mp_str(t),
                            "scale_law": scale_law,
                            "scale_multiplier": mp_str(multiplier),
                            "window": window,
                            "zero_height_at_n": mp_str(zero_heights[n_bound]),
                            "zero_pair_count_at_n": zero_pair_counts[n_bound],
                            "max_zero_height_used_at_n": max_heights_used[n_bound],
                            "exact_psi_n": mp_str(exact_psi_values[n_bound]),
                            "explicit_psi_n": mp_str(estimates[n_bound]),
                            "psi_endpoint_residual": mp_str(endpoint_psi_residual),
                            "psi_endpoint_residual_abs": mp_str(abs(endpoint_psi_residual)),
                            "increment_l1_residual": mp_str(increment_residual_prefix[n_bound]),
                            "increment_mean_abs_residual": mp_str(
                                increment_residual_prefix[n_bound] / max(n_bound - 1, 1)
                            ),
                            "exact_finite_lambda_sum": complex_record(exact_finite_sum),
                            "explicit_projected_lambda_sum": complex_record(explicit_projected_sum),
                            "negative_zeta_prime_over_zeta": complex_record(exact_target),
                            "bridge_residual": complex_record(bridge_residual),
                            "bridge_residual_abs": mp_str(bridge_residual_abs),
                            "bridge_relative_to_exact_finite_sum": mp_str(
                                _relative_abs(bridge_residual, exact_finite_sum)
                            ),
                            "exact_cutoff_residual": complex_record(exact_cutoff_residual),
                            "exact_cutoff_residual_abs": mp_str(exact_cutoff_residual_abs),
                            "combined_explicit_to_infinite_residual": complex_record(combined_residual),
                            "combined_explicit_to_infinite_residual_abs": mp_str(combined_residual_abs),
                            "bridge_over_exact_cutoff_residual_abs": _safe_ratio(
                                bridge_residual_abs,
                                exact_cutoff_residual_abs,
                            ),
                            "combined_over_exact_cutoff_residual_abs": _safe_ratio(
                                combined_residual_abs,
                                exact_cutoff_residual_abs,
                            ),
                        }
                    )

    best_bridge_rows: list[dict[str, Any]] = []
    for n_bound in selected_n_bounds:
        for sigma, t in selected_samples:
            candidates = [
                record
                for record in records
                if record["n_bound"] == n_bound and record["sigma"] == sigma and record["t"] == t
            ]
            best = min(candidates, key=lambda record: record["bridge_residual_abs"])
            best_bridge_rows.append(
                {
                    "n_bound": n_bound,
                    "sigma": mp_str(sigma),
                    "t": mp_str(t),
                    "best_scale_law": best["scale_law"],
                    "best_scale_multiplier": mp_str(best["scale_multiplier"]),
                    "best_window": best["window"],
                    "best_bridge_residual_abs": mp_str(best["bridge_residual_abs"]),
                    "combined_residual_abs_at_best_bridge": mp_str(best["combined_residual_abs"]),
                    "exact_cutoff_residual_abs": mp_str(best["exact_cutoff_residual_abs"]),
                }
            )

    configuration_summary_rows: list[dict[str, Any]] = []
    for multiplier in selected_multipliers:
        for window in selected_windows:
            config_records = [
                record
                for record in records
                if record["scale_multiplier"] == multiplier and record["window"] == window
            ]
            bridge_residuals = [record["bridge_residual_abs"] for record in config_records]
            combined_residuals = [record["combined_residual_abs"] for record in config_records]
            configuration_summary_rows.append(
                {
                    "scale_law": scale_law,
                    "scale_multiplier": mp_str(multiplier),
                    "window": window,
                    "row_count": len(config_records),
                    "average_bridge_residual_abs": mp_str(mp.fsum(bridge_residuals) / len(bridge_residuals)),
                    "min_bridge_residual_abs": mp_str(min(bridge_residuals)),
                    "max_bridge_residual_abs": mp_str(max(bridge_residuals)),
                    "average_combined_residual_abs": mp_str(mp.fsum(combined_residuals) / len(combined_residuals)),
                }
            )

    return {
        "metadata": metadata(
            "lambda_mellin_bridge_atlas",
            dps,
            "finite_lambda_mellin_bridge_not_rh_evidence",
        ),
        "parameters": {
            "n_bounds": selected_n_bounds,
            "samples": [{"sigma": mp_str(sigma), "t": mp_str(t)} for sigma, t in selected_samples],
            "scale_law": scale_law,
            "scale_multipliers": [mp_str(multiplier) for multiplier in selected_multipliers],
            "windows": selected_windows,
            "max_zero_height": mp_str(max_zero_height),
            "zero_count_available_to_max_height": len(zero_values),
            "shared_unit": "finite weighted Lambda contribution Sum_{n<=N} Delta psi_hat(n) n^-s",
            "exact_cutoff_unit": "finite weighted Lambda contribution Sum_{n<=N} Lambda(n) n^-s",
            "target": "-zeta_prime/zeta(s) for Re(s) > 1",
        },
        "summary": {
            "max_n_bound": max_n,
            "n_bound_count": len(selected_n_bounds),
            "sample_count": len(selected_samples),
            "scale_multiplier_count": len(selected_multipliers),
            "window_count": len(selected_windows),
            "row_count": len(rows),
            "best_bridge_row_count": len(best_bridge_rows),
            "configuration_summary_row_count": len(configuration_summary_rows),
            "increment_row_count": len(increment_rows),
        },
        "rows": rows,
        "best_bridge_rows": best_bridge_rows,
        "configuration_summary_rows": configuration_summary_rows,
        "increment_rows": increment_rows,
    }


def partial_summation_bridge_atlas(
    n_bounds: list[int] | None = None,
    samples: list[tuple[str | float, str | float]] | None = None,
    scale_law: str = "log",
    multipliers: list[str] | list[float] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    selected_n_bounds = _selected_bridge_n_bounds(n_bounds)
    selected_samples = _selected_bridge_samples(samples)
    selected_multipliers = _selected_scale_multipliers(multipliers or ["16", "32"])
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    scale_law = scale_law.lower()
    if scale_law not in SUPPORTED_SCALE_LAWS:
        raise ValueError(f"unsupported scale law: {scale_law}")
    comparison_tolerance = mp.mpf(10) ** (-(max(20, dps // 2)))

    max_n = max(selected_n_bounds)
    max_zero_height = max(scale_tied_zero_height(max_n, multiplier, scale_law) for multiplier in selected_multipliers)
    zero_values = _zero_values_until_height(max_zero_height)
    lambda_values = _von_mangoldt_values(max_n)
    exact_psi_values = [mp.mpf("0") for _ in range(max_n + 1)]
    running_psi = mp.mpf("0")
    for n in range(2, max_n + 1):
        running_psi += lambda_values[n]
        exact_psi_values[n] = running_psi

    exact_targets = {
        (mp_str(sigma), mp_str(t)): negative_zeta_log_derivative(mp.mpc(sigma, t))
        for sigma, t in selected_samples
    }

    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for multiplier in selected_multipliers:
        for window in selected_windows:
            estimates, zero_pair_counts, max_heights_used, zero_heights = _explicit_psi_estimates_up_to(
                max_n,
                scale_law,
                multiplier,
                window,
                zero_values,
            )
            for sigma, t in selected_samples:
                s = mp.mpc(sigma, t)
                exact_target = exact_targets[(mp_str(sigma), mp_str(t))]
                for n_bound in selected_n_bounds:
                    exact_finite_sum = mp.fsum(lambda_values[n] * mp.power(n, -s) for n in range(2, n_bound + 1))
                    exact_partial_sum = _partial_summation_projection(exact_psi_values, n_bound, s)
                    explicit_partial_sum = _partial_summation_projection(estimates, n_bound, s)
                    raw_difference_sum = _finite_difference_projection(estimates, n_bound, s)
                    exact_partial_residual = exact_partial_sum - exact_finite_sum
                    partial_bridge_residual = explicit_partial_sum - exact_finite_sum
                    raw_bridge_residual = raw_difference_sum - exact_finite_sum
                    exact_cutoff_residual = exact_finite_sum - exact_target
                    combined_partial_residual = explicit_partial_sum - exact_target
                    partial_bridge_residual_abs = abs(partial_bridge_residual)
                    raw_bridge_residual_abs = abs(raw_bridge_residual)
                    exact_cutoff_residual_abs = abs(exact_cutoff_residual)
                    combined_partial_residual_abs = abs(combined_partial_residual)
                    improvement_delta = raw_bridge_residual_abs - partial_bridge_residual_abs
                    partial_improved_over_raw = improvement_delta > comparison_tolerance
                    record = {
                        "n_bound": n_bound,
                        "sigma": sigma,
                        "t": t,
                        "scale_law": scale_law,
                        "scale_multiplier": multiplier,
                        "window": window,
                        "partial_bridge_residual_abs": partial_bridge_residual_abs,
                        "raw_bridge_residual_abs": raw_bridge_residual_abs,
                        "combined_partial_residual_abs": combined_partial_residual_abs,
                        "exact_cutoff_residual_abs": exact_cutoff_residual_abs,
                        "partial_improved_over_raw": partial_improved_over_raw,
                    }
                    records.append(record)
                    rows.append(
                        {
                            "n_bound": n_bound,
                            "sigma": mp_str(sigma),
                            "t": mp_str(t),
                            "scale_law": scale_law,
                            "scale_multiplier": mp_str(multiplier),
                            "window": window,
                            "zero_height_at_n": mp_str(zero_heights[n_bound]),
                            "zero_pair_count_at_n": zero_pair_counts[n_bound],
                            "max_zero_height_used_at_n": max_heights_used[n_bound],
                            "exact_psi_n": mp_str(exact_psi_values[n_bound]),
                            "explicit_psi_n": mp_str(estimates[n_bound]),
                            "psi_endpoint_residual": mp_str(estimates[n_bound] - exact_psi_values[n_bound]),
                            "exact_finite_lambda_sum": complex_record(exact_finite_sum),
                            "exact_partial_summation_sum": complex_record(exact_partial_sum),
                            "exact_partial_summation_residual": complex_record(exact_partial_residual),
                            "exact_partial_summation_residual_abs": mp_str(abs(exact_partial_residual)),
                            "explicit_partial_summation_sum": complex_record(explicit_partial_sum),
                            "raw_finite_difference_sum": complex_record(raw_difference_sum),
                            "negative_zeta_prime_over_zeta": complex_record(exact_target),
                            "partial_bridge_residual": complex_record(partial_bridge_residual),
                            "partial_bridge_residual_abs": mp_str(partial_bridge_residual_abs),
                            "raw_bridge_residual": complex_record(raw_bridge_residual),
                            "raw_bridge_residual_abs": mp_str(raw_bridge_residual_abs),
                            "partial_over_raw_bridge_residual_abs": _safe_ratio(
                                partial_bridge_residual_abs,
                                raw_bridge_residual_abs,
                            ),
                            "partial_improvement_delta_abs": mp_str(improvement_delta),
                            "partial_improved_over_raw": partial_improved_over_raw,
                            "partial_relative_to_exact_finite_sum": mp_str(
                                _relative_abs(partial_bridge_residual, exact_finite_sum)
                            ),
                            "exact_cutoff_residual": complex_record(exact_cutoff_residual),
                            "exact_cutoff_residual_abs": mp_str(exact_cutoff_residual_abs),
                            "combined_partial_to_infinite_residual": complex_record(combined_partial_residual),
                            "combined_partial_to_infinite_residual_abs": mp_str(combined_partial_residual_abs),
                            "partial_bridge_over_exact_cutoff_residual_abs": _safe_ratio(
                                partial_bridge_residual_abs,
                                exact_cutoff_residual_abs,
                            ),
                        }
                    )

    best_partial_rows: list[dict[str, Any]] = []
    for n_bound in selected_n_bounds:
        for sigma, t in selected_samples:
            candidates = [
                record
                for record in records
                if record["n_bound"] == n_bound and record["sigma"] == sigma and record["t"] == t
            ]
            best = min(candidates, key=lambda record: record["partial_bridge_residual_abs"])
            best_partial_rows.append(
                {
                    "n_bound": n_bound,
                    "sigma": mp_str(sigma),
                    "t": mp_str(t),
                    "best_scale_law": best["scale_law"],
                    "best_scale_multiplier": mp_str(best["scale_multiplier"]),
                    "best_window": best["window"],
                    "best_partial_bridge_residual_abs": mp_str(best["partial_bridge_residual_abs"]),
                    "raw_bridge_residual_abs_at_best_partial": mp_str(best["raw_bridge_residual_abs"]),
                    "combined_partial_residual_abs_at_best_partial": mp_str(best["combined_partial_residual_abs"]),
                    "exact_cutoff_residual_abs": mp_str(best["exact_cutoff_residual_abs"]),
                    "partial_improved_over_raw": best["partial_improved_over_raw"],
                }
            )

    configuration_summary_rows: list[dict[str, Any]] = []
    for multiplier in selected_multipliers:
        for window in selected_windows:
            config_records = [
                record
                for record in records
                if record["scale_multiplier"] == multiplier and record["window"] == window
            ]
            partial_residuals = [record["partial_bridge_residual_abs"] for record in config_records]
            raw_residuals = [record["raw_bridge_residual_abs"] for record in config_records]
            combined_residuals = [record["combined_partial_residual_abs"] for record in config_records]
            improvement_count = sum(1 for record in config_records if record["partial_improved_over_raw"])
            configuration_summary_rows.append(
                {
                    "scale_law": scale_law,
                    "scale_multiplier": mp_str(multiplier),
                    "window": window,
                    "row_count": len(config_records),
                    "partial_improvement_count": improvement_count,
                    "average_partial_bridge_residual_abs": mp_str(mp.fsum(partial_residuals) / len(partial_residuals)),
                    "average_raw_bridge_residual_abs": mp_str(mp.fsum(raw_residuals) / len(raw_residuals)),
                    "average_partial_over_raw_bridge_residual_abs": _safe_ratio(
                        mp.fsum(partial_residuals) / len(partial_residuals),
                        mp.fsum(raw_residuals) / len(raw_residuals),
                    ),
                    "min_partial_bridge_residual_abs": mp_str(min(partial_residuals)),
                    "max_partial_bridge_residual_abs": mp_str(max(partial_residuals)),
                    "average_combined_partial_residual_abs": mp_str(
                        mp.fsum(combined_residuals) / len(combined_residuals)
                    ),
                }
            )

    return {
        "metadata": metadata(
            "partial_summation_bridge_atlas",
            dps,
            "finite_partial_summation_bridge_not_rh_evidence",
        ),
        "parameters": {
            "n_bounds": selected_n_bounds,
            "samples": [{"sigma": mp_str(sigma), "t": mp_str(t)} for sigma, t in selected_samples],
            "scale_law": scale_law,
            "scale_multipliers": [mp_str(multiplier) for multiplier in selected_multipliers],
            "windows": selected_windows,
            "max_zero_height": mp_str(max_zero_height),
            "zero_count_available_to_max_height": len(zero_values),
            "shared_unit": "finite weighted Lambda contribution by partial summation from psi values",
            "exact_identity": "Sum_{n<=N} Lambda(n)n^-s = psi(N)N^-s + Sum_{k=2}^{N-1} psi(k)*(k^-s - (k+1)^-s)",
            "target": "-zeta_prime/zeta(s) for Re(s) > 1",
            "partial_raw_comparison_tolerance": mp_str(comparison_tolerance),
        },
        "summary": {
            "max_n_bound": max_n,
            "n_bound_count": len(selected_n_bounds),
            "sample_count": len(selected_samples),
            "scale_multiplier_count": len(selected_multipliers),
            "window_count": len(selected_windows),
            "row_count": len(rows),
            "best_partial_row_count": len(best_partial_rows),
            "configuration_summary_row_count": len(configuration_summary_rows),
            "partial_improvement_row_count": sum(1 for record in records if record["partial_improved_over_raw"]),
        },
        "rows": rows,
        "best_partial_rows": best_partial_rows,
        "configuration_summary_rows": configuration_summary_rows,
    }


def _pareto_alpha_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pareto_rows: list[dict[str, Any]] = []
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in records:
        key = (
            record["n_bound"],
            mp_str(record["sigma"]),
            mp_str(record["t"]),
            record["scale_law"],
            mp_str(record["scale_multiplier"]),
            record["window"],
        )
        grouped.setdefault(key, []).append(record)

    for group_records in grouped.values():
        for candidate in group_records:
            dominated = False
            for other in group_records:
                if other is candidate:
                    continue
                candidate_bridge = candidate["bridge_residual_abs"]
                candidate_cutoff = candidate["exact_cutoff_residual_abs"]
                other_bridge = other["bridge_residual_abs"]
                other_cutoff = other["exact_cutoff_residual_abs"]
                if (
                    other_bridge <= candidate_bridge
                    and other_cutoff <= candidate_cutoff
                    and (other_bridge < candidate_bridge or other_cutoff < candidate_cutoff)
                ):
                    dominated = True
                    break
            if not dominated:
                pareto_rows.append(
                    {
                        "n_bound": candidate["n_bound"],
                        "sigma": mp_str(candidate["sigma"]),
                        "t": mp_str(candidate["t"]),
                        "scale_law": candidate["scale_law"],
                        "scale_multiplier": mp_str(candidate["scale_multiplier"]),
                        "zero_window": candidate["window"],
                        "alpha": mp_str(candidate["alpha"]),
                        "bridge_residual_abs": mp_str(candidate["bridge_residual_abs"]),
                        "exact_cutoff_residual_abs": mp_str(candidate["exact_cutoff_residual_abs"]),
                        "bridge_improvement_over_sharp_abs": mp_str(candidate["bridge_improvement_over_sharp_abs"]),
                        "cutoff_bias_increase_over_sharp_abs": mp_str(candidate["cutoff_bias_increase_over_sharp_abs"]),
                    }
                )
    return pareto_rows


def bias_tuned_kernel_bridge_atlas(
    n_bounds: list[int] | None = None,
    samples: list[tuple[str | float, str | float]] | None = None,
    scale_law: str = "log",
    multipliers: list[str] | list[float] | None = None,
    windows: list[str] | None = None,
    alphas: list[str] | list[float] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    selected_n_bounds = _selected_bridge_n_bounds(n_bounds)
    selected_samples = _selected_bridge_samples(samples)
    selected_multipliers = _selected_scale_multipliers(multipliers or ["16", "32"])
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    selected_alphas = _selected_kernel_alphas(alphas)
    scale_law = scale_law.lower()
    if scale_law not in SUPPORTED_SCALE_LAWS:
        raise ValueError(f"unsupported scale law: {scale_law}")
    comparison_tolerance = mp.mpf(10) ** (-(max(20, dps // 2)))

    max_n = max(selected_n_bounds)
    max_zero_height = max(scale_tied_zero_height(max_n, multiplier, scale_law) for multiplier in selected_multipliers)
    zero_values = _zero_values_until_height(max_zero_height)
    lambda_values = _von_mangoldt_values(max_n)
    exact_targets = {
        (mp_str(sigma), mp_str(t)): negative_zeta_log_derivative(mp.mpc(sigma, t))
        for sigma, t in selected_samples
    }

    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for multiplier in selected_multipliers:
        for window in selected_windows:
            estimates, zero_pair_counts, max_heights_used, zero_heights = _explicit_psi_estimates_up_to(
                max_n,
                scale_law,
                multiplier,
                window,
                zero_values,
            )
            for sigma, t in selected_samples:
                s = mp.mpc(sigma, t)
                exact_target = exact_targets[(mp_str(sigma), mp_str(t))]
                for n_bound in selected_n_bounds:
                    sharp_exact_sum = _alpha_weighted_lambda_projection(lambda_values, n_bound, s, mp.mpf("0"))
                    sharp_explicit_sum = _alpha_weighted_projection(estimates, n_bound, s, mp.mpf("0"))
                    sharp_bridge_residual = sharp_explicit_sum - sharp_exact_sum
                    sharp_bridge_residual_abs = abs(sharp_bridge_residual)
                    sharp_cutoff_residual = sharp_exact_sum - exact_target
                    sharp_cutoff_residual_abs = abs(sharp_cutoff_residual)
                    for alpha in selected_alphas:
                        exact_weighted_sum = _alpha_weighted_lambda_projection(lambda_values, n_bound, s, alpha)
                        explicit_weighted_sum = _alpha_weighted_projection(estimates, n_bound, s, alpha)
                        bridge_residual = explicit_weighted_sum - exact_weighted_sum
                        exact_cutoff_residual = exact_weighted_sum - exact_target
                        combined_residual = explicit_weighted_sum - exact_target
                        bridge_residual_abs = abs(bridge_residual)
                        exact_cutoff_residual_abs = abs(exact_cutoff_residual)
                        combined_residual_abs = abs(combined_residual)
                        bridge_improvement = sharp_bridge_residual_abs - bridge_residual_abs
                        cutoff_bias_increase = exact_cutoff_residual_abs - sharp_cutoff_residual_abs
                        improved_over_sharp = bridge_improvement > comparison_tolerance
                        record = {
                            "n_bound": n_bound,
                            "sigma": sigma,
                            "t": t,
                            "scale_law": scale_law,
                            "scale_multiplier": multiplier,
                            "window": window,
                            "alpha": alpha,
                            "bridge_residual_abs": bridge_residual_abs,
                            "exact_cutoff_residual_abs": exact_cutoff_residual_abs,
                            "combined_residual_abs": combined_residual_abs,
                            "sharp_bridge_residual_abs": sharp_bridge_residual_abs,
                            "sharp_cutoff_residual_abs": sharp_cutoff_residual_abs,
                            "bridge_improvement_over_sharp_abs": bridge_improvement,
                            "cutoff_bias_increase_over_sharp_abs": cutoff_bias_increase,
                            "improved_over_sharp": improved_over_sharp,
                        }
                        records.append(record)
                        rows.append(
                            {
                                "n_bound": n_bound,
                                "sigma": mp_str(sigma),
                                "t": mp_str(t),
                                "scale_law": scale_law,
                                "scale_multiplier": mp_str(multiplier),
                                "zero_window": window,
                                "alpha": mp_str(alpha),
                                "kernel_formula": "K_alpha(n,N)=1-alpha*n/(N+1)",
                                "kernel_weight_at_2": mp_str(alpha_cesaro_kernel_weight(2, n_bound, alpha)),
                                "kernel_weight_at_n": mp_str(alpha_cesaro_kernel_weight(n_bound, n_bound, alpha)),
                                "zero_height_at_n": mp_str(zero_heights[n_bound]),
                                "zero_pair_count_at_n": zero_pair_counts[n_bound],
                                "max_zero_height_used_at_n": max_heights_used[n_bound],
                                "exact_weighted_lambda_sum": complex_record(exact_weighted_sum),
                                "explicit_weighted_lambda_sum": complex_record(explicit_weighted_sum),
                                "sharp_exact_lambda_sum": complex_record(sharp_exact_sum),
                                "sharp_explicit_lambda_sum": complex_record(sharp_explicit_sum),
                                "negative_zeta_prime_over_zeta": complex_record(exact_target),
                                "bridge_residual": complex_record(bridge_residual),
                                "bridge_residual_abs": mp_str(bridge_residual_abs),
                                "sharp_bridge_residual_abs": mp_str(sharp_bridge_residual_abs),
                                "bridge_over_sharp_residual_abs": _safe_ratio(
                                    bridge_residual_abs,
                                    sharp_bridge_residual_abs,
                                ),
                                "bridge_improvement_over_sharp_abs": mp_str(bridge_improvement),
                                "improved_over_sharp": improved_over_sharp,
                                "exact_cutoff_residual": complex_record(exact_cutoff_residual),
                                "exact_cutoff_residual_abs": mp_str(exact_cutoff_residual_abs),
                                "sharp_exact_cutoff_residual_abs": mp_str(sharp_cutoff_residual_abs),
                                "cutoff_bias_increase_over_sharp_abs": mp_str(cutoff_bias_increase),
                                "combined_weighted_to_infinite_residual": complex_record(combined_residual),
                                "combined_weighted_to_infinite_residual_abs": mp_str(combined_residual_abs),
                            }
                        )

    pareto_rows = _pareto_alpha_rows(records)
    alpha_summary_rows: list[dict[str, Any]] = []
    for alpha in selected_alphas:
        alpha_records = [record for record in records if record["alpha"] == alpha]
        bridge_residuals = [record["bridge_residual_abs"] for record in alpha_records]
        cutoff_residuals = [record["exact_cutoff_residual_abs"] for record in alpha_records]
        improvements = [record["bridge_improvement_over_sharp_abs"] for record in alpha_records]
        bias_increases = [record["cutoff_bias_increase_over_sharp_abs"] for record in alpha_records]
        improved_count = sum(1 for record in alpha_records if record["improved_over_sharp"])
        pareto_count = sum(1 for row in pareto_rows if mp.mpf(row["alpha"]) == alpha)
        alpha_summary_rows.append(
            {
                "alpha": mp_str(alpha),
                "row_count": len(alpha_records),
                "improved_over_sharp_count": improved_count,
                "pareto_row_count": pareto_count,
                "average_bridge_residual_abs": mp_str(mp.fsum(bridge_residuals) / len(bridge_residuals)),
                "average_exact_cutoff_residual_abs": mp_str(mp.fsum(cutoff_residuals) / len(cutoff_residuals)),
                "average_bridge_improvement_over_sharp_abs": mp_str(mp.fsum(improvements) / len(improvements)),
                "average_cutoff_bias_increase_over_sharp_abs": mp_str(mp.fsum(bias_increases) / len(bias_increases)),
            }
        )

    best_bridge_rows: list[dict[str, Any]] = []
    for n_bound in selected_n_bounds:
        for sigma, t in selected_samples:
            candidates = [
                record
                for record in records
                if record["n_bound"] == n_bound and record["sigma"] == sigma and record["t"] == t
            ]
            best = min(candidates, key=lambda record: record["bridge_residual_abs"])
            best_bridge_rows.append(
                {
                    "n_bound": n_bound,
                    "sigma": mp_str(sigma),
                    "t": mp_str(t),
                    "best_scale_law": best["scale_law"],
                    "best_scale_multiplier": mp_str(best["scale_multiplier"]),
                    "best_zero_window": best["window"],
                    "best_alpha": mp_str(best["alpha"]),
                    "best_bridge_residual_abs": mp_str(best["bridge_residual_abs"]),
                    "exact_cutoff_residual_abs_at_best": mp_str(best["exact_cutoff_residual_abs"]),
                    "bridge_improvement_over_sharp_abs_at_best": mp_str(best["bridge_improvement_over_sharp_abs"]),
                    "cutoff_bias_increase_over_sharp_abs_at_best": mp_str(best["cutoff_bias_increase_over_sharp_abs"]),
                }
            )

    return {
        "metadata": metadata(
            "bias_tuned_kernel_bridge_atlas",
            dps,
            "finite_bias_tuned_kernel_bridge_not_rh_evidence",
        ),
        "parameters": {
            "n_bounds": selected_n_bounds,
            "samples": [{"sigma": mp_str(sigma), "t": mp_str(t)} for sigma, t in selected_samples],
            "scale_law": scale_law,
            "scale_multipliers": [mp_str(multiplier) for multiplier in selected_multipliers],
            "zero_windows": selected_windows,
            "alphas": [mp_str(alpha) for alpha in selected_alphas],
            "max_zero_height": mp_str(max_zero_height),
            "zero_count_available_to_max_height": len(zero_values),
            "kernel_formula": "K_alpha(n,N)=1-alpha*n/(N+1)",
            "alpha_0": "sharp baseline",
            "alpha_1": "Cesaro endpoint",
            "target": "-zeta_prime/zeta(s) for Re(s) > 1",
            "comparison_tolerance": mp_str(comparison_tolerance),
        },
        "summary": {
            "max_n_bound": max_n,
            "n_bound_count": len(selected_n_bounds),
            "sample_count": len(selected_samples),
            "scale_multiplier_count": len(selected_multipliers),
            "zero_window_count": len(selected_windows),
            "alpha_count": len(selected_alphas),
            "row_count": len(rows),
            "alpha_summary_row_count": len(alpha_summary_rows),
            "pareto_row_count": len(pareto_rows),
            "best_bridge_row_count": len(best_bridge_rows),
            "improved_over_sharp_row_count": sum(1 for record in records if record["improved_over_sharp"]),
        },
        "rows": rows,
        "alpha_summary_rows": alpha_summary_rows,
        "pareto_rows": pareto_rows,
        "best_bridge_rows": best_bridge_rows,
    }


def cesaro_mellin_bridge_atlas(
    n_bounds: list[int] | None = None,
    samples: list[tuple[str | float, str | float]] | None = None,
    scale_law: str = "log",
    multipliers: list[str] | list[float] | None = None,
    windows: list[str] | None = None,
    kernels: list[str] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    selected_n_bounds = _selected_bridge_n_bounds(n_bounds)
    selected_samples = _selected_bridge_samples(samples)
    selected_multipliers = _selected_scale_multipliers(multipliers or ["16", "32"])
    selected_windows = _selected_windows(windows or list(SUPPORTED_ZERO_WINDOWS))
    selected_kernels = _selected_n_domain_kernels(kernels)
    scale_law = scale_law.lower()
    if scale_law not in SUPPORTED_SCALE_LAWS:
        raise ValueError(f"unsupported scale law: {scale_law}")
    comparison_tolerance = mp.mpf(10) ** (-(max(20, dps // 2)))

    max_n = max(selected_n_bounds)
    max_zero_height = max(scale_tied_zero_height(max_n, multiplier, scale_law) for multiplier in selected_multipliers)
    zero_values = _zero_values_until_height(max_zero_height)
    lambda_values = _von_mangoldt_values(max_n)
    exact_targets = {
        (mp_str(sigma), mp_str(t)): negative_zeta_log_derivative(mp.mpc(sigma, t))
        for sigma, t in selected_samples
    }

    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for multiplier in selected_multipliers:
        for window in selected_windows:
            estimates, zero_pair_counts, max_heights_used, zero_heights = _explicit_psi_estimates_up_to(
                max_n,
                scale_law,
                multiplier,
                window,
                zero_values,
            )
            for sigma, t in selected_samples:
                s = mp.mpc(sigma, t)
                exact_target = exact_targets[(mp_str(sigma), mp_str(t))]
                for n_bound in selected_n_bounds:
                    raw_exact_sum = _kernel_weighted_lambda_projection(lambda_values, n_bound, s, "sharp")
                    raw_explicit_sum = _kernel_weighted_projection(estimates, n_bound, s, "sharp")
                    raw_bridge_residual = raw_explicit_sum - raw_exact_sum
                    raw_bridge_residual_abs = abs(raw_bridge_residual)
                    for kernel in selected_kernels:
                        exact_smoothed_sum = _kernel_weighted_lambda_projection(lambda_values, n_bound, s, kernel)
                        explicit_smoothed_sum = _kernel_weighted_projection(estimates, n_bound, s, kernel)
                        bridge_residual = explicit_smoothed_sum - exact_smoothed_sum
                        exact_smoothed_cutoff_residual = exact_smoothed_sum - exact_target
                        combined_smoothed_residual = explicit_smoothed_sum - exact_target
                        bridge_residual_abs = abs(bridge_residual)
                        exact_smoothed_cutoff_residual_abs = abs(exact_smoothed_cutoff_residual)
                        combined_smoothed_residual_abs = abs(combined_smoothed_residual)
                        improvement_delta = raw_bridge_residual_abs - bridge_residual_abs
                        improved_over_raw = improvement_delta > comparison_tolerance
                        record = {
                            "n_bound": n_bound,
                            "sigma": sigma,
                            "t": t,
                            "scale_law": scale_law,
                            "scale_multiplier": multiplier,
                            "window": window,
                            "kernel": kernel,
                            "bridge_residual_abs": bridge_residual_abs,
                            "raw_bridge_residual_abs": raw_bridge_residual_abs,
                            "combined_smoothed_residual_abs": combined_smoothed_residual_abs,
                            "exact_smoothed_cutoff_residual_abs": exact_smoothed_cutoff_residual_abs,
                            "improved_over_raw": improved_over_raw,
                        }
                        records.append(record)
                        rows.append(
                            {
                                "n_bound": n_bound,
                                "sigma": mp_str(sigma),
                                "t": mp_str(t),
                                "scale_law": scale_law,
                                "scale_multiplier": mp_str(multiplier),
                                "zero_window": window,
                                "n_domain_kernel": kernel,
                                "zero_height_at_n": mp_str(zero_heights[n_bound]),
                                "zero_pair_count_at_n": zero_pair_counts[n_bound],
                                "max_zero_height_used_at_n": max_heights_used[n_bound],
                                "kernel_weight_at_2": mp_str(n_domain_kernel_weight(2, n_bound, kernel)),
                                "kernel_weight_at_n": mp_str(n_domain_kernel_weight(n_bound, n_bound, kernel)),
                                "exact_smoothed_lambda_sum": complex_record(exact_smoothed_sum),
                                "explicit_smoothed_lambda_sum": complex_record(explicit_smoothed_sum),
                                "raw_exact_lambda_sum": complex_record(raw_exact_sum),
                                "raw_explicit_lambda_sum": complex_record(raw_explicit_sum),
                                "negative_zeta_prime_over_zeta": complex_record(exact_target),
                                "smoothed_bridge_residual": complex_record(bridge_residual),
                                "smoothed_bridge_residual_abs": mp_str(bridge_residual_abs),
                                "raw_bridge_residual": complex_record(raw_bridge_residual),
                                "raw_bridge_residual_abs": mp_str(raw_bridge_residual_abs),
                                "smoothed_over_raw_bridge_residual_abs": _safe_ratio(
                                    bridge_residual_abs,
                                    raw_bridge_residual_abs,
                                ),
                                "smoothed_improvement_delta_abs": mp_str(improvement_delta),
                                "smoothed_improved_over_raw": improved_over_raw,
                                "exact_smoothed_cutoff_residual": complex_record(exact_smoothed_cutoff_residual),
                                "exact_smoothed_cutoff_residual_abs": mp_str(exact_smoothed_cutoff_residual_abs),
                                "combined_smoothed_to_infinite_residual": complex_record(combined_smoothed_residual),
                                "combined_smoothed_to_infinite_residual_abs": mp_str(combined_smoothed_residual_abs),
                                "smoothed_bridge_over_exact_smoothed_cutoff_residual_abs": _safe_ratio(
                                    bridge_residual_abs,
                                    exact_smoothed_cutoff_residual_abs,
                                ),
                            }
                        )

    best_kernel_rows: list[dict[str, Any]] = []
    for n_bound in selected_n_bounds:
        for sigma, t in selected_samples:
            candidates = [
                record
                for record in records
                if record["n_bound"] == n_bound and record["sigma"] == sigma and record["t"] == t
            ]
            best = min(candidates, key=lambda record: record["bridge_residual_abs"])
            best_kernel_rows.append(
                {
                    "n_bound": n_bound,
                    "sigma": mp_str(sigma),
                    "t": mp_str(t),
                    "best_scale_law": best["scale_law"],
                    "best_scale_multiplier": mp_str(best["scale_multiplier"]),
                    "best_zero_window": best["window"],
                    "best_n_domain_kernel": best["kernel"],
                    "best_smoothed_bridge_residual_abs": mp_str(best["bridge_residual_abs"]),
                    "raw_bridge_residual_abs_at_best": mp_str(best["raw_bridge_residual_abs"]),
                    "combined_smoothed_residual_abs_at_best": mp_str(best["combined_smoothed_residual_abs"]),
                    "exact_smoothed_cutoff_residual_abs_at_best": mp_str(best["exact_smoothed_cutoff_residual_abs"]),
                    "smoothed_improved_over_raw": best["improved_over_raw"],
                }
            )

    kernel_summary_rows: list[dict[str, Any]] = []
    for kernel in selected_kernels:
        kernel_records = [record for record in records if record["kernel"] == kernel]
        bridge_residuals = [record["bridge_residual_abs"] for record in kernel_records]
        raw_residuals = [record["raw_bridge_residual_abs"] for record in kernel_records]
        cutoff_residuals = [record["exact_smoothed_cutoff_residual_abs"] for record in kernel_records]
        improvement_count = sum(1 for record in kernel_records if record["improved_over_raw"])
        kernel_summary_rows.append(
            {
                "n_domain_kernel": kernel,
                "row_count": len(kernel_records),
                "smoothed_improvement_count": improvement_count,
                "average_smoothed_bridge_residual_abs": mp_str(mp.fsum(bridge_residuals) / len(bridge_residuals)),
                "average_raw_bridge_residual_abs": mp_str(mp.fsum(raw_residuals) / len(raw_residuals)),
                "average_smoothed_over_raw_bridge_residual_abs": _safe_ratio(
                    mp.fsum(bridge_residuals) / len(bridge_residuals),
                    mp.fsum(raw_residuals) / len(raw_residuals),
                ),
                "min_smoothed_bridge_residual_abs": mp_str(min(bridge_residuals)),
                "max_smoothed_bridge_residual_abs": mp_str(max(bridge_residuals)),
                "average_exact_smoothed_cutoff_residual_abs": mp_str(
                    mp.fsum(cutoff_residuals) / len(cutoff_residuals)
                ),
            }
        )

    configuration_summary_rows: list[dict[str, Any]] = []
    for multiplier in selected_multipliers:
        for window in selected_windows:
            for kernel in selected_kernels:
                config_records = [
                    record
                    for record in records
                    if record["scale_multiplier"] == multiplier
                    and record["window"] == window
                    and record["kernel"] == kernel
                ]
                bridge_residuals = [record["bridge_residual_abs"] for record in config_records]
                raw_residuals = [record["raw_bridge_residual_abs"] for record in config_records]
                improvement_count = sum(1 for record in config_records if record["improved_over_raw"])
                configuration_summary_rows.append(
                    {
                        "scale_law": scale_law,
                        "scale_multiplier": mp_str(multiplier),
                        "zero_window": window,
                        "n_domain_kernel": kernel,
                        "row_count": len(config_records),
                        "smoothed_improvement_count": improvement_count,
                        "average_smoothed_bridge_residual_abs": mp_str(
                            mp.fsum(bridge_residuals) / len(bridge_residuals)
                        ),
                        "average_raw_bridge_residual_abs": mp_str(mp.fsum(raw_residuals) / len(raw_residuals)),
                        "average_smoothed_over_raw_bridge_residual_abs": _safe_ratio(
                            mp.fsum(bridge_residuals) / len(bridge_residuals),
                            mp.fsum(raw_residuals) / len(raw_residuals),
                        ),
                    }
                )

    return {
        "metadata": metadata(
            "cesaro_mellin_bridge_atlas",
            dps,
            "finite_cesaro_mellin_bridge_not_rh_evidence",
        ),
        "parameters": {
            "n_bounds": selected_n_bounds,
            "samples": [{"sigma": mp_str(sigma), "t": mp_str(t)} for sigma, t in selected_samples],
            "scale_law": scale_law,
            "scale_multipliers": [mp_str(multiplier) for multiplier in selected_multipliers],
            "zero_windows": selected_windows,
            "n_domain_kernels": selected_kernels,
            "max_zero_height": mp_str(max_zero_height),
            "zero_count_available_to_max_height": len(zero_values),
            "kernel_definitions": {
                "sharp": "K(n,N)=1",
                "cesaro": "K(n,N)=1-n/(N+1)",
                "hann": "K(n,N)=0.5*(1+cos(pi*n/(N+1)))",
            },
            "raw_baseline": "sharp n-domain kernel over the same explicit psi_hat increments",
            "target": "-zeta_prime/zeta(s) for Re(s) > 1",
            "smoothed_raw_comparison_tolerance": mp_str(comparison_tolerance),
        },
        "summary": {
            "max_n_bound": max_n,
            "n_bound_count": len(selected_n_bounds),
            "sample_count": len(selected_samples),
            "scale_multiplier_count": len(selected_multipliers),
            "zero_window_count": len(selected_windows),
            "n_domain_kernel_count": len(selected_kernels),
            "row_count": len(rows),
            "best_kernel_row_count": len(best_kernel_rows),
            "kernel_summary_row_count": len(kernel_summary_rows),
            "configuration_summary_row_count": len(configuration_summary_rows),
            "smoothed_improvement_row_count": sum(1 for record in records if record["improved_over_raw"]),
        },
        "rows": rows,
        "best_kernel_rows": best_kernel_rows,
        "kernel_summary_rows": kernel_summary_rows,
        "configuration_summary_rows": configuration_summary_rows,
    }
