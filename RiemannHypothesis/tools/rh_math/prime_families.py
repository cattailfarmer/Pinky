"""Special-prime family profiling for finite arithmetic inquiry."""

from __future__ import annotations

from math import gcd
from typing import Any

import sympy as sp

from .common import metadata


DEFAULT_SPECIAL_PRIME_SEEDS = [3, 5, 17, 257, 65537, 641]

SPECIAL_PRIME_FAMILY_NAMES = [
    "fermat_prime_identity",
    "fermat_number_factor_periphery",
    "mersenne_prime",
    "proth_prime",
    "pierpont_prime",
    "sophie_germain_prime",
    "safe_prime",
    "base2_wieferich_prime",
]


def special_prime_family_names() -> list[str]:
    return list(SPECIAL_PRIME_FAMILY_NAMES)


def row_matches_family(row: dict[str, Any], family: str) -> bool:
    if family == "fermat_prime_identity":
        return row["identity_scope"] == "fermat_prime_identity"
    if family == "fermat_number_factor_periphery":
        return row["identity_scope"] == "fermat_number_factor_periphery"
    if family == "mersenne_prime":
        return bool(row["is_mersenne_prime"])
    if family == "proth_prime":
        return bool(row["proth"]["is_proth_form"])
    if family == "pierpont_prime":
        return bool(row["pierpont"]["is_pierpont_form"])
    if family == "sophie_germain_prime":
        return bool(row["is_sophie_germain_prime"])
    if family == "safe_prime":
        return bool(row["is_safe_prime"])
    if family == "base2_wieferich_prime":
        return row["is_base2_wieferich_prime"] is True
    raise ValueError(f"unsupported special-prime family: {family}")


def _as_int(value: int | str) -> int:
    n = int(value)
    if n < 2:
        raise ValueError("prime profile inputs must be integers at least 2")
    return n


def power_of_two_exponent(value: int) -> int | None:
    if value < 1:
        return None
    if value & (value - 1):
        return None
    return value.bit_length() - 1


def remove_factor(value: int, factor: int) -> tuple[int, int]:
    count = 0
    remainder = value
    while remainder % factor == 0:
        count += 1
        remainder //= factor
    return count, remainder


def fermat_prime_index(p: int) -> int | None:
    exponent = power_of_two_exponent(p - 1)
    if exponent is None:
        return None
    return power_of_two_exponent(exponent)


def mersenne_prime_exponent(p: int) -> int | None:
    exponent = power_of_two_exponent(p + 1)
    if exponent is None:
        return None
    if bool(sp.isprime(exponent)):
        return exponent
    return None


def fermat_divisor_hits(p: int, max_n: int = 8) -> list[int]:
    if max_n < 0:
        raise ValueError("max_n must be nonnegative")
    if p == 2:
        return []
    target = p - 1
    hits: list[int] = []
    for n in range(max_n + 1):
        if pow(2, 1 << n, p) == target:
            hits.append(n)
    return hits


def multiplicative_order_base2(p: int) -> int | None:
    if gcd(2, p) != 1:
        return None
    return int(sp.n_order(2, p))


def proth_profile(p: int) -> dict[str, Any]:
    two_power, odd_part = remove_factor(p - 1, 2)
    return {
        "is_proth_form": bool(two_power > 0 and odd_part < (1 << two_power)),
        "odd_k": odd_part,
        "two_power": two_power,
        "representation": f"{odd_part}*2^{two_power}+1",
    }


def pierpont_profile(p: int) -> dict[str, Any]:
    two_power, remainder = remove_factor(p - 1, 2)
    three_power, remainder = remove_factor(remainder, 3)
    return {
        "is_pierpont_form": remainder == 1,
        "two_power": two_power,
        "three_power": three_power,
        "remaining_factor": remainder,
        "representation": f"2^{two_power}*3^{three_power}+1",
    }


def factorint_record(value: int) -> dict[str, int]:
    return {str(prime): int(power) for prime, power in sp.factorint(value).items()}


def base2_wieferich(p: int, is_prime: bool) -> bool | None:
    if not is_prime or p == 2:
        return None
    return pow(2, p - 1, p * p) == 1


def identity_scope(fermat_index: int | None, fermat_hits: list[int]) -> str:
    if fermat_index is not None:
        return "fermat_prime_identity"
    if fermat_hits:
        return "fermat_number_factor_periphery"
    return "special_prime_or_general_prime_periphery"


def special_prime_row(p: int | str, max_fermat_n: int = 8) -> dict[str, Any]:
    prime = _as_int(p)
    is_prime = bool(sp.isprime(prime))
    exact_fermat_index = fermat_prime_index(prime)
    fermat_index = exact_fermat_index if is_prime else None
    fermat_hits = fermat_divisor_hits(prime, max_n=max_fermat_n) if is_prime else []
    order = multiplicative_order_base2(prime)
    sophie_partner = 2 * prime + 1
    safe_parent = (prime - 1) // 2 if prime % 2 else None
    mersenne_exponent = mersenne_prime_exponent(prime)

    return {
        "p": prime,
        "is_prime": is_prime,
        "identity_scope": identity_scope(fermat_index, fermat_hits),
        "exact_fermat_number_index": exact_fermat_index,
        "fermat_prime_index": fermat_index,
        "fermat_divisor_hits": fermat_hits,
        "smallest_fermat_number_divided": min(fermat_hits) if fermat_hits else None,
        "multiplicative_order_2_mod_p": order,
        "p_minus_1_factorization": factorint_record(prime - 1),
        "p_plus_1_factorization": factorint_record(prime + 1),
        "mersenne_prime_exponent": mersenne_exponent,
        "is_mersenne_prime": mersenne_exponent is not None,
        "proth": proth_profile(prime),
        "pierpont": pierpont_profile(prime),
        "is_sophie_germain_prime": bool(is_prime and sp.isprime(sophie_partner)),
        "sophie_germain_partner": sophie_partner,
        "is_safe_prime": bool(is_prime and safe_parent is not None and sp.isprime(safe_parent)),
        "safe_prime_parent": safe_parent,
        "is_base2_wieferich_prime": base2_wieferich(prime, is_prime),
    }


def special_prime_profile(
    primes: list[int] | None = None,
    max_fermat_n: int = 8,
    dps: int = 80,
) -> dict[str, Any]:
    values = primes or DEFAULT_SPECIAL_PRIME_SEEDS
    rows = [special_prime_row(value, max_fermat_n=max_fermat_n) for value in values]
    return {
        "metadata": metadata("special_prime_profile", dps, "finite_prime_family_profile_not_rh_evidence"),
        "parameters": {
            "primes": values,
            "max_fermat_n": max_fermat_n,
        },
        "rows": rows,
    }


def scan_special_prime_families(
    limit: int = 10000,
    max_fermat_n: int = 8,
    include_profiles: bool = False,
    dps: int = 80,
) -> dict[str, Any]:
    if limit < 2:
        raise ValueError("limit must be at least 2")
    rows = [special_prime_row(p, max_fermat_n=max_fermat_n) for p in sp.primerange(2, limit + 1)]
    summary_rows = []
    for family in SPECIAL_PRIME_FAMILY_NAMES:
        members = [row["p"] for row in rows if row_matches_family(row, family)]
        summary_rows.append(
            {
                "family": family,
                "count": len(members),
                "members": members,
            }
        )
    payload = {
        "metadata": metadata("special_prime_scan", dps, "bounded_prime_family_scan_not_rh_evidence"),
        "parameters": {
            "limit": limit,
            "max_fermat_n": max_fermat_n,
            "include_profiles": include_profiles,
        },
        "rows": summary_rows,
    }
    if include_profiles:
        payload["profile_rows"] = rows
    return payload
