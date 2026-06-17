from __future__ import annotations

import enum
import sys
from pathlib import Path

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint

from .models import RoundResult
from .presets import get_preset
from .refiner import Refiner

app = typer.Typer(add_completion=False)


class TaskType(str, enum.Enum):
    text = "text"
    code = "code"
    json = "json"


@app.command()
def main(
    prompt: str | None = typer.Option(None, "--prompt", "-p", help="Input prompt text"),
    file: Path | None = typer.Option(None, "--file", "-f", help="Path to file containing prompt"),
    max_iters: int = typer.Option(5, "--max-iters", help="Maximum refinement iterations"),
    threshold: float = typer.Option(0.8, "--threshold", help="Quality score threshold (0-1) to stop early"),
    model: str = typer.Option("claude-sonnet-4-6", "--model", help="Anthropic model to use"),
    task_type: TaskType = typer.Option(TaskType.text, "--task-type", help="Task type hint"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)"),
    log: Path | None = typer.Option(None, "--log", help="JSONL log file path"),
    preset: str | None = typer.Option(None, "--preset", help="Built-in preset: improve-essay | review-code | compress-summary"),
    compare: bool = typer.Option(False, "--compare", help="Run single-shot vs refined and print score delta"),
) -> None:
    # Resolve prompt
    input_text: str | None = None
    if prompt is not None:
        input_text = prompt
    elif file is not None:
        if not file.exists():
            typer.echo(f"Error: file {file} does not exist.", err=True)
            raise typer.Exit(1)
        input_text = file.read_text(encoding="utf-8").strip()
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read().strip()

    if not input_text:
        typer.echo("Error: provide a prompt via --prompt, --file, or stdin.", err=True)
        raise typer.Exit(1)

    # Resolve preset
    system_prompt: str | None = None
    critique_rubric: str | None = None
    if preset is not None:
        try:
            p = get_preset(preset)
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(1)
        system_prompt = p.system_prompt
        critique_rubric = p.critique_rubric

    # Resolve log path
    log_path: Path
    if log is not None:
        log_path = log
    elif output is not None:
        log_path = output.with_suffix(".jsonl")
    else:
        log_path = Path("refine_run.jsonl")

    results: list[RoundResult] = []

    # Single-shot baseline (before refinement progress bar so output is sequential)
    single_shot_score: float | None = None
    if compare:
        refiner_ss = Refiner(
            model=model,
            max_iters=max_iters,
            threshold=threshold,
            log_path=None,
            system_prompt=system_prompt,
            critique_rubric=critique_rubric,
        )
        single_shot_text = refiner_ss._generate(input_text)
        single_shot_critique = refiner_ss._critique(single_shot_text)
        single_shot_score = single_shot_critique.score

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task_id = progress.add_task(f"Iter 0/{max_iters}  score: —", total=100)

        def on_round(round_result: RoundResult) -> None:
            results.append(round_result)
            score_pct = int(round_result.critique.score * 100)
            progress.update(
                task_id,
                completed=score_pct,
                description=f"Iter {round_result.iteration}/{max_iters}  score: {round_result.critique.score:.2f}",
            )

        refiner = Refiner(
            model=model,
            max_iters=max_iters,
            threshold=threshold,
            log_path=str(log_path),
            on_round=on_round,
            system_prompt=system_prompt,
            critique_rubric=critique_rubric,
        )
        all_results = refiner.run(input_text)

    # on_round accumulates into results; use all_results as authoritative
    results = all_results

    # Final summary table
    table = Table(title="Refinement Summary", show_lines=True)
    table.add_column("Iter", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Stopped Early", justify="center")
    for r in results:
        table.add_row(
            str(r.iteration),
            f"{r.critique.score:.3f}",
            "Yes" if r.stopped_early else "No",
        )
    rprint(table)

    # Compare table
    if compare and single_shot_score is not None:
        final_score = results[-1].critique.score if results else 0.0
        delta = final_score - single_shot_score
        delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
        compare_table = Table(title="Single-shot vs Refined", show_lines=True)
        compare_table.add_column("Mode", justify="left")
        compare_table.add_column("Score", justify="right")
        compare_table.add_column("Δ Score", justify="right")
        compare_table.add_row("Single-shot", f"{single_shot_score:.3f}", "")
        compare_table.add_row(f"Refined (N={len(results)})", f"{final_score:.3f}", delta_str)
        rprint(compare_table)

    # Write final output
    final_text = results[-1].revision if results else ""
    if output is not None:
        output.write_text(final_text, encoding="utf-8")
        typer.echo(f"Output written to {output}", err=True)
    else:
        print(final_text)

    typer.echo(f"Log written to {log_path}", err=True)


if __name__ == "__main__":
    app()
