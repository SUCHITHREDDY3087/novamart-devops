-- =============================================================================
-- NovaMart E-Commerce Database Schema (MySQL 8)
--
-- NOTE FOR SUPABASE:
-- If you are deploying or connecting with Supabase, DO NOT run this file!
-- Please run "database/supabase_schema.sql" instead. Supabase uses PostgreSQL
-- syntax and does not support MySQL commands like "USE" or "ENGINE=InnoDB".
-- =============================================================================

CREATE DATABASE IF NOT EXISTS ecommerce_db;
USE ecommerce_db;

-- 1. Users Table (Authentication & Customer Profiles)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    address VARCHAR(255),
    city VARCHAR(100),
    postal VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL DEFAULT '',
    role VARCHAR(20) DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Products Table (Catalog & Inventory)
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

-- 3. Orders Table (Customer Checkout Records)
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

-- 4. Order Items Table (Relational Line Items with Foreign Keys)
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

-- 5. Activity Logs Table (SQL Event & Audit Logging for All User Actions)
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

-- =============================================================================
-- Seed Realistic Initial Catalog Data
-- =============================================================================

INSERT INTO users (name, email, phone, address, city, postal, password_hash, role) VALUES 
('Demo Customer', 'john@example.com', '+1 (555) 019-2834', '123 Innovation Way', 'San Francisco', '94107', 'scrypt:32768:8:1$EI95qDL5dPu8AuG4$61f6b13625b2106618288ee241a0f65b58b24674e66c3a773e3391e791d67101d24b038f4d306ca7cc365b0a20437081d4beba2b1ba0c8f559870ea77c68e055', 'customer'),
('Admin User', 'admin@novamart.local', '+1 (555) 019-0000', '1 NovaMart Plaza', 'New York', '10001', 'scrypt:32768:8:1$EI95qDL5dPu8AuG4$61f6b13625b2106618288ee241a0f65b58b24674e66c3a773e3391e791d67101d24b038f4d306ca7cc365b0a20437081d4beba2b1ba0c8f559870ea77c68e055', 'admin')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO products (id, name, category, price, rating, reviews_count, stock, image_url, description, specs_json) VALUES
(1, 'Aura Pro Wireless Headphones', 'Audio', 199.99, 4.8, 142, 25, 
 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80',
 'Premium over-ear active noise cancelling headphones with 40-hour battery life, high-fidelity spatial audio drivers, and ultra-plush memory foam earcups.',
 '["Active Noise Cancellation (ANC)", "40-Hour Battery Life", "Bluetooth 5.3 Multipoint", "USB-C Fast Charging (10m = 5hrs)"]'),

(2, 'Pulse Ultra Smartwatch', 'Wearables', 249.50, 4.7, 98, 18,
 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80',
 'Sleek titanium smart timepiece featuring an always-on AMOLED retina display, ECG sensor, SpO2 monitor, dual-band GPS, and 50m water resistance.',
 '["1.43 Inch AMOLED 60Hz Display", "ECG + Heart Rate + SpO2", "Built-in Dual-Frequency GPS", "7-Day Battery on Single Charge"]'),

(3, 'Apex Mechanical Gaming Keyboard', 'Electronics', 129.99, 4.9, 215, 32,
 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80',
 'Compact 75% hot-swappable mechanical keyboard equipped with pre-lubed linear switches, sound-dampening silicone gaskets, and per-key RGB backlighting.',
 '["Hot-Swappable Switches", "PBT Double-shot Keycaps", "Gasket Mounted Structure", "Tri-Mode (2.4G / BT / Wired)"]'),

(4, 'ErgoPrecision Wireless Mouse', 'Electronics', 79.99, 4.6, 87, 40,
 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=600&q=80',
 'Sculpted ergonomic wireless mouse designed for all-day comfort. Features a precision 26K DPI optical sensor, quiet click switches, and thumb scroll wheel.',
 '["26,000 DPI Optical Sensor", "Dual Bluetooth + 2.4GHz Dongle", "MagSpeed Electromagnetic Wheel", "Rechargeable 70-day Battery"]'),

(5, 'Horizon 4K IPS Studio Monitor', 'Electronics', 499.00, 4.9, 64, 12,
 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=600&q=80',
 '27-inch 4K UHD designer monitor with factory calibrated 99% DCI-P3 color accuracy, HDR400 certification, and 90W USB-C one-cable laptop charging.',
 '["27 Inch 3840x2160 IPS Panel", "99% DCI-P3 & Delta E < 2", "USB-C 90W Power Delivery", "Fully Ergonomic Height Stand"]'),

(6, 'SonicBeam Soundbar & Subwoofer', 'Audio', 189.00, 4.5, 53, 15,
 'https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&q=80',
 'Cinematic room-filling sound with Dolby Atmos decoding, wireless deep bass subwoofer, optical in, HDMI eARC, and seamless Bluetooth streaming.',
 '["2.1 Ch 240W Peak Output", "Dolby Digital & Atmos support", "Wireless 6.5 Inch Subwoofer", "HDMI eARC + Optical + BT 5.2"]'),

(7, 'Veloce Leather Tech Backpack', 'Accessories', 119.50, 4.8, 110, 28,
 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80',
 'Weather-resistant, full-grain vegan leather backpack with a dedicated padded 16 inch laptop sleeve, hidden anti-theft pocket, and luggage pass-through strap.',
 '["Waterproof PU Coated Fabric", "Padded 16-inch Laptop Sleeve", "RFID-Blocking Card Pocket", "Ergonomic Air-Mesh Back"]'),

(8, 'MagCharge 3-in-1 Charging Dock', 'Accessories', 64.99, 4.7, 94, 35,
 'https://images.unsplash.com/photo-1586816879360-004f5b0c51e5?auto=format&fit=crop&w=600&q=80',
 'Fast wireless charging station capable of simultaneously powering your smartphone (15W), smartwatch, and wireless earbuds in one minimalist desk stand.',
 '["15W MagSafe Fast Wireless", "Simultaneous 3-Device Charging", "Solid Aluminum Alloy Chassis", "Over-Temperature Protection"]')
ON DUPLICATE KEY UPDATE name=VALUES(name);
