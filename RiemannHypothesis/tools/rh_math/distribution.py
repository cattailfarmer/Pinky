"""Whole-prime distribution probes for special-prime family inquiry."""

from __future__ import annotations

from bisect import bisect_right
from typing import Any

import mpmath as mp
import sympy as sp

from .common import metadata, mp_str, set_precision
from .prime_families import row_matches_family, special_prime_family_names, special_prime_row
from .primes import generated_sample_points, riemann_r


def _prefix_log_sums(values: list[int]) -> list[mp.mpf]:
    total = mp.mpf("0")
    cumulative: list[mp.mpf] = []
    for value in values:
        total += mp.log(value)
        cumulative.append(total)
    return cumulative


def _prefix_sum_at(values: list[int], cumulative: list[mp.mpf], x: int) -> mp.mpf:
    index = bisect_right(values, x)
    if index == 0:
        return mp.mpf("0")
    return cumulative[index - 1]


def _interval_sum(values: list[int], cumulative: list[mp.mpf], lower: int, upper: int) -> mp.mpf:
    return _prefix_sum_at(values, cumulative, upper) - _prefix_sum_at(values, cumulative, lower)


def _interval_count(values: list[int], lower: int, upper: int) -> int:
    return bisect_right(values, upper) - bisect_right(values, lower)


def chebyshev_theta(x: int) -> mp.mpf:
    if x < 2:
        return mp.mpf("0")
    return mp.fsum(mp.log(p) for p in sp.primerange(2, x + 1))


def chebyshev_psi(x: int) -> mp.mpf:
    if x < 2:
        return mp.mpf("0")
    total = mp.mpf("0")
    for prime in sp.primerange(2, x + 1):
        power = prime
        log_prime = mp.log(prime)
        while power <= x:
            total += log_prime
            power *= prime
    return total


def _prime_power_events(max_x: int) -> list[dict[str, Any]]:
    if max_x < 2:
        return []
    events: list[dict[str, Any]] = []
    for prime in sp.primerange(2, max_x + 1):
        exponent = 1
        power = prime
        log_prime = mp.log(prime)
        while power <= max_x:
            events.append(
                {
                    "prime": int(prime),
                    "exponent": exponent,
                    "prime_power": int(power),
                    "log_prime": log_prime,
                }
            )
            exponent += 1
            power *= prime
    events.sort(key=lambda row: (row["prime_power"], row["prime"], row["exponent"]))
    return events


def _event_layer_sums(events: list[dict[str, Any]], lower: int, upper: int) -> dict[int, mp.mpf]:
    sums: dict[int, mp.mpf] = {}
    for event in events:
        prime_power = int(event["prime_power"])
        if lower < prime_power <= upper:
            exponent = int(event["exponent"])
            sums[exponent] = sums.get(exponent, mp.mpf("0")) + mp.mpf(event["log_prime"])
    return sums


def _layer_rows(layer_sums: dict[int, mp.mpf], psi_total: mp.mpf) -> list[dict[str, Any]]:
    rows = []
    for exponent in sorted(layer_sums):
        layer_sum = layer_sums[exponent]
        layer_name = "theta_prime_layer" if exponent == 1 else f"prime_power_layer_{exponent}"
        rows.append(
            {
                "exponent": exponent,
                "layer": layer_name,
                "contribution": mp_str(layer_sum),
                "share_of_psi": mp_str(layer_sum / psi_total if psi_total else 0),
            }
        )
    return rows


def _selected_sample_points(points: list[int] | None, max_x: int | None, count: int) -> list[int]:
    if points:
        sample_points = sorted(set(int(x) for x in points))
    else:
        sample_points = generated_sample_points(int(max_x or 100000), int(count))
    if not sample_points:
        raise ValueError("at least one sample point is required")
    if sample_points[0] < 2:
        raise ValueError("sample points must be at least 2")
    return sample_points


def _interval_endpoints(points: list[int] | None, max_x: int | None, count: int) -> list[tuple[int, int]]:
    sample_points = _selected_sample_points(points, max_x, count)
    lower_bounds = [0] + sample_points[:-1]
    return list(zip(lower_bounds, sample_points))


def _selected_families(families: list[str] | None) -> list[str]:
    allowed = set(special_prime_family_names())
    selected = families or special_prime_family_names()
    unsupported = sorted(set(selected) - allowed)
    if unsupported:
        raise ValueError(f"unsupported families: {', '.join(unsupported)}")
    return selected


def _li_interval(lower: int, upper: int) -> mp.mpf:
    lower_anchor = max(2, lower)
    if upper <= 2:
        return mp.mpf("0")
    return mp.li(upper) - mp.li(lower_anchor)


def _odd_candidates(lower: int, upper: int) -> list[int]:
    start = max(3, lower + 1)
    if start % 2 == 0:
        start += 1
    return list(range(start, upper + 1, 2))


def _sieve_survivor_row(lower: int, upper: int, max_examples: int) -> dict[str, Any]:
    candidates = _odd_candidates(lower, upper)
    witness_bound = int(mp.floor(mp.sqrt(upper))) if upper >= 2 else 0
    witness_primes = list(sp.primerange(3, witness_bound + 1))
    survivors: list[int] = []
    covered: list[int] = []
    for candidate in candidates:
        candidate_bound = int(mp.floor(mp.sqrt(candidate)))
        is_covered = False
        for prime in witness_primes:
            if prime > candidate_bound:
                break
            if candidate != prime and candidate % prime == 0:
                is_covered = True
                break
        if is_covered:
            covered.append(candidate)
        else:
            survivors.append(candidate)
    return {
        "witness_prime_bound": witness_bound,
        "witness_prime_count": len(witness_primes),
        "odd_candidate_count": len(candidates),
        "composite_covered_candidate_count": len(covered),
        "survivor_candidate_count": len(survivors),
        "survivor_share_of_odd_candidates": mp_str(mp.mpf(len(survivors)) / len(candidates) if candidates else 0),
        "survivor_examples": survivors[:max_examples],
        "covered_examples": covered[:max_examples],
    }


def _global_row(x: int, prime_values: list[int], prime_log_sums: list[mp.mpf], terms: int) -> dict[str, Any]:
    prime_pi = bisect_right(prime_values, x)
    li_x = mp.li(x)
    r_x = riemann_r(x, terms=terms)
    theta_x = _prefix_sum_at(prime_values, prime_log_sums, x)
    psi_x = chebyshev_psi(x)
    scale = mp.sqrt(x) * mp.log(x)
    theta_error = theta_x - x
    psi_error = psi_x - x
    return {
        "x": x,
        "prime_pi": prime_pi,
        "li_x": mp_str(li_x),
        "li_minus_pi": mp_str(li_x - prime_pi),
        "riemann_r_terms": terms,
        "riemann_r": mp_str(r_x),
        "riemann_r_minus_pi": mp_str(r_x - prime_pi),
        "theta_x": mp_str(theta_x),
        "theta_minus_x": mp_str(theta_error),
        "psi_x": mp_str(psi_x),
        "psi_minus_x": mp_str(psi_error),
        "sqrt_x_log_x_scale": mp_str(scale),
        "theta_error_over_sqrt_x_log_x": mp_str(theta_error / scale),
        "psi_error_over_sqrt_x_log_x": mp_str(psi_error / scale),
    }


def prime_family_distribution(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 6,
    families: list[str] | None = None,
    max_fermat_n: int = 8,
    terms: int = 20,
    dps: int = 80,
    include_members: bool = False,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    selected_families = _selected_families(families)
    max_sample = max(sample_points)
    prime_values = list(sp.primerange(2, max_sample + 1))
    prime_log_sums = _prefix_log_sums(prime_values)
    profile_rows = [special_prime_row(p, max_fermat_n=max_fermat_n) for p in prime_values]

    global_rows = [_global_row(x, prime_values, prime_log_sums, terms) for x in sample_points]
    globals_by_x = {row["x"]: row for row in global_rows}
    family_members: dict[str, list[int]] = {
        family: [row["p"] for row in profile_rows if row_matches_family(row, family)]
        for family in selected_families
    }
    family_log_sums = {family: _prefix_log_sums(values) for family, values in family_members.items()}

    family_rows: list[dict[str, Any]] = []
    for x in sample_points:
        global_row = globals_by_x[x]
        prime_pi = int(global_row["prime_pi"])
        theta_x = mp.mpf(global_row["theta_x"])
        for family in selected_families:
            members = family_members[family]
            index = bisect_right(members, x)
            family_theta = _prefix_sum_at(members, family_log_sums[family], x)
            row: dict[str, Any] = {
                "x": x,
                "family": family,
                "family_count": index,
                "prime_pi": prime_pi,
                "family_density_among_primes": mp_str(mp.mpf(index) / prime_pi if prime_pi else 0),
                "family_theta": mp_str(family_theta),
                "theta_x": mp_str(theta_x),
                "family_theta_share": mp_str(family_theta / theta_x if theta_x else 0),
                "last_family_member": members[index - 1] if index else None,
                "global_theta_minus_x": global_row["theta_minus_x"],
                "global_psi_minus_x": global_row["psi_minus_x"],
            }
            if include_members:
                row["members_up_to_x"] = members[:index]
            family_rows.append(row)

    return {
        "metadata": metadata("prime_family_distribution", dps, "finite_family_distribution_probe_not_rh_evidence"),
        "parameters": {
            "points": sample_points,
            "families": selected_families,
            "max_fermat_n": max_fermat_n,
            "riemann_r_terms": terms,
            "include_members": include_members,
        },
        "global_rows": global_rows,
        "rows": family_rows,
    }


def prime_family_interval_distribution(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 6,
    families: list[str] | None = None,
    max_fermat_n: int = 8,
    dps: int = 80,
    include_members: bool = False,
) -> dict[str, Any]:
    set_precision(dps)
    intervals = _interval_endpoints(points, max_x, count)
    selected_families = _selected_families(families)
    max_sample = max(upper for _, upper in intervals)
    prime_values = list(sp.primerange(2, max_sample + 1))
    prime_log_sums = _prefix_log_sums(prime_values)
    profile_rows = [special_prime_row(p, max_fermat_n=max_fermat_n) for p in prime_values]
    psi_cache = {0: mp.mpf("0")}
    for lower, upper in intervals:
        psi_cache.setdefault(lower, chebyshev_psi(lower))
        psi_cache.setdefault(upper, chebyshev_psi(upper))

    family_members: dict[str, list[int]] = {
        family: [row["p"] for row in profile_rows if row_matches_family(row, family)]
        for family in selected_families
    }
    family_log_sums = {family: _prefix_log_sums(values) for family, values in family_members.items()}

    global_rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    for lower, upper in intervals:
        interval_length = upper - lower
        prime_count = _interval_count(prime_values, lower, upper)
        theta_increment = _interval_sum(prime_values, prime_log_sums, lower, upper)
        psi_increment = psi_cache[upper] - psi_cache[lower]
        theta_error_move = theta_increment - interval_length
        psi_error_move = psi_increment - interval_length
        theta_sign = "positive" if theta_error_move > 0 else "negative" if theta_error_move < 0 else "zero"
        psi_sign = "positive" if psi_error_move > 0 else "negative" if psi_error_move < 0 else "zero"
        global_row = {
            "lower": lower,
            "upper": upper,
            "interval_length": interval_length,
            "prime_count_increment": prime_count,
            "theta_increment": mp_str(theta_increment),
            "theta_increment_minus_length": mp_str(theta_error_move),
            "theta_error_move_sign": theta_sign,
            "psi_increment": mp_str(psi_increment),
            "psi_increment_minus_length": mp_str(psi_error_move),
            "psi_error_move_sign": psi_sign,
        }
        global_rows.append(global_row)
        for family in selected_families:
            members = family_members[family]
            count_increment = _interval_count(members, lower, upper)
            family_theta_increment = _interval_sum(members, family_log_sums[family], lower, upper)
            row: dict[str, Any] = {
                "lower": lower,
                "upper": upper,
                "family": family,
                "family_count_increment": count_increment,
                "prime_count_increment": prime_count,
                "family_count_share_of_interval_primes": mp_str(mp.mpf(count_increment) / prime_count if prime_count else 0),
                "family_theta_increment": mp_str(family_theta_increment),
                "theta_increment": mp_str(theta_increment),
                "family_theta_share_of_interval_theta": mp_str(
                    family_theta_increment / theta_increment if theta_increment else 0
                ),
                "theta_error_move_sign": theta_sign,
                "psi_error_move_sign": psi_sign,
            }
            if include_members:
                start = bisect_right(members, lower)
                stop = bisect_right(members, upper)
                row["members_in_interval"] = members[start:stop]
            family_rows.append(row)

    return {
        "metadata": metadata("prime_family_intervals", dps, "finite_family_interval_probe_not_rh_evidence"),
        "parameters": {
            "intervals": [{"lower": lower, "upper": upper} for lower, upper in intervals],
            "families": selected_families,
            "max_fermat_n": max_fermat_n,
            "include_members": include_members,
        },
        "global_rows": global_rows,
        "rows": family_rows,
    }


def prime_power_decomposition(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 6,
    dps: int = 80,
    include_events: bool = False,
) -> dict[str, Any]:
    set_precision(dps)
    intervals = _interval_endpoints(points, max_x, count)
    sample_points = [upper for _, upper in intervals]
    max_sample = max(sample_points)
    events = _prime_power_events(max_sample)

    cumulative_rows: list[dict[str, Any]] = []
    interval_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []

    for x in sample_points:
        layer_sums = _event_layer_sums(events, 0, x)
        psi_x = mp.fsum(layer_sums.values())
        theta_x = layer_sums.get(1, mp.mpf("0"))
        higher_power_sum = psi_x - theta_x
        row: dict[str, Any] = {
            "x": x,
            "psi_x": mp_str(psi_x),
            "theta_x": mp_str(theta_x),
            "higher_prime_power_sum": mp_str(higher_power_sum),
            "psi_minus_theta": mp_str(higher_power_sum),
            "higher_power_share_of_psi": mp_str(higher_power_sum / psi_x if psi_x else 0),
            "layer_rows": _layer_rows(layer_sums, psi_x),
        }
        cumulative_rows.append(row)

    for lower, upper in intervals:
        layer_sums = _event_layer_sums(events, lower, upper)
        psi_increment = mp.fsum(layer_sums.values())
        theta_increment = layer_sums.get(1, mp.mpf("0"))
        higher_power_increment = psi_increment - theta_increment
        interval_length = upper - lower
        row = {
            "lower": lower,
            "upper": upper,
            "interval_length": interval_length,
            "psi_increment": mp_str(psi_increment),
            "theta_increment": mp_str(theta_increment),
            "higher_prime_power_increment": mp_str(higher_power_increment),
            "psi_increment_minus_length": mp_str(psi_increment - interval_length),
            "theta_increment_minus_length": mp_str(theta_increment - interval_length),
            "higher_power_share_of_interval_psi": mp_str(higher_power_increment / psi_increment if psi_increment else 0),
            "layer_rows": _layer_rows(layer_sums, psi_increment),
        }
        interval_rows.append(row)

    if include_events:
        for event in events:
            event_rows.append(
                {
                    "prime_power": event["prime_power"],
                    "prime": event["prime"],
                    "exponent": event["exponent"],
                    "log_prime": mp_str(event["log_prime"]),
                    "layer": "theta_prime_layer" if event["exponent"] == 1 else f"prime_power_layer_{event['exponent']}",
                }
            )

    return {
        "metadata": metadata("prime_power_decomposition", dps, "finite_prime_power_decomposition_not_rh_evidence"),
        "parameters": {
            "points": sample_points,
            "intervals": [{"lower": lower, "upper": upper} for lower, upper in intervals],
            "include_events": include_events,
        },
        "summary": {
            "max_sample": max_sample,
            "prime_power_event_count": len(events),
            "higher_prime_power_event_count": sum(1 for event in events if event["exponent"] >= 2),
            "max_exponent_seen": max((int(event["exponent"]) for event in events), default=0),
        },
        "cumulative_rows": cumulative_rows,
        "rows": interval_rows,
        "event_rows": event_rows,
    }


def prime_emergence_shell_signature(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 6,
    families: list[str] | None = None,
    max_fermat_n: int = 8,
    dps: int = 80,
    include_members: bool = False,
    include_layers: bool = True,
    max_examples: int = 12,
) -> dict[str, Any]:
    set_precision(dps)
    intervals = _interval_endpoints(points, max_x, count)
    selected_families = _selected_families(families)
    max_sample = max(upper for _, upper in intervals)
    prime_values = list(sp.primerange(2, max_sample + 1))
    prime_log_sums = _prefix_log_sums(prime_values)
    profile_rows = [special_prime_row(p, max_fermat_n=max_fermat_n) for p in prime_values]
    family_members: dict[str, list[int]] = {
        family: [row["p"] for row in profile_rows if row_matches_family(row, family)]
        for family in selected_families
    }
    family_log_sums = {family: _prefix_log_sums(values) for family, values in family_members.items()}
    prime_power_events = _prime_power_events(max_sample)

    rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    for lower, upper in intervals:
        shell_length = upper - lower
        midpoint = mp.mpf(lower + upper) / 2
        shell_primes = [p for p in prime_values if lower < p <= upper]
        prime_count = len(shell_primes)
        odd_prime_count = sum(1 for p in shell_primes if p != 2)
        theta_increment = _interval_sum(prime_values, prime_log_sums, lower, upper)
        layer_sums = _event_layer_sums(prime_power_events, lower, upper)
        psi_increment = mp.fsum(layer_sums.values())
        higher_power_increment = psi_increment - layer_sums.get(1, mp.mpf("0"))
        sieve_row = _sieve_survivor_row(lower, upper, max_examples)
        density_estimate = 1 / mp.log(midpoint) if midpoint > 1 else mp.mpf("0")
        expected_by_simple_density = mp.mpf(shell_length) * density_estimate
        li_increment = _li_interval(lower, upper)
        row: dict[str, Any] = {
            "lower": lower,
            "upper": upper,
            "shell_length": shell_length,
            "midpoint": mp_str(midpoint),
            "prime_count": prime_count,
            "odd_prime_count": odd_prime_count,
            "prime_count_density_per_integer": mp_str(mp.mpf(prime_count) / shell_length if shell_length else 0),
            "odd_prime_density_per_odd_candidate": mp_str(
                mp.mpf(odd_prime_count) / sieve_row["odd_candidate_count"] if sieve_row["odd_candidate_count"] else 0
            ),
            "simple_density_1_over_log_midpoint": mp_str(density_estimate),
            "expected_prime_count_by_shell_over_log_midpoint": mp_str(expected_by_simple_density),
            "prime_count_minus_simple_density_estimate": mp_str(mp.mpf(prime_count) - expected_by_simple_density),
            "li_increment_estimate": mp_str(li_increment),
            "prime_count_minus_li_increment": mp_str(mp.mpf(prime_count) - li_increment),
            "theta_increment": mp_str(theta_increment),
            "theta_increment_minus_length": mp_str(theta_increment - shell_length),
            "psi_increment": mp_str(psi_increment),
            "psi_increment_minus_length": mp_str(psi_increment - shell_length),
            "higher_prime_power_increment": mp_str(higher_power_increment),
            "higher_power_share_of_interval_psi": mp_str(higher_power_increment / psi_increment if psi_increment else 0),
            "sieve": sieve_row,
        }
        if include_layers:
            row["lambda_layer_rows"] = _layer_rows(layer_sums, psi_increment)
        if include_members:
            row["primes_in_shell"] = shell_primes
        rows.append(row)

        for family in selected_families:
            members = family_members[family]
            start = bisect_right(members, lower)
            stop = bisect_right(members, upper)
            shell_members = members[start:stop]
            family_theta_increment = _interval_sum(members, family_log_sums[family], lower, upper)
            family_row: dict[str, Any] = {
                "lower": lower,
                "upper": upper,
                "family": family,
                "family_count": len(shell_members),
                "prime_count": prime_count,
                "family_share_of_shell_primes": mp_str(mp.mpf(len(shell_members)) / prime_count if prime_count else 0),
                "family_theta_increment": mp_str(family_theta_increment),
                "theta_increment": mp_str(theta_increment),
                "family_theta_share_of_shell_theta": mp_str(
                    family_theta_increment / theta_increment if theta_increment else 0
                ),
            }
            if include_members:
                family_row["members_in_shell"] = shell_members
            family_rows.append(family_row)

    return {
        "metadata": metadata(
            "prime_emergence_shell_signature",
            dps,
            "finite_prime_emergence_shell_signature_not_rh_evidence",
        ),
        "parameters": {
            "intervals": [{"lower": lower, "upper": upper} for lower, upper in intervals],
            "families": selected_families,
            "max_fermat_n": max_fermat_n,
            "include_members": include_members,
            "include_layers": include_layers,
            "max_examples": max_examples,
        },
        "summary": {
            "max_sample": max_sample,
            "shell_count": len(intervals),
            "family_count": len(selected_families),
        },
        "rows": rows,
        "family_rows": family_rows,
    }
