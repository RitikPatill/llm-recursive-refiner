from pydantic import BaseModel


class CritiqueResult(BaseModel):
    score: float  # 0.0–1.0
    feedback: str  # actionable weaknesses


class RoundResult(BaseModel):
    iteration: int
    revision: str
    critique: CritiqueResult
    stopped_early: bool  # True if this round triggered threshold exit
