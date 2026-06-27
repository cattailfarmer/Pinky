"""Finite modular probes for large exponential shift forms."""

from __future__ import annotations

from typing import Any

import sympy as sp

from .common import metadata


def expression_parity(base: int, shift: int) -> str:
    value_mod_2 = (base % 2 + shift % 2) % 2
    return "odd" if value_mod_2 else "even"


def forced_divisor_records(base: int, exponent: int, shift: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if shift == -1:
        divisor = base - 1
        records.append(
            {
                "divisor": divisor,
                "reason": "base^exponent - 1 is divisible by base - 1",
                "factorization": {str(p): int(e) for p, e in sp.factorint(divisor).items()},
            }
        )
    if shift == 1 and exponent % 2 == 1:
        divisor = base + 1
        records.append(
            {
                "divisor": divisor,
                "reason": "base^odd_exponent + 1 is divisible by base + 1",
                "factorization": {str(p): int(e) for p, e in sp.factorint(divisor).items()},
            }
        )
    return records


def bounded_small_divisors(base: int, exponent: int, shift: int, limit: int, max_hits: int) -> list[int]:
    if limit < 2:
        raise ValueError("small factor limit must be at least 2")
    if max_hits < 1:
        raise ValueError("max hits must be at least 1")
    hits: list[int] = []
    for prime in sp.primerange(2, limit + 1):
        if (pow(base, exponent, prime) + shift) % prime == 0:
            hits.append(int(prime))
            if len(hits) >= max_hits:
                break
    return hits


def bounded_small_divisors_power_exponent(
    base: int,
    exponent_base: int,
    exponent_power: int,
    shift: int,
    limit: int,
    max_hits: int,
) -> list[int]:
    if limit < 2:
        raise ValueError("small factor limit must be at least 2")
    if max_hits < 1:
        raise ValueError("max hits must be at least 1")
    if exponent_base < 1 or exponent_power < 1:
        raise ValueError("exponent base and power must be positive")
    hits: list[int] = []
    for prime in sp.primerange(2, limit + 1):
        if base % prime == 0:
            residue = shift % prime
        else:
            exponent_mod = pow(exponent_base, exponent_power, prime - 1)
            residue = (pow(base, exponent_mod, prime) + shift) % prime
        if residue == 0:
            hits.append(int(prime))
            if len(hits) >= max_hits:
                break
    return hits


def coefficient_power_shift_value_mod(
    coefficient: int,
    power_base: int,
    power: int,
    shift: int,
    prime: int,
) -> int:
    if power < 0:
        raise ValueError("power must be nonnegative")
    return ((coefficient % prime) * pow(power_base, power, prime) + shift) % prime


def bounded_small_divisors_coefficient_power(
    coefficient: int,
    power_base: int,
    power: int,
    shift: int,
    limit: int,
    max_hits: int,
) -> list[int]:
    if limit < 2:
        raise ValueError("small factor limit must be at least 2")
    if max_hits < 1:
        raise ValueError("max hits must be at least 1")
    hits: list[int] = []
    for prime in sp.primerange(2, limit + 1):
        if coefficient_power_shift_value_mod(coefficient, power_base, power, shift, int(prime)) == 0:
            hits.append(int(prime))
            if len(hits) >= max_hits:
                break
    return hits


def coefficient_shift_modes(power: int, modes: list[str]) -> list[tuple[str, int]]:
    values: list[tuple[str, int]] = []
    for mode in modes:
        if mode == "plus_n":
            values.append((mode, power))
        elif mode == "minus_n":
            values.append((mode, -power))
        elif mode == "n_plus_1":
            values.append((mode, power + 1))
        elif mode == "one_minus_n":
            values.append((mode, 1 - power))
        elif mode == "minus_n_minus_1":
            values.append((mode, -(power + 1)))
        else:
            raise ValueError(f"unsupported coefficient shift mode: {mode}")
    return values


def exponential_shift_probe_row(
    base: int,
    exponent: int,
    shift: int,
    small_factor_limit: int,
    max_hits: int,
) -> dict[str, Any]:
    if base < 2:
        raise ValueError("base must be at least 2")
    if exponent < 1:
        raise ValueError("exponent must be positive")
    forced = forced_divisor_records(base, exponent, shift)
    hits = bounded_small_divisors(base, exponent, shift, small_factor_limit, max_hits)
    return {
        "base": base,
        "exponent": exponent,
        "shift": shift,
        "expression": f"{base}^{exponent}{shift:+d}",
        "parity": expression_parity(base, shift),
        "forced_divisors": forced,
        "small_factor_limit": small_factor_limit,
        "small_divisors": hits,
        "small_divisor_count_reported": len(hits),
        "first_small_divisor": hits[0] if hits else None,
        "bounded_result": "small_divisor_found" if hits else "no_small_divisor_found_within_bound",
    }


def exponential_shift_probe(
    base: int,
    exponents: list[int],
    shifts: list[int],
    small_factor_limit: int = 100000,
    max_hits: int = 10,
    dps: int = 80,
) -> dict[str, Any]:
    rows = [
        exponential_shift_probe_row(int(base), int(exponent), int(shift), int(small_factor_limit), int(max_hits))
        for exponent in exponents
        for shift in shifts
    ]
    return {
        "metadata": metadata("exponential_shift_probe", dps, "bounded_exponential_shift_probe_not_primality_proof"),
        "parameters": {
            "base": int(base),
            "exponents": [int(exponent) for exponent in exponents],
            "shifts": [int(shift) for shift in shifts],
            "small_factor_limit": int(small_factor_limit),
            "max_hits": int(max_hits),
        },
        "rows": rows,
    }


def exponential_power_shift_probe(
    base: int,
    exponent_base: int,
    exponent_powers: list[int],
    shifts: list[int],
    small_factor_limit: int = 100000,
    max_hits: int = 10,
    dps: int = 80,
) -> dict[str, Any]:
    if base < 2:
        raise ValueError("base must be at least 2")
    rows: list[dict[str, Any]] = []
    for exponent_power in exponent_powers:
        exponent_parity = "odd" if exponent_base % 2 and exponent_power >= 1 else "unknown"
        for shift in shifts:
            forced = []
            if shift == 1 and exponent_base % 2 == 1:
                divisor = base + 1
                forced.append(
                    {
                        "divisor": divisor,
                        "reason": "base^odd_exponent + 1 is divisible by base + 1",
                        "factorization": {str(p): int(e) for p, e in sp.factorint(divisor).items()},
                    }
                )
            hits = bounded_small_divisors_power_exponent(
                int(base),
                int(exponent_base),
                int(exponent_power),
                int(shift),
                int(small_factor_limit),
                int(max_hits),
            )
            rows.append(
                {
                    "base": int(base),
                    "exponent_form": f"{int(exponent_base)}^{int(exponent_power)}",
                    "exponent_base": int(exponent_base),
                    "exponent_power": int(exponent_power),
                    "exponent_parity": exponent_parity,
                    "shift": int(shift),
                    "expression": f"{int(base)}^({int(exponent_base)}^{int(exponent_power)}){int(shift):+d}",
                    "parity": expression_parity(int(base), int(shift)),
                    "forced_divisors": forced,
                    "small_factor_limit": int(small_factor_limit),
                    "small_divisors": hits,
                    "small_divisor_count_reported": len(hits),
                    "first_small_divisor": hits[0] if hits else None,
                    "bounded_result": "small_divisor_found" if hits else "no_small_divisor_found_within_bound",
                }
            )
    return {
        "metadata": metadata("exponential_power_shift_probe", dps, "bounded_power_exponent_shift_probe_not_primality_proof"),
        "parameters": {
            "base": int(base),
            "exponent_base": int(exponent_base),
            "exponent_powers": [int(exponent_power) for exponent_power in exponent_powers],
            "shifts": [int(shift) for shift in shifts],
            "small_factor_limit": int(small_factor_limit),
            "max_hits": int(max_hits),
        },
        "rows": rows,
    }


def coefficient_power_shift_probe(
    coefficient: int,
    power_base: int,
    powers: list[int],
    fixed_shifts: list[int] | None = None,
    shift_modes: list[str] | None = None,
    small_factor_limit: int = 100000,
    max_hits: int = 10,
    dps: int = 80,
) -> dict[str, Any]:
    if coefficient < 1:
        raise ValueError("coefficient must be positive")
    if power_base < 1:
        raise ValueError("power base must be positive")
    fixed = fixed_shifts or []
    modes = shift_modes or []
    if not fixed and not modes:
        raise ValueError("at least one fixed shift or shift mode is required")
    rows: list[dict[str, Any]] = []
    for power in powers:
        if power < 0:
            raise ValueError("powers must be nonnegative")
        shifts = [(f"fixed_{shift:+d}", int(shift)) for shift in fixed]
        shifts.extend(coefficient_shift_modes(int(power), modes))
        for shift_label, shift in shifts:
            hits = bounded_small_divisors_coefficient_power(
                int(coefficient),
                int(power_base),
                int(power),
                int(shift),
                int(small_factor_limit),
                int(max_hits),
            )
            rows.append(
                {
                    "coefficient": int(coefficient),
                    "power_base": int(power_base),
                    "power": int(power),
                    "shift_label": shift_label,
                    "shift": int(shift),
                    "expression": f"{int(coefficient)}*{int(power_base)}^{int(power)}{int(shift):+d}",
                    "parity": expression_parity((int(coefficient) % 2) * (int(power_base) % 2), int(shift)),
                    "small_factor_limit": int(small_factor_limit),
                    "small_divisors": hits,
                    "small_divisor_count_reported": len(hits),
                    "first_small_divisor": hits[0] if hits else None,
                    "bounded_result": "small_divisor_found" if hits else "no_small_divisor_found_within_bound",
                }
            )
    return {
        "metadata": metadata(
            "coefficient_power_shift_probe",
            dps,
            "bounded_coefficient_power_shift_probe_not_primality_proof",
        ),
        "parameters": {
            "coefficient": int(coefficient),
            "power_base": int(power_base),
            "powers": [int(power) for power in powers],
            "fixed_shifts": [int(shift) for shift in fixed],
            "shift_modes": modes,
            "small_factor_limit": int(small_factor_limit),
            "max_hits": int(max_hits),
        },
        "rows": rows,
    }
