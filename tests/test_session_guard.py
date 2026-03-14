"""Tests for session_guard.py — per-session spend and image cap enforcement."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.session_guard import (
    SessionGuard,
    SessionOverLimitError,
    DEFAULT_MAX_SPEND,
    DEFAULT_MAX_IMAGES,
    DEFAULT_WINDOW_HOURS,
)


@pytest.fixture
def state_file(tmp_path):
    """Provide a temp path for session state."""
    return tmp_path / "session_state.json"


@pytest.fixture
def guard(state_file):
    """Create a SessionGuard with default limits using temp state file."""
    return SessionGuard(state_file=state_file)


class TestSessionGuardInit:
    def test_creates_fresh_session_on_first_use(self, guard, state_file):
        status = guard.check()
        assert status["remaining_spend"] == DEFAULT_MAX_SPEND
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES
        assert state_file.exists()

    def test_loads_existing_session(self, guard, state_file):
        guard.record_spend(1.00)
        guard.record_image()

        guard2 = SessionGuard(state_file=state_file)
        status = guard2.check()
        assert status["remaining_spend"] == pytest.approx(DEFAULT_MAX_SPEND - 1.00)
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES - 1


class TestSpendTracking:
    def test_record_spend_updates_total(self, guard):
        guard.record_spend(0.20)
        status = guard.check()
        assert status["remaining_spend"] == pytest.approx(DEFAULT_MAX_SPEND - 0.20)

    def test_raises_when_spend_exceeds_limit(self, guard):
        guard.record_spend(DEFAULT_MAX_SPEND - 0.01)
        with pytest.raises(SessionOverLimitError, match="spend"):
            guard.require_budget(0.20)

    def test_require_budget_passes_when_under_limit(self, guard):
        guard.require_budget(0.20)  # should not raise


class TestImageTracking:
    def test_record_image_updates_count(self, guard):
        guard.record_image()
        guard.record_image()
        status = guard.check()
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES - 2

    def test_raises_when_images_exceed_limit(self, guard):
        for _ in range(DEFAULT_MAX_IMAGES):
            guard.record_image()
        with pytest.raises(SessionOverLimitError, match="image"):
            guard.require_image()


class TestSessionExpiry:
    def test_session_resets_after_window(self, guard, state_file):
        guard.record_spend(5.00)

        # Fake the session start to be past the window
        state = json.loads(state_file.read_text())
        state["session_start"] = time.time() - (DEFAULT_WINDOW_HOURS * 3600 + 1)
        state_file.write_text(json.dumps(state))

        guard2 = SessionGuard(state_file=state_file)
        status = guard2.check()
        assert status["remaining_spend"] == DEFAULT_MAX_SPEND

    def test_session_persists_within_window(self, guard, state_file):
        guard.record_spend(5.00)
        guard2 = SessionGuard(state_file=state_file)
        status = guard2.check()
        assert status["remaining_spend"] == pytest.approx(DEFAULT_MAX_SPEND - 5.00)


class TestReset:
    def test_manual_reset_clears_session(self, guard):
        guard.record_spend(5.00)
        guard.record_image()
        guard.reset()
        status = guard.check()
        assert status["remaining_spend"] == DEFAULT_MAX_SPEND
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES


class TestCustomLimits:
    def test_custom_spend_limit(self, state_file, monkeypatch):
        monkeypatch.setenv("SESSION_MAX_SPEND", "5.00")
        g = SessionGuard(state_file=state_file)
        status = g.check()
        assert status["remaining_spend"] == 5.00

    def test_custom_image_limit(self, state_file, monkeypatch):
        monkeypatch.setenv("SESSION_MAX_IMAGES", "5")
        g = SessionGuard(state_file=state_file)
        status = g.check()
        assert status["remaining_images"] == 5
