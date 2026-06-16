from __future__ import annotations

import enum
import sys
from pathlib import Path

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint

from .models import RoundResult
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

    # Resolve log path
    log_path: Path
    if log is not None:
        log_path = log
    elif output is not None:
        log_path = output.with_suffix(".jsonl")
    else:
        log_path = Path("refine_run.jsonl")

    results: list[RoundResult] = []

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
