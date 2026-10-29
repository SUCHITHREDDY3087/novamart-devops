# 🛒 NovaMart — 3-Tier DevOps E-Commerce Platform

[![CI/CD Pipeline](https://github.com/Shivan1000/Devopsecommerce/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Shivan1000/Devopsecommerce/actions/workflows/ci-cd.yml)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v2-blue?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Nginx](https://img.shields.io/badge/Nginx-Alpine-009639?logo=nginx&logoColor=white)](https://nginx.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Supabase](https://img.shields.io/badge/Supabase-Cloud%20PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![Vercel](https://img.shields.io/badge/Vercel-Deployment%20Ready-000000?logo=vercel&logoColor=white)](https://vercel.com/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)](https://www.python.org/)

A production-ready, full-stack 3-tier e-commerce web application engineered with modern DevOps principles. Features containerized microservices, reverse proxy routing, multi-engine relational storage (Supabase Cloud PostgreSQL / MySQL 8 / SQLite), automated CI/CD pipeline, and responsive modern UI.

---

## 🏗️ Architecture Overview

NovaMart is built on a 3-tier microservices architecture:

```
                  ┌──────────────────────────────────────────────┐
                  │                 User Browser                 │
                  └──────────────────────┬───────────────────────┘
                                         │ HTTP / Port 80
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│  Docker Bridge Network (ecommerce-network)                                      │
│                                                                                │
│   ┌───────────────────────────────┐     Proxy Pass /api     ┌────────────────┐  │
│   │    Tier 1: Web & Proxy        ├────────────────────────►│ Tier 2: Flask  │  │
│   │    Nginx (Alpine)             │                         │ REST API (App) │  │
│   │    - Static File Serving      │     Port 5000 (Backend) └───────┬────────┘  │
│   │    - Reverse Proxy / Load Bal.│                                 │           │
│   └───────────────────────────────┘                                 │ SQL/REST  │
│                                                                     ▼           │
│                                          ┌───────────────────────────────────┐  │
│                                          │ Tier 3: Database Engines          │  │
│                                          │ - Supabase Cloud PostgreSQL       │  │
│                                          │ - Local MySQL 8.0 Engine          │  │
│                                          │ - Lightweight SQLite Fallback     │  │
│                                          └───────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────┘
```

- **Tier 1 (Frontend & Reverse Proxy)**: Nginx web server hosting static assets (HTML5, Vanilla CSS, JS) and reverse-proxying API calls directly to the application backend.
- **Tier 2 (Application Backend)**: Python Flask REST API handling business logic, authentication, order processing, and database transactions with healthcheck monitoring.
- **Tier 3 (Database Layer)**: Multi-engine support featuring Supabase Cloud PostgreSQL via PostgREST, local containerized MySQL 8.0, and automated local SQLite fallback.

---

## ✨ Features

- **Product Catalog & Filtering**: Real-time product search, category filtering, stock availability badges, and sorting.
- **Interactive Shopping Cart**: Session-persistent cart, quantity adjustments, item removal, and subtotal calculation.
- **Checkout & Order Tracking**: Multi-step checkout with order ID generation and persistent order status tracking.
- **Authentication Flow**: User registration and login interfaces.
- **Modern Responsive Design**: Glassmorphism aesthetic, dark/light theme toggle, toast notifications, and responsive mobile-first grid.
- **Automated Healthchecks**: Built-in container healthchecks ensuring zero-downtime dependency availability (`db` -> `backend` -> `frontend`).
- **CI/CD Automation**: GitHub Actions pipeline running automated Pytest test suites and Docker build validations on every push.

---

## 📁 Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions CI/CD pipeline
├── backend/
│   ├── tests/
│   │   └── test_app.py        # Automated Pytest suite
│   ├── app.py                 # Flask REST API server & routing
│   ├── config.py              # Environment configuration loader
│   ├── db.py                  # Database driver (MySQL + SQLite fallback)
│   ├── Dockerfile             # Multi-stage Backend container build
│   └── requirements.txt       # Python dependencies
├── database/
│   └── init.sql               # Database schema & seed catalog
├── frontend/
│   ├── css/
│   │   └── style.css          # Modern custom design system & themes
│   ├── js/
│   │   ├── api.js             # API client & fetch abstraction
│   │   └── app.js             # State management, cart & UI logic
│   ├── Dockerfile             # Nginx frontend container build
│   ├── index.html             # Storefront catalog & cart
│   ├── login.html             # User login
│   ├── nginx.conf             # Nginx reverse proxy routing
│   ├── orders.html            # Order management & tracking
│   └── signup.html            # User registration
├── .env.example               # Example environment variables template
├── .gitignore                 # Git ignore rules
├── compose.yaml               # Docker Compose multi-container configuration
└── README.md                  # Project documentation
```

---

## 🚀 Quick Start (Docker Compose)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24.0+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.0+)

### 1. Clone the Repository

```bash
git clone https://github.com/Shivan1000/Devopsecommerce.git
cd Devopsecommerce
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

*(Recommended)* Replace the example database passwords and `SECRET_KEY` in `.env` before use. Leave `SUPABASE_URL` and `SUPABASE_KEY` empty unless you have configured a real Supabase project. Never commit `.env` or real credentials.

### 3. Launch Services

Start the entire 3-tier stack in detached mode:

```bash
docker compose up -d --build
```

### 4. Access the Application

Once healthy, open your browser:

| Service | URL | Description |
|---|---|---|
| **Frontend Storefront** | [http://localhost:80](http://localhost:80) | Web Application UI |
| **Backend REST API** | [http://localhost:5000](http://localhost:5000) | Flask API Server |
| **API Healthcheck** | [http://localhost:5000/api/health](http://localhost:5000/api/health) | Service Health Status |
| **MySQL Database** | `localhost:3306` | Relational Database |

### 5. Stop Services

```bash
docker compose down -v
```

---

## ⚡ Deploy to Vercel (Cloud Hosting)

This project is pre-configured with `vercel.json` for serverless deployment on [Vercel](https://vercel.com/):

### 1. Import Repository in Vercel
1. Go to [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New...** &rarr; **Project**.
2. Select your repository: `Shivan1000/Devopsecommerce`.
3. Vercel automatically detects the Python API and static frontend.

### 2. Configure Environment Variables
In the Vercel project configuration, add your environment variables under **Environment Variables**:
- `SUPABASE_URL`: Your Supabase Project URL (`https://<project-id>.supabase.co`)
- `SUPABASE_KEY`: Your Supabase Secret Key (`sb_secret_...`)
- `SECRET_KEY`: A secure session signing key (e.g. `novamart_secure_key_2026`)

### 3. Deploy
Click **Deploy**. Vercel will build the frontend assets on its Global Edge Network and route `/api/*` to the Python serverless function (`api/index.py`).

---

---

## 💻 Local Development (Without Docker)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend development server
python app.py
```
Backend runs on `http://localhost:5000`.

### Frontend Setup

Serve the `frontend/` directory using any static file server (such as Python's built-in HTTP server or VS Code Live Server):

```bash
cd frontend
python -m http.server 8080
```
Open `http://localhost:8080` in your browser.

---

## 🧪 Testing

Run the automated backend test suite using Pytest:

```bash
# From workspace root
PYTHONPATH=backend pytest backend/tests -v
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Application & database connectivity healthcheck |
| `GET` | `/api/stats` | System statistics (product count, order count) |
| `GET` | `/api/categories` | Fetch all product categories |
| `GET` | `/api/products` | Fetch products (optional `?category=`, `?search=`) |
| `GET` | `/api/products/<id>` | Fetch single product details |
| `POST` | `/api/orders` | Place a new customer order |
| `GET` | `/api/orders/<id>` | Retrieve order details & status |
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Authenticate user credentials |

---

## 🔄 CI/CD Pipeline

The repository includes a automated GitHub Actions workflow (`.github/workflows/ci-cd.yml`):

1. **Pytest Test Suite**: Runs automated unit & integration tests on Python 3.10.
2. **Compose Configuration Check**: Validates syntax and services in `compose.yaml`.
3. **Docker Image Build**: Compiles and verifies Docker builds for both Frontend and Backend microservices.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
