"""Tokenization for the SLM prototype."""

from __future__ import annotations

from dataclasses import dataclass
import re


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class Token:
    index: int
    text: str
    normalized: str
    is_punctuation: bool = False


def tokenize(text: str) -> list[Token]:
    """Split text into stable token objects."""
    tokens: list[Token] = []
    for index, match in enumerate(TOKEN_PATTERN.finditer(text)):
        raw = match.group(0)
        tokens.append(
            Token(
                index=index,
                text=raw,
                normalized=raw.lower(),
                is_punctuation=not any(char.isalnum() for char in raw),
            )
        )
    return tokens
