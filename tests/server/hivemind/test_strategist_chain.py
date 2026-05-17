import json
from unittest.mock import MagicMock
import pytest

from server.hivemind.strategist_chain import StrategistChain, _normalize_angles
from server.hivemind.prompts import ad_set_copy_text
from server.hivemind.types import BusinessContext


@pytest.fixture
def context() -> BusinessContext:
    return BusinessContext(
        website_url="https://demo.test",
        voice_notes="",
        focus_notes="",
    )


def _chat_response(payload: dict) -> dict:
    return {"status": "success", "data": {"response": json.dumps(payload), "persona": {"id": "genius-strategist"}}}


def _strategist_payload(tier: str) -> dict:
    return {
        "diagnosed_gaps": ["gap A"],
        "opportunity_angles": [
            {"id": "a1", "angle": "angle A", "rationale": "r1", "framework_cited": "Narrative Health Audit"}
        ],
        "tier": tier,
        "framework_cited": "Narrative Health Audit",
    }


def _ghostwriter_payload() -> dict:
    return {
        "headline": "Hook",
        "body": "Body copy",
        "cta": "LEARN_MORE",
        "image_prompt": "cinematic abstract",
        "rationale": "supports gap",
    }


def _ad_set_payload() -> dict:
    return {
        "drafts": [
            {
                "platform": "facebook",
                "variant": 1,
                "headline": "FB Hook",
                "body": "FB body",
                "cta": "LEARN_MORE",
                "image_prompt": "abstract image",
                "rationale": "variant rationale",
            },
            {
                "platform": "linkedin",
                "variant": 1,
                "headline": "LI Hook",
                "body": "LI body",
                "cta": "LEARN_MORE",
                "image_prompt": "abstract image",
                "rationale": "variant rationale",
            },
        ]
    }


def test_normalize_angle_ideas_preserves_structured_reasoning():
    result = _normalize_angles({
        "angles": [{
            "id": "angle_1",
            "title": "Local competitor gaps as urgency",
            "angle": "Use local competitive gaps as the reason to act now. Position the report as a shortcut to seeing what nearby competitors already know.",
            "fit_reason": "This uses a specificity hook from Hivemind's knowledge layer. It leverages Aurevon's Canadian SMB focus and $50 market report offer. Ghostwriter thinks it fits because the project sells fast clarity to operators who do not have time for slow research.",
            "reasoning": "This uses a specificity hook from Hivemind's knowledge layer.",
        }]
    }, 4)
    assert result[0]["title"] == "Local competitor gaps as urgency"
    assert result[0]["angle_description"].startswith("Use local competitive gaps")
    assert result[0]["fit_reason"].startswith("This uses a specificity hook")


def test_normalize_angle_ideas_backfills_title_for_legacy_shape():
    result = _normalize_angles({
        "angles": [{
            "id": "angle_1",
            "angle": "Show why restaurant owners miss competitor moves until revenue drops.",
            "reasoning": "Uses problem recognition before product proof.",
        }]
    }, 4)
    assert result[0]["title"] == "Show why restaurant owners miss competitor moves until"
    assert result[0]["fit_reason"] == "Uses problem recognition before product proof."


def test_refine_angle_appends_to_existing_conversation(context):
    hivemind = MagicMock()
    hivemind.chat.return_value = _chat_response({
        "angles": [{
            "id": "angle_1",
            "title": "Proof before local ad spend",
            "angle": "Use proof gaps before ad spend as the core message. Show that better market knowledge should come before campaign budget.",
            "fit_reason": "This uses a problem-aware conversion hook. It highlights Canadian SMBs as operators who need clarity before they spend. It makes the offer feel lower-risk.",
            "reasoning": "This uses a problem-aware conversion hook.",
        }]
    })
    chain = StrategistChain(hivemind=hivemind)
    result = chain.refine_angle(
        project_id="proj-1",
        business=context,
        angle={"id": "angle_1", "angle": "Original angle", "reasoning": "Original reason"},
        guidance="Make it more proof-led.",
        conversation_id="conv-1",
    )
    assert result["angle"]["id"] == "angle_1"
    assert result["angle"]["title"] == "Proof before local ad spend"
    call = hivemind.chat.call_args
    assert call.kwargs["persona"] == "ghostwriter"
    assert call.kwargs["conversation_id"] == "conv-1"


def test_ad_set_copy_prompt_compacts_large_angle_and_project_payload():
    huge_angle = {
        "id": "angle_1",
        "title": "The Crew Down The Road Hook",
        "angle": "A viral-style ad set. " * 200,
        "hivemind_hooks": ["hook " * 100 for _ in range(10)],
        "project_information": ["project fact " * 100 for _ in range(10)],
        "fit_reason": "Trades operators respond to specificity. " * 200,
        "reasoning": "reason " * 200,
    }
    huge_project = {
        "website_url": "https://demo.test",
        "project_name": "Demo",
        "description": "Long scraped markdown. " * 500,
        "geographics": ["Canada"],
    }
    prompt = ad_set_copy_text(
        angle=huge_angle,
        project=huge_project,
        voice_notes="",
        platforms=["facebook", "linkedin"],
        ads_per_platform=3,
    )
    assert len(prompt) < 8000
    assert "The Crew Down The Road Hook" in prompt
    assert '"drafts"' in prompt


def test_generate_from_angle_uses_single_stateless_ghostwriter_call(context):
    hivemind = MagicMock()
    hivemind.chat.return_value = _chat_response(_ad_set_payload())
    chain = StrategistChain(hivemind=hivemind)
    result = chain.generate_from_angle(
        project_id="proj-1",
        tier="B",
        business=context,
        angle={"id": "angle_1", "title": "Proof angle", "angle": "Use proof."},
        platforms=["facebook", "linkedin"],
        ads_per_platform=3,
        conversation_id="conv-ideas",
    )
    assert hivemind.chat.call_count == 1
    call = hivemind.chat.call_args
    assert call.kwargs["persona"] == "ghostwriter"
    assert call.kwargs["project_id"] == "proj-1"
    assert "conversation_id" not in call.kwargs or call.kwargs["conversation_id"] is None
    assert len(result["drafts"]) == 2
    assert result["strategist_output"]["source_conversation_id"] == "conv-ideas"


def test_refine_draft_copy_uses_guidance_and_preserves_platform(context):
    hivemind = MagicMock()
    hivemind.chat.return_value = _chat_response({
        "headline": "Sharper Hook",
        "body": "Sharper body copy",
        "cta": "LEARN_MORE",
        "image_prompt": "abstract image",
        "rationale": "Better matches the requested proof point.",
    })
    chain = StrategistChain(hivemind=hivemind)
    result = chain.refine_draft_copy(
        project_id="proj-1",
        tier="B",
        business=context,
        draft={
            "id": "d-1",
            "platform": "linkedin",
            "headline": "Old Hook",
            "body": "Old body",
            "cta": "SIGN_UP",
            "source_angle_id": "angle_1",
        },
        guidance="Make it more proof-led.",
    )

    assert result["draft"]["headline"] == "Sharper Hook"
    assert result["draft"]["platform"] == "linkedin"
    assert result["draft"]["angle_id"] == "angle_1"
    assert result["strategist_output"]["mode"] == "refine_ad_copy"
    call = hivemind.chat.call_args
    assert call.kwargs["persona"] == "ghostwriter"
    assert "Make it more proof-led" in call.kwargs["text"]


def test_generate_tier_a_uses_two_chat_calls(context):
    hivemind = MagicMock()
    hivemind.chat.side_effect = [
        _chat_response(_strategist_payload("A")),
        _chat_response(_ghostwriter_payload()),
    ]
    chain = StrategistChain(hivemind=hivemind)
    result = chain.generate(
        project_id="proj-1",
        tier="A",
        business=context,
        current_active_ads=[],
        platforms=["linkedin"],
        count=1,
    )
    assert result["tier"] == "A"
    assert len(result["drafts"]) == 1
    assert result["drafts"][0]["headline"] == "Hook"
    assert hivemind.chat.call_count == 2
    first_call = hivemind.chat.call_args_list[0]
    assert first_call.kwargs["persona"] == "genius-strategist"
    assert first_call.kwargs["project_id"] == "proj-1"


def test_generate_tier_b_propagates_tier_through_pipeline(context):
    hivemind = MagicMock()
    hivemind.chat.side_effect = [
        _chat_response(_strategist_payload("B")),
        _chat_response(_ghostwriter_payload()),
    ]
    chain = StrategistChain(hivemind=hivemind)
    result = chain.generate(
        project_id="proj-1",
        tier="B",
        business=context,
        current_active_ads=[],
        platforms=["facebook"],
        count=1,
    )
    assert result["tier"] == "B"
    strategist_text = hivemind.chat.call_args_list[0].kwargs["text"]
    assert "Tier: B" in strategist_text


def test_generate_tolerates_markdown_wrapped_json(context):
    hivemind = MagicMock()
    wrapped = "```json\n" + json.dumps(_strategist_payload("A")) + "\n```"
    hivemind.chat.side_effect = [
        {"status": "success", "data": {"response": wrapped}},
        _chat_response(_ghostwriter_payload()),
    ]
    chain = StrategistChain(hivemind=hivemind)
    result = chain.generate(
        project_id="proj-1",
        tier="A",
        business=context,
        current_active_ads=[],
        platforms=["linkedin"],
        count=1,
    )
    assert result["tier"] == "A"
    assert len(result["drafts"]) == 1
