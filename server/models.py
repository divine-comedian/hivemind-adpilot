"""Pydantic v2 models for workspace input/output."""

from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class OnboardIn(BaseModel):
    website_url: HttpUrl


class LinkedInCredentialsIn(BaseModel):
    access_token: str = Field(min_length=10)
    account_id: str
    org_urn: str = Field(pattern=r"^urn:li:organization:\d+$")


class FacebookCredentialsIn(BaseModel):
    access_token: str = Field(min_length=10)
    account_id: str
    page_id: str


class CredentialsIn(BaseModel):
    linkedin: LinkedInCredentialsIn | None = None
    facebook: FacebookCredentialsIn | None = None


class VoicePatch(BaseModel):
    voice_notes: str = ""
    focus_notes: str = ""


class ProjectInfoPatch(BaseModel):
    project_name: str = Field(min_length=1)
    description: str = ""
    geographics: list[str] = Field(default_factory=list, max_length=5)


class DraftIdeaRefineIn(BaseModel):
    angle: dict
    guidance: str = Field(min_length=1, max_length=1200)
    conversation_id: str | None = None


class DraftIdeaDismissIn(BaseModel):
    angle_id: str = Field(min_length=1)


class GenerateJobIn(BaseModel):
    platforms: list[Literal["linkedin", "facebook"]] = Field(default_factory=lambda: ["linkedin"])
    count: int = Field(default=5, ge=1, le=20)
    focus_note: str = Field(default="", max_length=2000)
    angle: dict | None = None
    angle_id: str | None = None
    conversation_id: str | None = None
    ads_per_platform: int = Field(default=3, ge=1, le=10)
