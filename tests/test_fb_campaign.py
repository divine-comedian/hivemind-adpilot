"""Tests for fb_campaign.py — Facebook campaign and ad management."""

import json
from unittest.mock import patch, MagicMock

import pytest

from scripts.fb_campaign import (
    list_campaigns,
    create_campaign,
    update_campaign,
    upload_image,
    list_adsets,
    create_adset,
    update_adset_status,
    create_ad_creative,
    create_ad,
    create_full_ad,
    list_ads,
    update_ad_status,
)

ACCOUNT_ID = "22243234"


class TestListCampaigns:
    @patch("scripts.fb_campaign.requests.get")
    def test_returns_campaigns(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "6952504195779",
                        "name": "Aurevon Test Traffic Drive",
                        "status": "ACTIVE",
                        "objective": "OUTCOME_TRAFFIC",
                        "daily_budget": "2000",
                    }
                ],
            },
        )
        result = list_campaigns(ACCOUNT_ID)
        assert len(result) == 1
        assert result[0]["id"] == "6952504195779"
        assert result[0]["name"] == "Aurevon Test Traffic Drive"


class TestCreateCampaign:
    @patch("scripts.fb_campaign.requests.post")
    def test_creates_campaign_paused(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "120218765432"},
        )
        result = create_campaign(
            account_id=ACCOUNT_ID,
            name="Aurevon Traffic",
            objective="OUTCOME_TRAFFIC",
            daily_budget_cents=2500,
        )
        assert result["campaign_id"] == "120218765432"
        assert result["status"] == "PAUSED"

        call_kwargs = mock_post.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["daily_budget"] == "2500"
        assert params["status"] == "PAUSED"

    @patch("scripts.fb_campaign.requests.post")
    def test_creates_campaign_active(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "120218765432"},
        )
        result = create_campaign(
            account_id=ACCOUNT_ID,
            name="Test",
            objective="OUTCOME_TRAFFIC",
            daily_budget_cents=2500,
            status="ACTIVE",
        )
        assert result["status"] == "ACTIVE"

    @patch("scripts.fb_campaign.requests.post")
    def test_auth_error_exits(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=400,
            text="error",
            json=lambda: {"error": {"message": "Invalid token", "code": 190}},
        )
        with pytest.raises(SystemExit):
            create_campaign(ACCOUNT_ID, "Test", "OUTCOME_TRAFFIC", 2500)

    @patch("scripts.fb_campaign.requests.post")
    def test_normalizes_act_prefix(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "120218765432"},
        )
        create_campaign(f"act_{ACCOUNT_ID}", "Test", "OUTCOME_TRAFFIC", 2500)
        url = mock_post.call_args.args[0] if mock_post.call_args.args else mock_post.call_args[0][0]
        assert f"act_{ACCOUNT_ID}" in url
        assert "act_act_" not in url


class TestUpdateCampaign:
    @patch("scripts.fb_campaign.requests.post")
    def test_updates_campaign_status(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True},
        )
        result = update_campaign(ACCOUNT_ID, "120218765432", {"status": "PAUSED"})
        assert result["success"] is True

    @patch("scripts.fb_campaign.requests.post")
    def test_update_fails_gracefully(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=400,
            text="error",
            json=lambda: {"error": {"message": "Invalid parameter", "code": 100}},
        )
        with pytest.raises(SystemExit):
            update_campaign(ACCOUNT_ID, "120218765432", {"status": "BAD"})


class TestUploadImage:
    @patch("scripts.fb_campaign.requests.post")
    def test_uploads_image_returns_hash(self, mock_post, tmp_path):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "images": {
                    "test.png": {
                        "hash": "abc123def456",
                        "url": "https://scontent.xx.fbcdn.net/v/xxx",
                    }
                }
            },
        )
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-png-data")

        result = upload_image(ACCOUNT_ID, str(img_file))
        assert result["image_hash"] == "abc123def456"
        assert "fbcdn" in result["image_url"]

    @patch("scripts.fb_campaign.requests.post")
    def test_upload_error_exits(self, mock_post, tmp_path):
        mock_post.return_value = MagicMock(
            status_code=400,
            text="error",
            json=lambda: {"error": {"message": "Upload failed", "code": 100}},
        )
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-png-data")

        with pytest.raises(SystemExit):
            upload_image(ACCOUNT_ID, str(img_file))


class TestCreateAdset:
    @patch("scripts.fb_campaign.requests.get")
    @patch("scripts.fb_campaign.requests.post")
    def test_creates_adset_with_targeting(self, mock_post, mock_get):
        # Mock _get_campaign_info: no campaign budget, no existing adsets
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {}),
            MagicMock(status_code=200, json=lambda: {"data": []}),
        ]
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "23850001234"},
        )
        result = create_adset(
            account_id=ACCOUNT_ID,
            campaign_id="120218765432",
            name="Canada 25-65",
            daily_budget_cents=2500,
            destination_url="https://aurevon.ca",
            countries=["CA"],
        )
        assert result["adset_id"] == "23850001234"
        assert result["campaign_id"] == "120218765432"

        call_kwargs = mock_post.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        targeting = json.loads(params["targeting"])
        assert targeting["geo_locations"]["countries"] == ["CA"]
        assert targeting["targeting_automation"]["advantage_audience"] == 1
        # Budget should be set when campaign has no budget
        assert params["daily_budget"] == "2500"

    @patch("scripts.fb_campaign.requests.get")
    @patch("scripts.fb_campaign.requests.post")
    def test_skips_budget_when_campaign_has_one(self, mock_post, mock_get):
        # Campaign has daily_budget set
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"daily_budget": "2000"}),
            MagicMock(status_code=200, json=lambda: {"data": [{"optimization_goal": "LANDING_PAGE_VIEWS"}]}),
        ]
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "23850001234"},
        )
        create_adset(
            account_id=ACCOUNT_ID,
            campaign_id="120218765432",
            name="Test",
            daily_budget_cents=2500,
        )
        call_kwargs = mock_post.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert "daily_budget" not in params
        assert params["optimization_goal"] == "LANDING_PAGE_VIEWS"

    @patch("scripts.fb_campaign.requests.get")
    @patch("scripts.fb_campaign.requests.post")
    def test_clamps_age_for_advantage_audience(self, mock_post, mock_get):
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {}),
            MagicMock(status_code=200, json=lambda: {"data": []}),
        ]
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "23850001234"},
        )
        create_adset(
            account_id=ACCOUNT_ID,
            campaign_id="120218765432",
            name="Test",
            age_min=30,
            age_max=54,
        )
        call_kwargs = mock_post.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        targeting = json.loads(params["targeting"])
        # Advantage+ clamps age_min to max 25, age_max to min 65
        assert targeting["age_min"] == 25
        assert targeting["age_max"] == 65


class TestListAdsets:
    @patch("scripts.fb_campaign.requests.get")
    def test_returns_adsets(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "6955623856979",
                        "name": "CA ICP 25-65 Price Anchor",
                        "status": "PAUSED",
                        "effective_status": "PAUSED",
                        "daily_budget": None,
                        "optimization_goal": "LANDING_PAGE_VIEWS",
                    }
                ],
            },
        )
        result = list_adsets(ACCOUNT_ID, "6952504195779")
        assert len(result) == 1
        assert result[0]["id"] == "6955623856979"
        assert result[0]["optimization_goal"] == "LANDING_PAGE_VIEWS"


class TestUpdateAdsetStatus:
    @patch("scripts.fb_campaign.requests.post")
    def test_pauses_adset(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True},
        )
        result = update_adset_status("6955623856979", "PAUSED")
        assert result["status"] == "PAUSED"
        assert result["adset_id"] == "6955623856979"


class TestCreateAdCreative:
    @patch("scripts.fb_campaign.requests.post")
    def test_creates_creative_with_copy(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "23850005678"},
        )
        result = create_ad_creative(
            account_id=ACCOUNT_ID,
            image_hash="abc123",
            headline="Know Your Competition",
            body="Instant competitive intelligence reports.",
            cta="LEARN_MORE",
            destination_url="https://aurevon.ca",
        )
        assert result["creative_id"] == "23850005678"

        call_kwargs = mock_post.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        spec = json.loads(params["object_story_spec"])
        assert spec["link_data"]["name"] == "Know Your Competition"
        assert spec["link_data"]["image_hash"] == "abc123"
        assert spec["page_id"] == "123456789"


class TestCreateAd:
    @patch("scripts.fb_campaign.requests.post")
    def test_creates_ad_linking_creative_to_adset(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "23850009999"},
        )
        result = create_ad(
            account_id=ACCOUNT_ID,
            adset_id="23850001234",
            creative_id="23850005678",
            name="Test Ad",
        )
        assert result["ad_id"] == "23850009999"
        assert result["adset_id"] == "23850001234"
        assert result["creative_id"] == "23850005678"


class TestCreateFullAd:
    @patch("scripts.fb_campaign.requests.get")
    @patch("scripts.fb_campaign.requests.post")
    def test_full_4_step_flow(self, mock_post, mock_get, tmp_path):
        # Mock _get_campaign_info
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {}),
            MagicMock(status_code=200, json=lambda: {"data": []}),
        ]
        mock_post.side_effect = [
            # Step 1: upload image
            MagicMock(
                status_code=200,
                json=lambda: {"images": {"ad.png": {"hash": "abc123", "url": "https://cdn/img"}}},
            ),
            # Step 2: create adset
            MagicMock(
                status_code=200,
                json=lambda: {"id": "23850001234"},
            ),
            # Step 3: create ad creative
            MagicMock(
                status_code=200,
                json=lambda: {"id": "23850005678"},
            ),
            # Step 4: create ad
            MagicMock(
                status_code=200,
                json=lambda: {"id": "23850009999"},
            ),
        ]

        img_file = tmp_path / "ad.png"
        img_file.write_bytes(b"fake-ad-image")

        result = create_full_ad(
            account_id=ACCOUNT_ID,
            campaign_id="120218765432",
            image_path=str(img_file),
            adset_name="Canada 25-54",
            daily_budget_cents=2500,
            countries=["CA"],
            age_min=25,
            age_max=54,
            headline="Know Your Competition",
            body="Instant competitive intelligence reports.",
            cta="LEARN_MORE",
            destination_url="https://aurevon.ca",
        )

        assert result["ad_id"] == "23850009999"
        assert result["adset_id"] == "23850001234"
        assert result["creative_id"] == "23850005678"
        assert result["image_hash"] == "abc123"
        assert mock_post.call_count == 4

    @patch("scripts.fb_campaign.requests.get")
    @patch("scripts.fb_campaign.requests.post")
    def test_partial_failure_reports_progress(self, mock_post, mock_get, tmp_path):
        """If creative creation fails after image upload + adset, exits with error."""
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {}),
            MagicMock(status_code=200, json=lambda: {"data": []}),
        ]
        mock_post.side_effect = [
            # Step 1: upload image — success
            MagicMock(
                status_code=200,
                json=lambda: {"images": {"ad.png": {"hash": "abc123", "url": ""}}},
            ),
            # Step 2: create adset — success
            MagicMock(
                status_code=200,
                json=lambda: {"id": "23850001234"},
            ),
            # Step 3: create creative — failure
            MagicMock(
                status_code=400,
                text="error",
                json=lambda: {"error": {"message": "Invalid image", "code": 100}},
            ),
        ]

        img_file = tmp_path / "ad.png"
        img_file.write_bytes(b"fake-ad-image")

        with pytest.raises(SystemExit):
            create_full_ad(
                account_id=ACCOUNT_ID,
                campaign_id="120218765432",
                image_path=str(img_file),
                adset_name="Canada 25-54",
                daily_budget_cents=2500,
                countries=["CA"],
                age_min=25,
                age_max=54,
                headline="Test",
                body="Test body",
                cta="LEARN_MORE",
                destination_url="https://aurevon.ca",
            )


class TestListAds:
    @patch("scripts.fb_campaign.requests.get")
    def test_returns_formatted_ads(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "23850009999",
                        "name": "Know Your Competition",
                        "status": "ACTIVE",
                        "effective_status": "ACTIVE",
                        "creative": {"id": "23850005678"},
                    }
                ],
            },
        )
        result = list_ads(ACCOUNT_ID, "23850001234")
        assert len(result) == 1
        assert result[0]["id"] == "23850009999"
        assert result[0]["status"] == "ACTIVE"
        assert result[0]["creative_id"] == "23850005678"

    @patch("scripts.fb_campaign.requests.get")
    def test_handles_pagination(self, mock_get):
        page1 = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [{"id": "111", "name": "Ad 1", "status": "ACTIVE"}],
                "paging": {"next": "https://graph.facebook.com/v25.0/page2"},
            },
        )
        page2 = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [{"id": "222", "name": "Ad 2", "status": "PAUSED"}],
            },
        )
        mock_get.side_effect = [page1, page2]

        result = list_ads(ACCOUNT_ID, "23850001234")
        assert len(result) == 2
        assert mock_get.call_count == 2


class TestUpdateAdStatus:
    @patch("scripts.fb_campaign.requests.post")
    def test_pauses_ad(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True},
        )
        result = update_ad_status("23850009999", "PAUSED")
        assert result["status"] == "PAUSED"
        assert result["ad_id"] == "23850009999"

    @patch("scripts.fb_campaign.requests.post")
    def test_activates_ad(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True},
        )
        result = update_ad_status("23850009999", "ACTIVE")
        assert result["status"] == "ACTIVE"

    @patch("scripts.fb_campaign.requests.post")
    def test_error_exits(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=400,
            text="error",
            json=lambda: {"error": {"message": "Cannot change status", "code": 100}},
        )
        with pytest.raises(SystemExit):
            update_ad_status("23850009999", "ACTIVE")
