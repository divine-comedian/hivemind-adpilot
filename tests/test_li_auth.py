"""Tests for LinkedIn auth helpers — token validation."""

import pytest
import requests
from unittest.mock import patch, MagicMock

from scripts.li_auth import validate_token


class TestValidateToken:
    @patch("scripts.li_auth.requests.get")
    def test_valid_token_returns_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": 520217301, "name": "Aurevon Intelligence", "status": "ACTIVE"},
        )
        result = validate_token()
        assert result["valid"] is True
        assert result["account_name"] == "Aurevon Intelligence"

    @patch("scripts.li_auth.requests.get")
    def test_expired_token_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=401,
            json=lambda: {"status": 401, "code": "EXPIRED_ACCESS_TOKEN"},
        )
        result = validate_token()
        assert result["valid"] is False
        assert "expired" in result["error"].lower() or "401" in result["error"]

    @patch("scripts.li_auth.requests.get")
    def test_forbidden_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=403,
            json=lambda: {"status": 403, "message": "Not enough permissions"},
        )
        result = validate_token()
        assert result["valid"] is False

    @patch("scripts.li_auth.requests.get")
    def test_network_error_returns_failure(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("DNS failure")
        result = validate_token()
        assert result["valid"] is False
        assert "error" in result
