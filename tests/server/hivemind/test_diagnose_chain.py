import json
from unittest.mock import MagicMock
import pytest
from server.hivemind.diagnose_chain import DiagnoseChain


def _diagnose_json(tier: str, kills: int = 1, replacements: int = 1):
    return json.dumps({
        "summary": "The narrative is anchored too far upstream of buyer intent.",
        "kill_recommendations": [
            {"target_id": f"ad-{i}", "reasoning": "0 clicks on 5000 impressions.", "framework_cited": "Narrative Health Audit"}
            for i in range(kills)
        ],
        "replacement_angles": [
            {"id": f"r{i}", "angle": "Sharper-buyer angle", "rationale": "Closer to active intent.", "framework_cited": "Narrative Health Audit"}
            for i in range(replacements)
        ],
        "tier": tier,
    })


def _ghostwriter_json():
    return json.dumps({"headline": "H", "body": "B", "cta": "LEARN_MORE", "image_prompt": "abstract", "rationale": "r"})


def test_diagnose_returns_kills_and_replacements():
    hivemind = MagicMock()
    hivemind.intelligence_get_report.return_value = None
    hivemind.knowledge_search.return_value = {"results": []}
    hivemind.chat.side_effect = [
        {"reply": _diagnose_json("A", kills=2, replacements=2)},
        {"reply": _ghostwriter_json()},
        {"reply": _ghostwriter_json()},
    ]
    chain = DiagnoseChain(hivemind=hivemind)
    result = chain.diagnose(
        project_id="proj-1",
        performance_data=[{"ad_id": "ad-0", "impressions": 5000, "clicks": 0}],
        active_creative_copy=[],
        platforms=["linkedin"],
    )
    assert len(result["kill_recommendations"]) == 2
    assert len(result["replacement_drafts"]) == 2
    assert result["tier"] == "A"
