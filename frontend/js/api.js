/**
 * api.js - Centralized API Service for NovaMart E-Commerce Store
 * Handles REST API calls to the Flask backend, User Authentication (Signup/Login/Logout),
 * and Real-time SQL Database Activity Logging.
 */

const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port && window.location.port !== '80' && window.location.port !== '5000'
    ? 'http://localhost:5000/api' 
    : '/api';

// Realistic fallback seed products
const SEED_PRODUCTS = [
    {
        id: 1,
        name: "Aura Pro Wireless Headphones",
        category: "Audio",
        price: 199.99,
        rating: 4.8,
        reviews_count: 142,
        stock: 25,
        image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
        description: "Premium over-ear active noise cancelling headphones with 40-hour battery life, high-fidelity spatial audio drivers, and ultra-plush memory foam earcups.",
        specs: ["Active Noise Cancellation (ANC)", "40-Hour Battery Life", "Bluetooth 5.3 Multipoint", "USB-C Fast Charging (10m = 5hrs)"]
    },
    {
        id: 2,
        name: "Pulse Ultra Smartwatch",
        category: "Wearables",
        price: 249.50,
        rating: 4.7,
        reviews_count: 98,
        stock: 18,
        image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
        description: "Sleek titanium smart timepiece featuring an always-on AMOLED retina display, ECG sensor, SpO2 monitor, dual-band GPS, and 50m water resistance.",
        specs: ["1.43\" AMOLED 60Hz Display", "ECG + Heart Rate + SpO2", "Built-in Dual-Frequency GPS", "7-Day Battery on Single Charge"]
    },
    {
        id: 3,
        name: "Apex Mechanical Gaming Keyboard",
        category: "Electronics",
        price: 129.99,
        rating: 4.9,
        reviews_count: 215,
        stock: 32,
        image: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
        description: "Compact 75% hot-swappable mechanical keyboard equipped with pre-lubed linear switches, sound-dampening silicone gaskets, and per-key RGB backlighting.",
        specs: ["Hot-Swappable Switches", "PBT Double-shot Keycaps", "Gasket Mounted Structure", "Tri-Mode (2.4G / BT / Wired)"]
    },
    {
        id: 4,
        name: "ErgoPrecision Wireless Mouse",
        category: "Electronics",
        price: 79.99,
        rating: 4.6,
        reviews_count: 87,
        stock: 40,
        image: "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=600&q=80",
        description: "Sculpted ergonomic wireless mouse designed for all-day comfort. Features a precision 26K DPI optical sensor, quiet click switches, and thumb scroll wheel.",
        specs: ["26,000 DPI Optical Sensor", "Dual Bluetooth + 2.4GHz Dongle", "MagSpeed Electromagnetic Wheel", "Rechargeable 70-day Battery"]
    },
    {
        id: 5,
        name: "Horizon 4K IPS Studio Monitor",
        category: "Electronics",
        price: 499.00,
        rating: 4.9,
        reviews_count: 64,
        stock: 12,
        image: "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=600&q=80",
        description: "27-inch 4K UHD designer monitor with factory calibrated 99% DCI-P3 color accuracy, HDR400 certification, and 90W USB-C one-cable laptop charging.",
        specs: ["27\" 3840x2160 IPS Panel", "99% DCI-P3 & Delta E < 2", "USB-C 90W Power Delivery", "Fully Ergonomic Height Stand"]
    },
    {
        id: 6,
        name: "SonicBeam Soundbar & Subwoofer",
        category: "Audio",
        price: 189.00,
        rating: 4.5,
        reviews_count: 53,
        stock: 15,
        image: "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&q=80",
        description: "Cinematic room-filling sound with Dolby Atmos decoding, wireless deep bass subwoofer, optical in, HDMI eARC, and seamless Bluetooth streaming.",
        specs: ["2.1 Ch 240W Peak Output", "Dolby Digital & Atmos support", "Wireless 6.5\" Subwoofer", "HDMI eARC + Optical + BT 5.2"]
    },
    {
        id: 7,
        name: "Veloce Leather Tech Backpack",
        category: "Accessories",
        price: 119.50,
        rating: 4.8,
        reviews_count: 110,
        stock: 28,
        image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80",
        description: "Weather-resistant, full-grain vegan leather backpack with a dedicated padded 16\" laptop sleeve, hidden anti-theft pocket, and luggage pass-through strap.",
        specs: ["Waterproof PU Coated Fabric", "Padded 16-inch Laptop Sleeve", "RFID-Blocking Card Pocket", "Ergonomic Air-Mesh Back"]
    },
    {
        id: 8,
        name: "MagCharge 3-in-1 Charging Dock",
        category: "Accessories",
        price: 64.99,
        rating: 4.7,
        reviews_count: 94,
        stock: 35,
        image: "https://images.unsplash.com/photo-1586816879360-004f5b0c51e5?auto=format&fit=crop&w=600&q=80",
        description: "Fast wireless charging station capable of simultaneously powering your smartphone (15W), smartwatch, and wireless earbuds in one minimalist desk stand.",
        specs: ["15W MagSafe Fast Wireless", "Simultaneous 3-Device Charging", "Solid Aluminum Alloy Chassis", "Over-Temperature Protection"]
    }
];

class ApiService {
    constructor() {
        this.isBackendLive = false;
        this.sessionId = this.initSessionId();
        this.currentUser = this.loadStoredUser();
        this.token = localStorage.getItem('novamart_token') || null;
    }

    initSessionId() {
        let sid = localStorage.getItem('novamart_session_id');
        if (!sid) {
            sid = 'sess_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now();
            localStorage.setItem('novamart_session_id', sid);
        }
        return sid;
    }

    getSessionId() {
        return this.sessionId;
    }

    loadStoredUser() {
        try {
            const raw = localStorage.getItem('novamart_user');
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }

    getCurrentUser() {
        return this.currentUser;
    }

    isAuthenticated() {
        return !!(this.currentUser && this.token);
    }

    getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }

    // =========================================================================
    // Health Check
    // =========================================================================
    async checkHealth() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            const res = await fetch(`${API_BASE_URL}/health`, { signal: controller.signal });
            clearTimeout(timeoutId);
            const data = await res.json();
            this.isBackendLive = res.ok;
            return { isLive: this.isBackendLive, engine: data.engine || 'unknown' };
        } catch {
            this.isBackendLive = false;
            return { isLive: false, engine: 'none' };
        }
    }

    // =========================================================================
    // Activity Logging to SQL Database
    // =========================================================================
    /**
     * Record any user action or system event into the SQL database activity_logs table.
     */
    async logActivity(action, description, details = {}) {
        const payload = {
            session_id: this.sessionId,
            action: action,
            description: description,
            details: details,
            user_id: this.currentUser ? this.currentUser.id : null,
            user_email: this.currentUser ? this.currentUser.email : null
        };

        try {
            // Non-blocking fire-and-forget fetch to API
            fetch(`${API_BASE_URL}/activities`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify(payload)
            }).catch(() => {});
        } catch (e) {
            // Silently ignore if offline
        }
    }

    /**
     * Retrieve recent activity log entries from the SQL database.
     */
    async getActivities(limit = 50) {
        try {
            const res = await fetch(`${API_BASE_URL}/activities?limit=${limit}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            return { activities: data.activities || [], count: data.count || 0, engine: data.engine };
        } catch (err) {
            return { activities: [], count: 0, engine: 'offline' };
        }
    }

    // =========================================================================
    // Safe Response Parsing (Guards against non-JSON gateway/server errors)
    // =========================================================================
    async safeJson(res) {
        const text = await res.text();
        try {
            return JSON.parse(text);
        } catch {
            if (!res.ok) {
                if (text.includes("A server error has occurred") || text.includes("FUNCTION_INVOCATION")) {
                    throw new Error("Server Error: Database tables may not be created in Supabase yet. Please run database/supabase_schema.sql in the Supabase SQL Editor.");
                }
                throw new Error(text || `Server returned error (${res.status})`);
            }
            return {};
        }
    }

    // =========================================================================
    // User Authentication (Signup, Login, Logout)
    // =========================================================================
    async signup(userData) {
        userData.session_id = this.sessionId;
        const res = await fetch(`${API_BASE_URL}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        const data = await this.safeJson(res);
        if (!res.ok) {
            throw new Error(data.error || 'Signup failed');
        }

        this.token = data.token;
        this.currentUser = data.user;
        localStorage.setItem('novamart_token', data.token);
        localStorage.setItem('novamart_user', JSON.stringify(data.user));

        return data;
    }

    async login(credentials) {
        credentials.session_id = this.sessionId;
        const res = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials)
        });

        const data = await this.safeJson(res);
        if (!res.ok) {
            throw new Error(data.error || 'Login failed');
        }

        this.token = data.token;
        this.currentUser = data.user;
        localStorage.setItem('novamart_token', data.token);
        localStorage.setItem('novamart_user', JSON.stringify(data.user));

        return data;
    }

    async logout() {
        try {
            await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({ session_id: this.sessionId })
            });
        } catch (e) {}

        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('novamart_token');
        localStorage.removeItem('novamart_user');
    }

    // =========================================================================
    // Product Catalog
    // =========================================================================
    async getProducts(category = 'All', search = '') {
        try {
            const params = new URLSearchParams();
            if (category && category !== 'All') params.append('category', category);
            if (search) params.append('q', search);
            params.append('session_id', this.sessionId);

            const res = await fetch(`${API_BASE_URL}/products?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const data = await res.json();
            this.isBackendLive = true;
            return { data: data.products || [], isLive: true };
        } catch (err) {
            this.isBackendLive = false;
            let filtered = [...SEED_PRODUCTS];
            if (category && category !== 'All') {
                filtered = filtered.filter(p => p.category.toLowerCase() === category.toLowerCase());
            }
            if (search) {
                const q = search.toLowerCase();
                filtered = filtered.filter(p => 
                    p.name.toLowerCase().includes(q) || 
                    p.description.toLowerCase().includes(q) ||
                    p.category.toLowerCase().includes(q)
                );
            }
            return { data: filtered, isLive: false };
        }
    }

    async getProductById(id) {
        try {
            const res = await fetch(`${API_BASE_URL}/products/${id}?session_id=${this.sessionId}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            return { data: data.product || data, isLive: true };
        } catch (err) {
            const product = SEED_PRODUCTS.find(p => p.id === parseInt(id));
            if (!product) throw new Error("Product not found");
            return { data: product, isLive: false };
        }
    }

    // =========================================================================
    // Orders & Checkout (Credentials Mandatory)
    // =========================================================================
    async createOrder(orderPayload) {
        orderPayload.session_id = this.sessionId;

        const res = await fetch(`${API_BASE_URL}/orders`, {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(orderPayload)
        });

        const data = await this.safeJson(res);
        if (!res.ok) {
            const err = new Error(data.error || `Server responded with ${res.status}`);
            err.auth_required = data.auth_required || res.status === 401;
            throw err;
        }

        return { data, isLive: true };
    }

    async getOrders(params = {}) {
        try {
            const query = new URLSearchParams();
            query.append('session_id', this.sessionId);
            if (params.q) query.append('q', params.q);
            if (params.email) query.append('email', params.email);
            if (params.order_id) query.append('order_id', params.order_id);

            const res = await fetch(`${API_BASE_URL}/orders?${query.toString()}`, {
                headers: this.getAuthHeaders()
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            return { data: data.orders || [], count: data.count || 0, isLive: true };
        } catch (err) {
            console.error("Failed to fetch orders:", err);
            return { data: [], count: 0, isLive: false, error: err.message };
        }
    }
}

// Global API instance
window.api = new ApiService();
