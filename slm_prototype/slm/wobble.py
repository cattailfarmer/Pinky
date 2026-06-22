"""Wobble detection for unresolved semantic instability."""

from __future__ import annotations

from dataclasses import dataclass

from slm.candidate_roles import RoleCandidate
from slm.tokenizer import Token


@dataclass(frozen=True)
class WobbleReport:
    score: float
    factors: list[str]


def score_wobble(tokens: list[Token], candidates: dict[int, list[RoleCandidate]], structural_hints: object) -> WobbleReport:
    factors: list[str] = []
    instability = 0.0

    for token in tokens:
        if token.is_punctuation:
            continue
        roles = candidates[token.index]
        if len(roles) > 1 and roles[0].activation - roles[1].activation < 0.2:
            instability += 0.18
            factors.append(f"role competition at token {token.index} ({token.text})")
        if roles[0].role in {"noun", "verb", "adjective"} and roles[0].activation < 0.6:
            instability += 0.14
            factors.append(f"weak open-class commitment at token {token.index} ({token.text})")

    if not structural_hints:
        instability += 0.2
        factors.append("no structural hints found")

    content_count = len([token for token in tokens if not token.is_punctuation])
    score = min(1.0, instability / max(content_count, 1))
    return WobbleReport(score=round(score, 3), factors=factors)
