"""Zeta-function numerical routines for finite RH-adjacent traces."""

from __future__ import annotations

from typing import Any

import mpmath as mp

from .common import complex_record, metadata, mp_range, mp_str, scalar_record, set_precision


def zeta_value(sigma: str | float, t: str | float, dps: int = 80) -> dict[str, Any]:
    set_precision(dps)
    s = mp.mpc(mp.mpf(sigma), mp.mpf(t))
    value = mp.zeta(s)
    return {
        "metadata": metadata("zeta_eval", dps, "numerical_zeta_value_not_proof"),
        "row": {
            "sigma": mp_str(mp.re(s)),
            "t": mp_str(mp.im(s)),
            "s": complex_record(s),
            "zeta": complex_record(value),
        },
    }


def completed_xi(s: mp.mpc) -> mp.mpc:
    return mp.mpf("0.5") * s * (s - 1) * mp.power(mp.pi, -s / 2) * mp.gamma(s / 2) * mp.zeta(s)


def zeta_functional_chi(s: mp.mpc) -> mp.mpc:
    return mp.power(2, s) * mp.power(mp.pi, s - 1) * mp.sin(mp.pi * s / 2) * mp.gamma(1 - s)


def residual_record(left: mp.mpc, right: mp.mpc) -> dict[str, Any]:
    residual = left - right
    denominator = max(abs(left), abs(right), mp.mpf(1))
    relative = abs(residual) / denominator
    return {
        "left": complex_record(left),
        "right": complex_record(right),
        "residual": complex_record(residual),
        "residual_abs": mp_str(abs(residual)),
        "relative_residual": mp_str(relative),
    }


def functional_equation_check(
    sigma: str | float,
    t: str | float,
    dps: int = 80,
    equation: str = "xi",
) -> dict[str, Any]:
    set_precision(dps)
    s = mp.mpc(mp.mpf(sigma), mp.mpf(t))
    equation = equation.lower()
    if equation == "xi":
        left = completed_xi(s)
        right = completed_xi(1 - s)
        proof_status = "finite_xi_symmetry_residual_not_proof"
    elif equation == "zeta":
        left = mp.zeta(s)
        right = zeta_functional_chi(s) * mp.zeta(1 - s)
        proof_status = "finite_zeta_functional_equation_residual_not_proof"
    else:
        raise ValueError("equation must be xi or zeta")
    row = {
        "equation": equation,
        "sigma": mp_str(mp.re(s)),
        "t": mp_str(mp.im(s)),
        "s": complex_record(s),
        **residual_record(left, right),
    }
    return {
        "metadata": metadata("functional_equation_check", dps, proof_status),
        "row": row,
    }


def hardy_z(t: mp.mpf) -> mp.mpf:
    return mp.siegelz(t)


def critical_line_samples(
    t_min: str | float,
    t_max: str | float,
    step: str | float,
    dps: int = 80,
    max_samples: int = 20000,
) -> list[dict[str, Any]]:
    set_precision(dps)
    rows: list[dict[str, Any]] = []
    for idx, t in enumerate(mp_range(t_min, t_max, step)):
        if idx >= max_samples:
            raise ValueError(f"sample count exceeds max_samples={max_samples}")
        s = mp.mpc(mp.mpf("0.5"), t)
        zeta = mp.zeta(s)
        z_value = hardy_z(t)
        rows.append(
            {
                "index": idx,
                "t": mp_str(t),
                "hardy_z": mp_str(z_value),
                "hardy_z_sign": sign_name(z_value),
                "zeta": complex_record(zeta),
            }
        )
    return rows


def sign_name(value: mp.mpf) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def sign_changes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    previous: tuple[mp.mpf, mp.mpf] | None = None
    for row in rows:
        t = mp.mpf(row["t"])
        z = mp.mpf(row["hardy_z"])
        if previous is not None:
            prev_t, prev_z = previous
            if z == 0 or prev_z == 0 or (z > 0) != (prev_z > 0):
                changes.append(
                    {
                        "a": mp_str(prev_t),
                        "b": mp_str(t),
                        "hardy_z_a": mp_str(prev_z),
                        "hardy_z_b": mp_str(z),
                    }
                )
        previous = (t, z)
    return changes


def refine_bracket(a: str | float, b: str | float, dps: int = 80, iterations: int | None = None) -> dict[str, Any]:
    set_precision(dps)
    left = mp.mpf(a)
    right = mp.mpf(b)
    f_left = hardy_z(left)
    f_right = hardy_z(right)
    if f_left == 0:
        root = left
    elif f_right == 0:
        root = right
    elif (f_left > 0) == (f_right > 0):
        raise ValueError("bracket endpoints must have opposite signs or include a zero")
    else:
        steps = iterations or max(80, int(dps * 3.5))
        lo, hi = left, right
        flo, fhi = f_left, f_right
        for _ in range(steps):
            mid = (lo + hi) / 2
            fmid = hardy_z(mid)
            if fmid == 0:
                lo = hi = mid
                break
            if (flo > 0) == (fmid > 0):
                lo, flo = mid, fmid
            else:
                hi, fhi = mid, fmid
        root = (lo + hi) / 2
    zeta_at_root = mp.zeta(mp.mpc(mp.mpf("0.5"), root))
    return {
        "a": mp_str(left),
        "b": mp_str(right),
        "root_t_estimate": mp_str(root),
        "hardy_z_at_root": mp_str(hardy_z(root)),
        "zeta_at_root": complex_record(zeta_at_root),
        "zeta_abs_at_root": mp_str(abs(zeta_at_root)),
    }


def critical_line_scan(
    t_min: str | float,
    t_max: str | float,
    step: str | float,
    dps: int = 80,
    refine: bool = False,
) -> dict[str, Any]:
    rows = critical_line_samples(t_min, t_max, step, dps=dps)
    changes = sign_changes(rows)
    refined = []
    if refine:
        for change in changes:
            refined.append(refine_bracket(change["a"], change["b"], dps=dps))
    return {
        "metadata": metadata("critical_line_scan", dps, "sign_change_probe_not_zero_certification"),
        "parameters": {"t_min": str(t_min), "t_max": str(t_max), "step": str(step), "refine": refine},
        "rows": rows,
        "sign_changes": changes,
        "refined_zero_estimates": refined,
    }


def known_zero_probe(start: int = 1, count: int = 10, dps: int = 80) -> dict[str, Any]:
    if start < 1:
        raise ValueError("start must be at least 1")
    if count < 1:
        raise ValueError("count must be at least 1")
    set_precision(dps)
    rows: list[dict[str, Any]] = []
    for n in range(start, start + count):
        zero = mp.zetazero(n)
        value = mp.zeta(zero)
        rows.append(
            {
                "zero_index": n,
                "zero": complex_record(zero),
                "critical_line_offset": mp_str(mp.re(zero) - mp.mpf("0.5")),
                "zeta_residual": complex_record(value),
                "zeta_abs_residual": mp_str(abs(value)),
            }
        )
    return {
        "metadata": metadata("zero_probe", dps, "library_numeric_lookup_not_independent_zero_certification"),
        "parameters": {"start": start, "count": count},
        "rows": rows,
    }
