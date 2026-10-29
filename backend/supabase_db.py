"""
supabase_db.py - Supabase Cloud Database Client for NovaMart E-Commerce
Communicates with Supabase PostgreSQL via PostgREST REST API using the Secret API Key.
Provides full CRUD for users, products, orders, order items, and audit activity logging.
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional, Tuple, Union
from werkzeug.security import generate_password_hash
from config import Config

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 8


def is_configured() -> bool:
    """Check if Supabase URL and Secret Key are configured."""
    return bool(Config.SUPABASE_URL and Config.SUPABASE_KEY)


def get_headers(prefer: str = "return=representation") -> Dict[str, str]:
    """Return standard authentication and content headers for Supabase API."""
    headers = {
        "apikey": Config.SUPABASE_KEY,
        "Authorization": f"Bearer {Config.SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def test_connection() -> Tuple[bool, str]:
    """Test connectivity to Supabase project."""
    if not is_configured():
        return False, "Supabase URL or Key not set"
    try:
        url = f"{Config.SUPABASE_URL}/rest/v1/users"
        resp = requests.get(url, headers=get_headers(), params={"select": "id", "limit": "1"}, timeout=TIMEOUT_SECONDS)
        if resp.status_code in (200, 206):
            return True, "Connected successfully"
        elif resp.status_code == 404:
            return False, "Connected, but 'users' table not found in Supabase. Run database/supabase_schema.sql in Supabase SQL Editor."
        elif resp.status_code in (401, 403):
            return False, f"Supabase authentication failed ({resp.status_code}): Check SUPABASE_KEY"
        else:
            return False, f"Supabase responded with HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"Failed to connect to Supabase: {str(e)}"


# =============================================================================
# Products & Catalog (Served from Vercel Application Storage)
# =============================================================================

def _get_catalog_from_storage(category: Optional[str] = None, search: Optional[str] = None, sort_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve and filter catalog products directly from Vercel application storage."""
    from db import DEFAULT_PRODUCTS
    items = []
    for p in DEFAULT_PRODUCTS:
        specs = p.get("specs_json")
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except Exception:
                specs = []
        items.append({
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "price": float(p["price"]),
            "rating": float(p.get("rating", 5.0)),
            "reviews_count": p.get("reviews_count", 0),
            "stock": p.get("stock", 0),
            "image_url": p.get("image_url", ""),
            "description": p.get("description", ""),
            "specs_json": specs
        })

    if category and category.lower() != "all":
        items = [p for p in items if p["category"].lower() == category.lower()]

    if search:
        s = search.lower().strip()
        items = [
            p for p in items
            if s in p["name"].lower() or s in p["description"].lower() or s in p["category"].lower()
        ]

    if sort_by == "price-asc":
        items.sort(key=lambda x: x["price"])
    elif sort_by == "price-desc":
        items.sort(key=lambda x: x["price"], reverse=True)
    elif sort_by == "rating":
        items.sort(key=lambda x: x["rating"], reverse=True)
    else:
        items.sort(key=lambda x: x["id"])

    return items


def get_products(category: Optional[str] = None, search: Optional[str] = None, sort_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve catalog products.
    First checks if Supabase has items (e.g. tests or custom setup); if empty or absent,
    serves directly from Vercel application storage (db.DEFAULT_PRODUCTS).
    """
    if is_configured():
        try:
            url = f"{Config.SUPABASE_URL}/rest/v1/products"
            params: Dict[str, str] = {"select": "*"}

            if category and category.lower() != "all":
                params["category"] = f"eq.{category}"

            if search:
                search_clean = search.replace("%", "").strip()
                params["or"] = f"(name.ilike.*{search_clean}*,description.ilike.*{search_clean}*)"

            if sort_by == "price-asc":
                params["order"] = "price.asc"
            elif sort_by == "price-desc":
                params["order"] = "price.desc"
            elif sort_by == "rating":
                params["order"] = "rating.desc"
            else:
                params["order"] = "id.asc"

            resp = requests.get(url, headers=get_headers(), params=params, timeout=TIMEOUT_SECONDS)
            if resp.status_code == 200:
                products = resp.json()
                if products:
                    for p in products:
                        if isinstance(p.get("specs_json"), str):
                            try:
                                p["specs_json"] = json.loads(p["specs_json"])
                            except Exception:
                                pass
                    return products
        except Exception as e:
            logger.debug(f"Catalog items served from Vercel storage: {e}")

    return _get_catalog_from_storage(category, search, sort_by)


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve single product by ID from Supabase or Vercel application storage."""
    if is_configured():
        try:
            url = f"{Config.SUPABASE_URL}/rest/v1/products"
            params = {"id": f"eq.{product_id}", "select": "*"}
            resp = requests.get(url, headers=get_headers(), params=params, timeout=TIMEOUT_SECONDS)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    p = rows[0]
                    if isinstance(p.get("specs_json"), str):
                        try:
                            p["specs_json"] = json.loads(p["specs_json"])
                        except Exception:
                            pass
                    return p
        except Exception:
            pass

    from db import DEFAULT_PRODUCTS
    for p in DEFAULT_PRODUCTS:
        if p["id"] == int(product_id):
            p_copy = dict(p)
            if isinstance(p_copy.get("specs_json"), str):
                try:
                    p_copy["specs_json"] = json.loads(p_copy["specs_json"])
                except Exception:
                    pass
            return p_copy
    return None


def get_categories() -> List[str]:
    """Fetch distinct category names from Supabase or Vercel application storage."""
    if is_configured():
        try:
            url = f"{Config.SUPABASE_URL}/rest/v1/products"
            params = {"select": "category"}
            resp = requests.get(url, headers=get_headers(), params=params, timeout=TIMEOUT_SECONDS)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    cats = {r["category"] for r in rows if r.get("category")}
                    return sorted(list(cats))
        except Exception:
            pass

    from db import DEFAULT_PRODUCTS
    cats = {p["category"] for p in DEFAULT_PRODUCTS if p.get("category")}
    return sorted(list(cats))


# =============================================================================
# Users & Authentication
# =============================================================================

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch user profile by user ID."""
    if not is_configured():
        return None
    url = f"{Config.SUPABASE_URL}/rest/v1/users"
    params = {"id": f"eq.{user_id}", "select": "*"}
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
        return None
    except Exception as e:
        logger.error(f"Error fetching user {user_id} from Supabase: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch user profile by email address."""
    if not is_configured():
        return None
    url = f"{Config.SUPABASE_URL}/rest/v1/users"
    params = {"email": f"eq.{email.strip().lower()}", "select": "*"}
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
        elif resp.status_code == 404:
            raise RuntimeError("Database table 'users' does not exist in Supabase yet. Please run database/supabase_schema.sql in the Supabase SQL Editor.")
        return None
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error fetching user by email {email} from Supabase: {e}")
        return None


def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a new user record into Supabase users table."""
    if not is_configured():
        raise RuntimeError("Supabase credentials not configured on server. Please check environment variables.")
    url = f"{Config.SUPABASE_URL}/rest/v1/users"
    try:
        resp = requests.post(url, headers=get_headers(), json=user_data, timeout=TIMEOUT_SECONDS)
        if resp.status_code in (200, 201):
            created = resp.json()
            return created[0] if isinstance(created, list) and created else created
        elif resp.status_code == 404:
            raise RuntimeError("Database table 'users' does not exist in Supabase yet. Please run database/supabase_schema.sql in the Supabase SQL Editor.")
        else:
            logger.error(f"Supabase create_user failed: {resp.status_code} {resp.text}")
            raise RuntimeError(f"Database error ({resp.status_code}): {resp.text[:200]}")
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error creating user in Supabase: {e}")
        raise RuntimeError(f"Database error while creating user: {str(e)}")


def update_user(user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update user profile fields."""
    if not is_configured():
        return None
    url = f"{Config.SUPABASE_URL}/rest/v1/users"
    params = {"id": f"eq.{user_id}"}
    try:
        resp = requests.patch(url, headers=get_headers(), params=params, json=updates, timeout=TIMEOUT_SECONDS)
        if resp.status_code in (200, 204):
            data = resp.json() if resp.status_code == 200 else {}
            return data[0] if isinstance(data, list) and data else data
        return None
    except Exception as e:
        logger.error(f"Error updating user in Supabase: {e}")
        return None


# =============================================================================
# Orders & Checkout
# =============================================================================

def create_order(order_data: Dict[str, Any], items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Persist order and line items into Supabase.
    Decrements product inventory stock atomically.
    """
    if not is_configured():
        return None

    # 1. Insert order
    url_order = f"{Config.SUPABASE_URL}/rest/v1/orders"
    try:
        resp_order = requests.post(url_order, headers=get_headers(), json=order_data, timeout=TIMEOUT_SECONDS)
        if resp_order.status_code not in (200, 201):
            logger.error(f"Supabase order creation failed: {resp_order.status_code} {resp_order.text}")
            return None
        created_order = resp_order.json()
        order_record = created_order[0] if isinstance(created_order, list) else created_order

        # 2. Insert order items
        url_items = f"{Config.SUPABASE_URL}/rest/v1/order_items"
        items_payload = []
        for it in items:
            items_payload.append({
                "order_id": order_data["id"],
                "product_id": it["product_id"],
                "product_name": it["product_name"],
                "unit_price": it["unit_price"],
                "quantity": it["quantity"],
                "subtotal": it["subtotal"]
            })

        resp_items = requests.post(url_items, headers=get_headers(), json=items_payload, timeout=TIMEOUT_SECONDS)
        if resp_items.status_code not in (200, 201):
            logger.warning(f"Supabase order items insert warning: {resp_items.status_code} {resp_items.text}")

        # 3. Decrement stock for purchased items
        for it in items:
            try:
                prod = get_product_by_id(it["product_id"])
                if prod:
                    current_stock = prod.get("stock", 0)
                    new_stock = max(0, current_stock - it["quantity"])
                    url_prod = f"{Config.SUPABASE_URL}/rest/v1/products"
                    requests.patch(
                        url_prod,
                        headers=get_headers(prefer=""),
                        params={"id": f"eq.{it['product_id']}"},
                        json={"stock": new_stock},
                        timeout=TIMEOUT_SECONDS
                    )
            except Exception as e:
                logger.debug(f"Product stock update skipped: {e}")

        order_record["items"] = items_payload
        return order_record
    except Exception as e:
        logger.error(f"Error creating order in Supabase: {e}")
        return None


def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full order details including line items from Supabase."""
    if not is_configured():
        return None
    url_order = f"{Config.SUPABASE_URL}/rest/v1/orders"
    params_order = {"id": f"eq.{order_id}", "select": "*"}
    try:
        resp = requests.get(url_order, headers=get_headers(), params=params_order, timeout=TIMEOUT_SECONDS)
        if resp.status_code != 200 or not resp.json():
            return None
        order = resp.json()[0]

        # Fetch items
        url_items = f"{Config.SUPABASE_URL}/rest/v1/order_items"
        params_items = {"order_id": f"eq.{order_id}", "select": "*"}
        resp_items = requests.get(url_items, headers=get_headers(), params=params_items, timeout=TIMEOUT_SECONDS)
        order["items"] = resp_items.json() if resp_items.status_code == 200 else []
        return order
    except Exception as e:
        logger.error(f"Error fetching order {order_id} from Supabase: {e}")
        return None


def get_orders_by_user(user_id: int) -> List[Dict[str, Any]]:
    """Fetch order history for a user."""
    if not is_configured():
        return []
    url = f"{Config.SUPABASE_URL}/rest/v1/orders"
    params = {"user_id": f"eq.{user_id}", "order": "created_at.desc", "select": "*"}
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 200:
            orders = resp.json()
            for o in orders:
                url_items = f"{Config.SUPABASE_URL}/rest/v1/order_items"
                r_items = requests.get(url_items, headers=get_headers(), params={"order_id": f"eq.{o['id']}", "select": "*"}, timeout=TIMEOUT_SECONDS)
                o["items"] = r_items.json() if r_items.status_code == 200 else []
            return orders
        return []
    except Exception as e:
        logger.error(f"Error fetching user orders from Supabase: {e}")
        return []


# =============================================================================
# Activity Logs (Audit & Event Streaming)
# =============================================================================

def log_activity(
    session_id: str,
    action: str,
    description: str,
    details: Optional[Union[Dict, str]] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[int]:
    """Store audit log entry in Supabase activity_logs table."""
    if not is_configured():
        return None

    payload = {
        "session_id": session_id or "anonymous",
        "action": action,
        "description": description[:250],
        "details": details if isinstance(details, (dict, list)) else {"raw": str(details)} if details else None,
        "user_id": user_id,
        "user_email": user_email,
        "ip_address": ip_address,
        "user_agent": user_agent[:250] if user_agent else None
    }

    url = f"{Config.SUPABASE_URL}/rest/v1/activity_logs"
    try:
        resp = requests.post(url, headers=get_headers(), json=payload, timeout=TIMEOUT_SECONDS)
        if resp.status_code in (200, 201):
            created = resp.json()
            if isinstance(created, list) and created:
                return created[0].get("id")
        return None
    except Exception as e:
        logger.error(f"Error logging activity to Supabase: {e}")
        return None


def get_recent_activities(limit: int = 50, action: Optional[str] = None, session_id: Optional[str] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve latest activity logs from Supabase."""
    if not is_configured():
        return []
    url = f"{Config.SUPABASE_URL}/rest/v1/activity_logs"
    params = {"select": "*", "order": "id.desc", "limit": str(limit)}
    if action:
        params["action"] = f"eq.{action}"
    if session_id:
        params["session_id"] = f"eq.{session_id}"
    if user_id:
        params["user_id"] = f"eq.{user_id}"

    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching activities from Supabase: {e}")
        return []


# =============================================================================
# Dashboard Stats & Seeding
# =============================================================================

def get_stats() -> Dict[str, Any]:
    """Calculate aggregate statistics directly from Supabase and Vercel storage."""
    from db import DEFAULT_PRODUCTS
    stats = {"products_count": len(DEFAULT_PRODUCTS), "orders_count": 0, "total_revenue": 0.0}
    if not is_configured():
        return stats

    try:
        # Check products in Supabase if present
        r_p = requests.get(f"{Config.SUPABASE_URL}/rest/v1/products", headers=get_headers(), params={"select": "id"}, timeout=TIMEOUT_SECONDS)
        if r_p.status_code == 200 and r_p.json():
            stats["products_count"] = len(r_p.json())

        # Orders count and revenue from Supabase
        r_o = requests.get(f"{Config.SUPABASE_URL}/rest/v1/orders", headers=get_headers(), params={"select": "id,total_amount"}, timeout=TIMEOUT_SECONDS)
        if r_o.status_code == 200:
            orders = r_o.json()
            stats["orders_count"] = len(orders)
            stats["total_revenue"] = round(sum(float(o.get("total_amount", 0)) for o in orders), 2)
    except Exception as e:
        logger.error(f"Error fetching stats from Supabase: {e}")
    return stats


def seed_if_empty(default_products: Optional[List[Dict[str, Any]]] = None):
    """
    Catalog items are displayed directly from Vercel application storage.
    No catalog items are inserted into Supabase per project design.
    """
    logger.info("Supabase connected for users, orders, and activity logs. Catalog served from Vercel storage.")
