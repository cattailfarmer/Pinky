"""Candidate role generation without premature commitment."""

from __future__ import annotations

from dataclasses import dataclass

from slm.tokenizer import Token


ROLE_NAMES = {
    "noun",
    "verb",
    "adjective",
    "adverb",
    "determiner",
    "preposition",
    "conjunction",
    "auxiliary",
    "modal",
    "punctuation",
}

DETERMINERS = {"a", "an", "the", "this", "that", "these", "those", "some", "any"}
PREPOSITIONS = {"for", "to", "from", "with", "by", "in", "on", "of", "as", "at"}
CONJUNCTIONS = {"and", "or", "but", "while", "because", "if"}
AUXILIARIES = {"be", "am", "is", "are", "was", "were", "do", "does", "did", "have", "has", "had"}
MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}
COMMON_VERBS = {
    "build",
    "create",
    "design",
    "make",
    "parse",
    "compile",
    "run",
    "detect",
    "emit",
    "produce",
    "convert",
}
TECHNICAL_NOUNS = {"compiler", "fpga", "hardware", "software", "model", "graph", "parser"}


@dataclass(frozen=True)
class RoleCandidate:
    role: str
    activation: float
    source: str


def candidate_roles_for(token: Token) -> list[RoleCandidate]:
    """Return ranked-but-uncommitted role candidates for a token."""
    if token.is_punctuation:
        return [RoleCandidate("punctuation", 1.0, "punctuation")]

    word = token.normalized
    candidates: list[RoleCandidate] = []

    if word in DETERMINERS:
        candidates.append(RoleCandidate("determiner", 0.95, "closed-class"))
    if word in PREPOSITIONS:
        candidates.append(RoleCandidate("preposition", 0.95, "closed-class"))
    if word in CONJUNCTIONS:
        candidates.append(RoleCandidate("conjunction", 0.95, "closed-class"))
    if word in AUXILIARIES:
        candidates.append(RoleCandidate("auxiliary", 0.95, "closed-class"))
    if word in MODALS:
        candidates.append(RoleCandidate("modal", 0.95, "closed-class"))

    if word in COMMON_VERBS or word.endswith(("ize", "ify")):
        candidates.append(RoleCandidate("verb", 0.72, "lexical"))
    if word in TECHNICAL_NOUNS or word[:1].isupper():
        candidates.append(RoleCandidate("noun", 0.72, "lexical"))
    if word.endswith("ly"):
        candidates.append(RoleCandidate("adverb", 0.68, "suffix"))
    if word.endswith(("al", "ive", "ous", "ic", "ary")):
        candidates.append(RoleCandidate("adjective", 0.58, "suffix"))

    open_class_roles = {"noun", "verb", "adjective"}
    existing = {candidate.role for candidate in candidates}
    for role in open_class_roles - existing:
        candidates.append(RoleCandidate(role, 0.35, "open-class-prior"))

    return sorted(candidates, key=lambda candidate: candidate.activation, reverse=True)


def build_candidate_roles(tokens: list[Token]) -> dict[int, list[RoleCandidate]]:
    return {token.index: candidate_roles_for(token) for token in tokens}
