"""
db.py - Resilient Dual-Engine SQL Database Layer for NovaMart E-Commerce
Supports MySQL 8 and SQLite 3 with automatic failover, table schema initialization,
seed data population, and transactional activity logging.
"""

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
from werkzeug.security import generate_password_hash
from config import Config

logger = logging.getLogger(__name__)

# Determine active SQL engine ('mysql' or 'sqlite')
ACTIVE_ENGINE = None

# Default catalog seed data
DEFAULT_PRODUCTS = [
    {
        "id": 1,
        "name": "Aura Pro Wireless Headphones",
        "category": "Audio",
        "price": 199.99,
        "rating": 4.8,
        "reviews_count": 142,
        "stock": 25,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
        "description": "Premium over-ear active noise cancelling headphones with 40-hour battery life, high-fidelity spatial audio drivers, and ultra-plush memory foam earcups.",
        "specs_json": json.dumps(["Active Noise Cancellation (ANC)", "40-Hour Battery Life", "Bluetooth 5.3 Multipoint", "USB-C Fast Charging (10m = 5hrs)"])
    },
    {
        "id": 2,
        "name": "Pulse Ultra Smartwatch",
        "category": "Wearables",
        "price": 249.50,
        "rating": 4.7,
        "reviews_count": 98,
        "stock": 18,
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
        "description": "Sleek titanium smart timepiece featuring an always-on AMOLED retina display, ECG sensor, SpO2 monitor, dual-band GPS, and 50m water resistance.",
        "specs_json": json.dumps(["1.43\" AMOLED 60Hz Display", "ECG + Heart Rate + SpO2", "Built-in Dual-Frequency GPS", "7-Day Battery on Single Charge"])
    },
    {
        "id": 3,
        "name": "Apex Mechanical Gaming Keyboard",
        "category": "Electronics",
        "price": 129.99,
        "rating": 4.9,
        "reviews_count": 215,
        "stock": 32,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
        "description": "Compact 75% hot-swappable mechanical keyboard equipped with pre-lubed linear switches, sound-dampening silicone gaskets, and per-key RGB backlighting.",
        "specs_json": json.dumps(["Hot-Swappable Switches", "PBT Double-shot Keycaps", "Gasket Mounted Structure", "Tri-Mode (2.4G / BT / Wired)"])
    },
    {
        "id": 4,
        "name": "ErgoPrecision Wireless Mouse",
        "category": "Electronics",
        "price": 79.99,
        "rating": 4.6,
        "reviews_count": 87,
        "stock": 40,
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=600&q=80",
        "description": "Sculpted ergonomic wireless mouse designed for all-day comfort. Features a precision 26K DPI optical sensor, quiet click switches, and thumb scroll wheel.",
        "specs_json": json.dumps(["26,000 DPI Optical Sensor", "Dual Bluetooth + 2.4GHz Dongle", "MagSpeed Electromagnetic Wheel", "Rechargeable 70-day Battery"])
    },
    {
        "id": 5,
        "name": "Horizon 4K IPS Studio Monitor",
        "category": "Electronics",
        "price": 499.00,
        "rating": 4.9,
        "reviews_count": 64,
        "stock": 12,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=600&q=80",
        "description": "27-inch 4K UHD designer monitor with factory calibrated 99% DCI-P3 color accuracy, HDR400 certification, and 90W USB-C one-cable laptop charging.",
        "specs_json": json.dumps(["27\" 3840x2160 IPS Panel", "99% DCI-P3 & Delta E < 2", "USB-C 90W Power Delivery", "Fully Ergonomic Height Stand"])
    },
    {
        "id": 6,
        "name": "SonicBeam Soundbar & Subwoofer",
        "category": "Audio",
        "price": 189.00,
        "rating": 4.5,
        "reviews_count": 53,
        "stock": 15,
        "image_url": "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&q=80",
        "description": "Cinematic room-filling sound with Dolby Atmos decoding, wireless deep bass subwoofer, optical in, HDMI eARC, and seamless Bluetooth streaming.",
        "specs_json": json.dumps(["2.1 Ch 240W Peak Output", "Dolby Digital & Atmos support", "Wireless 6.5\" Subwoofer", "HDMI eARC + Optical + BT 5.2"])
    },
    {
        "id": 7,
        "name": "Veloce Leather Tech Backpack",
        "category": "Accessories",
        "price": 119.50,
        "rating": 4.8,
        "reviews_count": 110,
        "stock": 28,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80",
        "description": "Weather-resistant, full-grain vegan leather backpack with a dedicated padded 16\" laptop sleeve, hidden anti-theft pocket, and luggage pass-through strap.",
        "specs_json": json.dumps(["Waterproof PU Coated Fabric", "Padded 16-inch Laptop Sleeve", "RFID-Blocking Card Pocket", "Ergonomic Air-Mesh Back"])
    },
    {
        "id": 8,
        "name": "MagCharge 3-in-1 Charging Dock",
        "category": "Accessories",
        "price": 64.99,
        "rating": 4.7,
        "reviews_count": 94,
        "stock": 35,
        "image_url": "https://images.unsplash.com/photo-1586816879360-004f5b0c51e5?auto=format&fit=crop&w=600&q=80",
        "description": "Fast wireless charging station capable of simultaneously powering your smartphone (15W), smartwatch, and wireless earbuds in one minimalist desk stand.",
        "specs_json": json.dumps(["15W MagSafe Fast Wireless", "Simultaneous 3-Device Charging", "Solid Aluminum Alloy Chassis", "Over-Temperature Protection"])
    }
]


class SQLiteCursorWrapper:
    """Wraps an SQLite cursor to emulate mysql.connector dictionary cursor."""
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query: str, params: Union[Tuple, List] = ()):
        # Convert MySQL %s placeholder to SQLite ?
        sqlite_query = query.replace("%s", "?")
        return self.cursor.execute(sqlite_query, params)

    def executemany(self, query: str, seq_of_params):
        sqlite_query = query.replace("%s", "?")
        return self.cursor.executemany(sqlite_query, seq_of_params)

    def fetchone(self) -> Optional[Dict[str, Any]]:
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self) -> List[Dict[str, Any]]:
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        try:
            self.cursor.close()
        except Exception:
            pass


class SQLiteConnectionWrapper:
    """Wraps an SQLite connection to emulate mysql.connector connection interface."""
    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def cursor(self, dictionary=True):
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


def _connect_mysql():
    """Try to establish a MySQL connection using Config."""
    if os.getenv("VERCEL"):
        raise RuntimeError("MySQL disabled in Vercel serverless environment")

    # Fast check to avoid OS DNS timeout on unresolvable docker hosts like 'db'
    if Config.DB_HOST in ("db", "localhost", "127.0.0.1"):
        import socket
        try:
            socket.gethostbyname(Config.DB_HOST)
        except Exception:
            raise RuntimeError(f"Database host '{Config.DB_HOST}' is not resolvable")

    import mysql.connector
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=2
    )


def _connect_sqlite():
    """Establish a local SQLite connection."""
    db_path = getattr(Config, "SQLITE_PATH", os.path.join(os.path.dirname(__file__), "ecommerce.db"))
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    return SQLiteConnectionWrapper(conn)


def get_db_connection():
    """
    Return an active database connection.
    Attempts MySQL first if configured; falls back automatically to SQLite.
    """
    global ACTIVE_ENGINE

    preferred = getattr(Config, "DB_ENGINE", "auto").lower()

    if preferred == "sqlite":
        ACTIVE_ENGINE = "sqlite"
        return _connect_sqlite()

    if preferred == "mysql":
        ACTIVE_ENGINE = "mysql"
        return _connect_mysql()

    # 'auto' mode: test MySQL, fall back to SQLite
    if ACTIVE_ENGINE == "sqlite":
        return _connect_sqlite()

    try:
        conn = _connect_mysql()
        ACTIVE_ENGINE = "mysql"
        return conn
    except Exception as e:
        logger.info(f"MySQL unavailable ({e}). Falling back to SQLite SQL engine.")
        ACTIVE_ENGINE = "sqlite"
        return _connect_sqlite()


def get_active_engine() -> str:
    """Return the name of the active SQL engine ('supabase', 'mysql', or 'sqlite')."""
    global ACTIVE_ENGINE
    if ACTIVE_ENGINE == "supabase":
        return "supabase"

    if getattr(Config, "SUPABASE_URL", None) and getattr(Config, "SUPABASE_KEY", None):
        ACTIVE_ENGINE = "supabase"
        return "supabase"

    if ACTIVE_ENGINE is None:
        try:
            conn = get_db_connection()
            conn.close()
        except Exception:
            ACTIVE_ENGINE = "sqlite"
    return ACTIVE_ENGINE or "sqlite"


def init_db():
    """
    Ensure all SQL tables exist across Supabase, MySQL, or SQLite,
    and seed default products and users if not present.
    """
    global ACTIVE_ENGINE

    # Check if Supabase Cloud Database is configured
    if getattr(Config, "SUPABASE_URL", None) and getattr(Config, "SUPABASE_KEY", None):
        try:
            import supabase_db
            ok, msg = supabase_db.test_connection()
            if ok:
                ACTIVE_ENGINE = "supabase"
                logger.info("Connected to Supabase Cloud Database! Checking catalog seed...")
                supabase_db.seed_if_empty(DEFAULT_PRODUCTS)
                return
            else:
                logger.warning(f"Supabase configured but connection check returned: {msg}. Falling back to local engines.")
        except Exception as e:
            logger.warning(f"Error checking Supabase connection: {e}")

    conn = get_db_connection()
    engine = get_active_engine()
    cursor = conn.cursor()

    logger.info(f"Initializing SQL database using [{engine.upper()}] engine...")

    if engine == "mysql":
        _init_mysql_tables(cursor)
    else:
        _init_sqlite_tables(cursor)

    conn.commit()

    # Ensure catalog has products
    cursor.execute("SELECT COUNT(*) as count FROM products")
    row = cursor.fetchone()
    count = row["count"] if row else 0

    if count == 0:
        logger.info("Products table is empty. Seeding catalog products into SQL database...")
        _seed_products(cursor, engine)
        conn.commit()

    # Ensure default users exist
    _seed_users(cursor, engine)
    conn.commit()

    cursor.close()
    conn.close()
    logger.info(f"SQL database initialization complete ({engine.upper()}).")


def _init_sqlite_tables(cursor):
    """Create SQLite tables if they do not exist."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        address TEXT,
        city TEXT,
        postal TEXT,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'customer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        rating REAL DEFAULT 5.0,
        reviews_count INTEGER DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        image_url TEXT NOT NULL,
        description TEXT,
        specs_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id INTEGER NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        shipping_address TEXT NOT NULL,
        payment_method TEXT DEFAULT 'Cash on Delivery',
        status TEXT DEFAULT 'Confirmed',
        subtotal REAL NOT NULL,
        shipping_fee REAL NOT NULL DEFAULT 0.00,
        tax_amount REAL NOT NULL DEFAULT 0.00,
        total_amount REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NULL,
        user_email TEXT NULL,
        session_id TEXT NOT NULL,
        action TEXT NOT NULL,
        description TEXT NOT NULL,
        details TEXT NULL,
        ip_address TEXT NULL,
        user_agent TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


def _init_mysql_tables(cursor):
    """Create MySQL tables if they do not exist."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(150) NOT NULL UNIQUE,
        phone VARCHAR(20),
        address VARCHAR(255),
        city VARCHAR(100),
        postal VARCHAR(20),
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'customer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        category VARCHAR(50) NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        rating DECIMAL(2, 1) DEFAULT 5.0,
        reviews_count INT DEFAULT 0,
        stock INT NOT NULL DEFAULT 0,
        image_url VARCHAR(500) NOT NULL,
        description TEXT,
        specs_json JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id VARCHAR(30) PRIMARY KEY,
        user_id INT NULL,
        customer_name VARCHAR(100) NOT NULL,
        customer_email VARCHAR(150) NOT NULL,
        customer_phone VARCHAR(20) NOT NULL,
        shipping_address TEXT NOT NULL,
        payment_method VARCHAR(50) DEFAULT 'Cash on Delivery',
        status VARCHAR(30) DEFAULT 'Confirmed',
        subtotal DECIMAL(10, 2) NOT NULL,
        shipping_fee DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        total_amount DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id VARCHAR(30) NOT NULL,
        product_id INT NOT NULL,
        product_name VARCHAR(150) NOT NULL,
        unit_price DECIMAL(10, 2) NOT NULL,
        quantity INT NOT NULL,
        subtotal DECIMAL(10, 2) NOT NULL,
        CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NULL,
        user_email VARCHAR(150) NULL,
        session_id VARCHAR(100) NOT NULL,
        action VARCHAR(60) NOT NULL,
        description VARCHAR(255) NOT NULL,
        details JSON,
        ip_address VARCHAR(50),
        user_agent VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_session (session_id),
        INDEX idx_action (action),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)


def _seed_products(cursor, engine: str):
    """Insert catalog seed products."""
    for p in DEFAULT_PRODUCTS:
        cursor.execute("""
            INSERT INTO products (id, name, category, price, rating, reviews_count, stock, image_url, description, specs_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            p["id"], p["name"], p["category"], p["price"], p["rating"],
            p["reviews_count"], p["stock"], p["image_url"], p["description"], p["specs_json"]
        ))


def _seed_users(cursor, engine: str):
    """Seed demo accounts if not already in users table."""
    demo_pass = generate_password_hash("password123")
    demo_users = [
        ("Demo Customer", "john@example.com", "+1 (555) 019-2834", "123 Innovation Way", "San Francisco", "94107", demo_pass, "customer"),
        ("Admin User", "admin@novamart.local", "+1 (555) 019-0000", "1 NovaMart Plaza", "New York", "10001", demo_pass, "admin")
    ]

    for name, email, phone, addr, city, postal, pw_hash, role in demo_users:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (name, email, phone, address, city, postal, password_hash, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, addr, city, postal, pw_hash, role))


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
    """
    Record an event into activity_logs table (Supabase or SQL).
    Ensures safe, atomic insertion with full exception handling.
    """
    if get_active_engine() == "supabase":
        try:
            import supabase_db
            return supabase_db.log_activity(
                session_id=session_id,
                action=action,
                description=description,
                details=details,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Failed to record activity log to Supabase: {e}")
            return None

    if not session_id:
        session_id = "anonymous"

    if isinstance(details, (dict, list)):
        details_str = json.dumps(details)
    elif details is not None:
        details_str = str(details)
    else:
        details_str = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (user_id, user_email, session_id, action, description, details, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, user_email, session_id, action,
            description[:250], details_str, ip_address, user_agent[:250] if user_agent else None
        ))
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return last_id
    except Exception as e:
        logger.error(f"Failed to record activity log to SQL: {e}")
        return None


def get_recent_activities(limit: int = 50, action: Optional[str] = None, session_id: Optional[str] = None, user_id: Optional[int] = None):
    """Retrieve recent activity logs from the database (Supabase or SQL)."""
    if get_active_engine() == "supabase":
        try:
            import supabase_db
            return supabase_db.get_recent_activities(
                limit=limit,
                action=action,
                session_id=session_id,
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"Failed to fetch activity logs from Supabase: {e}")
            return []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, user_id, user_email, session_id, action, description, details, ip_address, created_at FROM activity_logs WHERE 1=1"
        params = []

        if action:
            query += " AND action = %s"
            params.append(action)
        if session_id:
            query += " AND session_id = %s"
            params.append(session_id)
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)

        query += " ORDER BY id DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        activities = []
        for r in rows:
            details_obj = None
            if r.get("details"):
                try:
                    details_obj = json.loads(r["details"]) if isinstance(r["details"], str) else r["details"]
                except Exception:
                    details_obj = r["details"]

            created = r.get("created_at")
            if hasattr(created, "isoformat"):
                created_str = created.isoformat()
            else:
                created_str = str(created) if created else ""

            activities.append({
                "id": r["id"],
                "user_id": r.get("user_id"),
                "user_email": r.get("user_email"),
                "session_id": r.get("session_id"),
                "action": r.get("action"),
                "description": r.get("description"),
                "details": details_obj,
                "ip_address": r.get("ip_address"),
                "created_at": created_str
            })

        cursor.close()
        conn.close()
        return activities
    except Exception as e:
        logger.error(f"Failed to fetch activity logs: {e}")
        return []
