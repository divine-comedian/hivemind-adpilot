"""Tests for Facebook auth helpers — token validation."""

import pytest
import requests
from unittest.mock import patch, MagicMock

from scripts.fb_auth import validate_token


class TestValidateToken:
    @patch("scripts.fb_auth.requests.get")
    def test_valid_token_returns_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": "act_22243234",
                "name": "Aurevon Intelligence",
                "account_status": 1,
                "currency": "CAD",
                "balance": "0",
            },
        )
        result = validate_token()
        assert result["valid"] is True
        assert result["account_id"] == "22243234"
        assert result["account_name"] == "Aurevon Intelligence"
        assert result["currency"] == "CAD"

    @patch("scripts.fb_auth.requests.get")
    def test_expired_token_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            json=lambda: {
                "error": {
                    "message": "Error validating access token: Session has expired",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )
        result = validate_token()
        assert result["valid"] is False
        assert "expired" in result["error"].lower() or "400" in result["error"]

    @patch("scripts.fb_auth.requests.get")
    def test_invalid_token_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            json=lambda: {
                "error": {
                    "message": "Invalid OAuth access token",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )
        result = validate_token()
        assert result["valid"] is False

    @patch("scripts.fb_auth.requests.get")
    def test_network_error_returns_failure(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("DNS failure")
        result = validate_token()
        assert result["valid"] is False
        assert "error" in result
