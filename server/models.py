"""Pydantic v2 models for workspace input/output."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class BusinessIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    website: HttpUrl
    description: str = Field(min_length=1, max_length=2000)
    audiences: list[str] = Field(default_factory=list, max_length=5)
    geographies: list[str] = Field(default_factory=list, max_length=5)
    stage: Literal["seed", "growth", "mature"] = "seed"


class BrandIn(BaseModel):
    accent_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    voice_notes: str = ""
    logo_path: str = ""


class LinkedInIn(BaseModel):
    access_token: str = Field(min_length=10)
    account_id: str
    org_urn: str


class FacebookIn(BaseModel):
    access_token: str = Field(min_length=10)
    account_id: str
    page_id: str


class OnboardIn(BaseModel):
    business: BusinessIn
    brand: BrandIn
    linkedin: LinkedInIn
    facebook: FacebookIn
