from slm.diffusion import analyze
from slm.tokenizer import tokenize


def test_tokenizer_preserves_punctuation() -> None:
    tokens = tokenize("Design a compiler for FPGA hardware.")

    assert [token.text for token in tokens] == ["Design", "a", "compiler", "for", "FPGA", "hardware", "."]


def test_demo_sentence_produces_action_subjects_and_primer() -> None:
    result = analyze("Design a compiler for FPGA hardware.")

    assert result.candidates[0][0].role == "verb"
    assert any(hint.relation == "introduces_subject_candidate" for hint in result.structural_hints)
    assert any(hint.relation == "opens_relation_constraint" for hint in result.structural_hints)
    assert result.primer["actions"]
    assert result.primer["subjects"]
    assert result.primer["uncertainty"]["wobble"] < 0.4


def test_uncertainty_is_preserved_for_open_class_tokens() -> None:
    result = analyze("Design a compiler for FPGA hardware.")
    deferred = result.primer["uncertainty"]["deferred_roles"]

    assert "Design" in deferred
    assert any(role["role"] == "noun" for role in deferred["Design"])
