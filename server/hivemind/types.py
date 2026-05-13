"""Shared types for Strategist + Diagnose chains."""

from __future__ import annotations
from typing import Literal, TypedDict


Tier = Literal["A", "B"]
Platform = Literal["linkedin", "facebook"]


class BusinessContext(TypedDict):
    name: str
    description: str
    audiences: list[str]
    geographies: list[str]
    stage: str
    voice_notes: str
    focus_notes: str


class Angle(TypedDict):
    id: str
    angle: str
    rationale: str
    framework_cited: str | None


class GeneratedDraft(TypedDict):
    headline: str
    body: str
    cta: str
    image_prompt: str
    rationale: str
    angle_id: str


class StrategistOutput(TypedDict):
    diagnosed_gaps: list[str]
    opportunity_angles: list[Angle]
    tier: Tier
    framework_cited: str | None


class DiagnoseKillRec(TypedDict):
    target_id: str
    reasoning: str
    framework_cited: str | None


class DiagnoseOutput(TypedDict):
    summary: str
    kill_recommendations: list[DiagnoseKillRec]
    replacement_angles: list[Angle]
    tier: Tier
