import json
from unittest.mock import MagicMock
import pytest

from server.hivemind.strategist_chain import StrategistChain
from server.hivemind.types import BusinessContext


@pytest.fixture
def context():
    return BusinessContext(
        name="Demo",
        description="A test business",
        audiences=["analysts"],
        geographies=["US"],
        stage="seed",
        voice_notes="",
        focus_notes="",
    )


def _strategist_json(tier: str):
    return json.dumps({
        "diagnosed_gaps": ["gap A"],
        "opportunity_angles": [
            {"id": "a1", "angle": "angle A", "rationale": "r1", "framework_cited": "Narrative Health Audit"}
        ],
        "tier": tier,
        "framework_cited": "Narrative Health Audit",
    })


def _ghostwriter_json():
    return json.dumps({
        "headline": "Hook",
        "body": "Body copy",
        "cta": "LEARN_MORE",
        "image_prompt": "cinematic abstract",
        "rationale": "supports gap",
    })


def test_generate_tier_a_when_no_intelligence(context):
    hivemind = MagicMock()
    hivemind.intelligence_get_report.return_value = None  # no report yet
    hivemind.knowledge_search.return_value = {"results": [{"id": "k1", "body": "framework excerpt"}]}
    hivemind.chat.side_effect = [
        {"reply": _strategist_json("A")},
        {"reply": _ghostwriter_json()},
    ]
    chain = StrategistChain(hivemind=hivemind)
    result = chain.generate(
        project_id="proj-1",
        business=context,
        current_active_ads=[],
        platforms=["linkedin"],
        count=1,
    )
    assert result["tier"] == "A"
    assert len(result["drafts"]) == 1
    assert result["drafts"][0]["headline"] == "Hook"


def test_generate_tier_b_when_intelligence_present(context):
    hivemind = MagicMock()
    hivemind.intelligence_get_report.side_effect = [
        {"report": "competitive insights", "core_insight": "ci"},
        {"report": "attention insights", "core_insight": "ai"},
    ]
    hivemind.knowledge_search.return_value = {"results": [{"id": "k1", "body": "framework"}]}
    hivemind.chat.side_effect = [
        {"reply": _strategist_json("B")},
        {"reply": _ghostwriter_json()},
    ]
    chain = StrategistChain(hivemind=hivemind)
    result = chain.generate(
        project_id="proj-1",
        business=context,
        current_active_ads=[],
        platforms=["facebook"],
        count=1,
    )
    assert result["tier"] == "B"
