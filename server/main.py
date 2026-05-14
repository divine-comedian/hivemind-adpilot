"""AdPilot FastAPI sidecar. Local-only, no auth, talks to Next.js on localhost:3000."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKENS_FILE = PROJECT_ROOT / "workspace" / ".tokens.env"


def _load_tokens_from_disk() -> None:
    """Re-populate token env vars after a server restart.

    Onboarding writes the user's LinkedIn + Facebook tokens to workspace/.tokens.env
    and into os.environ. Without this loader, every restart forces a re-onboard.
    """
    if not TOKENS_FILE.exists():
        return
    for line in TOKENS_FILE.read_text().splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and value:
            os.environ[key] = value


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_tokens_from_disk()
    yield


app = FastAPI(title="AdPilot Sidecar", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from server.routes import events, workspace, generate, drafts, analytics, diagnose

app.include_router(events.router)
app.include_router(workspace.router)
app.include_router(generate.router)
app.include_router(drafts.router)
app.include_router(analytics.router)
app.include_router(diagnose.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
