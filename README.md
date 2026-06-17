# LLM Recursive Refiner

> CLI tool that iteratively self-improves LLM outputs through critique-and-revise loops with configurable stopping criteria and diff visualization.

<!-- TODO: replace with a 5-10 second demo gif. Record with ScreenToGif on
     Windows or peek on macOS. Save to docs/demo.gif and update path here. -->
![demo](docs/demo.gif)

## What it is

`llm-recursive-refiner` runs a generate → critique → revise loop against the Anthropic API. You give it a task via `--prompt`, a file, or stdin. Each iteration, the model scores its own output (0–1), identifies specific weaknesses, and rewrites — stopping when the score clears `--threshold` or `--max-iters` is exhausted. Every round is appended to a structured JSONL log containing the revision text, critique, numeric score, and a unified diff vs. the previous version.

The terminal renders a live Rich progress table with per-round score bars and colour-coded diffs. Three built-in presets (`improve-essay`, `review-code`, `compress-summary`) inject domain-specific system prompts and scoring rubrics. A `--compare` flag runs a single-shot baseline alongside the refinement loop and prints the score delta in a summary table.

## Quickstart

```bash
git clone https://github.com/RitikPatill/llm-recursive-refiner.git
cd llm-recursive-refiner
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...

python -m llm_recursive_refiner \
  --prompt "Write a short essay on photosynthesis" \
  --max-iters 4 \
  --threshold 0.8
```

Requires Python 3.10+.

## Usage

Pass input via `--prompt`, `--file`, or stdin (resolution order: prompt → file → stdin). The tool exits with code 1 if no input is provided.

```bash
# Refine a file using the essay preset; save output and log
python -m llm_recursive_refiner \
  --file draft.txt \
  --preset improve-essay \
  --output refined.txt \
  --log run.jsonl

# Pipe from stdin
echo "My rough draft" | python -m llm_recursive_refiner --task-type text

# Compare single-shot vs. refined on a code review task
python -m llm_recursive_refiner \
  --file snippet.py \
  --preset review-code \
  --compare
```

The `--compare` flag prints a table after the loop:

```
┌──────────────────┬────────┬─────────┐
│ Mode             │ Score  │ Δ Score │
├──────────────────┼────────┼─────────┤
│ Single-shot      │ 0.412  │         │
│ Refined (N=3)    │ 0.813  │ +0.401  │
└──────────────────┴────────┴─────────┘
```

**All flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt` / `-p` | — | Input prompt text |
| `--file` / `-f` | — | Path to file containing the prompt |
| `--max-iters` | `5` | Maximum refinement iterations |
| `--threshold` | `0.8` | Quality score (0–1) at which to stop early |
| `--model` | `claude-sonnet-4-6` | Anthropic model ID |
| `--task-type` | `text` | Scoring hint: `text`, `code`, or `json` |
| `--output` / `-o` | stdout | Write final text to this file |
| `--log` | `refine_run.jsonl` | JSONL log of every round |
| `--preset` | — | `improve-essay`, `review-code`, `compress-summary` |
| `--compare` | off | Score a single-shot baseline and print the delta |

## Architecture

```
input (prompt / file / stdin)
        │
        ▼
   _generate()  ◄── system prompt (preset or custom)
        │
        ▼
   _critique()  ──► score (0–1) + weaknesses
        │
   score ≥ threshold? ──yes──► write output + summary table
        │ no
        ▼
    _revise()   ──► new draft + unified diff
        │
        └──► append RoundResult to .jsonl ──► (next round)
```

## Project structure

```
llm-recursive-refiner/
├── src/
│   └── llm_recursive_refiner/
│       ├── __init__.py      # public exports: Refiner, RoundResult, CritiqueResult
│       ├── __main__.py      # Typer CLI entry point
│       ├── models.py        # Pydantic models: CritiqueResult, RoundResult
│       ├── presets.py       # Built-in task presets and Preset dataclass
│       └── refiner.py       # Core Refiner class (generate → critique → revise loop)
├── tests/
│   ├── test_refiner.py      # Refiner unit tests (all mocked, no API key needed)
│   ├── test_cli.py          # CLI unit tests (all mocked, no API key needed)
│   └── test_presets.py      # Preset registry tests
├── pyproject.toml           # package metadata and entry-point (refine = ...)
├── requirements.txt         # pinned: anthropic, rich, typer, pydantic
└── LICENSE                  # MIT
```

## Roadmap

- [ ] PyPI release so users can `pip install llm-recursive-refiner` without cloning
- [ ] `--system-prompt` flag for fully custom rubrics without editing source
- [ ] Streaming output during generation so long revisions don't stall the terminal
- [ ] HTML/Markdown report export from the JSONL log
- [ ] Support for OpenAI-compatible endpoints via a thin adapter layer

## License

MIT — see [LICENSE](LICENSE).

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
