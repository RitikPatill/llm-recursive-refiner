from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Preset:
    name: str
    system_prompt: str
    critique_rubric: str


PRESETS: dict[str, Preset] = {
    "improve-essay": Preset(
        name="improve-essay",
        system_prompt=(
            "You are an expert writing coach. Help the user produce clear, well-argued, "
            "and stylistically polished prose. Focus on logical flow, concrete evidence, "
            "and engaging language."
        ),
        critique_rubric=(
            "Score the text on three dimensions: "
            "(1) Clarity — is the argument easy to follow? "
            "(2) Argumentation — are claims supported with evidence or reasoning? "
            "(3) Style — is the language engaging and varied? "
            "Combine these into a single 0–1 score. "
        ),
    ),
    "review-code": Preset(
        name="review-code",
        system_prompt=(
            "You are a senior software engineer performing a thorough code review. "
            "Evaluate correctness, readability, and efficiency. Point out bugs, unclear "
            "naming, missing edge-case handling, and performance concerns."
        ),
        critique_rubric=(
            "Score the code on three dimensions: "
            "(1) Correctness — does it do what it should, with no bugs or edge-case failures? "
            "(2) Readability — is it easy to understand, with clear naming and structure? "
            "(3) Efficiency — are there obvious algorithmic or resource improvements? "
            "Combine these into a single 0–1 score. "
        ),
    ),
    "compress-summary": Preset(
        name="compress-summary",
        system_prompt=(
            "You are a summarization expert. Distill source material into the most concise "
            "form possible while retaining every key fact, date, and conclusion. "
            "Remove filler phrases, redundancy, and tangential detail."
        ),
        critique_rubric=(
            "Score the summary on three dimensions: "
            "(1) Conciseness — is every word earning its place? "
            "(2) Accuracy — are all facts and conclusions faithfully represented? "
            "(3) Coverage — are the most important points from the source included? "
            "Combine these into a single 0–1 score. "
        ),
    ),
}


def get_preset(name: str) -> Preset:
    """Return the named preset, or raise ValueError for unknown names."""
    try:
        return PRESETS[name]
    except KeyError:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown preset {name!r}. Known presets: {known}") from None
