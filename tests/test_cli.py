from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from llm_recursive_refiner.__main__ import app
from llm_recursive_refiner.models import CritiqueResult, RoundResult

runner = CliRunner()


def _make_round(iteration: int = 1, score: float = 0.9, stopped_early: bool = True) -> RoundResult:
    return RoundResult(
        iteration=iteration,
        revision="Refined text here.",
        critique=CritiqueResult(score=score, feedback="Good job."),
        stopped_early=stopped_early,
    )


def test_cli_prompt_flag(tmp_path):
    """--prompt flag produces exit code 0 and final revision text in stdout."""
    result_obj = _make_round(stopped_early=True)
    with patch("llm_recursive_refiner.__main__.Refiner") as MockRefiner:
        instance = MockRefiner.return_value
        instance.run.return_value = [result_obj]
        result = runner.invoke(app, ["--prompt", "Write a haiku", "--log", str(tmp_path / "run.jsonl")])

    assert result.exit_code == 0
    assert "Refined text here." in result.output


def test_cli_missing_prompt_exits():
    """No --prompt, no --file, no stdin → exit code 1."""
    result = runner.invoke(app, [])
    assert result.exit_code == 1


def test_cli_output_file(tmp_path):
    """--output writes final revision to the specified file."""
    out_file = tmp_path / "out.txt"
    result_obj = _make_round()
    with patch("llm_recursive_refiner.__main__.Refiner") as MockRefiner:
        instance = MockRefiner.return_value
        instance.run.return_value = [result_obj]
        result = runner.invoke(app, ["--prompt", "Hello", "--output", str(out_file), "--log", str(tmp_path / "run.jsonl")])

    assert result.exit_code == 0
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == "Refined text here."


def test_cli_jsonl_log_written(tmp_path):
    """--log path receives valid JSONL with iteration key per line."""
    log_file = tmp_path / "run.jsonl"
    rounds = [_make_round(i, 0.5 + i * 0.1, i == 2) for i in range(1, 3)]

    # Simulate Refiner that also writes the log itself
    def fake_run(prompt: str):
        for r in rounds:
            with open(str(log_file), "a", encoding="utf-8") as f:
                f.write(r.model_dump_json() + "\n")
        return rounds

    with patch("llm_recursive_refiner.__main__.Refiner") as MockRefiner:
        instance = MockRefiner.return_value
        instance.run.side_effect = fake_run
        result = runner.invoke(app, ["--prompt", "Hello", "--log", str(log_file)])

    assert result.exit_code == 0
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        data = json.loads(line)
        assert "iteration" in data


def test_cli_max_iters_flag(tmp_path):
    """--max-iters 2 instantiates Refiner with max_iters=2."""
    result_obj = _make_round()
    with patch("llm_recursive_refiner.__main__.Refiner") as MockRefiner:
        instance = MockRefiner.return_value
        instance.run.return_value = [result_obj]
        runner.invoke(app, ["--prompt", "Hello", "--max-iters", "2", "--log", str(tmp_path / "run.jsonl")])

    call_kwargs = MockRefiner.call_args
    assert call_kwargs.kwargs["max_iters"] == 2
