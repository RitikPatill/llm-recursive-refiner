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
│       ├── __init__.py      # package exports: Refiner, RoundResult, CritiqueResult
│       ├── __main__.py      # CLI entry point (stub, wired in M3)
│       ├── models.py        # Pydantic models: CritiqueResult, RoundResult
│       └── refiner.py       # Core Refiner class (generate → critique → revise loop)
├── tests/
│   ├── __init__.py
│   ├── test_placeholder.py
│   └── test_refiner.py      # Unit tests for Refiner (all mocked, no API key needed)
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

> The CLI interface below is the planned invocation. The entry point (`__main__.py`) is a stub until M3 wires it to the `Refiner` class.

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

## What works now (M2)

- **`Refiner` class** in `src/llm_recursive_refiner/refiner.py` — fully functional generate → critique → revise loop
- **Pydantic models** (`CritiqueResult`, `RoundResult`) in `models.py` as the shared data contract
- **JSONL logging** — pass `log_path=` to `Refiner` to get one JSON line per round
- **Early stopping** — loop halts as soon as `score >= threshold`; `RoundResult.stopped_early` is `True`
- **5 unit tests** in `tests/test_refiner.py` — all mocked, no API key required to run

```python
from llm_recursive_refiner import Refiner

refiner = Refiner(max_iters=4, threshold=0.8, log_path="run.jsonl")
results = refiner.run("Write a short essay about photosynthesis.")
for r in results:
    print(f"Round {r.iteration}: score={r.critique.score:.2f}")
print(results[-1].revision)
```

### Previously (M1)

- `src/` package layout, dependency set locked in `requirements.txt`, stub entry point, MIT license

## Project status

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Scaffold + README | ✅ Done |
| M2 | Core refine loop + data models | ✅ Done |
| M3 | Rich terminal UI + CLI wiring | Planned |
| M4 | Rich terminal UI + `--compare` flag | Planned |
| M5 | Task presets + packaging | Planned |
