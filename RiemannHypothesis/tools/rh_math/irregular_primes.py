"""Irregular-prime scans tied to Bernoulli numerators and zeta special values."""

from __future__ import annotations

from bisect import bisect_right
from functools import lru_cache
from typing import Any

import mpmath as mp
import sympy as sp

from .common import metadata, mp_str, set_precision
from .distribution import chebyshev_psi
from .primes import generated_sample_points


@lru_cache(maxsize=None)
def bernoulli_numerator(index: int) -> int:
    if index < 0:
        raise ValueError("Bernoulli index must be nonnegative")
    numerator, _ = sp.bernoulli(index).as_numer_denom()
    return int(numerator)


def irregular_pairs_for_prime(p: int) -> list[dict[str, Any]]:
    prime = int(p)
    if prime < 3 or not bool(sp.isprime(prime)):
        raise ValueError("irregular pair input must be an odd prime at least 3")
    pairs: list[dict[str, Any]] = []
    for bernoulli_index in range(2, prime - 2, 2):
        numerator_mod_p = bernoulli_numerator(bernoulli_index) % prime
        if numerator_mod_p == 0:
            pairs.append(
                {
                    "prime": prime,
                    "bernoulli_index": bernoulli_index,
                    "zeta_special_argument": 1 - bernoulli_index,
                    "relation": "zeta(1-k) = -B_k/k",
                    "divides_bernoulli_numerator": True,
                }
            )
    return pairs


def irregular_prime_row(p: int) -> dict[str, Any]:
    pairs = irregular_pairs_for_prime(p)
    return {
        "p": int(p),
        "is_irregular_prime": bool(pairs),
        "irregular_index": len(pairs),
        "irregular_pairs": pairs,
    }


def irregular_prime_scan(limit: int = 200, include_regular: bool = False, dps: int = 80) -> dict[str, Any]:
    if limit < 3:
        raise ValueError("limit must be at least 3")
    rows = []
    for prime in sp.primerange(3, int(limit) + 1):
        row = irregular_prime_row(int(prime))
        if include_regular or row["is_irregular_prime"]:
            rows.append(row)
    irregular_members = [row["p"] for row in rows if row["is_irregular_prime"]]
    all_prime_count = int(sp.primepi(limit) - 1)  # exclude 2, which is outside the irregular-prime definition
    return {
        "metadata": metadata("irregular_prime_scan", dps, "finite_irregular_prime_scan_not_zero_line_evidence"),
        "parameters": {
            "limit": int(limit),
            "include_regular": bool(include_regular),
        },
        "summary": {
            "odd_prime_count": all_prime_count,
            "reported_row_count": len(rows),
            "irregular_prime_count": len(irregular_members),
            "irregular_primes": irregular_members,
            "first_irregular_prime": irregular_members[0] if irregular_members else None,
        },
        "rows": rows,
    }


def _selected_sample_points(points: list[int] | None, max_x: int | None, count: int) -> list[int]:
    if points:
        sample_points = sorted(set(int(x) for x in points))
    else:
        sample_points = generated_sample_points(int(max_x or 200), int(count))
    if not sample_points:
        raise ValueError("at least one sample point is required")
    if sample_points[0] < 2:
        raise ValueError("sample points must be at least 2")
    return sample_points


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


@lru_cache(maxsize=None)
def irregular_prime_members_up_to(limit: int) -> tuple[int, ...]:
    if limit < 3:
        return ()
    members = []
    for prime in sp.primerange(3, int(limit) + 1):
        if irregular_pairs_for_prime(int(prime)):
            members.append(int(prime))
    return tuple(members)


def _global_distribution_row(x: int, prime_values: list[int], prime_log_sums: list[mp.mpf]) -> dict[str, Any]:
    prime_pi = bisect_right(prime_values, x)
    theta_x = _prefix_sum_at(prime_values, prime_log_sums, x)
    psi_x = chebyshev_psi(x)
    scale = mp.sqrt(x) * mp.log(x)
    theta_error = theta_x - x
    psi_error = psi_x - x
    return {
        "x": x,
        "prime_pi": prime_pi,
        "odd_prime_count": max(prime_pi - 1, 0),
        "theta_x": mp_str(theta_x),
        "theta_minus_x": mp_str(theta_error),
        "psi_x": mp_str(psi_x),
        "psi_minus_x": mp_str(psi_error),
        "sqrt_x_log_x_scale": mp_str(scale),
        "theta_error_over_sqrt_x_log_x": mp_str(theta_error / scale if scale else 0),
        "psi_error_over_sqrt_x_log_x": mp_str(psi_error / scale if scale else 0),
    }


def irregular_prime_distribution(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 6,
    dps: int = 80,
    include_members: bool = False,
) -> dict[str, Any]:
    set_precision(dps)
    sample_points = _selected_sample_points(points, max_x, count)
    max_sample = max(sample_points)
    prime_values = list(sp.primerange(2, max_sample + 1))
    prime_log_sums = _prefix_log_sums(prime_values)
    irregular_values = list(irregular_prime_members_up_to(max_sample))
    irregular_log_sums = _prefix_log_sums(irregular_values)

    global_rows = [_global_distribution_row(x, prime_values, prime_log_sums) for x in sample_points]
    globals_by_x = {row["x"]: row for row in global_rows}
    rows: list[dict[str, Any]] = []
    for x in sample_points:
        global_row = globals_by_x[x]
        odd_prime_count = int(global_row["odd_prime_count"])
        theta_x = mp.mpf(global_row["theta_x"])
        irregular_count = bisect_right(irregular_values, x)
        irregular_theta = _prefix_sum_at(irregular_values, irregular_log_sums, x)
        row: dict[str, Any] = {
            "x": x,
            "irregular_prime_count": irregular_count,
            "odd_prime_count": odd_prime_count,
            "irregular_density_among_odd_primes": mp_str(
                mp.mpf(irregular_count) / odd_prime_count if odd_prime_count else 0
            ),
            "irregular_theta": mp_str(irregular_theta),
            "theta_x": global_row["theta_x"],
            "irregular_theta_share": mp_str(irregular_theta / theta_x if theta_x else 0),
            "last_irregular_prime": irregular_values[irregular_count - 1] if irregular_count else None,
            "global_theta_minus_x": global_row["theta_minus_x"],
            "global_psi_minus_x": global_row["psi_minus_x"],
        }
        if include_members:
            row["irregular_primes_up_to_x"] = irregular_values[:irregular_count]
        rows.append(row)

    return {
        "metadata": metadata(
            "irregular_prime_distribution",
            dps,
            "finite_irregular_prime_distribution_not_zero_line_evidence",
        ),
        "parameters": {
            "points": sample_points,
            "include_members": include_members,
        },
        "summary": {
            "max_sample": max_sample,
            "irregular_prime_count_at_max_sample": len(irregular_values),
            "irregular_primes_at_max_sample": irregular_values,
            "first_irregular_prime": irregular_values[0] if irregular_values else None,
        },
        "global_rows": global_rows,
        "rows": rows,
    }
