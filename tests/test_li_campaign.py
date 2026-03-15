"""Tests for li_campaign.py — LinkedIn campaign and creative management."""

import json
from unittest.mock import patch, MagicMock, mock_open

import pytest

from scripts.li_campaign import (
    create_campaign,
    update_campaign,
    initialize_image_upload,
    upload_image_binary,
    upload_image,
    create_creative,
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

        # Verify the request body
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


class TestImageUpload:
    @patch("scripts.li_campaign.requests.post")
    def test_initialize_upload_returns_upload_url_and_image_urn(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "value": {
                    "uploadUrl": "https://www.linkedin.com/dms-uploads/xxx",
                    "image": "urn:li:image:C4E22AQH1234567890",
                }
            },
        )
        result = initialize_image_upload(account_id=ACCOUNT_ID)
        assert result["upload_url"] == "https://www.linkedin.com/dms-uploads/xxx"
        assert result["image_urn"] == "urn:li:image:C4E22AQH1234567890"

    @patch("scripts.li_campaign.requests.put")
    def test_upload_binary_succeeds(self, mock_put):
        mock_put.return_value = MagicMock(status_code=201)
        result = upload_image_binary(
            upload_url="https://www.linkedin.com/dms-uploads/xxx",
            image_data=b"fake-image-bytes",
        )
        assert result["success"] is True


class TestUploadImage:
    @patch("scripts.li_campaign.upload_image_binary")
    @patch("scripts.li_campaign.initialize_image_upload")
    def test_chains_initialize_and_upload(self, mock_init, mock_upload, tmp_path):
        mock_init.return_value = {
            "upload_url": "https://www.linkedin.com/dms-uploads/xxx",
            "image_urn": "urn:li:image:C4E22AQH1234567890",
        }
        mock_upload.return_value = {"success": True}

        # Create a temp image file
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-png-data")

        result = upload_image(account_id=ACCOUNT_ID, image_path=str(img_file))
        assert result["image_urn"] == "urn:li:image:C4E22AQH1234567890"
        mock_init.assert_called_once_with(ACCOUNT_ID)
        mock_upload.assert_called_once_with(
            "https://www.linkedin.com/dms-uploads/xxx",
            b"fake-png-data",
        )


class TestCreateCreative:
    @patch("scripts.li_campaign.requests.post")
    def test_creates_creative_with_image_and_copy(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201,
            headers={"x-restli-id": "creative-id-123"},
            json=lambda: {},
        )
        result = create_creative(
            account_id=ACCOUNT_ID,
            campaign_id="555838300",
            image_urn="urn:li:image:C4E22AQH1234567890",
            headline="Custom Intelligence",
            intro_text="Get competitive insights for your business.",
            cta="LEARN_MORE",
            destination_url="https://aurevon.com",
        )
        assert result["creative_id"] == "creative-id-123"

        # Verify request body structure
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["campaign"] == f"urn:li:sponsoredCampaign:555838300"
