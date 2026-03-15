"""Tests for li_campaign.py — LinkedIn campaign and creative management."""

import json
from unittest.mock import patch, MagicMock

import pytest

from scripts.li_campaign import (
    create_campaign,
    update_campaign,
    upload_image,
    create_ad,
    list_creatives,
    update_creative_status,
)

ACCOUNT_ID = "520217301"


class TestCreateCampaign:
    @patch("scripts.li_campaign.requests.post")
    def test_creates_campaign_in_draft_status(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201,
            headers={"x-restli-id": "555838300"},
            json=lambda: {},
        )
        result = create_campaign(
            account_id=ACCOUNT_ID,
            name="Test Campaign",
            objective="WEBSITE_VISITS",
            daily_budget_cad=50.00,
        )
        assert result["campaign_id"] == "555838300"

        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["status"] == "DRAFT"
        assert body["name"] == "Test Campaign"
        assert body["dailyBudget"]["amount"] == "50.00"
        assert body["dailyBudget"]["currencyCode"] == "CAD"

    @patch("scripts.li_campaign.requests.post")
    def test_401_raises_auth_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=401,
            text="Unauthorized",
            json=lambda: {"status": 401},
        )
        with pytest.raises(SystemExit):
            create_campaign(
                account_id=ACCOUNT_ID,
                name="Test",
                objective="WEBSITE_VISITS",
                daily_budget_cad=50.00,
            )


class TestUpdateCampaign:
    @patch("scripts.li_campaign.requests.post")
    def test_updates_campaign_status(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        result = update_campaign(
            account_id=ACCOUNT_ID,
            campaign_id="555838300",
            updates={"status": "PAUSED"},
        )
        assert result["success"] is True

    @patch("scripts.li_campaign.requests.post")
    def test_update_fails_gracefully(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=400,
            text="Bad Request",
            json=lambda: {"message": "Invalid status"},
        )
        with pytest.raises(SystemExit):
            update_campaign(
                account_id=ACCOUNT_ID,
                campaign_id="555838300",
                updates={"status": "INVALID"},
            )


class TestUploadImage:
    @patch("scripts.li_campaign.requests.put")
    @patch("scripts.li_campaign.requests.post")
    def test_uploads_image_with_org_owner(self, mock_post, mock_put, tmp_path):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "value": {
                    "uploadUrl": "https://www.linkedin.com/dms-uploads/xxx",
                    "image": "urn:li:image:C4E22AQH1234567890",
                }
            },
        )
        mock_put.return_value = MagicMock(status_code=201)

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-png-data")

        result = upload_image(account_id=ACCOUNT_ID, image_path=str(img_file))
        assert result["image_urn"] == "urn:li:image:C4E22AQH1234567890"

        # Verify org is the owner, not the ad account
        post_body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert "urn:li:organization:" in post_body["initializeUploadRequest"]["owner"]


class TestCreateAd:
    @patch("scripts.li_campaign.requests.post")
    @patch("scripts.li_campaign.requests.put")
    def test_full_3_step_flow(self, mock_put, mock_post, tmp_path):
        # Mock responses for: upload init, post creation, creative creation
        mock_post.side_effect = [
            # Step 1: initialize image upload
            MagicMock(
                status_code=200,
                json=lambda: {
                    "value": {
                        "uploadUrl": "https://cdn.linkedin.com/upload/xxx",
                        "image": "urn:li:image:TEST123",
                    }
                },
            ),
            # Step 2: create post
            MagicMock(
                status_code=201,
                headers={"x-restli-id": "urn:li:share:999888777"},
                json=lambda: {},
            ),
            # Step 3: create creative (BATCH_CREATE)
            MagicMock(
                status_code=200,
                json=lambda: {
                    "elements": [{"id": "urn:li:sponsoredCreative:123456", "status": 201}]
                },
            ),
        ]
        mock_put.return_value = MagicMock(status_code=201)

        img_file = tmp_path / "ad.png"
        img_file.write_bytes(b"fake-ad-image")

        result = create_ad(
            account_id=ACCOUNT_ID,
            campaign_id="555838216",
            image_path=str(img_file),
            headline="Test Headline",
            intro_text="Test intro text",
            cta="LEARN_MORE",
            destination_url="https://aurevon.ca",
        )

        assert result["creative_id"] == "urn:li:sponsoredCreative:123456"
        assert result["share_urn"] == "urn:li:share:999888777"
        assert result["image_urn"] == "urn:li:image:TEST123"
        assert mock_post.call_count == 3
        assert mock_put.call_count == 1


class TestListCreatives:
    @patch("scripts.li_campaign.requests.get")
    def test_returns_formatted_creatives(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "elements": [
                    {
                        "id": "urn:li:sponsoredCreative:111",
                        "name": "Ad_1",
                        "intendedStatus": "ACTIVE",
                        "isServing": True,
                        "review": {"status": "APPROVED"},
                        "content": {"reference": "urn:li:share:222"},
                    }
                ]
            },
        )
        result = list_creatives(ACCOUNT_ID, "555838216")
        assert len(result) == 1
        assert result[0]["id"] == "urn:li:sponsoredCreative:111"
        assert result[0]["status"] == "ACTIVE"
        assert result[0]["serving"] is True


class TestUpdateCreativeStatus:
    @patch("scripts.li_campaign.requests.post")
    def test_pauses_creative(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        result = update_creative_status(
            ACCOUNT_ID, "urn:li:sponsoredCreative:111", "PAUSED"
        )
        assert result["status"] == "PAUSED"
