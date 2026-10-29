"""
test_app.py - Automated Unit & API Tests for NovaMart Backend
Tests Database Connectivity, Authentication (Signup/Login),
SQL Activity Logging, and Mandatory Order Credentials.
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app import app, generate_token
import db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check_endpoint(client):
    """Test that /api/health reports healthy and returns database engine."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "engine" in data


def test_get_products_list(client):
    """Test listing products from the SQL catalog."""
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.get_json()
    assert "products" in data
    assert len(data["products"]) >= 1
    assert "name" in data["products"][0]
    assert "price" in data["products"][0]


def test_sql_activity_logging_endpoint(client):
    """Test that frontend activity is recorded into the SQL activity_logs table."""
    payload = {
        "session_id": "test-suite-session",
        "action": "TEST_UNIT_ACTION",
        "description": "Automated unit test event",
        "details": {"test": True, "runner": "pytest"}
    }
    response = client.post("/api/activities", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert "activity_id" in data

    # Verify retrieval
    res_get = client.get("/api/activities?limit=10")
    assert res_get.status_code == 200
    acts = res_get.get_json()["activities"]
    assert any(a["action"] == "TEST_UNIT_ACTION" for a in acts)


def test_user_signup_and_login_flow(client):
    """Test user registration and subsequent login."""
    test_email = f"tester_{os.getpid()}@example.com"
    signup_payload = {
        "name": "Pytest Tester",
        "email": test_email,
        "password": "securepassword123",
        "phone": "+1 555-000-1111",
        "address": "123 Test St",
        "city": "Testville",
        "postal": "12345"
    }

    # 1. Signup
    signup_res = client.post("/api/auth/signup", json=signup_payload)
    assert signup_res.status_code == 201
    s_data = signup_res.get_json()
    assert "token" in s_data
    assert s_data["user"]["email"] == test_email

    # 2. Duplicate signup should be rejected with 409
    dup_res = client.post("/api/auth/signup", json=signup_payload)
    assert dup_res.status_code == 409

    # 3. Login with correct credentials
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    l_data = login_res.get_json()
    assert "token" in l_data
    assert l_data["user"]["name"] == "Pytest Tester"

    # 4. Login with wrong password should fail with 401
    bad_login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "wrongpassword"
    })
    assert bad_login_res.status_code == 401


def test_order_creation_requires_credentials_401(client):
    """Test that placing an order without login/credentials returns 401 Unauthorized."""
    payload = {
        "customer_name": "Anonymous Guest",
        "customer_phone": "+1 555-1234",
        "shipping_address": "123 Guest St",
        "items": [{"product_id": 1, "quantity": 1}]
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 401
    data = response.get_json()
    assert data.get("auth_required") is True
    assert "credentials" in data.get("error").lower() or "authentication" in data.get("error").lower()


def test_order_creation_success_when_authenticated(client):
    """Test that authenticated order placement succeeds and records transaction in SQL."""
    # Create or use an authenticated user token
    token = generate_token(1, "john@example.com")

    payload = {
        "customer_name": "Demo Customer",
        "customer_phone": "+1 555-019-2834",
        "shipping_address": "456 Tech Blvd, Austin, TX",
        "payment_method": "Cash on Delivery",
        "items": [
            {"product_id": 1, "quantity": 1}
        ]
    }

    response = client.post(
        "/api/orders",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert "order_id" in data
    assert data["order"]["status"] == "Confirmed"
    assert data["order"]["customer_email"] == "john@example.com"
    assert data["order"]["subtotal"] > 0
