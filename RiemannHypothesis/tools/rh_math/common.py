"""Shared CLI and serialization helpers for RH math tools."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

import mpmath as mp


PROOF_STATUS_NUMERICAL_TRACE = "finite_numerical_trace_not_proof_or_certification"


def set_precision(dps: int) -> None:
    if dps < 15:
        raise ValueError("precision must be at least 15 decimal digits")
    mp.mp.dps = int(dps)


def require_positive(value: mp.mpf, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def require_ordered_range(start: mp.mpf, stop: mp.mpf, name: str = "range") -> None:
    if start > stop:
        raise ValueError(f"{name} start must be less than or equal to stop")


def mp_str(value: Any, digits: int | None = None) -> str:
    n = digits or mp.mp.dps
    return mp.nstr(value, n=n)


def complex_record(value: Any, digits: int | None = None) -> dict[str, str]:
    z = mp.mpc(value)
    return {
        "real": mp_str(mp.re(z), digits),
        "imag": mp_str(mp.im(z), digits),
        "abs": mp_str(abs(z), digits),
        "arg": mp_str(mp.arg(z), digits),
    }


def scalar_record(value: Any, digits: int | None = None) -> dict[str, str]:
    x = mp.mpf(value)
    return {
        "value": mp_str(x, digits),
        "abs": mp_str(abs(x), digits),
    }


def stringified(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, mp.mpf):
        return mp_str(value)
    if isinstance(value, mp.mpc):
        return complex_record(value)
    if isinstance(value, dict):
        return {str(k): stringified(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [stringified(v) for v in value]
    return str(value)


def metadata(tool: str, precision: int, proof_status: str | None = None) -> dict[str, Any]:
    return {
        "tool": tool,
        "precision_dps": int(precision),
        "proof_status": proof_status or PROOF_STATUS_NUMERICAL_TRACE,
    }


def emit_payload(payload: dict[str, Any], output_format: str, output: str | None = None) -> None:
    output_format = output_format.lower()
    if output_format not in {"json", "csv"}:
        raise ValueError("output format must be json or csv")

    text: str
    if output_format == "json":
        text = json.dumps(stringified(payload), indent=2, sort_keys=True)
    else:
        rows = payload.get("rows")
        if rows is None:
            rows = [payload.get("row", {})]
        if not isinstance(rows, list):
            raise ValueError("CSV output requires payload['rows'] to be a list")
        text = rows_to_csv(rows)

    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    normalized = [flatten_row(stringified(row)) for row in rows]
    fieldnames: list[str] = []
    for row in normalized:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    from io import StringIO

    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(normalized)
    return stream.getvalue().rstrip("\n")


def flatten_row(row: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in row.items():
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten_row(value, name))
        else:
            flat[name] = value
    return flat


def mp_range(start: str | float, stop: str | float, step: str | float) -> Iterable[mp.mpf]:
    a = mp.mpf(start)
    b = mp.mpf(stop)
    h = mp.mpf(step)
    require_ordered_range(a, b)
    require_positive(h, "step")
    count = int(mp.floor((b - a) / h)) + 1
    for i in range(count):
        value = a + h * i
        if value <= b:
            yield value
