"""Tests for fb_insights.py — Facebook ad insights."""

from datetime import date
from unittest.mock import patch, MagicMock

import pytest
import requests as requests_lib

from scripts.fb_insights import fetch_insights, build_insights_url


ACCOUNT_ID = "22243234"


class TestBuildInsightsUrl:
    def test_account_level_url(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert f"act_{ACCOUNT_ID}/insights" in url
        assert "2026-03-08" in params["time_range"]
        assert "2026-03-14" in params["time_range"]
        assert "level" not in params

    def test_campaign_level_url(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="campaign",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert f"act_{ACCOUNT_ID}/insights" in url
        assert params["level"] == "campaign"

    def test_ad_level_url(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="ad",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert params["level"] == "ad"

    def test_includes_required_fields(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        fields = params["fields"]
        assert "impressions" in fields
        assert "clicks" in fields
        assert "spend" in fields
        assert "cpc" in fields
        assert "ctr" in fields
        assert "actions" in fields

    def test_strips_act_prefix_if_present(self):
        url, params = build_insights_url(
            account_id=f"act_{ACCOUNT_ID}",
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert f"act_{ACCOUNT_ID}/insights" in url
        assert f"act_act_{ACCOUNT_ID}" not in url


class TestFetchInsights:
    @patch("scripts.fb_insights.requests.get")
    def test_returns_parsed_data(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "campaign_name": "Aurevon Traffic",
                        "campaign_id": "120218765432",
                        "impressions": "15234",
                        "clicks": "429",
                        "spend": "111.00",
                        "cpc": "0.26",
                        "ctr": "2.82",
                        "actions": [
                            {"action_type": "landing_page_view", "value": "429"}
                        ],
                    }
                ],
            },
        )
        result = fetch_insights(
            account_id=ACCOUNT_ID,
            level="campaign",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert len(result) == 1
        assert result[0]["impressions"] == "15234"
        assert result[0]["clicks"] == "429"

    @patch("scripts.fb_insights.requests.get")
    def test_handles_pagination(self, mock_get):
        """Facebook paginates large result sets via paging.next URL."""
        page1_response = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [{"campaign_id": "111", "impressions": "100"}],
                "paging": {"next": "https://graph.facebook.com/v25.0/page2"},
            },
        )
        page2_response = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [{"campaign_id": "222", "impressions": "200"}],
            },
        )
        mock_get.side_effect = [page1_response, page2_response]

        result = fetch_insights(
            account_id=ACCOUNT_ID,
            level="campaign",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert len(result) == 2
        assert mock_get.call_count == 2

    @patch("scripts.fb_insights.requests.get")
    def test_auth_error_exits(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            text='{"error":{"message":"Error validating access token","type":"OAuthException","code":190}}',
            json=lambda: {
                "error": {
                    "message": "Error validating access token",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )
        with pytest.raises(SystemExit):
            fetch_insights(
                account_id=ACCOUNT_ID,
                level="campaign",
                start_date=date(2026, 3, 8),
                end_date=date(2026, 3, 14),
            )

    @patch("scripts.fb_insights.requests.get")
    def test_empty_data_returns_empty_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": []},
        )
        result = fetch_insights(
            account_id=ACCOUNT_ID,
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert result == []

    @patch("scripts.fb_insights.requests.get")
    def test_network_error_exits(self, mock_get):
        mock_get.side_effect = requests_lib.ConnectionError("DNS failure")
        with pytest.raises(SystemExit):
            fetch_insights(
                account_id=ACCOUNT_ID,
                level="campaign",
                start_date=date(2026, 3, 8),
                end_date=date(2026, 3, 14),
            )

    @patch("scripts.fb_insights.requests.get")
    def test_rate_limit_error_exits(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            text='{"error":{"message":"Too many calls","type":"OAuthException","code":613}}',
            json=lambda: {
                "error": {
                    "message": "Too many calls",
                    "type": "OAuthException",
                    "code": 613,
                }
            },
        )
        with pytest.raises(SystemExit):
            fetch_insights(
                account_id=ACCOUNT_ID,
                level="campaign",
                start_date=date(2026, 3, 8),
                end_date=date(2026, 3, 14),
            )
