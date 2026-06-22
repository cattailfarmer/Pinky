# Semantic Logic Model Prototype

This is a small, meaning-first Semantic Logic Model (SLM) prototype.

It is not a machine learning model. It parses natural language into unresolved
semantic candidates, diffuses structural constraints through those candidates,
preserves uncertainty, and emits a compact semantic primer for later reasoning
or language generation.

## Demo

```powershell
python -m slm.demo "Design a compiler for FPGA hardware."
```

## Tests

```powershell
python -m pytest
```

## Architecture

- `tokenizer.py` creates stable token objects.
- `candidate_roles.py` assigns possible roles without committing too early.
- `semantic_graph.py` stores immutable glyphs and append-only edges/events.
- `diffusion.py` applies structural passes that rank, defer, and refine.
- `wobble.py` measures unresolved instability.
- `primer.py` emits a compact structured SLM primer.

The prototype favors explicit uncertainty over forced interpretation. Semantic
IDs are immutable once created; later passes append events, activations, links,
or retirements instead of rewriting identities.
