"""Euler-product and logarithmic-derivative probes in the convergent half-plane."""

from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp

from .common import complex_record, metadata, mp_range, mp_str, set_precision


DEFAULT_SAMPLES = [
    ("2", "0"),
    ("2", "14.134725141734693790457251983562"),
    ("1.5", "14.134725141734693790457251983562"),
]

DEFAULT_BOUNDARY_SIGMAS = ["2", "1.5", "1.25", "1.1", "1.05"]
DEFAULT_BOUNDARY_T_VALUES = ["0", "14.134725141734693790457251983562"]
DEFAULT_T_AXIS_SIGMAS = ["1.5", "1.05"]
DEFAULT_T_AXIS_T_VALUES = [
    "0",
    "5",
    "10",
    "14.134725141734693790457251983562",
    "20",
    "21.0220396387715549926284795938969",
    "25.0108575801456887632137909925628",
    "30",
]
REFERENCE_T_VALUES = {
    "first_zero_ordinate_reference": "14.134725141734693790457251983562",
    "second_zero_ordinate_reference": "21.0220396387715549926284795938969",
    "third_zero_ordinate_reference": "25.0108575801456887632137909925628",
}


def _selected_samples(samples: list[tuple[str | float, str | float]] | None) -> list[tuple[mp.mpf, mp.mpf]]:
    selected = samples or DEFAULT_SAMPLES
    if not selected:
        raise ValueError("at least one s sample is required")
    parsed: list[tuple[mp.mpf, mp.mpf]] = []
    for sigma_value, t_value in selected:
        sigma = mp.mpf(str(sigma_value))
        t = mp.mpf(str(t_value))
        if sigma <= 1:
            raise ValueError("Euler-product probes require sigma greater than 1")
        parsed.append((sigma, t))
    return parsed


def _selected_prime_bounds(prime_bounds: list[int] | None) -> list[int]:
    selected = sorted(set(int(value) for value in (prime_bounds or [10, 100, 500])))
    if not selected or selected[0] < 2:
        raise ValueError("prime bounds must be at least 2")
    return selected


def _selected_sigmas(sigmas: list[str | float] | None) -> list[mp.mpf]:
    selected = sorted({mp.mpf(str(value)) for value in (sigmas or DEFAULT_BOUNDARY_SIGMAS)}, reverse=True)
    if not selected:
        raise ValueError("at least one sigma value is required")
    if selected[-1] <= 1:
        raise ValueError("sigma-boundary probes require every sigma to be greater than 1")
    return selected


def _selected_t_values(t_values: list[str | float] | None) -> list[mp.mpf]:
    selected = [mp.mpf(str(value)) for value in (t_values or DEFAULT_BOUNDARY_T_VALUES)]
    if not selected:
        raise ValueError("at least one t value is required")
    return selected


def _selected_t_axis_values(t_values: list[str | float] | None) -> list[mp.mpf]:
    selected = sorted({mp.mpf(str(value)) for value in (t_values or DEFAULT_T_AXIS_T_VALUES)})
    if not selected:
        raise ValueError("at least one t value is required")
    if selected[0] < 0:
        raise ValueError("t-axis probes require nonnegative t values")
    return selected


def negative_zeta_log_derivative(s: mp.mpc) -> mp.mpc:
    zeta_s = mp.zeta(s)
    zeta_prime = mp.diff(lambda z: mp.zeta(z), s)
    return -zeta_prime / zeta_s


def _finite_euler_product_rows(s: mp.mpc, prime_bound: int) -> tuple[mp.mpc, mp.mpc, list[dict[str, Any]]]:
    product = mp.mpc("1")
    log_derivative_sum = mp.mpc("0")
    rows: list[dict[str, Any]] = []
    for prime in sp.primerange(2, prime_bound + 1):
        p = int(prime)
        p_to_minus_s = mp.power(p, -s)
        factor = 1 / (1 - p_to_minus_s)
        contribution = mp.log(p) * p_to_minus_s / (1 - p_to_minus_s)
        product *= factor
        log_derivative_sum += contribution
        rows.append(
            {
                "prime": p,
                "euler_factor": complex_record(factor),
                "log_derivative_contribution": complex_record(contribution),
            }
        )
    return product, log_derivative_sum, rows


def _prime_power_cutoff_rows(s: mp.mpc, prime_power_bound: int) -> tuple[mp.mpc, list[dict[str, Any]]]:
    total = mp.mpc("0")
    rows: list[dict[str, Any]] = []
    for prime in sp.primerange(2, prime_power_bound + 1):
        p = int(prime)
        exponent = 1
        power = p
        log_prime = mp.log(p)
        while power <= prime_power_bound:
            contribution = log_prime * mp.power(power, -s)
            total += contribution
            rows.append(
                {
                    "prime": p,
                    "exponent": exponent,
                    "prime_power": power,
                    "von_mangoldt_weight": mp_str(log_prime),
                    "weighted_contribution": complex_record(contribution),
                }
            )
            exponent += 1
            power *= p
    rows.sort(key=lambda row: (int(row["prime_power"]), int(row["prime"]), int(row["exponent"])))
    return total, rows


def _relative_residual(residual: mp.mpc, target: mp.mpc) -> mp.mpf:
    return abs(residual) / max(abs(target), mp.mpf("1"))


def _residual_ratio(current: str, previous: str) -> str | None:
    denominator = mp.mpf(previous)
    if denominator == 0:
        return None
    return mp_str(mp.mpf(current) / denominator)


def _distance_to_sigma_one(sigma: mp.mpf) -> str:
    return mp_str(sigma - mp.mpf("1"), digits=min(30, mp.mp.dps))


def _t_axis_annotation(t: mp.mpf) -> dict[str, Any]:
    tolerance = mp.mpf("1e-24")
    if abs(t) <= tolerance:
        return {
            "t_axis_annotation": "pole_axis_reference",
            "nearest_reference_label": "pole_axis_t_0",
            "nearest_reference_delta": mp_str(abs(t)),
        }
    nearest_label = None
    nearest_delta: mp.mpf | None = None
    for label, value in REFERENCE_T_VALUES.items():
        delta = abs(t - mp.mpf(value))
        if nearest_delta is None or delta < nearest_delta:
            nearest_label = label
            nearest_delta = delta
    if nearest_delta is not None and nearest_delta <= tolerance:
        annotation = "known_zero_ordinate_landmark"
    else:
        annotation = "ordinary_vertical_sample"
    return {
        "t_axis_annotation": annotation,
        "nearest_reference_label": nearest_label,
        "nearest_reference_delta": mp_str(nearest_delta if nearest_delta is not None else 0),
    }


def _vertical_sample_row(sigma: mp.mpf, t: mp.mpf, bound: int) -> dict[str, Any]:
    s = mp.mpc(sigma, t)
    zeta_s = mp.zeta(s)
    exact_log_derivative = negative_zeta_log_derivative(s)
    annotation = _t_axis_annotation(t)
    finite_product, prime_factor_sum, factor_rows = _finite_euler_product_rows(s, bound)
    prime_power_sum, power_rows = _prime_power_cutoff_rows(s, bound)
    product_residual = finite_product - zeta_s
    prime_factor_residual = prime_factor_sum - exact_log_derivative
    prime_power_residual = prime_power_sum - exact_log_derivative
    return {
        "sigma": mp_str(sigma),
        "distance_to_sigma_1": _distance_to_sigma_one(sigma),
        "t": mp_str(t),
        **annotation,
        "prime_bound": bound,
        "prime_count": len(factor_rows),
        "prime_power_term_count": len(power_rows),
        "zeta_abs": mp_str(abs(zeta_s)),
        "negative_zeta_prime_over_zeta_abs": mp_str(abs(exact_log_derivative)),
        "euler_product_residual_abs": mp_str(abs(product_residual)),
        "euler_product_relative_residual": mp_str(_relative_residual(product_residual, zeta_s)),
        "prime_factor_log_derivative_residual_abs": mp_str(abs(prime_factor_residual)),
        "prime_factor_log_derivative_relative_residual": mp_str(
            _relative_residual(prime_factor_residual, exact_log_derivative)
        ),
        "prime_power_cutoff_log_derivative_residual_abs": mp_str(abs(prime_power_residual)),
        "prime_power_cutoff_log_derivative_relative_residual": mp_str(
            _relative_residual(prime_power_residual, exact_log_derivative)
        ),
    }


def euler_product_probe(
    samples: list[tuple[str | float, str | float]] | None = None,
    prime_bounds: list[int] | None = None,
    dps: int = 80,
    include_terms: bool = False,
) -> dict[str, Any]:
    set_precision(dps)
    selected_samples = _selected_samples(samples)
    selected_bounds = _selected_prime_bounds(prime_bounds)
    rows: list[dict[str, Any]] = []
    prime_factor_rows: list[dict[str, Any]] = []
    prime_power_term_rows: list[dict[str, Any]] = []

    for sigma, t in selected_samples:
        s = mp.mpc(sigma, t)
        zeta_s = mp.zeta(s)
        exact_log_derivative = negative_zeta_log_derivative(s)
        for bound in selected_bounds:
            finite_product, prime_factor_sum, factor_rows = _finite_euler_product_rows(s, bound)
            prime_power_sum, power_rows = _prime_power_cutoff_rows(s, bound)
            product_residual = finite_product - zeta_s
            prime_factor_residual = prime_factor_sum - exact_log_derivative
            prime_power_residual = prime_power_sum - exact_log_derivative
            max_exponent = max((int(row["exponent"]) for row in power_rows), default=0)
            row = {
                "sigma": mp_str(sigma),
                "t": mp_str(t),
                "prime_bound": bound,
                "prime_count": len(factor_rows),
                "prime_power_term_count": len(power_rows),
                "max_prime_power_exponent": max_exponent,
                "zeta": complex_record(zeta_s),
                "finite_euler_product": complex_record(finite_product),
                "euler_product_minus_zeta": complex_record(product_residual),
                "euler_product_residual_abs": mp_str(abs(product_residual)),
                "euler_product_relative_residual": mp_str(_relative_residual(product_residual, zeta_s)),
                "negative_zeta_prime_over_zeta": complex_record(exact_log_derivative),
                "prime_factor_log_derivative_sum": complex_record(prime_factor_sum),
                "prime_factor_log_derivative_minus_exact": complex_record(prime_factor_residual),
                "prime_factor_log_derivative_residual_abs": mp_str(abs(prime_factor_residual)),
                "prime_factor_log_derivative_relative_residual": mp_str(
                    _relative_residual(prime_factor_residual, exact_log_derivative)
                ),
                "prime_power_cutoff_log_derivative_sum": complex_record(prime_power_sum),
                "prime_power_cutoff_log_derivative_minus_exact": complex_record(prime_power_residual),
                "prime_power_cutoff_log_derivative_residual_abs": mp_str(abs(prime_power_residual)),
                "prime_power_cutoff_log_derivative_relative_residual": mp_str(
                    _relative_residual(prime_power_residual, exact_log_derivative)
                ),
            }
            rows.append(row)
            if include_terms:
                for term_row in factor_rows:
                    prime_factor_rows.append(
                        {
                            "sigma": mp_str(sigma),
                            "t": mp_str(t),
                            "prime_bound": bound,
                            **term_row,
                        }
                    )
                for term_row in power_rows:
                    prime_power_term_rows.append(
                        {
                            "sigma": mp_str(sigma),
                            "t": mp_str(t),
                            "prime_power_bound": bound,
                            **term_row,
                        }
                    )

    return {
        "metadata": metadata(
            "euler_product_probe",
            dps,
            "finite_euler_product_log_derivative_probe_not_rh_evidence",
        ),
        "parameters": {
            "samples": [{"sigma": mp_str(sigma), "t": mp_str(t)} for sigma, t in selected_samples],
            "prime_bounds": selected_bounds,
            "include_terms": include_terms,
            "formula": {
                "euler_product": "zeta(s) = product_p (1 - p^-s)^-1 for Re(s) > 1",
                "logarithmic_derivative": "-zeta'(s)/zeta(s) = sum_n Lambda(n) n^-s for Re(s) > 1",
            },
        },
        "summary": {
            "sample_count": len(selected_samples),
            "max_prime_bound": max(selected_bounds),
            "row_count": len(rows),
        },
        "rows": rows,
        "prime_factor_rows": prime_factor_rows,
        "prime_power_term_rows": prime_power_term_rows,
    }


def sigma_boundary_probe(
    sigmas: list[str | float] | None = None,
    t_values: list[str | float] | None = None,
    prime_bounds: list[int] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    selected_sigmas = _selected_sigmas(sigmas)
    selected_t_values = _selected_t_values(t_values)
    selected_bounds = _selected_prime_bounds(prime_bounds)
    rows: list[dict[str, Any]] = []
    rows_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}

    for t in selected_t_values:
        for sigma in selected_sigmas:
            s = mp.mpc(sigma, t)
            zeta_s = mp.zeta(s)
            exact_log_derivative = negative_zeta_log_derivative(s)
            for bound in selected_bounds:
                finite_product, prime_factor_sum, factor_rows = _finite_euler_product_rows(s, bound)
                prime_power_sum, power_rows = _prime_power_cutoff_rows(s, bound)
                product_residual = finite_product - zeta_s
                prime_factor_residual = prime_factor_sum - exact_log_derivative
                prime_power_residual = prime_power_sum - exact_log_derivative
                row = {
                    "sigma": mp_str(sigma),
                    "t": mp_str(t),
                    "distance_to_sigma_1": _distance_to_sigma_one(sigma),
                    "prime_bound": bound,
                    "prime_count": len(factor_rows),
                    "prime_power_term_count": len(power_rows),
                    "zeta_abs": mp_str(abs(zeta_s)),
                    "negative_zeta_prime_over_zeta_abs": mp_str(abs(exact_log_derivative)),
                    "euler_product_residual_abs": mp_str(abs(product_residual)),
                    "euler_product_relative_residual": mp_str(_relative_residual(product_residual, zeta_s)),
                    "prime_factor_log_derivative_residual_abs": mp_str(abs(prime_factor_residual)),
                    "prime_factor_log_derivative_relative_residual": mp_str(
                        _relative_residual(prime_factor_residual, exact_log_derivative)
                    ),
                    "prime_power_cutoff_log_derivative_residual_abs": mp_str(abs(prime_power_residual)),
                    "prime_power_cutoff_log_derivative_relative_residual": mp_str(
                        _relative_residual(prime_power_residual, exact_log_derivative)
                    ),
                }
                rows.append(row)
                rows_by_key[(row["t"], row["sigma"], bound)] = row

    transition_rows: list[dict[str, Any]] = []
    for t in selected_t_values:
        t_key = mp_str(t)
        for bound in selected_bounds:
            previous: dict[str, Any] | None = None
            for sigma in selected_sigmas:
                current = rows_by_key[(t_key, mp_str(sigma), bound)]
                if previous is not None:
                    transition_rows.append(
                        {
                            "t": t_key,
                            "prime_bound": bound,
                            "from_sigma": previous["sigma"],
                            "to_sigma": current["sigma"],
                            "from_distance_to_sigma_1": previous["distance_to_sigma_1"],
                            "to_distance_to_sigma_1": current["distance_to_sigma_1"],
                            "direction": "toward_sigma_1_from_above",
                            "euler_product_residual_ratio": _residual_ratio(
                                current["euler_product_residual_abs"],
                                previous["euler_product_residual_abs"],
                            ),
                            "prime_factor_log_derivative_residual_ratio": _residual_ratio(
                                current["prime_factor_log_derivative_residual_abs"],
                                previous["prime_factor_log_derivative_residual_abs"],
                            ),
                            "prime_power_cutoff_log_derivative_residual_ratio": _residual_ratio(
                                current["prime_power_cutoff_log_derivative_residual_abs"],
                                previous["prime_power_cutoff_log_derivative_residual_abs"],
                            ),
                        }
                    )
                previous = current

    return {
        "metadata": metadata(
            "sigma_boundary_probe",
            dps,
            "finite_sigma_boundary_probe_not_critical_line_evidence",
        ),
        "parameters": {
            "sigmas": [mp_str(value) for value in selected_sigmas],
            "t_values": [mp_str(value) for value in selected_t_values],
            "prime_bounds": selected_bounds,
            "formula": {
                "euler_product": "zeta(s) = product_p (1 - p^-s)^-1 for Re(s) > 1",
                "logarithmic_derivative": "-zeta'(s)/zeta(s) = sum_n Lambda(n) n^-s for Re(s) > 1",
            },
        },
        "summary": {
            "sigma_count": len(selected_sigmas),
            "t_value_count": len(selected_t_values),
            "max_prime_bound": max(selected_bounds),
            "row_count": len(rows),
            "transition_row_count": len(transition_rows),
            "minimum_sigma": mp_str(min(selected_sigmas)),
            "minimum_distance_to_sigma_1": _distance_to_sigma_one(min(selected_sigmas)),
        },
        "rows": rows,
        "transition_rows": transition_rows,
    }


def t_axis_boundary_probe(
    sigmas: list[str | float] | None = None,
    t_values: list[str | float] | None = None,
    prime_bounds: list[int] | None = None,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    selected_sigmas = _selected_sigmas(sigmas or DEFAULT_T_AXIS_SIGMAS)
    selected_t_values = _selected_t_axis_values(t_values)
    selected_bounds = _selected_prime_bounds(prime_bounds)
    rows: list[dict[str, Any]] = []
    rows_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}

    for sigma in selected_sigmas:
        for t in selected_t_values:
            for bound in selected_bounds:
                row = _vertical_sample_row(sigma, t, bound)
                rows.append(row)
                rows_by_key[(row["sigma"], row["t"], bound)] = row

    transition_rows: list[dict[str, Any]] = []
    for sigma in selected_sigmas:
        sigma_key = mp_str(sigma)
        for bound in selected_bounds:
            previous: dict[str, Any] | None = None
            for t in selected_t_values:
                current = rows_by_key[(sigma_key, mp_str(t), bound)]
                if previous is not None:
                    t_gap = mp.mpf(current["t"]) - mp.mpf(previous["t"])
                    transition_rows.append(
                        {
                            "sigma": sigma_key,
                            "prime_bound": bound,
                            "from_t": previous["t"],
                            "to_t": current["t"],
                            "t_gap": mp_str(t_gap),
                            "from_annotation": previous["t_axis_annotation"],
                            "to_annotation": current["t_axis_annotation"],
                            "direction": "increasing_t_at_fixed_sigma",
                            "euler_product_residual_ratio": _residual_ratio(
                                current["euler_product_residual_abs"],
                                previous["euler_product_residual_abs"],
                            ),
                            "prime_factor_log_derivative_residual_ratio": _residual_ratio(
                                current["prime_factor_log_derivative_residual_abs"],
                                previous["prime_factor_log_derivative_residual_abs"],
                            ),
                            "prime_power_cutoff_log_derivative_residual_ratio": _residual_ratio(
                                current["prime_power_cutoff_log_derivative_residual_abs"],
                                previous["prime_power_cutoff_log_derivative_residual_abs"],
                            ),
                        }
                    )
                previous = current

    return {
        "metadata": metadata(
            "t_axis_boundary_probe",
            dps,
            "finite_t_axis_boundary_probe_not_zero_line_evidence",
        ),
        "parameters": {
            "sigmas": [mp_str(value) for value in selected_sigmas],
            "t_values": [mp_str(value) for value in selected_t_values],
            "prime_bounds": selected_bounds,
            "reference_t_values": REFERENCE_T_VALUES,
            "formula": {
                "euler_product": "zeta(s) = product_p (1 - p^-s)^-1 for Re(s) > 1",
                "logarithmic_derivative": "-zeta'(s)/zeta(s) = sum_n Lambda(n) n^-s for Re(s) > 1",
            },
        },
        "summary": {
            "sigma_count": len(selected_sigmas),
            "t_value_count": len(selected_t_values),
            "max_prime_bound": max(selected_bounds),
            "row_count": len(rows),
            "transition_row_count": len(transition_rows),
            "landmark_row_count": sum(1 for row in rows if row["t_axis_annotation"] == "known_zero_ordinate_landmark"),
            "pole_axis_row_count": sum(1 for row in rows if row["t_axis_annotation"] == "pole_axis_reference"),
        },
        "rows": rows,
        "transition_rows": transition_rows,
    }


def _vertical_resonance_candidates(rows: list[dict[str, Any]], metrics: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["sigma"], int(row["prime_bound"])), []).append(row)
    for (sigma, bound), group_rows in groups.items():
        ordered = sorted(group_rows, key=lambda row: mp.mpf(row["t"]))
        if len(ordered) < 3:
            continue
        for metric in metrics:
            for index in range(1, len(ordered) - 1):
                previous = mp.mpf(ordered[index - 1][metric])
                current = mp.mpf(ordered[index][metric])
                following = mp.mpf(ordered[index + 1][metric])
                extremum_type = None
                if current < previous and current < following:
                    extremum_type = "local_minimum"
                elif current > previous and current > following:
                    extremum_type = "local_maximum"
                if extremum_type:
                    row = ordered[index]
                    candidates.append(
                        {
                            "sigma": sigma,
                            "prime_bound": bound,
                            "metric": metric,
                            "extremum_type": extremum_type,
                            "t": row["t"],
                            "value": row[metric],
                            "previous_t": ordered[index - 1]["t"],
                            "previous_value": mp_str(previous),
                            "next_t": ordered[index + 1]["t"],
                            "next_value": mp_str(following),
                            "t_axis_annotation": row["t_axis_annotation"],
                            "nearest_reference_label": row["nearest_reference_label"],
                            "nearest_reference_delta": row["nearest_reference_delta"],
                        }
                    )
    candidates.sort(key=lambda row: (row["sigma"], row["prime_bound"], row["metric"], mp.mpf(row["t"])))
    return candidates


def vertical_resonance_scan(
    sigmas: list[str | float] | None = None,
    t_min: str | float = "0",
    t_max: str | float = "30",
    step: str | float = "0.5",
    prime_bounds: list[int] | None = None,
    dps: int = 80,
    max_samples: int = 1000,
) -> dict[str, Any]:
    set_precision(dps)
    selected_sigmas = _selected_sigmas(sigmas or DEFAULT_T_AXIS_SIGMAS)
    t_values = list(mp_range(t_min, t_max, step))
    if not t_values:
        raise ValueError("at least one t sample is required")
    if t_values[0] < 0:
        raise ValueError("vertical resonance scans require nonnegative t values")
    if len(t_values) > max_samples:
        raise ValueError(f"sample count exceeds max_samples={max_samples}")
    selected_bounds = _selected_prime_bounds(prime_bounds)
    rows: list[dict[str, Any]] = []

    for sigma in selected_sigmas:
        for t in t_values:
            for bound in selected_bounds:
                rows.append(_vertical_sample_row(sigma, t, bound))

    metrics = [
        "zeta_abs",
        "euler_product_residual_abs",
        "prime_factor_log_derivative_residual_abs",
    ]
    candidate_rows = _vertical_resonance_candidates(rows, metrics)

    return {
        "metadata": metadata(
            "vertical_resonance_scan",
            dps,
            "finite_vertical_resonance_scan_not_zero_line_evidence",
        ),
        "parameters": {
            "sigmas": [mp_str(value) for value in selected_sigmas],
            "t_min": str(t_min),
            "t_max": str(t_max),
            "step": str(step),
            "prime_bounds": selected_bounds,
            "metrics": metrics,
            "reference_t_values": REFERENCE_T_VALUES,
            "formula": {
                "euler_product": "zeta(s) = product_p (1 - p^-s)^-1 for Re(s) > 1",
                "logarithmic_derivative": "-zeta'(s)/zeta(s) = sum_n Lambda(n) n^-s for Re(s) > 1",
            },
        },
        "summary": {
            "sigma_count": len(selected_sigmas),
            "t_sample_count": len(t_values),
            "max_prime_bound": max(selected_bounds),
            "row_count": len(rows),
            "candidate_count": len(candidate_rows),
            "local_minimum_count": sum(1 for row in candidate_rows if row["extremum_type"] == "local_minimum"),
            "local_maximum_count": sum(1 for row in candidate_rows if row["extremum_type"] == "local_maximum"),
        },
        "rows": rows,
        "candidate_rows": candidate_rows,
    }
