"""Prime-count comparison helpers for finite arithmetic baselines."""

from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp

from .common import metadata, mp_str, set_precision


def riemann_r(x: int | str, terms: int = 20) -> mp.mpf:
    if terms < 1:
        raise ValueError("terms must be at least 1")
    xx = mp.mpf(x)
    if xx < 2:
        raise ValueError("x must be at least 2")
    total = mp.mpf("0")
    for n in range(1, terms + 1):
        mu = int(sp.mobius(n))
        if mu:
            total += (mp.mpf(mu) / n) * mp.li(mp.power(xx, mp.mpf(1) / n))
    return total


def prime_count_row(x: int, terms: int = 20) -> dict[str, Any]:
    if x < 2:
        raise ValueError("x must be at least 2")
    pi_x = int(sp.primepi(x))
    li_x = mp.li(x)
    r_x = riemann_r(x, terms=terms)
    return {
        "x": x,
        "prime_pi": pi_x,
        "li_x": mp_str(li_x),
        "li_error": mp_str(li_x - pi_x),
        "riemann_r_terms": terms,
        "riemann_r": mp_str(r_x),
        "riemann_r_error": mp_str(r_x - pi_x),
    }


def generated_sample_points(max_x: int, count: int) -> list[int]:
    if max_x < 2:
        raise ValueError("max_x must be at least 2")
    if count < 1:
        raise ValueError("count must be at least 1")
    if count == 1:
        return [max_x]
    values = set()
    log_min = mp.log10(2)
    log_max = mp.log10(max_x)
    for i in range(count):
        exponent = log_min + (log_max - log_min) * i / (count - 1)
        values.add(max(2, int(mp.floor(mp.power(10, exponent)))))
    values.add(max_x)
    return sorted(values)


def prime_count_compare(
    points: list[int] | None = None,
    max_x: int | None = None,
    count: int = 8,
    terms: int = 20,
    dps: int = 80,
) -> dict[str, Any]:
    set_precision(dps)
    if points:
        sample_points = sorted(set(int(x) for x in points))
    else:
        if max_x is None:
            max_x = 1000
        sample_points = generated_sample_points(int(max_x), int(count))
    rows = [prime_count_row(x, terms=terms) for x in sample_points]
    return {
        "metadata": metadata("prime_count_compare", dps, "finite_prime_count_comparison_not_asymptotic_proof"),
        "parameters": {"terms": terms, "points": sample_points},
        "rows": rows,
    }
