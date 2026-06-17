from __future__ import annotations

import difflib
import json
import re
from collections.abc import Callable

import anthropic

from .models import CritiqueResult, RoundResult


class Refiner:
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        max_iters: int = 5,
        threshold: float = 0.8,
        log_path: str | None = None,
        client: anthropic.Anthropic | None = None,
        on_round: Callable[[RoundResult], None] | None = None,
        system_prompt: str | None = None,
        critique_rubric: str | None = None,
    ):
        self.model = model
        self.max_iters = max_iters
        self.threshold = threshold
        self.log_path = log_path
        self.client = client if client is not None else anthropic.Anthropic()
        self.on_round = on_round
        self.system_prompt = system_prompt
        self.critique_rubric = critique_rubric

    def run(self, prompt: str) -> list[RoundResult]:
        results: list[RoundResult] = []

        text = self._generate(prompt)
        prev_text: str | None = None

        for i in range(1, self.max_iters + 1):
            critique = self._critique(text)
            stopped_early = critique.score >= self.threshold
            diff = self._compute_diff(prev_text, text) if prev_text is not None else None

            round_result = RoundResult(
                iteration=i,
                revision=text,
                critique=critique,
                stopped_early=stopped_early,
                diff=diff,
            )
            prev_text = text
            results.append(round_result)

            if self.log_path:
                self._append_log(self.log_path, round_result)

            if self.on_round:
                self.on_round(round_result)

            if stopped_early:
                break

            if i < self.max_iters:
                text = self._revise(text, critique.feedback, prompt)

        return results

    def _generate(self, prompt: str) -> str:
        message = f"{prompt}\n\nWrite a first draft. Output ONLY the draft, no preamble."
        kwargs: dict = dict(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": message}],
        )
        if self.system_prompt:
            kwargs["system"] = self.system_prompt
        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def _critique(self, text: str) -> CritiqueResult:
        rubric_prefix = self.critique_rubric if self.critique_rubric else ""
        message = (
            rubric_prefix
            + 'Critique the following text. Respond with ONLY valid JSON matching this schema:\n'
            '{"score": <float 0-1>, "feedback": "<actionable weaknesses>"}\n\n'
            f"TEXT:\n{text}"
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": message}],
        )
        raw = response.content[0].text

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Critic returned invalid JSON: {raw!r}") from e

        score = max(0.0, min(1.0, float(data["score"])))
        return CritiqueResult(score=score, feedback=data["feedback"])

    def _revise(self, text: str, feedback: str, task_prompt: str) -> str:
        message = (
            f"Original task: {task_prompt}\n\n"
            f"Previous version:\n{text}\n\n"
            f"Critique and feedback:\n{feedback}\n\n"
            "Rewrite the text, addressing every point in the feedback. "
            "Output ONLY the revised text, no preamble."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": message}],
        )
        return response.content[0].text

    def _compute_diff(self, old: str, new: str) -> str:
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        return "\n".join(difflib.unified_diff(
            old_lines, new_lines,
            fromfile="previous", tofile="revised", lineterm=""
        ))

    def _append_log(self, path: str, round_result: RoundResult) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(round_result.model_dump_json() + "\n")
