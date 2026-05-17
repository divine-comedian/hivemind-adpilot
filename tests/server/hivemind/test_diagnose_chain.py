import json
from unittest.mock import MagicMock
from server.hivemind.diagnose_chain import DiagnoseChain


def _chat_response(payload: dict) -> dict:
    return {"status": "success", "data": {"response": json.dumps(payload)}}


def _diagnose_payload(tier: str, kills: int = 1, replacements: int = 1) -> dict:
    return {
        "summary": "The narrative is anchored too far upstream of buyer intent.",
        "kill_recommendations": [
            {"target_id": f"ad-{i}", "platform": "linkedin", "reasoning": "0 clicks on 5000 impressions.", "framework_cited": "Narrative Health Audit"}
            for i in range(kills)
        ],
        "replacement_angles": [
            {"id": f"r{i}", "angle": "Sharper-buyer angle", "rationale": "Closer to active intent.", "framework_cited": "Narrative Health Audit"}
            for i in range(replacements)
        ],
        "tier": tier,
    }


def _ghostwriter_payload() -> dict:
    return {"headline": "H", "body": "B", "cta": "LEARN_MORE", "image_prompt": "abstract", "rationale": "r"}


def test_diagnose_returns_kills_and_replacements():
    hivemind = MagicMock()
    hivemind.chat.side_effect = [
        _chat_response(_diagnose_payload("A", kills=2, replacements=2)),
        _chat_response(_ghostwriter_payload()),
        _chat_response(_ghostwriter_payload()),
    ]
    chain = DiagnoseChain(hivemind=hivemind)
    result = chain.diagnose(
        project_id="proj-1",
        tier="A",
        performance_data=[{"ad_id": "ad-0", "platform": "linkedin", "impressions": 5000, "clicks": 0}],
        active_creative_copy=[],
        platforms=["linkedin"],
    )
    assert len(result["kill_recommendations"]) == 2
    assert len(result["replacement_drafts"]) == 2
    assert result["tier"] == "A"
    assert hivemind.chat.call_count == 3
    assert hivemind.chat.call_args_list[0].kwargs["persona"] == "genius-strategist"
    assert hivemind.chat.call_args_list[1].kwargs["persona"] == "ghostwriter"
