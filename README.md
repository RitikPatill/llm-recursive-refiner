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
│       ├── __main__.py      # Typer CLI entry point
│       ├── models.py        # Pydantic models: CritiqueResult, RoundResult
│       ├── presets.py       # Built-in task presets (improve-essay, review-code, compress-summary)
│       └── refiner.py       # Core Refiner class (generate → critique → revise loop)
├── tests/
│   ├── __init__.py
│   ├── test_placeholder.py
│   ├── test_presets.py      # Unit tests for presets module
│   ├── test_refiner.py      # Unit tests for Refiner (all mocked, no API key needed)
│   └── test_cli.py          # Unit tests for CLI (all mocked, no API key needed)
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

```bash
export ANTHROPIC_API_KEY=sk-...

python -m llm_recursive_refiner \
  --prompt "Write a short essay on photosynthesis" \
  --max-iters 4 \
  --threshold 0.8

# or read from a file
python -m llm_recursive_refiner --file draft.txt --output refined.txt --log run.jsonl

# or pipe from stdin
echo "My rough draft text" | python -m llm_recursive_refiner
```

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt` / `-p` | — | Input prompt text |
| `--file` / `-f` | — | Path to file containing the prompt |
| `--max-iters` | `5` | Maximum refinement iterations |
| `--threshold` | `0.8` | Quality score (0–1) to stop early |
| `--model` | `claude-sonnet-4-6` | Anthropic model ID |
| `--task-type` | `text` | Hint: `text`, `code`, or `json` |
| `--output` / `-o` | stdout | Write final text to this file |
| `--log` | `refine_run.jsonl` | JSONL log of every round |
| `--preset` | — | Built-in preset: `improve-essay`, `review-code`, `compress-summary` |
| `--compare` | off | Run single-shot alongside refinement and print score delta |

Prompt resolution order: `--prompt` → `--file` → stdin. Exits with code 1 if none provided.

### Task presets

Use `--preset <name>` to inject a domain-specific system prompt and scoring rubric:

| Preset | System role | Rubric dimensions |
|--------|-------------|-------------------|
| `improve-essay` | Writing coach | Clarity, argumentation, style |
| `review-code` | Senior engineer | Correctness, readability, efficiency |
| `compress-summary` | Summarization expert | Conciseness, accuracy, coverage |

### Compare mode

```bash
python -m llm_recursive_refiner \
  --prompt "Write a short essay on photosynthesis" \
  --preset improve-essay \
  --compare
```

Prints a side-by-side table after refinement:

```
┌──────────────────┬────────┬─────────┐
│ Mode             │ Score  │ Δ Score │
├──────────────────┼────────┼─────────┤
│ Single-shot      │ 0.412  │         │
│ Refined (N=3)    │ 0.813  │ +0.401  │
└──────────────────┴────────┴─────────┘
```

## How it works

1. **Generate** — the model produces an initial draft for your task. If a preset or custom `--system-prompt` is supplied, it is injected here.
2. **Critique** — the model scores the draft (0–1) and lists specific weaknesses. Preset rubric dimensions guide the scoring criteria.
3. **Revise** — the model rewrites the draft, targeting the identified weaknesses.
4. **Repeat** — steps 2–3 loop until the score exceeds `--threshold` or `--max-iters` is reached.

Each round is appended to a `.jsonl` log file for reproducibility. The terminal renders a live score bar and a final unified diff showing total changes across all revisions.

With `--compare`, a single-shot generation (one pass, no refinement) is scored before the loop begins; the final Rich table shows both scores and the delta.

## What works now (M4)

- **Task presets** — `--preset improve-essay | review-code | compress-summary` injects a domain system prompt and scoring rubric
- **Compare mode** — `--compare` runs a single-shot generation before the refinement loop and prints a Rich table with the score delta
- **`presets.py` module** — `Preset` dataclass + `PRESETS` registry + `get_preset()` helper
- **`system_prompt` / `critique_rubric` on `Refiner`** — presets (or custom prompts) wire directly into `_generate` and `_critique` API calls
- **17 unit tests** (7 refiner + 8 CLI + 4 preset) — all mocked, no API key required

### Previously (M3)

- **Full Typer CLI** in `src/llm_recursive_refiner/__main__.py` — all flags wired up
- **Rich live progress** — spinner + score bar updated each iteration via `on_round` callback
- **Final summary table** — Rich table showing iter, score, and early-stop status
- **JSONL log** — written alongside output; auto-named `refine_run.jsonl` when `--log` omitted

### Previously (M2)

- **`Refiner` class** in `src/llm_recursive_refiner/refiner.py` — fully functional generate → critique → revise loop
- **Pydantic models** (`CritiqueResult`, `RoundResult`) in `models.py` as the shared data contract
- **JSONL logging** — pass `log_path=` to `Refiner` to get one JSON line per round
- **Early stopping** — loop halts as soon as `score >= threshold`; `RoundResult.stopped_early` is `True`

### Previously (M1)

- `src/` package layout, dependency set locked in `requirements.txt`, MIT license

## Project status

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Scaffold + README | ✅ Done |
| M2 | Core refine loop + data models | ✅ Done |
| M3 | Rich terminal UI + CLI wiring | ✅ Done |
| M4 | Task presets + compare mode | ✅ Done |
| M5 | Packaging + PyPI publish | Planned |

## License

MIT. See [LICENSE](LICENSE).
