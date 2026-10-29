"""
app.py - NovaMart E-Commerce Flask REST API
Multi-Tier Application Logic with SQL Database Integration (MySQL / SQLite),
Comprehensive SQL Activity Logging for all user and system events,
and Mandatory Authentication during Order Checkout.
"""

import os
import sys

# Ensure backend directory is in sys.path so sibling modules (config, db, supabase_db) can be imported
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import base64
import hashlib
import hmac
import json
import logging
import random
import re
import string
import time
from typing import Optional, Tuple
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY
CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGIN, "supports_credentials": True}})

# Global error handlers ensuring all error responses are strictly JSON
@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({
        "error": "A server error occurred",
        "details": str(e)
    }), 500

@app.errorhandler(404)
def not_found_error(e):
    return jsonify({
        "error": "Endpoint not found",
        "path": request.path
    }), 404

@app.errorhandler(Exception)
def handle_unexpected_exception(e):
    logger.exception(f"Unhandled exception: {e}")
    return jsonify({
        "error": "An unexpected server error occurred",
        "message": str(e)
    }), 500

# Initialize database schema and initial seed data on startup
with app.app_context():
    try:
        db.init_db()
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")


# =============================================================================
# Helper Utilities: Authentication & Activity Logging
# =============================================================================

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


def generate_token(user_id: int, email: str) -> str:
    """Generate a tamper-proof signed session token."""
    ts = str(int(time.time()))
    payload = f"{user_id}:{email}:{ts}"
    signature = hmac.new(Config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def verify_token(token_str: str) -> Optional[Tuple[int, str]]:
    """Validate token signature and return (user_id, email) or None."""
    try:
        raw = base64.urlsafe_b64decode(token_str.encode()).decode()
        parts = raw.split(":")
        if len(parts) != 4:
            return None
        u_id, email, ts, sig = parts[0], parts[1], parts[2], parts[3]
        expected_sig = hmac.new(Config.SECRET_KEY.encode(), f"{u_id}:{email}:{ts}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return int(u_id), email
    except Exception:
        return None
    return None


def get_current_user():
    """Retrieve current authenticated user from request Authorization header or token param."""
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif request.headers.get("X-Auth-Token"):
        token = request.headers.get("X-Auth-Token").strip()
    elif request.args.get("token"):
        token = request.args.get("token").strip()

    if not token:
        return None

    verified = verify_token(token)
    if not verified:
        return None

    user_id, email = verified
    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            return supabase_db.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"Error fetching authenticated user {user_id} from Supabase: {e}")
            return None

    try:
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email, phone, address, city, postal, role, created_at FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error fetching authenticated user {user_id}: {e}")
        return None


def get_client_ip():
    """Extract client IP from proxy headers or remote addr."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


# =============================================================================
# Health & Diagnostic Endpoints
# =============================================================================

@app.route("/api", methods=["GET"])
@app.route("/api/", methods=["GET"])
def api_index():
    """Vercel API index route."""
    return jsonify({
        "name": "NovaMart E-Commerce API",
        "status": "online",
        "engine": db.get_active_engine(),
        "endpoints": [
            "/api/health",
            "/api/products",
            "/api/orders",
            "/api/auth/signup",
            "/api/auth/login"
        ]
    }), 200


@app.route("/api/health", methods=["GET"])
def health_check():
    """Check API health and database connectivity."""
    engine = db.get_active_engine()
    if engine == "supabase":
        import supabase_db
        ok, msg = supabase_db.test_connection()
        return jsonify({
            "status": "healthy" if ok else "degraded",
            "database": "connected" if ok else "disconnected",
            "engine": "supabase",
            "message": msg,
            "timestamp": time.time()
        }), (200 if ok else 503)

    db_status = "disconnected"
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        db_status = "connected"
        return jsonify({
            "status": "healthy",
            "database": db_status,
            "engine": engine,
            "timestamp": time.time()
        }), 200
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return jsonify({
            "status": "degraded",
            "database": db_status,
            "engine": engine,
            "error": str(e)
        }), 503


# =============================================================================
# SQL Activity Logging Endpoints (Records all User Actions into SQL DB)
# =============================================================================

@app.route("/api/activities", methods=["POST"])
def log_activity_endpoint():
    """
    Endpoint for frontend client activity logging.
    Records any activity (clicks, searches, filters, modal opens, cart changes)
    directly into the SQL database activity_logs table.
    """
    data = request.get_json() or {}
    session_id = data.get("session_id") or "guest-session"
    action = data.get("action") or "UNKNOWN_ACTION"
    description = data.get("description") or "User performed an activity"
    details = data.get("details")

    # Associate with authenticated user if present
    current_user = get_current_user()
    user_id = current_user["id"] if current_user else data.get("user_id")
    user_email = current_user["email"] if current_user else data.get("user_email")

    ip_address = get_client_ip()
    user_agent = request.user_agent.string if request.user_agent else "Browser"

    activity_id = db.log_activity(
        session_id=session_id,
        action=action,
        description=description,
        details=details,
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        user_agent=user_agent
    )

    return jsonify({
        "success": True,
        "message": "Activity recorded in SQL database",
        "activity_id": activity_id
    }), 201


@app.route("/api/activities", methods=["GET"])
def get_activities_endpoint():
    """
    Retrieve real-time activity stream from the SQL database.
    Useful for audit logs, live activity feeds, and verifying database writes.
    """
    limit = int(request.args.get("limit", 50))
    action = request.args.get("action")
    session_id = request.args.get("session_id")
    user_id = request.args.get("user_id", type=int)

    activities = db.get_recent_activities(
        limit=min(limit, 200),
        action=action,
        session_id=session_id,
        user_id=user_id
    )

    return jsonify({
        "activities": activities,
        "count": len(activities),
        "engine": db.get_active_engine()
    }), 200


# =============================================================================
# Authentication Endpoints (Signup, Login, Profile)
# =============================================================================

@app.route("/api/auth/signup", methods=["POST"])
def auth_signup():
    """
    Register a new user account.
    - Validates email format, unique email, and password strength
    - Securely hashes password using Werkzeug scrypt/pbkdf2
    - Inserts user into the SQL database
    - Logs USER_SIGNUP activity into the SQL database
    - Returns authentication token and user profile
    """
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()
    city = (data.get("city") or "").strip()
    postal = (data.get("postal") or "").strip()
    session_id = data.get("session_id") or "auth-session"

    if not name:
        return jsonify({"error": "Full name is required"}), 400
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"error": "A valid email address is required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400

    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            existing = supabase_db.get_user_by_email(email)
            if existing:
                return jsonify({"error": "An account with this email address already exists. Please log in."}), 409

            pw_hash = generate_password_hash(password)
            created_user = supabase_db.create_user({
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "city": city,
                "postal": postal,
                "password_hash": pw_hash,
                "role": "customer"
            })
            if not created_user:
                return jsonify({"error": "Failed to create account in database"}), 500

            user_id = created_user["id"]
            db.log_activity(
                session_id=session_id,
                action="USER_SIGNUP",
                description=f"New user registered: {name} ({email})",
                details={"email": email, "name": name, "user_id": user_id},
                user_id=user_id,
                user_email=email,
                ip_address=get_client_ip(),
                user_agent=request.user_agent.string if request.user_agent else None
            )

            token = generate_token(user_id, email)
            user_profile = {
                "id": user_id,
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "city": city,
                "postal": postal,
                "role": "customer"
            }
            logger.info(f"User signed up (Supabase): {email} (ID: {user_id})")
            return jsonify({
                "message": "Account created successfully",
                "token": token,
                "user": user_profile
            }), 201
        except Exception as e:
            logger.error(f"Signup error (Supabase): {e}")
            return jsonify({"error": f"Failed to create account: {str(e)}"}), 500

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "An account with this email address already exists. Please log in."}), 409

        # Hash password and insert
        pw_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (name, email, phone, address, city, postal, password_hash, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, email, phone, address, city, postal, pw_hash, "customer"))
        conn.commit()

        user_id = cursor.lastrowid
        cursor.close()
        conn.close()

        # Log signup activity into SQL database
        db.log_activity(
            session_id=session_id,
            action="USER_SIGNUP",
            description=f"New user registered: {name} ({email})",
            details={"email": email, "name": name, "user_id": user_id},
            user_id=user_id,
            user_email=email,
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string if request.user_agent else None
        )

        token = generate_token(user_id, email)
        user_profile = {
            "id": user_id,
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "city": city,
            "postal": postal,
            "role": "customer"
        }

        logger.info(f"User signed up: {email} (ID: {user_id})")
        return jsonify({
            "message": "Account created successfully",
            "token": token,
            "user": user_profile
        }), 201

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        logger.error(f"Signup error: {e}")
        return jsonify({"error": f"Failed to create account: {str(e)}"}), 500


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """
    Authenticate user credentials.
    - Validates email and password hash
    - Logs USER_LOGIN or LOGIN_FAILED activity into the SQL database
    - Returns authentication token and user profile
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    session_id = data.get("session_id") or "auth-session"

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            user = supabase_db.get_user_by_email(email)
            if not user or not check_password_hash(user["password_hash"], password):
                db.log_activity(
                    session_id=session_id,
                    action="LOGIN_FAILED",
                    description=f"Failed login attempt for email: {email}",
                    details={"email": email},
                    user_email=email,
                    ip_address=get_client_ip(),
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"error": "Invalid email or password"}), 401

            user_id = user["id"]
            token = generate_token(user_id, user["email"])
            user_profile = {
                "id": user_id,
                "name": user["name"],
                "email": user["email"],
                "phone": user.get("phone", ""),
                "address": user.get("address", ""),
                "city": user.get("city", ""),
                "postal": user.get("postal", ""),
                "role": user.get("role", "customer")
            }
            db.log_activity(
                session_id=session_id,
                action="USER_LOGIN",
                description=f"User logged in: {user['name']} ({user['email']})",
                details={"email": user["email"], "user_id": user_id},
                user_id=user_id,
                user_email=user["email"],
                ip_address=get_client_ip(),
                user_agent=request.user_agent.string if request.user_agent else None
            )
            logger.info(f"User logged in (Supabase): {user['email']}")
            return jsonify({
                "message": "Logged in successfully",
                "token": token,
                "user": user_profile
            }), 200
        except Exception as e:
            logger.error(f"Login error (Supabase): {e}")
            return jsonify({"error": "Database error during authentication"}), 500

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            db.log_activity(
                session_id=session_id,
                action="LOGIN_FAILED",
                description=f"Failed login attempt for email: {email}",
                details={"email": email},
                user_email=email,
                ip_address=get_client_ip(),
                user_agent=request.user_agent.string if request.user_agent else None
            )
            return jsonify({"error": "Invalid email or password"}), 401

        # Successful login
        user_id = user["id"]
        token = generate_token(user_id, user["email"])
        user_profile = {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "address": user.get("address", ""),
            "city": user.get("city", ""),
            "postal": user.get("postal", ""),
            "role": user.get("role", "customer")
        }

        # Log login activity into SQL database
        db.log_activity(
            session_id=session_id,
            action="USER_LOGIN",
            description=f"User logged in: {user['name']} ({user['email']})",
            details={"email": user["email"], "user_id": user_id},
            user_id=user_id,
            user_email=user["email"],
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string if request.user_agent else None
        )

        logger.info(f"User logged in: {user['email']}")
        return jsonify({
            "message": "Logged in successfully",
            "token": token,
            "user": user_profile
        }), 200

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Database error during authentication"}), 500


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Log user logout activity into the SQL database."""
    data = request.get_json() or {}
    session_id = data.get("session_id") or "auth-session"
    current_user = get_current_user()

    db.log_activity(
        session_id=session_id,
        action="USER_LOGOUT",
        description=f"User logged out: {current_user['name'] if current_user else 'Session'}",
        details={"user_id": current_user["id"] if current_user else None},
        user_id=current_user["id"] if current_user else None,
        user_email=current_user["email"] if current_user else None,
        ip_address=get_client_ip(),
        user_agent=request.user_agent.string if request.user_agent else None
    )

    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Retrieve current authenticated user profile."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Not authenticated"}), 401

    return jsonify({
        "user": {
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
            "phone": current_user.get("phone", ""),
            "address": current_user.get("address", ""),
            "city": current_user.get("city", ""),
            "postal": current_user.get("postal", ""),
            "role": current_user.get("role", "customer")
        }
    }), 200


# =============================================================================
# Product Catalog Endpoints (Browsing is 100% Free / Non-Mandatory Auth)
# =============================================================================

@app.route("/api/products", methods=["GET"])
def get_products():
    """
    List catalog products with optional category and search filters.
    Automatically logs search/catalog browse activity into the database.
    """
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()
    session_id = request.args.get("session_id", "guest-session")

    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            raw_products = supabase_db.get_products(category=category, search=search)
            products = []
            for r in raw_products:
                specs = r.get("specs_json") or []
                if isinstance(specs, str):
                    try:
                        specs = json.loads(specs)
                    except Exception:
                        specs = []
                products.append({
                    "id": r["id"],
                    "name": r["name"],
                    "category": r["category"],
                    "price": float(r["price"]),
                    "rating": float(r.get("rating", 5.0)),
                    "reviews_count": r.get("reviews_count", 0),
                    "stock": r["stock"],
                    "image": r.get("image_url", ""),
                    "description": r.get("description", ""),
                    "specs": specs
                })
            if search:
                db.log_activity(
                    session_id=session_id,
                    action="SEARCH",
                    description=f"Searched catalog for '{search}' (found {len(products)} items)",
                    details={"query": search, "category": category, "result_count": len(products)},
                    ip_address=get_client_ip(),
                    user_agent=request.user_agent.string if request.user_agent else None
                )
            return jsonify({"products": products, "count": len(products)}), 200
        except Exception as e:
            logger.error(f"Error fetching products from Supabase: {e}")
            return jsonify({"error": "Failed to retrieve products from database"}), 500

    query = "SELECT id, name, category, price, rating, reviews_count, stock, image_url, description, specs_json FROM products WHERE 1=1"
    params = []

    if category and category.lower() != "all":
        query += " AND LOWER(category) = LOWER(%s)"
        params.append(category)

    if search:
        query += " AND (LOWER(name) LIKE %s OR LOWER(description) LIKE %s OR LOWER(category) LIKE %s)"
        like_term = f"%{search.lower()}%"
        params.extend([like_term, like_term, like_term])

    query += " ORDER BY id ASC"

    try:
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        products = []
        for r in rows:
            specs = []
            if r.get("specs_json"):
                try:
                    specs = json.loads(r["specs_json"]) if isinstance(r["specs_json"], str) else r["specs_json"]
                except Exception:
                    specs = []

            products.append({
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "price": float(r["price"]),
                "rating": float(r["rating"]),
                "reviews_count": r["reviews_count"],
                "stock": r["stock"],
                "image": r["image_url"],
                "description": r["description"],
                "specs": specs
            })

        cursor.close()
        conn.close()

        # Log search activity into SQL database if search was performed
        if search:
            db.log_activity(
                session_id=session_id,
                action="SEARCH",
                description=f"Searched catalog for '{search}' (found {len(products)} items)",
                details={"query": search, "category": category, "result_count": len(products)},
                ip_address=get_client_ip(),
                user_agent=request.user_agent.string if request.user_agent else None
            )

        return jsonify({"products": products, "count": len(products)}), 200
    except Exception as err:
        logger.error(f"Error fetching products: {err}")
        return jsonify({"error": "Failed to retrieve products from database"}), 500


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """
    Retrieve single product by ID.
    Automatically logs PRODUCT_VIEW into database.
    """
    session_id = request.args.get("session_id", "guest-session")

    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            r = supabase_db.get_product_by_id(product_id)
            if not r:
                return jsonify({"error": f"Product with ID {product_id} not found"}), 404
            specs = r.get("specs_json") or []
            if isinstance(specs, str):
                try:
                    specs = json.loads(specs)
                except Exception:
                    specs = []
            product = {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "price": float(r["price"]),
                "rating": float(r.get("rating", 5.0)),
                "reviews_count": r.get("reviews_count", 0),
                "stock": r["stock"],
                "image": r.get("image_url", ""),
                "description": r.get("description", ""),
                "specs": specs
            }
            db.log_activity(
                session_id=session_id,
                action="VIEW_PRODUCT",
                description=f"Viewed product: {product['name']} (${product['price']})",
                details={"product_id": product_id, "name": product["name"], "price": product["price"]},
                ip_address=get_client_ip(),
                user_agent=request.user_agent.string if request.user_agent else None
            )
            return jsonify({"product": product}), 200
        except Exception as err:
            logger.error(f"Error fetching product {product_id} from Supabase: {err}")
            return jsonify({"error": "Database error while fetching product"}), 500

    try:
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, category, price, rating, reviews_count, stock, image_url, description, specs_json FROM products WHERE id = %s",
            (product_id,)
        )
        r = cursor.fetchone()
        cursor.close()
        conn.close()

        if not r:
            return jsonify({"error": f"Product with ID {product_id} not found"}), 404

        specs = []
        if r.get("specs_json"):
            try:
                specs = json.loads(r["specs_json"]) if isinstance(r["specs_json"], str) else r["specs_json"]
            except Exception:
                specs = []

        product = {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "price": float(r["price"]),
            "rating": float(r["rating"]),
            "reviews_count": r["reviews_count"],
            "stock": r["stock"],
            "image": r["image_url"],
            "description": r["description"],
            "specs": specs
        }

        # Log product view in SQL database
        db.log_activity(
            session_id=session_id,
            action="VIEW_PRODUCT",
            description=f"Viewed product: {product['name']} (${product['price']})",
            details={"product_id": product_id, "name": product["name"], "price": product["price"]},
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string if request.user_agent else None
        )

        return jsonify({"product": product}), 200
    except Exception as err:
        logger.error(f"Error fetching product {product_id}: {err}")
        return jsonify({"error": "Database error while fetching product"}), 500


# =============================================================================
# Order Processing Endpoints (CREDENTIALS MANDATORY ONLY HERE)
# =============================================================================

@app.route("/api/orders", methods=["POST"])
def create_order():
    """
    Create a new customer order.
    MANDATORY AUTHENTICATION:
    The user explicitly requested that login/signup should NOT be mandatory to browse,
    BUT when ordering something, credentials ARE MANDATORY.
    - Requires either an active authenticated user session or valid credentials in the request.
    - Re-calculates prices on the server to prevent client-side tampering.
    - Executes atomic SQL database transaction across orders, order_items, and products.
    - Logs ORDER_PLACED into the SQL activity_logs table.
    """
    data = request.get_json() or {}
    session_id = data.get("session_id") or "order-session"

    # 1. Check Authentication / Credentials Requirement
    current_user = get_current_user()

    # Check for inline credentials if no session token
    if not current_user and data.get("credentials"):
        creds = data.get("credentials")
        c_email = (creds.get("email") or "").strip().lower()
        c_pass = creds.get("password") or ""
        if c_email and c_pass:
            if db.get_active_engine() == "supabase":
                import supabase_db
                u = supabase_db.get_user_by_email(c_email)
            else:
                conn_auth = db.get_db_connection()
                cur_auth = conn_auth.cursor(dictionary=True)
                cur_auth.execute("SELECT * FROM users WHERE LOWER(email) = %s", (c_email,))
                u = cur_auth.fetchone()
                cur_auth.close()
                conn_auth.close()
            if u and check_password_hash(u["password_hash"], c_pass):
                current_user = u

    # If still unauthenticated, REJECT order and ask for credentials!
    if not current_user:
        db.log_activity(
            session_id=session_id,
            action="ORDER_AUTH_REQUIRED",
            description="Guest tried to checkout without credentials; prompt for login/signup presented",
            details={"cart_items_count": len(data.get("items") or [])},
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string if request.user_agent else None
        )
        return jsonify({
            "error": "Authentication required. Please sign in or create an account with your credentials to complete your order.",
            "auth_required": True
        }), 401

    # 2. Extract Customer & Order Information
    customer_name = (data.get("customer_name") or current_user["name"]).strip()
    customer_email = current_user["email"]
    customer_phone = (data.get("customer_phone") or current_user.get("phone") or "").strip()
    shipping_address = (data.get("shipping_address") or current_user.get("address") or "").strip()
    payment_method = data.get("payment_method") or "Cash on Delivery"
    items = data.get("items") or []

    if not customer_name:
        return jsonify({"error": "Customer name is required"}), 400
    if not customer_phone:
        return jsonify({"error": "Phone number is required for shipping"}), 400
    if not shipping_address:
        return jsonify({"error": "Shipping address is required"}), 400
    if not items or not isinstance(items, list):
        return jsonify({"error": "Order must contain at least one item"}), 400

    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            calculated_subtotal = 0.0
            verified_items = []
            for item in items:
                p_id = item.get("product_id") or item.get("id")
                qty = item.get("quantity", 0)
                if not p_id or not isinstance(qty, int) or qty <= 0:
                    return jsonify({"error": f"Invalid item or quantity for product ID {p_id}"}), 400
                prod = supabase_db.get_product_by_id(p_id)
                if not prod:
                    return jsonify({"error": f"Product with ID {p_id} does not exist"}), 400
                if prod["stock"] < qty:
                    return jsonify({"error": f"Insufficient stock for '{prod['name']}'. Available: {prod['stock']}"}), 400
                unit_price = float(prod["price"])
                line_subtotal = round(unit_price * qty, 2)
                calculated_subtotal += line_subtotal
                verified_items.append({
                    "product_id": prod["id"],
                    "product_name": prod["name"],
                    "unit_price": unit_price,
                    "quantity": qty,
                    "subtotal": line_subtotal
                })

            calculated_subtotal = round(calculated_subtotal, 2)
            shipping_fee = 0.0 if calculated_subtotal > 150.0 else 15.0
            tax_amount = round(calculated_subtotal * 0.08, 2)
            total_amount = round(calculated_subtotal + shipping_fee + tax_amount, 2)

            random_suffix = "".join(random.choices(string.digits, k=6))
            order_id = f"ORD-{random_suffix}"

            order_payload = {
                "id": order_id,
                "user_id": current_user["id"],
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "shipping_address": shipping_address,
                "payment_method": payment_method,
                "status": "Confirmed",
                "subtotal": calculated_subtotal,
                "shipping_fee": shipping_fee,
                "tax_amount": tax_amount,
                "total_amount": total_amount
            }

            created_order = supabase_db.create_order(order_payload, verified_items)
            if not created_order:
                return jsonify({"error": "Failed to create order in Supabase"}), 500

            db.log_activity(
                session_id=session_id,
                action="ORDER_PLACED",
                description=f"Order {order_id} placed by {customer_name} (${total_amount:.2f})",
                details={
                    "order_id": order_id,
                    "total_amount": total_amount,
                    "items_count": len(verified_items),
                    "items": [{"name": i["product_name"], "qty": i["quantity"]} for i in verified_items],
                    "payment_method": payment_method
                },
                user_id=current_user["id"],
                user_email=customer_email,
                ip_address=get_client_ip(),
                user_agent=request.user_agent.string if request.user_agent else None
            )

            logger.info(f"Order {order_id} created for {customer_email} (Supabase)")
            return jsonify({
                "message": "Order created successfully",
                "order_id": order_id,
                "order": {
                    "id": order_id,
                    "user_id": current_user["id"],
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "shipping_address": shipping_address,
                    "payment_method": payment_method,
                    "status": "Confirmed",
                    "items": verified_items,
                    "subtotal": calculated_subtotal,
                    "shipping_fee": shipping_fee,
                    "tax_amount": tax_amount,
                    "total_amount": total_amount
                }
            }), 201
        except Exception as e:
            logger.error(f"Error placing order in Supabase: {e}")
            return jsonify({"error": f"Failed to place order in Supabase: {str(e)}"}), 500

    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 3. Server-Side Price & Inventory Verification
        calculated_subtotal = 0.0
        verified_items = []

        for item in items:
            p_id = item.get("product_id") or item.get("id")
            qty = item.get("quantity", 0)

            if not p_id or not isinstance(qty, int) or qty <= 0:
                conn.rollback()
                return jsonify({"error": f"Invalid item or quantity for product ID {p_id}"}), 400

            cursor.execute("SELECT id, name, price, stock FROM products WHERE id = %s", (p_id,))
            prod = cursor.fetchone()

            if not prod:
                conn.rollback()
                return jsonify({"error": f"Product with ID {p_id} does not exist"}), 400

            if prod["stock"] < qty:
                conn.rollback()
                return jsonify({"error": f"Insufficient stock for '{prod['name']}'. Available: {prod['stock']}"}), 400

            unit_price = float(prod["price"])
            line_subtotal = round(unit_price * qty, 2)
            calculated_subtotal += line_subtotal

            verified_items.append({
                "product_id": prod["id"],
                "product_name": prod["name"],
                "unit_price": unit_price,
                "quantity": qty,
                "subtotal": line_subtotal
            })

        calculated_subtotal = round(calculated_subtotal, 2)
        shipping_fee = 0.0 if calculated_subtotal > 150.0 else 15.0
        tax_amount = round(calculated_subtotal * 0.08, 2)
        total_amount = round(calculated_subtotal + shipping_fee + tax_amount, 2)

        # 4. Generate unique order ID
        random_suffix = "".join(random.choices(string.digits, k=6))
        order_id = f"ORD-{random_suffix}"

        # 5. Insert into `orders` SQL table
        insert_order_query = """
            INSERT INTO orders (id, user_id, customer_name, customer_email, customer_phone, 
                                shipping_address, payment_method, status, 
                                subtotal, shipping_fee, tax_amount, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_order_query, (
            order_id, current_user["id"], customer_name, customer_email, customer_phone,
            shipping_address, payment_method, "Confirmed",
            calculated_subtotal, shipping_fee, tax_amount, total_amount
        ))

        # 6. Insert into `order_items` & decrement stock
        insert_item_query = """
            INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        update_stock_query = "UPDATE products SET stock = stock - %s WHERE id = %s"

        for v_item in verified_items:
            cursor.execute(insert_item_query, (
                order_id, v_item["product_id"], v_item["product_name"],
                v_item["unit_price"], v_item["quantity"], v_item["subtotal"]
            ))
            cursor.execute(update_stock_query, (v_item["quantity"], v_item["product_id"]))

        # 7. Commit transaction atomically
        conn.commit()
        cursor.close()
        conn.close()

        # 8. Record ORDER_PLACED into SQL activity_logs table
        db.log_activity(
            session_id=session_id,
            action="ORDER_PLACED",
            description=f"Order {order_id} placed by {customer_name} (${total_amount:.2f})",
            details={
                "order_id": order_id,
                "total_amount": total_amount,
                "items_count": len(verified_items),
                "items": [{"name": i["product_name"], "qty": i["quantity"]} for i in verified_items],
                "payment_method": payment_method
            },
            user_id=current_user["id"],
            user_email=customer_email,
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string if request.user_agent else None
        )

        logger.info(f"Order {order_id} created for {customer_email}")

        return jsonify({
            "message": "Order created successfully",
            "order_id": order_id,
            "order": {
                "id": order_id,
                "user_id": current_user["id"],
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "shipping_address": shipping_address,
                "payment_method": payment_method,
                "status": "Confirmed",
                "items": verified_items,
                "subtotal": calculated_subtotal,
                "shipping_fee": shipping_fee,
                "tax_amount": tax_amount,
                "total_amount": total_amount
            }
        }), 201

    except Exception as err:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Error placing order: {err}")
        return jsonify({"error": f"Failed to place order: {str(err)}"}), 500


@app.route("/api/orders", methods=["GET"])
def get_orders():
    """
    Retrieve historical orders with their line items.
    Supports filtering by search query (order ID or customer email) or authenticated user.
    """
    current_user = get_current_user()
    session_id = request.args.get("session_id", "guest-session")
    search_q = request.args.get("q", "").strip()
    search_email = request.args.get("email", "").strip().lower()
    search_order_id = request.args.get("order_id", "").strip()

    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            if search_order_id:
                single = supabase_db.get_order_by_id(search_order_id)
                orders = [single] if single else []
            elif current_user:
                orders = supabase_db.get_orders_by_user(current_user["id"])
            else:
                orders = []
            return jsonify({"orders": orders, "count": len(orders)}), 200
        except Exception as e:
            logger.error(f"Error fetching orders from Supabase: {e}")
            return jsonify({"error": "Failed to retrieve orders"}), 500

    try:
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, user_id, customer_name, customer_email, customer_phone, 
                   shipping_address, payment_method, status, 
                   subtotal, shipping_fee, tax_amount, total_amount, created_at
            FROM orders WHERE 1=1
        """
        params = []

        if search_order_id:
            query += " AND LOWER(id) LIKE %s"
            params.append(f"%{search_order_id.lower()}%")
        elif search_email:
            query += " AND LOWER(customer_email) = %s"
            params.append(search_email)
        elif search_q:
            query += " AND (LOWER(id) LIKE %s OR LOWER(customer_email) LIKE %s OR LOWER(customer_name) LIKE %s)"
            like_term = f"%{search_q.lower()}%"
            params.extend([like_term, like_term, like_term])
        elif current_user and current_user.get("role") != "admin":
            query += " AND (user_id = %s OR LOWER(customer_email) = %s)"
            params.extend([current_user["id"], current_user["email"].lower()])

        query += " ORDER BY created_at DESC LIMIT 50"

        cursor.execute(query, tuple(params))
        orders = cursor.fetchall()

        for o in orders:
            o["subtotal"] = float(o["subtotal"])
            o["shipping_fee"] = float(o["shipping_fee"])
            o["tax_amount"] = float(o["tax_amount"])
            o["total_amount"] = float(o["total_amount"])
            created = o.get("created_at")
            if hasattr(created, "isoformat"):
                o["created_at"] = created.isoformat()
            else:
                o["created_at"] = str(created).replace(" ", "T") if created else ""

            # Fetch line items for each order
            cursor.execute(
                "SELECT product_id, product_name, unit_price, quantity, subtotal FROM order_items WHERE order_id = %s",
                (o["id"],)
            )
            items = cursor.fetchall()
            for itm in items:
                itm["unit_price"] = float(itm["unit_price"])
                itm["subtotal"] = float(itm["subtotal"])
            o["items"] = items

        cursor.close()
        conn.close()

        # Log viewing order history into SQL database
        db.log_activity(
            session_id=session_id,
            action="VIEW_ORDERS_HISTORY",
            description=f"Viewed orders list ({len(orders)} orders found)",
            details={"orders_count": len(orders), "filter": search_q or search_email or search_order_id},
            user_id=current_user["id"] if current_user else None,
            user_email=current_user["email"] if current_user else None,
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string if request.user_agent else None
        )

        return jsonify({"orders": orders, "count": len(orders)}), 200
    except Exception as err:
        logger.error(f"Error fetching orders: {err}")
        return jsonify({"error": "Failed to retrieve orders"}), 500


@app.route("/api/orders/<order_id>", methods=["GET"])
def get_order_by_id(order_id):
    """Retrieve detailed order information along with its line items."""
    if db.get_active_engine() == "supabase":
        try:
            import supabase_db
            order = supabase_db.get_order_by_id(order_id)
            if not order:
                return jsonify({"error": f"Order {order_id} not found"}), 404
            return jsonify({"order": order}), 200
        except Exception as e:
            logger.error(f"Error fetching order {order_id} from Supabase: {e}")
            return jsonify({"error": "Failed to fetch order details"}), 500

    try:
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()

        if not order:
            cursor.close()
            conn.close()
            return jsonify({"error": f"Order {order_id} not found"}), 404

        order["subtotal"] = float(order["subtotal"])
        order["shipping_fee"] = float(order["shipping_fee"])
        order["tax_amount"] = float(order["tax_amount"])
        order["total_amount"] = float(order["total_amount"])
        created = order.get("created_at")
        order["created_at"] = created.isoformat() if hasattr(created, "isoformat") else str(created)

        # Fetch line items
        cursor.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
        items = cursor.fetchall()
        for i in items:
            i["unit_price"] = float(i["unit_price"])
            i["subtotal"] = float(i["subtotal"])

        order["items"] = items

        cursor.close()
        conn.close()
        return jsonify({"order": order}), 200
    except Exception as err:
        logger.error(f"Error fetching order {order_id}: {err}")
        return jsonify({"error": "Failed to fetch order details"}), 500


# =============================================================================
# Application Startup
# =============================================================================

if __name__ == "__main__":
    logger.info(f"Starting NovaMart Flask API on port {Config.PORT} (SQL Engine={db.get_active_engine()})...")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
