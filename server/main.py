"""AdPilot FastAPI sidecar. Local-only, no auth, talks to Next.js on localhost:3000."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AdPilot Sidecar", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from server.routes import events, workspace, generate

app.include_router(events.router)
app.include_router(workspace.router)
app.include_router(generate.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
