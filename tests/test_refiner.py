import json
from unittest.mock import MagicMock, patch

import pytest

from llm_recursive_refiner.refiner import Refiner
from llm_recursive_refiner.models import CritiqueResult, RoundResult


def _make_client(responses: list[str]) -> MagicMock:
    """Build a mock anthropic.Anthropic client that returns responses in order."""
    client = MagicMock()
    side_effects = []
    for text in responses:
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        side_effects.append(msg)
    client.messages.create.side_effect = side_effects
    return client


def test_stops_at_threshold():
    """Critic returns score=0.95 on round 1 → only 1 RoundResult with stopped_early=True."""
    generate_text = "First draft."
    critique_json = '{"score": 0.95, "feedback": "Excellent, minor polish only."}'

    client = _make_client([generate_text, critique_json])
    refiner = Refiner(max_iters=3, threshold=0.9, client=client)
    results = refiner.run("Write a paragraph about the ocean.")

    assert len(results) == 1
    assert results[0].stopped_early is True
    assert results[0].iteration == 1
    assert results[0].critique.score == pytest.approx(0.95)


def test_runs_max_iters():
    """Critic always returns score=0.3 → exactly max_iters results, last stopped_early=False."""
    max_iters = 3
    low_critique = '{"score": 0.3, "feedback": "Needs significant improvement."}'

    # generate + (critique + revise) * (max_iters - 1) + final critique
    responses = ["First draft."]
    for _ in range(max_iters - 1):
        responses.append(low_critique)
        responses.append("Revised draft.")
    responses.append(low_critique)

    client = _make_client(responses)
    refiner = Refiner(max_iters=max_iters, threshold=0.9, client=client)
    results = refiner.run("Write something.")

    assert len(results) == max_iters
    assert results[-1].stopped_early is False
    for r in results:
        assert r.critique.score == pytest.approx(0.3)


def test_critique_parse_error():
    """_critique with plain-text response raises ValueError."""
    client = _make_client(["This is not JSON at all."])
    refiner = Refiner(client=client)

    with pytest.raises(ValueError, match="Critic returned invalid JSON"):
        refiner._critique("Some text to critique.")


def test_jsonl_logging(tmp_path):
    """Each round is logged as a valid JSON line with required keys."""
    log_file = tmp_path / "run.jsonl"
    max_iters = 2
    low_critique = '{"score": 0.4, "feedback": "Keep improving."}'

    responses = ["Draft."]
    for _ in range(max_iters - 1):
        responses.append(low_critique)
        responses.append("Better draft.")
    responses.append(low_critique)

    client = _make_client(responses)
    refiner = Refiner(max_iters=max_iters, threshold=0.9, log_path=str(log_file), client=client)
    results = refiner.run("Task prompt.")

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(results)

    for line in lines:
        data = json.loads(line)
        assert "iteration" in data
        assert "revision" in data
        assert "critique" in data
        assert "stopped_early" in data


def test_system_prompt_passed_to_api():
    """Refiner with system_prompt passes it as system= to messages.create."""
    generate_text = "First draft."
    critique_json = '{"score": 0.95, "feedback": "Great."}'

    client = _make_client([generate_text, critique_json])
    refiner = Refiner(max_iters=1, threshold=0.9, system_prompt="Be concise.", client=client)
    refiner.run("Write something.")

    # The first call is _generate — check it received system="Be concise."
    first_call_kwargs = client.messages.create.call_args_list[0].kwargs
    assert first_call_kwargs.get("system") == "Be concise."


def test_critique_rubric_prepended():
    """Refiner with critique_rubric prepends it to the critique prompt."""
    critique_json = '{"score": 0.7, "feedback": "OK."}'

    client = _make_client([critique_json])
    refiner = Refiner(client=client, critique_rubric="Score X on Y. ")
    refiner._critique("some text")

    call_kwargs = client.messages.create.call_args.kwargs
    message_content = call_kwargs["messages"][0]["content"]
    assert message_content.startswith("Score X on Y. ")


def test_round_result_fields():
    """RoundResult fields have correct types and value ranges."""
    generate_text = "My draft."
    # Score above threshold so loop stops after 1 round (no revise call needed)
    critique_json = '{"score": 0.72, "feedback": "Could be more specific."}'

    client = _make_client([generate_text, critique_json])
    refiner = Refiner(max_iters=3, threshold=0.5, client=client)
    results = refiner.run("Write something.")

    r = results[0]
    assert isinstance(r, RoundResult)
    assert isinstance(r.iteration, int) and r.iteration >= 1
    assert isinstance(r.revision, str)
    assert isinstance(r.critique, CritiqueResult)
    assert isinstance(r.critique.score, float)
    assert 0.0 <= r.critique.score <= 1.0
    assert isinstance(r.stopped_early, bool)
