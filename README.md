# Hitech AVL CRM

Production-grade full-stack CRM built for professional audio, video, and lighting (AVL) enterprise workflows.

## Architecture

- **Frontend:** React (SPA) served via Nginx with automated API proxying (`/api/*` → FastAPI backend).
- **Backend:** FastAPI (Python 3.12) with a high-performance PostgreSQL document compatibility layer (`pgdb`) providing MongoDB semantics over PostgreSQL JSONB.
- **Database:** Supabase PostgreSQL (Single source of truth).
- **Deployment:** Docker Compose + Coolify on Hostinger VPS.

## Key Features

- **Inventory & Shipment Tracking:** Complete logistics management for OEM imports (L-Acoustics, DiGiCo, RCF, KLANG, etc.) with serial numbers, warranty tracking, and landed cost calculation.
- **Quotation & BOQ Builder:** Professional PDF quotation and bill of quantities (BOQ) generation with tax calculation, discounts, and customer-facing share links.
- **Pipeline & Lead Management:** Full CRM pipeline tracking from lead qualification to closed-won projects and annual maintenance contracts (AMCs).
- **Role-Based Access Control:** Granular permissions for Super Admin, Admin, and Sales representatives with brand-level access restrictions.
- **Integrations:** WhatsApp notifications via Twilio, AI catalogue enrichment via Google Gemini, email via Zoho SMTP / Resend, and n8n webhooks.

## Quick Start (Local Development)

1. Copy `.env.example` to `.env` and configure `DATABASE_URL` and `JWT_SECRET`.
2. Start backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m pgbootstrap
   uvicorn server:app --reload
   ```
3. Start frontend:
   ```bash
   cd frontend
   npm install --legacy-peer-deps
   npm start
   ```

## Production Deployment via Coolify

See [DEPLOYMENT.md](./DEPLOYMENT.md) for full instructions on deploying this repository to a Hostinger VPS using Coolify and Supabase PostgreSQL.
