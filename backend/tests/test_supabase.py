"""
test_supabase.py - Automated Tests for Supabase Cloud Database Adapter
Tests configuration detection, request header generation, and REST CRUD integration.
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch, MagicMock
from config import Config
import supabase_db


def test_supabase_configured_status():
    """Verify is_configured returns correctly based on Config."""
    with patch.object(Config, "SUPABASE_URL", "https://xyz.supabase.co"), \
         patch.object(Config, "SUPABASE_KEY", "sb_secret_test123"):
        assert supabase_db.is_configured() is True

    with patch.object(Config, "SUPABASE_URL", ""), \
         patch.object(Config, "SUPABASE_KEY", ""):
        assert supabase_db.is_configured() is False


def test_supabase_headers():
    """Verify request headers contain API key and Authorization bearer."""
    with patch.object(Config, "SUPABASE_KEY", "sb_secret_test123"):
        headers = supabase_db.get_headers()
        assert headers["apikey"] == "sb_secret_test123"
        assert headers["Authorization"] == "Bearer sb_secret_test123"
        assert headers["Content-Type"] == "application/json"


@patch("requests.get")
def test_supabase_get_products(mock_get):
    """Test retrieving products via Supabase REST adapter."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": 1,
            "name": "Cloud Headphones",
            "category": "Audio",
            "price": 199.99,
            "rating": 4.8,
            "reviews_count": 50,
            "stock": 10,
            "image_url": "https://example.com/img.jpg",
            "description": "Test description",
            "specs_json": ["ANC", "Bluetooth 5.3"]
        }
    ]
    mock_get.return_value = mock_resp

    with patch.object(Config, "SUPABASE_URL", "https://xyz.supabase.co"), \
         patch.object(Config, "SUPABASE_KEY", "sb_secret_test123"):
        products = supabase_db.get_products()
        assert len(products) == 1
        assert products[0]["name"] == "Cloud Headphones"
        assert products[0]["category"] == "Audio"


@patch("requests.post")
def test_supabase_log_activity(mock_post):
    """Test sending activity log to Supabase."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = [{"id": 101}]
    mock_post.return_value = mock_resp

    with patch.object(Config, "SUPABASE_URL", "https://xyz.supabase.co"), \
         patch.object(Config, "SUPABASE_KEY", "sb_secret_test123"):
        log_id = supabase_db.log_activity(
            session_id="test-session",
            action="TEST_ACTION",
            description="Testing Supabase log",
            details={"foo": "bar"}
        )
        assert log_id == 101
