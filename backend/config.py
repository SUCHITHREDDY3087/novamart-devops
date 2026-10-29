"""
config.py - Environment & Database Configuration for NovaMart Backend
Loads database connection parameters and application environment variables.
"""

import os
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("MYSQL_USER", "root")
    DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "rootpassword")
    DB_NAME = os.getenv("MYSQL_DATABASE", "ecommerce_db")
    
    DB_ENGINE = os.getenv("DB_ENGINE", "auto")
    # In Vercel serverless environment, local filesystem is read-only; fallback SQLite must use /tmp
    if os.getenv("VERCEL"):
        SQLITE_PATH = os.getenv("SQLITE_PATH", "/tmp/ecommerce.db")
    else:
        SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "ecommerce.db"))
    
    # Supabase Cloud Database Configuration (supports manual & Vercel Supabase integration env vars)
    SUPABASE_URL = (
        os.getenv("SUPABASE_URL") or 
        os.getenv("NEXT_PUBLIC_SUPABASE_URL") or 
        ""
    ).rstrip("/")
    SUPABASE_KEY = (
        os.getenv("SUPABASE_KEY") or 
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or 
        os.getenv("SUPABASE_ANON_KEY") or 
        os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or 
        ""
    )
    
    SECRET_KEY = os.getenv("SECRET_KEY", "novamart_ecommerce_secure_key_2026")
    
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("FLASK_ENV", "production") == "development"
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")
