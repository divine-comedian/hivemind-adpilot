"""Tests for li_analytics.py — LinkedIn campaign analytics."""

import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest
import requests as requests_lib

from scripts.li_analytics import fetch_analytics, build_analytics_url


ACCOUNT_ID = "520217301"


class TestBuildAnalyticsUrl:
    def test_campaign_pivot_default_date_range(self):
        url = build_analytics_url(
            account_id=ACCOUNT_ID,
            pivot="CAMPAIGN",
            start_date=date(2026, 3, 7),
            end_date=date(2026, 3, 14),
        )
        assert "q=analytics" in url
        assert "pivot=CAMPAIGN" in url
        assert f"urn%3Ali%3AsponsoredAccount%3A{ACCOUNT_ID}" in url
        assert "year:2026" in url
        assert "month:3" in url
        assert "day:7" in url
        assert "day:14" in url

    def test_creative_pivot(self):
        url = build_analytics_url(
            account_id=ACCOUNT_ID,
            pivot="CREATIVE",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )
        assert "pivot=CREATIVE" in url


class TestFetchAnalytics:
    @patch("scripts.li_analytics.requests.get")
    def test_returns_parsed_elements(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "elements": [
                    {
                        "pivotValue": "urn:li:sponsoredCampaign:555838216",
                        "impressions": 5000,
                        "clicks": 345,
                        "costInLocalCurrency": "193.00",
                        "landingPageClicks": 200,
                        "likes": 5,
                        "shares": 2,
                        "externalWebsiteConversions": 0,
                    }
                ]
            },
        )
        result = fetch_analytics(
            account_id=ACCOUNT_ID,
            pivot="CAMPAIGN",
            start_date=date(2026, 3, 7),
            end_date=date(2026, 3, 14),
        )
        assert len(result) == 1
        assert result[0]["impressions"] == 5000
        assert result[0]["clicks"] == 345

    @patch("scripts.li_analytics.requests.get")
    def test_401_raises_auth_error(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=401,
            text='{"status":401,"code":"EXPIRED_ACCESS_TOKEN"}',
            json=lambda: {"status": 401, "code": "EXPIRED_ACCESS_TOKEN"},
        )
        with pytest.raises(SystemExit):
            fetch_analytics(
                account_id=ACCOUNT_ID,
                pivot="CAMPAIGN",
                start_date=date(2026, 3, 7),
                end_date=date(2026, 3, 14),
            )

    @patch("scripts.li_analytics.requests.get")
    def test_empty_elements_returns_empty_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"elements": []},
        )
        result = fetch_analytics(
            account_id=ACCOUNT_ID,
            pivot="CAMPAIGN",
            start_date=date(2026, 3, 7),
            end_date=date(2026, 3, 14),
        )
        assert result == []

    @patch("scripts.li_analytics.requests.get")
    def test_network_error_exits(self, mock_get):
        mock_get.side_effect = requests_lib.ConnectionError("DNS failure")
        with pytest.raises(SystemExit):
            fetch_analytics(
                account_id=ACCOUNT_ID,
                pivot="CAMPAIGN",
                start_date=date(2026, 3, 7),
                end_date=date(2026, 3, 14),
            )
