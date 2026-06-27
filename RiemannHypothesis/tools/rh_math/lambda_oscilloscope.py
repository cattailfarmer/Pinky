"""Finite Lambda log-Fourier oscilloscope probes."""

from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp

from .common import complex_record, metadata, mp_range, mp_str, set_precision
from .euler_product import REFERENCE_T_VALUES, negative_zeta_log_derivative


DEFAULT_SIGMAS = ["1.5", "0.5"]
DEFAULT_T_MIN = "0"
DEFAULT_T_MAX = "30"
DEFAULT_T_STEP = "1"
DEFAULT_PRIME_POWER_BOUND = 100
DEFAULT_SCAN_SIGMAS = ["1.5", "1.05"]
DEFAULT_SCAN_BOUNDS = [100, 500]
DEFAULT_REFERENCE_OFFSETS = ["-0.5", "0", "0.5"]
WINDOWS = {"hard", "fejer"}


def lambda_window_weight(prime_power: int, prime_power_bound: int, window: str = "hard") -> mp.mpf:
    if prime_power_bound < 2:
        raise ValueError("prime_power_bound must be at least 2")
    if prime_power < 1:
        raise ValueError("prime_power must be positive")
    if window == "hard":
        return mp.mpf("1")
    if window == "fejer":
        return max(mp.mpf("0"), mp.mpf("1") - (mp.mpf(prime_power) / mp.mpf(prime_power_bound + 1)))
    raise ValueError(f"unsupported window: {window}")


def _selected_sigmas(sigmas: list[str | float] | None) -> list[mp.mpf]:
    selected = [mp.mpf(str(value)) for value in (sigmas or DEFAULT_SIGMAS)]
    if not selected:
        raise ValueError("at least one sigma value is required")
    if any(value < 0 for value in selected):
        raise ValueError("sigma values must be nonnegative")
    return selected


def _selected_windows(windows: list[str] | None) -> list[str]:
    selected = windows or ["hard", "fejer"]
    if not selected:
        raise ValueError("at least one window is required")
    unknown = [window for window in selected if window not in WINDOWS]
    if unknown:
        raise ValueError(f"unsupported windows: {', '.join(unknown)}")
    return list(dict.fromkeys(selected))


def _selected_reference_labels(reference_labels: list[str] | None) -> list[str]:
    selected = reference_labels or list(REFERENCE_T_VALUES)
    if not selected:
        raise ValueError("at least one reference label is required")
    unknown = [label for label in selected if label not in REFERENCE_T_VALUES]
    if unknown:
        raise ValueError(f"unknown reference labels: {', '.join(unknown)}")
    return list(dict.fromkeys(selected))


def _selected_offsets(offsets: list[str | float] | None) -> list[mp.mpf]:
    selected = [mp.mpf(str(value)) for value in (offsets or DEFAULT_REFERENCE_OFFSETS)]
    if not selected:
        raise ValueError("at least one reference offset is required")
    return sorted(set(selected))


def _selected_prime_power_bounds(prime_power_bounds: list[int] | None) -> list[int]:
    selected = sorted(set(int(value) for value in (prime_power_bounds or DEFAULT_SCAN_BOUNDS)))
    if not selected or selected[0] < 2:
        raise ValueError("prime_power_bounds must be at least 2")
    return selected


def _selected_t_values(t_min: str | float, t_max: str | float, step: str | float, max_samples: int) -> list[mp.mpf]:
    values = list(mp_range(t_min, t_max, step))
    if not values:
        raise ValueError("at least one t sample is required")
    if values[0] < 0:
        raise ValueError("Lambda Oscilloscope traces require nonnegative t values")
    if len(values) > max_samples:
        raise ValueError(f"sample count exceeds max_samples={max_samples}")
    return values


def _nearest_reference(t: mp.mpf) -> dict[str, str]:
    nearest_label = None
    nearest_delta: mp.mpf | None = None
    for label, value in REFERENCE_T_VALUES.items():
        delta = abs(t - mp.mpf(value))
        if nearest_delta is None or delta < nearest_delta:
            nearest_label = label
            nearest_delta = delta
    return {
        "nearest_reference_label": nearest_label or "none",
        "nearest_reference_delta": mp_str(nearest_delta if nearest_delta is not None else 0),
    }


def _prime_power_terms(prime_power_bound: int, window: str) -> list[dict[str, Any]]:
    if prime_power_bound < 2:
        raise ValueError("prime_power_bound must be at least 2")
    if window not in WINDOWS:
        raise ValueError(f"unsupported window: {window}")
    rows: list[dict[str, Any]] = []
    for prime in sp.primerange(2, prime_power_bound + 1):
        p = int(prime)
        exponent = 1
        power = p
        log_prime = mp.log(p)
        while power <= prime_power_bound:
            rows.append(
                {
                    "prime": p,
                    "exponent": exponent,
                    "prime_power": power,
                    "von_mangoldt_weight": log_prime,
                    "window_weight": lambda_window_weight(power, prime_power_bound, window),
                }
            )
            exponent += 1
            power *= p
    rows.sort(key=lambda row: (int(row["prime_power"]), int(row["prime"]), int(row["exponent"])))
    return rows


def _term_contribution(term: dict[str, Any], sigma: mp.mpf, t: mp.mpf) -> tuple[mp.mpf, mp.mpf, mp.mpc]:
    prime_power = int(term["prime_power"])
    lambda_weight = mp.mpf(term["von_mangoldt_weight"])
    window_weight = mp.mpf(term["window_weight"])
    amplitude = lambda_weight * window_weight * mp.power(prime_power, -sigma)
    phase = -t * mp.log(prime_power)
    contribution = amplitude * mp.e ** (mp.j * phase)
    return amplitude, phase, contribution


def _safe_ratio(numerator: mp.mpf, denominator: mp.mpf) -> str:
    if denominator == 0:
        return "0"
    return mp_str(numerator / denominator)


def _contribution_layer_record(
    layer_id: str,
    terms: list[dict[str, Any]],
    total_abs: mp.mpf,
    total_amplitude: mp.mpf,
) -> dict[str, Any]:
    vector = mp.fsum([term["contribution"] for term in terms])
    amplitude_sum = mp.fsum([term["amplitude"] for term in terms])
    return {
        "layer_id": layer_id,
        "term_count": len(terms),
        "amplitude_sum": mp_str(amplitude_sum),
        "amplitude_share_of_total_amplitude": _safe_ratio(amplitude_sum, total_amplitude),
        "vector": complex_record(vector),
        "vector_abs_share_of_total_abs": _safe_ratio(abs(vector), total_abs),
    }


def _top_contribution_rows(
    terms: list[dict[str, Any]],
    key: str,
    count: int,
    reverse: bool = True,
) -> list[dict[str, Any]]:
    ordered = sorted(terms, key=lambda term: term[key], reverse=reverse)[:count]
    rows: list[dict[str, Any]] = []
    for rank, term in enumerate(ordered, start=1):
        rows.append(
            {
                "rank": rank,
                "prime": int(term["prime"]),
                "exponent": int(term["exponent"]),
                "prime_power": int(term["prime_power"]),
                "amplitude": mp_str(term["amplitude"]),
                "phase": mp_str(term["phase"]),
                "projection_onto_total_direction": mp_str(term["projection"]),
                "contribution": complex_record(term["contribution"]),
            }
        )
    return rows


def lambda_oscilloscope_probe(
    sigmas: list[str | float] | None = None,
    t_min: str | float = DEFAULT_T_MIN,
    t_max: str | float = DEFAULT_T_MAX,
    step: str | float = DEFAULT_T_STEP,
    prime_power_bound: int = DEFAULT_PRIME_POWER_BOUND,
    window: str = "hard",
    dps: int = 80,
    include_terms: bool = False,
    compare_exact: bool = True,
    max_samples: int = 1000,
) -> dict[str, Any]:
    set_precision(dps)
    selected_sigmas = _selected_sigmas(sigmas)
    selected_t_values = _selected_t_values(t_min, t_max, step, max_samples)
    terms = _prime_power_terms(prime_power_bound, window)
    rows: list[dict[str, Any]] = []
    term_rows: list[dict[str, Any]] = []

    for sigma in selected_sigmas:
        for t in selected_t_values:
            total = mp.mpc("0")
            for term in terms:
                amplitude, phase, contribution = _term_contribution(term, sigma, t)
                total += contribution
                if include_terms:
                    term_rows.append(
                        {
                            "sigma": mp_str(sigma),
                            "t": mp_str(t),
                            "prime_power_bound": prime_power_bound,
                            "window": window,
                            "prime": int(term["prime"]),
                            "exponent": int(term["exponent"]),
                            "prime_power": int(term["prime_power"]),
                            "von_mangoldt_weight": mp_str(term["von_mangoldt_weight"]),
                            "window_weight": mp_str(term["window_weight"]),
                            "amplitude": mp_str(amplitude),
                            "phase": mp_str(phase),
                            "contribution": complex_record(contribution),
                        }
                    )

            row: dict[str, Any] = {
                "sigma": mp_str(sigma),
                "t": mp_str(t),
                "prime_power_bound": prime_power_bound,
                "window": window,
                "term_count": len(terms),
                "lambda_oscilloscope_trace": complex_record(total),
                "comparison_status": "not_compared_sigma_not_greater_than_one",
            }
            if compare_exact and sigma > 1:
                exact = negative_zeta_log_derivative(mp.mpc(sigma, t))
                residual = total - exact
                row.update(
                    {
                        "comparison_status": "compared_to_negative_zeta_prime_over_zeta",
                        "negative_zeta_prime_over_zeta": complex_record(exact),
                        "finite_trace_minus_exact": complex_record(residual),
                        "finite_trace_residual_abs": mp_str(abs(residual)),
                    }
                )
            elif not compare_exact:
                row["comparison_status"] = "comparison_disabled"
            rows.append(row)

    return {
        "metadata": metadata(
            "lambda_oscilloscope_probe",
            dps,
            "finite_lambda_oscilloscope_trace_not_rh_evidence",
        ),
        "parameters": {
            "sigmas": [mp_str(value) for value in selected_sigmas],
            "t_min": str(t_min),
            "t_max": str(t_max),
            "step": str(step),
            "prime_power_bound": prime_power_bound,
            "window": window,
            "include_terms": include_terms,
            "compare_exact": compare_exact,
            "formula": {
                "finite_trace": "sum_{q=p^k<=N} Lambda(q) W_N(q) q^-sigma exp(-i t log(q))",
                "half_plane_identity": "sum_n Lambda(n)n^-s = -zeta'(s)/zeta(s) for Re(s) > 1",
            },
        },
        "summary": {
            "sigma_count": len(selected_sigmas),
            "t_sample_count": len(selected_t_values),
            "row_count": len(rows),
            "term_count_per_trace": len(terms),
            "max_prime_power_exponent": max((int(term["exponent"]) for term in terms), default=0),
            "comparison_row_count": sum(
                1 for row in rows if row["comparison_status"] == "compared_to_negative_zeta_prime_over_zeta"
            ),
        },
        "rows": rows,
        "term_rows": term_rows,
    }


def _lambda_candidate_rows(rows: list[dict[str, Any]], metrics: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["sigma"], row["window"], int(row["prime_power_bound"])), []).append(row)
    for (sigma, window, bound), group_rows in groups.items():
        ordered = sorted(group_rows, key=lambda row: mp.mpf(row["t"]))
        if len(ordered) < 3:
            continue
        for metric in metrics:
            metric_rows = [row for row in ordered if row.get(metric) is not None]
            if len(metric_rows) < 3:
                continue
            for index in range(1, len(metric_rows) - 1):
                previous = mp.mpf(metric_rows[index - 1][metric])
                current = mp.mpf(metric_rows[index][metric])
                following = mp.mpf(metric_rows[index + 1][metric])
                extremum_type = None
                if current < previous and current < following:
                    extremum_type = "local_minimum"
                elif current > previous and current > following:
                    extremum_type = "local_maximum"
                if extremum_type:
                    row = metric_rows[index]
                    t = mp.mpf(row["t"])
                    candidates.append(
                        {
                            "sigma": sigma,
                            "window": window,
                            "prime_power_bound": bound,
                            "metric": metric,
                            "extremum_type": extremum_type,
                            "t": row["t"],
                            "value": row[metric],
                            "previous_t": metric_rows[index - 1]["t"],
                            "previous_value": mp_str(previous),
                            "next_t": metric_rows[index + 1]["t"],
                            "next_value": mp_str(following),
                            **_nearest_reference(t),
                        }
                    )
    candidates.sort(
        key=lambda row: (
            row["sigma"],
            row["window"],
            int(row["prime_power_bound"]),
            row["metric"],
            row["extremum_type"],
            mp.mpf(row["t"]),
        )
    )
    return candidates


def _nearest_candidate(candidate: dict[str, Any], options: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not options:
        return None
    t = mp.mpf(candidate["t"])
    return min(options, key=lambda row: abs(mp.mpf(row["t"]) - t))


def _cutoff_stability_rows(candidates: list[dict[str, Any]], tolerance: mp.mpf) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    groups: dict[tuple[str, str, str, str], dict[int, list[dict[str, Any]]]] = {}
    for candidate in candidates:
        key = (candidate["sigma"], candidate["window"], candidate["metric"], candidate["extremum_type"])
        groups.setdefault(key, {}).setdefault(int(candidate["prime_power_bound"]), []).append(candidate)
    for (sigma, window, metric, extremum_type), by_bound in groups.items():
        bounds = sorted(by_bound)
        for index in range(len(bounds) - 1):
            from_bound = bounds[index]
            to_bound = bounds[index + 1]
            for candidate in by_bound[from_bound]:
                match = _nearest_candidate(candidate, by_bound[to_bound])
                if match is None:
                    continue
                delta = abs(mp.mpf(candidate["t"]) - mp.mpf(match["t"]))
                rows.append(
                    {
                        "sigma": sigma,
                        "window": window,
                        "metric": metric,
                        "extremum_type": extremum_type,
                        "from_bound": from_bound,
                        "to_bound": to_bound,
                        "from_t": candidate["t"],
                        "to_t": match["t"],
                        "t_delta": mp_str(delta),
                        "stable_within_tolerance": delta <= tolerance,
                        "tolerance": mp_str(tolerance),
                    }
                )
    return rows


def _cross_window_rows(candidates: list[dict[str, Any]], tolerance: mp.mpf) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    groups: dict[tuple[str, int, str, str], dict[str, list[dict[str, Any]]]] = {}
    for candidate in candidates:
        key = (
            candidate["sigma"],
            int(candidate["prime_power_bound"]),
            candidate["metric"],
            candidate["extremum_type"],
        )
        groups.setdefault(key, {}).setdefault(candidate["window"], []).append(candidate)
    for (sigma, bound, metric, extremum_type), by_window in groups.items():
        hard_candidates = by_window.get("hard", [])
        fejer_candidates = by_window.get("fejer", [])
        for candidate in hard_candidates:
            match = _nearest_candidate(candidate, fejer_candidates)
            if match is None:
                continue
            delta = abs(mp.mpf(candidate["t"]) - mp.mpf(match["t"]))
            rows.append(
                {
                    "sigma": sigma,
                    "prime_power_bound": bound,
                    "metric": metric,
                    "extremum_type": extremum_type,
                    "hard_t": candidate["t"],
                    "fejer_t": match["t"],
                    "t_delta": mp_str(delta),
                    "stable_within_tolerance": delta <= tolerance,
                    "tolerance": mp_str(tolerance),
                }
            )
    return rows


def lambda_window_cutoff_scan(
    sigmas: list[str | float] | None = None,
    t_min: str | float = "0",
    t_max: str | float = "30",
    step: str | float = "0.5",
    prime_power_bounds: list[int] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
    max_samples: int = 1000,
    stability_tolerance: str | float | None = None,
) -> dict[str, Any]:
    set_precision(dps)
    selected_sigmas = _selected_sigmas(sigmas or DEFAULT_SCAN_SIGMAS)
    selected_t_values = _selected_t_values(t_min, t_max, step, max_samples)
    selected_bounds = _selected_prime_power_bounds(prime_power_bounds)
    selected_windows = _selected_windows(windows)
    tolerance = mp.mpf(str(stability_tolerance)) if stability_tolerance is not None else mp.mpf(str(step))
    if tolerance < 0:
        raise ValueError("stability_tolerance must be nonnegative")

    rows: list[dict[str, Any]] = []
    for window in selected_windows:
        for bound in selected_bounds:
            payload = lambda_oscilloscope_probe(
                sigmas=[mp_str(sigma) for sigma in selected_sigmas],
                t_min=t_min,
                t_max=t_max,
                step=step,
                prime_power_bound=bound,
                window=window,
                dps=dps,
                include_terms=False,
                compare_exact=True,
                max_samples=max_samples,
            )
            for row in payload["rows"]:
                rows.append(
                    {
                        "sigma": row["sigma"],
                        "t": row["t"],
                        "window": window,
                        "prime_power_bound": bound,
                        "term_count": row["term_count"],
                        "comparison_status": row["comparison_status"],
                        "lambda_trace_abs": row["lambda_oscilloscope_trace"]["abs"],
                        "finite_trace_residual_abs": row.get("finite_trace_residual_abs"),
                    }
                )

    metrics = ["lambda_trace_abs", "finite_trace_residual_abs"]
    candidate_rows = _lambda_candidate_rows(rows, metrics)
    cutoff_rows = _cutoff_stability_rows(candidate_rows, tolerance)
    window_rows = _cross_window_rows(candidate_rows, tolerance)

    return {
        "metadata": metadata(
            "lambda_window_cutoff_scan",
            dps,
            "finite_lambda_window_cutoff_scan_not_rh_evidence",
        ),
        "parameters": {
            "sigmas": [mp_str(value) for value in selected_sigmas],
            "t_min": str(t_min),
            "t_max": str(t_max),
            "step": str(step),
            "prime_power_bounds": selected_bounds,
            "windows": selected_windows,
            "stability_tolerance": mp_str(tolerance),
            "metrics": metrics,
            "reference_t_values": REFERENCE_T_VALUES,
            "formula": {
                "finite_trace": "sum_{q=p^k<=N} Lambda(q) W_N(q) q^-sigma exp(-i t log(q))",
                "half_plane_identity": "sum_n Lambda(n)n^-s = -zeta'(s)/zeta(s) for Re(s) > 1",
            },
        },
        "summary": {
            "sigma_count": len(selected_sigmas),
            "t_sample_count": len(selected_t_values),
            "window_count": len(selected_windows),
            "bound_count": len(selected_bounds),
            "row_count": len(rows),
            "candidate_count": len(candidate_rows),
            "cutoff_stability_row_count": len(cutoff_rows),
            "cutoff_stable_count": sum(1 for row in cutoff_rows if row["stable_within_tolerance"]),
            "cross_window_row_count": len(window_rows),
            "cross_window_stable_count": sum(1 for row in window_rows if row["stable_within_tolerance"]),
        },
        "rows": rows,
        "candidate_rows": candidate_rows,
        "cutoff_stability_rows": cutoff_rows,
        "cross_window_rows": window_rows,
    }


def lambda_phasor_reference_contribution(
    sigmas: list[str | float] | None = None,
    reference_labels: list[str] | None = None,
    offsets: list[str | float] | None = None,
    prime_power_bounds: list[int] | None = None,
    windows: list[str] | None = None,
    dps: int = 80,
    top_terms: int = 8,
) -> dict[str, Any]:
    set_precision(dps)
    selected_sigmas = _selected_sigmas(sigmas or DEFAULT_SCAN_SIGMAS)
    selected_labels = _selected_reference_labels(reference_labels)
    selected_offsets = _selected_offsets(offsets)
    selected_bounds = _selected_prime_power_bounds(prime_power_bounds)
    selected_windows = _selected_windows(windows)
    if top_terms < 1:
        raise ValueError("top_terms must be at least 1")

    rows: list[dict[str, Any]] = []
    layer_rows: list[dict[str, Any]] = []
    exponent_layer_rows: list[dict[str, Any]] = []
    top_amplitude_rows: list[dict[str, Any]] = []
    top_projection_rows: list[dict[str, Any]] = []
    top_cancellation_rows: list[dict[str, Any]] = []

    for window in selected_windows:
        for bound in selected_bounds:
            base_terms = _prime_power_terms(bound, window)
            low_q_threshold = mp.sqrt(bound)
            for sigma in selected_sigmas:
                for label in selected_labels:
                    reference_t = mp.mpf(REFERENCE_T_VALUES[label])
                    for offset in selected_offsets:
                        sampled_t = reference_t + offset
                        if sampled_t < 0:
                            raise ValueError("reference offset produces negative sampled t")

                        terms: list[dict[str, Any]] = []
                        total = mp.mpc("0")
                        total_amplitude = mp.mpf("0")
                        for term in base_terms:
                            amplitude, phase, contribution = _term_contribution(term, sigma, sampled_t)
                            total += contribution
                            total_amplitude += amplitude
                            terms.append(
                                {
                                    "prime": int(term["prime"]),
                                    "exponent": int(term["exponent"]),
                                    "prime_power": int(term["prime_power"]),
                                    "amplitude": amplitude,
                                    "phase": phase,
                                    "contribution": contribution,
                                }
                            )

                        total_abs = abs(total)
                        unit = total / total_abs if total_abs != 0 else mp.mpc("0")
                        for term in terms:
                            term["projection"] = mp.re(term["contribution"] * mp.conj(unit))

                        row_index = len(rows)
                        row: dict[str, Any] = {
                            "row_index": row_index,
                            "sigma": mp_str(sigma),
                            "reference_label": label,
                            "reference_t": mp_str(reference_t),
                            "offset": mp_str(offset),
                            "sampled_t": mp_str(sampled_t),
                            "window": window,
                            "prime_power_bound": bound,
                            "low_q_threshold": mp_str(low_q_threshold),
                            "term_count": len(terms),
                            "total_amplitude": mp_str(total_amplitude),
                            "lambda_phasor_trace": complex_record(total),
                            "comparison_status": "not_compared_sigma_not_greater_than_one",
                        }
                        if sigma > 1:
                            exact = negative_zeta_log_derivative(mp.mpc(sigma, sampled_t))
                            residual = total - exact
                            row.update(
                                {
                                    "comparison_status": "compared_to_negative_zeta_prime_over_zeta",
                                    "negative_zeta_prime_over_zeta": complex_record(exact),
                                    "finite_trace_minus_exact": complex_record(residual),
                                    "finite_trace_residual_abs": mp_str(abs(residual)),
                                }
                            )
                        rows.append(row)

                        layer_sets = {
                            "prime_terms": [term for term in terms if int(term["exponent"]) == 1],
                            "higher_prime_power_terms": [term for term in terms if int(term["exponent"]) > 1],
                            "low_q_terms": [term for term in terms if int(term["prime_power"]) <= low_q_threshold],
                            "high_q_terms": [term for term in terms if int(term["prime_power"]) > low_q_threshold],
                        }
                        for layer_id, layer_terms in layer_sets.items():
                            layer_rows.append(
                                {
                                    "row_index": row_index,
                                    "sigma": row["sigma"],
                                    "reference_label": label,
                                    "offset": row["offset"],
                                    "sampled_t": row["sampled_t"],
                                    "window": window,
                                    "prime_power_bound": bound,
                                    **_contribution_layer_record(
                                        layer_id,
                                        layer_terms,
                                        total_abs,
                                        total_amplitude,
                                    ),
                                }
                            )

                        exponent_values = sorted({int(term["exponent"]) for term in terms})
                        for exponent in exponent_values:
                            exponent_terms = [term for term in terms if int(term["exponent"]) == exponent]
                            exponent_layer_rows.append(
                                {
                                    "row_index": row_index,
                                    "sigma": row["sigma"],
                                    "reference_label": label,
                                    "offset": row["offset"],
                                    "sampled_t": row["sampled_t"],
                                    "window": window,
                                    "prime_power_bound": bound,
                                    "exponent": exponent,
                                    **_contribution_layer_record(
                                        f"exponent_{exponent}",
                                        exponent_terms,
                                        total_abs,
                                        total_amplitude,
                                    ),
                                }
                            )

                        for top_row in _top_contribution_rows(terms, "amplitude", top_terms):
                            top_amplitude_rows.append(
                                {
                                    "row_index": row_index,
                                    "sigma": row["sigma"],
                                    "reference_label": label,
                                    "offset": row["offset"],
                                    "sampled_t": row["sampled_t"],
                                    "window": window,
                                    "prime_power_bound": bound,
                                    **top_row,
                                }
                            )
                        for top_row in _top_contribution_rows(terms, "projection", top_terms):
                            top_projection_rows.append(
                                {
                                    "row_index": row_index,
                                    "sigma": row["sigma"],
                                    "reference_label": label,
                                    "offset": row["offset"],
                                    "sampled_t": row["sampled_t"],
                                    "window": window,
                                    "prime_power_bound": bound,
                                    **top_row,
                                }
                            )
                        for top_row in _top_contribution_rows(terms, "projection", top_terms, reverse=False):
                            top_cancellation_rows.append(
                                {
                                    "row_index": row_index,
                                    "sigma": row["sigma"],
                                    "reference_label": label,
                                    "offset": row["offset"],
                                    "sampled_t": row["sampled_t"],
                                    "window": window,
                                    "prime_power_bound": bound,
                                    **top_row,
                                }
                            )

    higher_layer_rows = [row for row in layer_rows if row["layer_id"] == "higher_prime_power_terms"]
    prime_layer_rows = [row for row in layer_rows if row["layer_id"] == "prime_terms"]
    higher_share_values = [mp.mpf(row["amplitude_share_of_total_amplitude"]) for row in higher_layer_rows]
    prime_vector_share_values = [mp.mpf(row["vector_abs_share_of_total_abs"]) for row in prime_layer_rows]

    return {
        "metadata": metadata(
            "lambda_phasor_reference_contribution",
            dps,
            "finite_lambda_phasor_reference_contribution_not_rh_evidence",
        ),
        "parameters": {
            "sigmas": [mp_str(value) for value in selected_sigmas],
            "reference_labels": selected_labels,
            "reference_t_values": {label: REFERENCE_T_VALUES[label] for label in selected_labels},
            "offsets": [mp_str(value) for value in selected_offsets],
            "prime_power_bounds": selected_bounds,
            "windows": selected_windows,
            "top_terms": top_terms,
            "formula": {
                "finite_trace": "sum_{q=p^k<=N} Lambda(q) W_N(q) q^-sigma exp(-i t log(q))",
                "term_contribution": "Lambda(q) W_N(q) q^-sigma exp(-i t log(q))",
                "half_plane_identity": "sum_n Lambda(n)n^-s = -zeta'(s)/zeta(s) for Re(s) > 1",
            },
        },
        "summary": {
            "row_count": len(rows),
            "layer_row_count": len(layer_rows),
            "exponent_layer_row_count": len(exponent_layer_rows),
            "top_amplitude_row_count": len(top_amplitude_rows),
            "top_projection_row_count": len(top_projection_rows),
            "top_cancellation_row_count": len(top_cancellation_rows),
            "comparison_row_count": sum(
                1 for row in rows if row["comparison_status"] == "compared_to_negative_zeta_prime_over_zeta"
            ),
            "higher_prime_power_amplitude_share_min": mp_str(min(higher_share_values, default=mp.mpf("0"))),
            "higher_prime_power_amplitude_share_max": mp_str(max(higher_share_values, default=mp.mpf("0"))),
            "prime_vector_abs_share_min": mp_str(min(prime_vector_share_values, default=mp.mpf("0"))),
            "prime_vector_abs_share_max": mp_str(max(prime_vector_share_values, default=mp.mpf("0"))),
        },
        "rows": rows,
        "layer_rows": layer_rows,
        "exponent_layer_rows": exponent_layer_rows,
        "top_amplitude_rows": top_amplitude_rows,
        "top_projection_rows": top_projection_rows,
        "top_cancellation_rows": top_cancellation_rows,
    }
