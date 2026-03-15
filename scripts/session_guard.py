"""Per-session spend and image generation cap enforcement.

Tracks cumulative spend and image count within a rolling session window.
Session resets automatically after SESSION_WINDOW_HOURS of inactivity.

CLI usage:
    python -m scripts.session_guard --check    # Show remaining budget
    python -m scripts.session_guard --reset    # Reset session
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_MAX_SPEND = 10.00
DEFAULT_MAX_IMAGES = 20
DEFAULT_WINDOW_HOURS = 1

_STATE_DIR = Path(__file__).resolve().parent.parent / "memory"
_DEFAULT_STATE_FILE = _STATE_DIR / "session_state.json"


class SessionOverLimitError(Exception):
    """Raised when a session cap would be exceeded."""


class SessionGuard:
    def __init__(self, state_file: Path = _DEFAULT_STATE_FILE):
        self._state_file = Path(state_file)
        self._max_spend = float(os.getenv("SESSION_MAX_SPEND", DEFAULT_MAX_SPEND))
        self._max_images = int(os.getenv("SESSION_MAX_IMAGES", DEFAULT_MAX_IMAGES))
        self._window_seconds = float(os.getenv("SESSION_WINDOW_HOURS", DEFAULT_WINDOW_HOURS)) * 3600
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if self._state_file.exists():
            try:
                state = json.loads(self._state_file.read_text())
            except (json.JSONDecodeError, KeyError):
                return self._fresh_state()
            elapsed = time.time() - state.get("session_start", 0)
            if elapsed > self._window_seconds:
                return self._fresh_state()
            return state
        return self._fresh_state()

    def _fresh_state(self) -> dict:
        return {
            "session_start": time.time(),
            "total_spend": 0.0,
            "image_count": 0,
        }

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(self._state, indent=2))

    def check(self) -> dict:
        """Return current session status."""
        self._save()
        return {
            "remaining_spend": round(self._max_spend - self._state["total_spend"], 2),
            "remaining_images": self._max_images - self._state["image_count"],
            "total_spend": round(self._state["total_spend"], 2),
            "image_count": self._state["image_count"],
            "max_spend": self._max_spend,
            "max_images": self._max_images,
        }

    def require_budget(self, amount: float) -> None:
        """Raise if spending amount would exceed session limit."""
        if self._state["total_spend"] + amount > self._max_spend:
            remaining = round(self._max_spend - self._state["total_spend"], 2)
            raise SessionOverLimitError(
                f"Session spend limit reached. Remaining: ${remaining}, requested: ${amount}"
            )

    def require_image(self) -> None:
        """Raise if generating another image would exceed session limit."""
        if self._state["image_count"] >= self._max_images:
            raise SessionOverLimitError(
                f"Session image limit reached ({self._max_images} images)"
            )

    def record_spend(self, amount: float) -> None:
        """Record a spend event."""
        self._state["total_spend"] += amount
        self._save()

    def record_image(self) -> None:
        """Record an image generation event."""
        self._state["image_count"] += 1
        self._save()

    def reset(self) -> None:
        """Manually reset the session."""
        self._state = self._fresh_state()
        self._save()


def main():
    parser = argparse.ArgumentParser(description="Session budget guard")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Show remaining budget")
    group.add_argument("--reset", action="store_true", help="Reset session")
    args = parser.parse_args()

    guard = SessionGuard()

    if args.check:
        status = guard.check()
        json.dump(status, sys.stdout, indent=2)
        print()
    elif args.reset:
        guard.reset()
        print("Session reset.", file=sys.stderr)
        status = guard.check()
        json.dump(status, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
