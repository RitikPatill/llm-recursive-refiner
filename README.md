# llm-recursive-refiner

A command-line tool that implements **recursive self-refinement** for language model outputs.

## What is recursive self-refinement?

Recursive self-refinement (RSR) is an iterative prompting technique where a language model generates an initial response, critiques its own output, and then revises based on that critique — repeating until quality converges. Research on Recursive Language Models (RLMs) shows this loop reliably outperforms single-shot generation on writing, code review, argument construction, and summarisation tasks because each revision targets concrete weaknesses identified in the previous round.

## What this tool does

`llm-recursive-refiner` runs a configurable generate → critique → revise loop using the Anthropic API. You give it a task via stdin, file, or `--prompt` flag; it iterates up to `--max-iters` times, stopping early when a quality score crosses `--threshold`. Every round is logged as a structured JSONL entry (revision text, critique, numeric quality score 0–1, unified diff). The terminal shows a live Rich-rendered progress table; final output goes to stdout or a file.

## Repository layout

```
llm-recursive-refiner/
├── src/
│   └── llm_recursive_refiner/
│       ├── __init__.py      # package version (0.1.0)
│       └── __main__.py      # CLI entry point (stub, implemented in M2+)
├── tests/
│   ├── __init__.py
│   └── test_placeholder.py
├── requirements.txt         # pinned deps: anthropic, rich, typer, pydantic
├── pyproject.toml
├── LICENSE                  # MIT
└── .gitignore
```

## Installation

```bash
pip install -r requirements.txt
```

A PyPI package will be published in a later milestone.

## Quick start

> The CLI interface below is the planned invocation. The entry point is a stub until M2 lands.

```bash
python -m llm_recursive_refiner \
  --prompt "Write a short essay on photosynthesis" \
  --max-iters 4 \
  --threshold 0.8
```

## How it works

1. **Generate** — the model produces an initial draft for your task.
2. **Critique** — the model scores the draft (0–1) and lists specific weaknesses.
3. **Revise** — the model rewrites the draft, targeting the identified weaknesses.
4. **Repeat** — steps 2–3 loop until the score exceeds `--threshold` or `--max-iters` is reached.

Each round is appended to a `.jsonl` log file for reproducibility. The terminal renders a live score bar and a final unified diff showing total changes across all revisions.

## What works now (M1)

- `src/` package layout with `llm_recursive_refiner` importable as a module (`v0.1.0`)
- Dependency set locked in `requirements.txt`: `anthropic==0.28.0`, `rich==13.7.1`, `typer==0.12.3`, `pydantic==2.7.1`
- Stub entry point (`python -m llm_recursive_refiner`) runs without error
- MIT license, `.gitignore`, and `pyproject.toml` in place
- Placeholder test suite under `tests/`

## Project status

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Scaffold + README | ✅ Done |
| M2 | Core data models + Anthropic client | Planned |
| M3 | Refine loop + JSONL logging | Planned |
| M4 | Rich terminal UI + `--compare` flag | Planned |
| M5 | Task presets + packaging | Planned |
