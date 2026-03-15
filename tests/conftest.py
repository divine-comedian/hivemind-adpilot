"""Shared test fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set test env vars so scripts don't need a real .env."""
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "test-token-123")
    monkeypatch.setenv("LINKEDIN_AD_ACCOUNT_ID", "520217301")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "test-fb-token-456")
    monkeypatch.setenv("FACEBOOK_AD_ACCOUNT_ID", "22243234")
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
