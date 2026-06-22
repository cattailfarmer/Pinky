# SLM Rust Projection

This crate is the Rust target projection for the Semantic Logic Model prototype.

The source authority remains the SOP specification set under:

- `../slm_project/source_documents/2026-06-20_slm_intake/`
- `../slm_project/specifications/`
- `../slm_project/specifications/contracts/`

Current status: v0 deterministic prototype implemented.

Build the lexical substrate before running lexicon-backed demos:

```powershell
cd ..\slm_lexicon
python scripts\download_open_english_wordnet.py
python scripts\build_lexicon_db.py
python scripts\build_lexical_substrate_pack.py
cd ..\slm_rust
```

Run the default demo after Cargo-generated executables are allowed by Windows
Application Control:

```powershell
$env:Path="$env:USERPROFILE\.cargo\bin;$env:Path"
cargo run --quiet --bin slm_demo
```

The demo defaults to:

```text
Design a compiler for FPGA hardware.
```

It emits JSON with tokens, candidate roles, structural relation hints, diffusion
trace, semantic graph, wobble vector, and final SLM primer.

Current local note: this machine blocked Cargo-generated build/test executables
under `target/` during lexical integration. The Rust source has been adjusted to
avoid native SQLite bindings and use the generated SLM Lexical Substrate Pack;
the remaining build gate is Windows policy around Cargo's generated executables,
not the SLM source layout.
