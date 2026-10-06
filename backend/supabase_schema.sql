-- ===========================================================================
-- Hitech AVL CRM -- Supabase PostgreSQL schema
--
-- GENERATED FILE -- do not edit by hand.
-- Source of truth: backend/pgschema.py
-- Regenerate with:  python backend/pgschema.py > backend/supabase_schema.sql
--
-- Apply with any of:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/supabase_schema.sql
--   Supabase dashboard -> SQL Editor -> paste this file -> Run
--   python -m backend.pgbootstrap --schema
--
-- One table per application collection. The document is stored verbatim in
-- `body` (jsonb) because the FastAPI backend is written against the Motor API
-- and adds fields from Python migrations, not from DDL. `pub_id` mirrors the
-- document's public `id` so the hottest query in the API -- fetch by id -- is an
-- indexed equality instead of a JSONB walk.
--
-- This script is idempotent and additive. It never drops or renames anything, and
-- a unique index that legacy duplicate data would reject is reported as a WARNING
-- rather than aborting the run.
-- ===========================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------

-- users
CREATE TABLE IF NOT EXISTS c_users (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_users_pub_id ON c_users (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_users_body ON c_users USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_users_updated_at ON c_users (updated_at);


-- roles
CREATE TABLE IF NOT EXISTS c_roles (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_roles_pub_id ON c_roles (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_roles_body ON c_roles USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_roles_updated_at ON c_roles (updated_at);


-- schema_migrations
CREATE TABLE IF NOT EXISTS c_schema_migrations (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_schema_migrations_pub_id ON c_schema_migrations (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_schema_migrations_body ON c_schema_migrations USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_schema_migrations_updated_at ON c_schema_migrations (updated_at);


-- schema_migration_lock
CREATE TABLE IF NOT EXISTS c_schema_migration_lock (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_schema_migration_lock_pub_id ON c_schema_migration_lock (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_schema_migration_lock_body ON c_schema_migration_lock USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_schema_migration_lock_updated_at ON c_schema_migration_lock (updated_at);


-- settings
CREATE TABLE IF NOT EXISTS c_settings (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_settings_pub_id ON c_settings (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_settings_body ON c_settings USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_settings_updated_at ON c_settings (updated_at);


-- crm_config_sets
CREATE TABLE IF NOT EXISTS c_crm_config_sets (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_crm_config_sets_pub_id ON c_crm_config_sets (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_crm_config_sets_body ON c_crm_config_sets USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_crm_config_sets_updated_at ON c_crm_config_sets (updated_at);


-- sidebar_layouts
CREATE TABLE IF NOT EXISTS c_sidebar_layouts (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_sidebar_layouts_pub_id ON c_sidebar_layouts (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_sidebar_layouts_body ON c_sidebar_layouts USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_sidebar_layouts_updated_at ON c_sidebar_layouts (updated_at);


-- dashboard_layouts
CREATE TABLE IF NOT EXISTS c_dashboard_layouts (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_dashboard_layouts_pub_id ON c_dashboard_layouts (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_dashboard_layouts_body ON c_dashboard_layouts USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_dashboard_layouts_updated_at ON c_dashboard_layouts (updated_at);


-- audit_logs
CREATE TABLE IF NOT EXISTS c_audit_logs (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_audit_logs_pub_id ON c_audit_logs (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_audit_logs_body ON c_audit_logs USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_audit_logs_updated_at ON c_audit_logs (updated_at);


-- activity_logs
CREATE TABLE IF NOT EXISTS c_activity_logs (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_activity_logs_pub_id ON c_activity_logs (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_activity_logs_body ON c_activity_logs USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_activity_logs_updated_at ON c_activity_logs (updated_at);


-- notification_rules
CREATE TABLE IF NOT EXISTS c_notification_rules (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_notification_rules_pub_id ON c_notification_rules (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_notification_rules_body ON c_notification_rules USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_notification_rules_updated_at ON c_notification_rules (updated_at);


-- leads
CREATE TABLE IF NOT EXISTS c_leads (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_leads_pub_id ON c_leads (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_leads_body ON c_leads USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_leads_updated_at ON c_leads (updated_at);


-- lost_leads
CREATE TABLE IF NOT EXISTS c_lost_leads (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_lost_leads_pub_id ON c_lost_leads (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_lost_leads_body ON c_lost_leads USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_lost_leads_updated_at ON c_lost_leads (updated_at);


-- lead_qualifications
CREATE TABLE IF NOT EXISTS c_lead_qualifications (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_lead_qualifications_pub_id ON c_lead_qualifications (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_lead_qualifications_body ON c_lead_qualifications USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_lead_qualifications_updated_at ON c_lead_qualifications (updated_at);


-- activities
CREATE TABLE IF NOT EXISTS c_activities (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_activities_pub_id ON c_activities (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_activities_body ON c_activities USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_activities_updated_at ON c_activities (updated_at);


-- follow_ups
CREATE TABLE IF NOT EXISTS c_follow_ups (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_follow_ups_pub_id ON c_follow_ups (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_follow_ups_body ON c_follow_ups USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_follow_ups_updated_at ON c_follow_ups (updated_at);


-- negotiations
CREATE TABLE IF NOT EXISTS c_negotiations (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_negotiations_pub_id ON c_negotiations (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_negotiations_body ON c_negotiations USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_negotiations_updated_at ON c_negotiations (updated_at);


-- requirement_discussions
CREATE TABLE IF NOT EXISTS c_requirement_discussions (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_requirement_discussions_pub_id ON c_requirement_discussions (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_requirement_discussions_body ON c_requirement_discussions USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_requirement_discussions_updated_at ON c_requirement_discussions (updated_at);


-- contact_attempts
CREATE TABLE IF NOT EXISTS c_contact_attempts (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_contact_attempts_pub_id ON c_contact_attempts (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_contact_attempts_body ON c_contact_attempts USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_contact_attempts_updated_at ON c_contact_attempts (updated_at);


-- sales_targets
CREATE TABLE IF NOT EXISTS c_sales_targets (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_sales_targets_pub_id ON c_sales_targets (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_sales_targets_body ON c_sales_targets USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_sales_targets_updated_at ON c_sales_targets (updated_at);


-- notifications
CREATE TABLE IF NOT EXISTS c_notifications (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_notifications_pub_id ON c_notifications (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_notifications_body ON c_notifications USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_notifications_updated_at ON c_notifications (updated_at);


-- customers
CREATE TABLE IF NOT EXISTS c_customers (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_customers_pub_id ON c_customers (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_customers_body ON c_customers USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_customers_updated_at ON c_customers (updated_at);


-- contacts
CREATE TABLE IF NOT EXISTS c_contacts (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_contacts_pub_id ON c_contacts (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_contacts_body ON c_contacts USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_contacts_updated_at ON c_contacts (updated_at);


-- project_contacts
CREATE TABLE IF NOT EXISTS c_project_contacts (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_project_contacts_pub_id ON c_project_contacts (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_project_contacts_body ON c_project_contacts USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_project_contacts_updated_at ON c_project_contacts (updated_at);


-- products
CREATE TABLE IF NOT EXISTS c_products (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_products_pub_id ON c_products (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_products_body ON c_products USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_products_updated_at ON c_products (updated_at);


-- brands
CREATE TABLE IF NOT EXISTS c_brands (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_brands_pub_id ON c_brands (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_brands_body ON c_brands USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_brands_updated_at ON c_brands (updated_at);


-- product_categories
CREATE TABLE IF NOT EXISTS c_product_categories (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_product_categories_pub_id ON c_product_categories (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_product_categories_body ON c_product_categories USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_product_categories_updated_at ON c_product_categories (updated_at);


-- product_attributes
CREATE TABLE IF NOT EXISTS c_product_attributes (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_product_attributes_pub_id ON c_product_attributes (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_product_attributes_body ON c_product_attributes USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_product_attributes_updated_at ON c_product_attributes (updated_at);


-- packages
CREATE TABLE IF NOT EXISTS c_packages (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_packages_pub_id ON c_packages (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_packages_body ON c_packages USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_packages_updated_at ON c_packages (updated_at);


-- inventory
CREATE TABLE IF NOT EXISTS c_inventory (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_inventory_pub_id ON c_inventory (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_inventory_body ON c_inventory USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_inventory_updated_at ON c_inventory (updated_at);


-- amcs
CREATE TABLE IF NOT EXISTS c_amcs (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_amcs_pub_id ON c_amcs (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_amcs_body ON c_amcs USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_amcs_updated_at ON c_amcs (updated_at);


-- quotations
CREATE TABLE IF NOT EXISTS c_quotations (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_quotations_pub_id ON c_quotations (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_quotations_body ON c_quotations USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_quotations_updated_at ON c_quotations (updated_at);


-- purchase_orders
CREATE TABLE IF NOT EXISTS c_purchase_orders (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_pub_id ON c_purchase_orders (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_body ON c_purchase_orders USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_updated_at ON c_purchase_orders (updated_at);


-- boqs
CREATE TABLE IF NOT EXISTS c_boqs (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_boqs_pub_id ON c_boqs (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_boqs_body ON c_boqs USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_boqs_updated_at ON c_boqs (updated_at);


-- work_orders
CREATE TABLE IF NOT EXISTS c_work_orders (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_work_orders_pub_id ON c_work_orders (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_work_orders_body ON c_work_orders USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_work_orders_updated_at ON c_work_orders (updated_at);


-- shipments
CREATE TABLE IF NOT EXISTS c_shipments (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_shipments_pub_id ON c_shipments (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_shipments_body ON c_shipments USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_shipments_updated_at ON c_shipments (updated_at);


-- bookings
CREATE TABLE IF NOT EXISTS c_bookings (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_bookings_pub_id ON c_bookings (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_bookings_body ON c_bookings USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_bookings_updated_at ON c_bookings (updated_at);


-- design_tasks
CREATE TABLE IF NOT EXISTS c_design_tasks (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_design_tasks_pub_id ON c_design_tasks (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_design_tasks_body ON c_design_tasks USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_design_tasks_updated_at ON c_design_tasks (updated_at);


-- accounting
CREATE TABLE IF NOT EXISTS c_accounting (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_accounting_pub_id ON c_accounting (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_accounting_body ON c_accounting USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_accounting_updated_at ON c_accounting (updated_at);


-- invoices
CREATE TABLE IF NOT EXISTS c_invoices (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_invoices_pub_id ON c_invoices (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_invoices_body ON c_invoices USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_invoices_updated_at ON c_invoices (updated_at);


-- projects
CREATE TABLE IF NOT EXISTS c_projects (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_projects_pub_id ON c_projects (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_projects_body ON c_projects USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_projects_updated_at ON c_projects (updated_at);


-- project_documents
CREATE TABLE IF NOT EXISTS c_project_documents (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_project_documents_pub_id ON c_project_documents (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_project_documents_body ON c_project_documents USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_project_documents_updated_at ON c_project_documents (updated_at);


-- reports
CREATE TABLE IF NOT EXISTS c_reports (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_reports_pub_id ON c_reports (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_reports_body ON c_reports USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_reports_updated_at ON c_reports (updated_at);


-- suppliers
CREATE TABLE IF NOT EXISTS c_suppliers (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_suppliers_pub_id ON c_suppliers (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_suppliers_body ON c_suppliers USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_suppliers_updated_at ON c_suppliers (updated_at);


-- brand_requests
CREATE TABLE IF NOT EXISTS c_brand_requests (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_brand_requests_pub_id ON c_brand_requests (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_brand_requests_body ON c_brand_requests USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_brand_requests_updated_at ON c_brand_requests (updated_at);


-- email_logs
CREATE TABLE IF NOT EXISTS c_email_logs (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_email_logs_pub_id ON c_email_logs (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_email_logs_body ON c_email_logs USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_email_logs_updated_at ON c_email_logs (updated_at);


-- webhook_settings
CREATE TABLE IF NOT EXISTS c_webhook_settings (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_webhook_settings_pub_id ON c_webhook_settings (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_webhook_settings_body ON c_webhook_settings USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_webhook_settings_updated_at ON c_webhook_settings (updated_at);


-- webhook_logs
CREATE TABLE IF NOT EXISTS c_webhook_logs (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_webhook_logs_pub_id ON c_webhook_logs (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_webhook_logs_body ON c_webhook_logs USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_webhook_logs_updated_at ON c_webhook_logs (updated_at);


-- resend_settings
CREATE TABLE IF NOT EXISTS c_resend_settings (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_resend_settings_pub_id ON c_resend_settings (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_resend_settings_body ON c_resend_settings USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_resend_settings_updated_at ON c_resend_settings (updated_at);


-- meta_settings
CREATE TABLE IF NOT EXISTS c_meta_settings (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_meta_settings_pub_id ON c_meta_settings (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_meta_settings_body ON c_meta_settings USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_meta_settings_updated_at ON c_meta_settings (updated_at);


-- tally_settings
CREATE TABLE IF NOT EXISTS c_tally_settings (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_tally_settings_pub_id ON c_tally_settings (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_tally_settings_body ON c_tally_settings USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_tally_settings_updated_at ON c_tally_settings (updated_at);


-- sync_logs
CREATE TABLE IF NOT EXISTS c_sync_logs (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_sync_logs_pub_id ON c_sync_logs (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_sync_logs_body ON c_sync_logs USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_sync_logs_updated_at ON c_sync_logs (updated_at);


-- events
CREATE TABLE IF NOT EXISTS c_events (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_events_pub_id ON c_events (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_events_body ON c_events USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_events_updated_at ON c_events (updated_at);


-- campaigns
CREATE TABLE IF NOT EXISTS c_campaigns (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_campaigns_pub_id ON c_campaigns (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_campaigns_body ON c_campaigns USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_campaigns_updated_at ON c_campaigns (updated_at);


-- social_posts
CREATE TABLE IF NOT EXISTS c_social_posts (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_social_posts_pub_id ON c_social_posts (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_social_posts_body ON c_social_posts USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_social_posts_updated_at ON c_social_posts (updated_at);


-- media
CREATE TABLE IF NOT EXISTS c_media (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_c_media_pub_id ON c_media (pub_id);
CREATE INDEX IF NOT EXISTS ix_c_media_body ON c_media USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_c_media_updated_at ON c_media (updated_at);


-- ---------------------------------------------------------------------
-- Public-id uniqueness and query indexes
--
-- Public-id: these collections are fetched and updated by their public `id`, so a
-- duplicate id silently edits the wrong record. Partial, so a row with no public
-- id (possible when importing the backup) does not collide with another such row.
--
-- Query: gin(body jsonb_path_ops) cannot answer `body #>> '{field}' = $1`, which
-- is how the shim compiles every equality, range and sort. Without these btree
-- indexes every list endpoint is a sequential scan. Derived from the
-- create_index calls in server.py's startup hook plus the filter and sort keys
-- of every endpoint.
-- ---------------------------------------------------------------------

-- c_users.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_users_id ON c_users ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_users_id not created: %', SQLERRM;
END
$crm$;

-- c_roles.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_roles_id ON c_roles ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_roles_id not created: %', SQLERRM;
END
$crm$;

-- c_schema_migrations.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_schema_migrations_id ON c_schema_migrations ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_schema_migrations_id not created: %', SQLERRM;
END
$crm$;

-- c_settings.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_settings_id ON c_settings ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_settings_id not created: %', SQLERRM;
END
$crm$;

-- c_crm_config_sets.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_crm_config_sets_id ON c_crm_config_sets ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_crm_config_sets_id not created: %', SQLERRM;
END
$crm$;

-- c_webhook_settings.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_webhook_settings_id ON c_webhook_settings ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_webhook_settings_id not created: %', SQLERRM;
END
$crm$;

-- c_resend_settings.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_resend_settings_id ON c_resend_settings ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_resend_settings_id not created: %', SQLERRM;
END
$crm$;

-- c_meta_settings.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_meta_settings_id ON c_meta_settings ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_meta_settings_id not created: %', SQLERRM;
END
$crm$;

-- c_tally_settings.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_tally_settings_id ON c_tally_settings ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_tally_settings_id not created: %', SQLERRM;
END
$crm$;

-- c_leads.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_leads_id ON c_leads ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_leads_id not created: %', SQLERRM;
END
$crm$;

-- c_customers.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_customers_id ON c_customers ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_customers_id not created: %', SQLERRM;
END
$crm$;

-- c_contacts.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_contacts_id ON c_contacts ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_contacts_id not created: %', SQLERRM;
END
$crm$;

-- c_products.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_products_id ON c_products ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_products_id not created: %', SQLERRM;
END
$crm$;

-- c_brands.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_brands_id ON c_brands ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_brands_id not created: %', SQLERRM;
END
$crm$;

-- c_product_categories.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_product_categories_id ON c_product_categories ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_product_categories_id not created: %', SQLERRM;
END
$crm$;

-- c_product_attributes.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_product_attributes_id ON c_product_attributes ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_product_attributes_id not created: %', SQLERRM;
END
$crm$;

-- c_packages.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_packages_id ON c_packages ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_packages_id not created: %', SQLERRM;
END
$crm$;

-- c_projects.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_projects_id ON c_projects ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_projects_id not created: %', SQLERRM;
END
$crm$;

-- c_project_documents.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_project_documents_id ON c_project_documents ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_project_documents_id not created: %', SQLERRM;
END
$crm$;

-- c_quotations.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_quotations_id ON c_quotations ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_quotations_id not created: %', SQLERRM;
END
$crm$;

-- c_purchase_orders.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_purchase_orders_id ON c_purchase_orders ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_purchase_orders_id not created: %', SQLERRM;
END
$crm$;

-- c_boqs.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_boqs_id ON c_boqs ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_boqs_id not created: %', SQLERRM;
END
$crm$;

-- c_work_orders.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_work_orders_id ON c_work_orders ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_work_orders_id not created: %', SQLERRM;
END
$crm$;

-- c_accounting.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_accounting_id ON c_accounting ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_accounting_id not created: %', SQLERRM;
END
$crm$;

-- c_invoices.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_invoices_id ON c_invoices ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_invoices_id not created: %', SQLERRM;
END
$crm$;

-- c_events.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_events_id ON c_events ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_events_id not created: %', SQLERRM;
END
$crm$;

-- c_tasks.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_tasks_id ON c_tasks ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_tasks_id not created: %', SQLERRM;
END
$crm$;

-- c_shipments.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_shipments_id ON c_shipments ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_shipments_id not created: %', SQLERRM;
END
$crm$;

-- c_bookings.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_bookings_id ON c_bookings ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_bookings_id not created: %', SQLERRM;
END
$crm$;

-- c_design_tasks.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_design_tasks_id ON c_design_tasks ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_design_tasks_id not created: %', SQLERRM;
END
$crm$;

-- c_suppliers.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_suppliers_id ON c_suppliers ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_suppliers_id not created: %', SQLERRM;
END
$crm$;

-- c_social_posts.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_social_posts_id ON c_social_posts ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_social_posts_id not created: %', SQLERRM;
END
$crm$;

-- c_campaigns.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_campaigns_id ON c_campaigns ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_campaigns_id not created: %', SQLERRM;
END
$crm$;

-- c_amcs.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_amcs_id ON c_amcs ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_amcs_id not created: %', SQLERRM;
END
$crm$;

-- c_inventory.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_inventory_id ON c_inventory ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_inventory_id not created: %', SQLERRM;
END
$crm$;

-- c_reports.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_reports_id ON c_reports ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_reports_id not created: %', SQLERRM;
END
$crm$;

-- c_sales_targets.id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_sales_targets_id ON c_sales_targets ((body #>> '{id}'))
    WHERE ((body #>> '{id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_sales_targets_id not created: %', SQLERRM;
END
$crm$;

-- c_users.email
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_users_email ON c_users ((body #>> '{email}'))
    WHERE ((body #>> '{email}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_users_email not created: %', SQLERRM;
END
$crm$;

-- c_users.role
CREATE INDEX IF NOT EXISTS ix_c_users_role ON c_users ((body #>> '{role}'));

-- c_users.name
CREATE INDEX IF NOT EXISTS ix_c_users_name ON c_users ((body #>> '{name}'));

-- c_roles.name
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_roles_name ON c_roles ((body #>> '{name}'))
    WHERE ((body #>> '{name}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_roles_name not created: %', SQLERRM;
END
$crm$;

-- c_settings.key
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_settings_key ON c_settings ((body #>> '{key}'))
    WHERE ((body #>> '{key}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_settings_key not created: %', SQLERRM;
END
$crm$;

-- c_crm_config_sets.key
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_crm_config_sets_key ON c_crm_config_sets ((body #>> '{key}'))
    WHERE ((body #>> '{key}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_crm_config_sets_key not created: %', SQLERRM;
END
$crm$;

-- c_notification_rules.event
CREATE INDEX IF NOT EXISTS ix_c_notification_rules_event ON c_notification_rules ((body #>> '{event}'));

-- c_audit_logs.user_id
CREATE INDEX IF NOT EXISTS ix_c_audit_logs_user_id ON c_audit_logs ((body #>> '{user_id}'));

-- c_audit_logs.record_type
CREATE INDEX IF NOT EXISTS ix_c_audit_logs_record_type ON c_audit_logs ((body #>> '{record_type}'));

-- c_audit_logs.record_id
CREATE INDEX IF NOT EXISTS ix_c_audit_logs_record_id ON c_audit_logs ((body #>> '{record_id}'));

-- c_audit_logs.created_at
CREATE INDEX IF NOT EXISTS ix_c_audit_logs_created_at ON c_audit_logs ((body #>> '{created_at}'));

-- c_activity_logs.user_id
CREATE INDEX IF NOT EXISTS ix_c_activity_logs_user_id ON c_activity_logs ((body #>> '{user_id}'));

-- c_activity_logs.module
CREATE INDEX IF NOT EXISTS ix_c_activity_logs_module ON c_activity_logs ((body #>> '{module}'));

-- c_activity_logs.record_id
CREATE INDEX IF NOT EXISTS ix_c_activity_logs_record_id ON c_activity_logs ((body #>> '{record_id}'));

-- c_activity_logs.created_at
CREATE INDEX IF NOT EXISTS ix_c_activity_logs_created_at ON c_activity_logs ((body #>> '{created_at}'));

-- c_dashboard_layouts.user_id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_dashboard_layouts_user_id ON c_dashboard_layouts ((body #>> '{user_id}'))
    WHERE ((body #>> '{user_id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_dashboard_layouts_user_id not created: %', SQLERRM;
END
$crm$;

-- c_sidebar_layouts.user_id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_sidebar_layouts_user_id ON c_sidebar_layouts ((body #>> '{user_id}'))
    WHERE ((body #>> '{user_id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_sidebar_layouts_user_id not created: %', SQLERRM;
END
$crm$;

-- c_leads.assigned_to
CREATE INDEX IF NOT EXISTS ix_c_leads_assigned_to ON c_leads ((body #>> '{assigned_to}'));

-- c_leads.stage
CREATE INDEX IF NOT EXISTS ix_c_leads_stage ON c_leads ((body #>> '{stage}'));

-- c_leads.stage_id
CREATE INDEX IF NOT EXISTS ix_c_leads_stage_id ON c_leads ((body #>> '{stage_id}'));

-- c_leads.source
CREATE INDEX IF NOT EXISTS ix_c_leads_source ON c_leads ((body #>> '{source}'));

-- c_leads.customer_id
CREATE INDEX IF NOT EXISTS ix_c_leads_customer_id ON c_leads ((body #>> '{customer_id}'));

-- c_leads.created_by
CREATE INDEX IF NOT EXISTS ix_c_leads_created_by ON c_leads ((body #>> '{created_by}'));

-- c_leads.email
CREATE INDEX IF NOT EXISTS ix_c_leads_email ON c_leads ((body #>> '{email}'));

-- c_leads.created_at
CREATE INDEX IF NOT EXISTS ix_c_leads_created_at ON c_leads ((body #>> '{created_at}'));

-- c_leads.follow_up_date
CREATE INDEX IF NOT EXISTS ix_c_leads_follow_up_date ON c_leads ((body #>> '{follow_up_date}'));

-- c_leads.expected_close_date
CREATE INDEX IF NOT EXISTS ix_c_leads_expected_close_date ON c_leads ((body #>> '{expected_close_date}'));

-- c_leads.assigned_to+stage
CREATE INDEX IF NOT EXISTS ix_c_leads_assigned_to_stage ON c_leads ((body #>> '{assigned_to}'), (body #>> '{stage}'));

-- c_activities.lead_id
CREATE INDEX IF NOT EXISTS ix_c_activities_lead_id ON c_activities ((body #>> '{lead_id}'));

-- c_activities.user_id
CREATE INDEX IF NOT EXISTS ix_c_activities_user_id ON c_activities ((body #>> '{user_id}'));

-- c_activities.project_id
CREATE INDEX IF NOT EXISTS ix_c_activities_project_id ON c_activities ((body #>> '{project_id}'));

-- c_activities.created_at
CREATE INDEX IF NOT EXISTS ix_c_activities_created_at ON c_activities ((body #>> '{created_at}'));

-- c_activities.follow_up_at
CREATE INDEX IF NOT EXISTS ix_c_activities_follow_up_at ON c_activities ((body #>> '{follow_up_at}'));

-- c_follow_ups.lead_id
CREATE INDEX IF NOT EXISTS ix_c_follow_ups_lead_id ON c_follow_ups ((body #>> '{lead_id}'));

-- c_follow_ups.created_by
CREATE INDEX IF NOT EXISTS ix_c_follow_ups_created_by ON c_follow_ups ((body #>> '{created_by}'));

-- c_follow_ups.status
CREATE INDEX IF NOT EXISTS ix_c_follow_ups_status ON c_follow_ups ((body #>> '{status}'));

-- c_follow_ups.follow_up_date
CREATE INDEX IF NOT EXISTS ix_c_follow_ups_follow_up_date ON c_follow_ups ((body #>> '{follow_up_date}'));

-- c_contact_attempts.lead_id
CREATE INDEX IF NOT EXISTS ix_c_contact_attempts_lead_id ON c_contact_attempts ((body #>> '{lead_id}'));

-- c_contact_attempts.created_at
CREATE INDEX IF NOT EXISTS ix_c_contact_attempts_created_at ON c_contact_attempts ((body #>> '{created_at}'));

-- c_lead_qualifications.lead_id
CREATE INDEX IF NOT EXISTS ix_c_lead_qualifications_lead_id ON c_lead_qualifications ((body #>> '{lead_id}'));

-- c_lost_leads.lead_id
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_lost_leads_lead_id ON c_lost_leads ((body #>> '{lead_id}'))
    WHERE ((body #>> '{lead_id}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_lost_leads_lead_id not created: %', SQLERRM;
END
$crm$;

-- c_lost_leads.reason
CREATE INDEX IF NOT EXISTS ix_c_lost_leads_reason ON c_lost_leads ((body #>> '{reason}'));

-- c_requirement_discussions.lead_id
CREATE INDEX IF NOT EXISTS ix_c_requirement_discussions_lead_id ON c_requirement_discussions ((body #>> '{lead_id}'));

-- c_negotiations.lead_id
CREATE INDEX IF NOT EXISTS ix_c_negotiations_lead_id ON c_negotiations ((body #>> '{lead_id}'));

-- c_negotiations.quotation_id
CREATE INDEX IF NOT EXISTS ix_c_negotiations_quotation_id ON c_negotiations ((body #>> '{quotation_id}'));

-- c_notifications.user_id
CREATE INDEX IF NOT EXISTS ix_c_notifications_user_id ON c_notifications ((body #>> '{user_id}'));

-- c_notifications.read
CREATE INDEX IF NOT EXISTS ix_c_notifications_read ON c_notifications ((body #>> '{read}'));

-- c_notifications.created_at
CREATE INDEX IF NOT EXISTS ix_c_notifications_created_at ON c_notifications ((body #>> '{created_at}'));

-- c_notifications.user_id+read
CREATE INDEX IF NOT EXISTS ix_c_notifications_user_id_read ON c_notifications ((body #>> '{user_id}'), (body #>> '{read}'));

-- c_sales_targets.user_id
CREATE INDEX IF NOT EXISTS ix_c_sales_targets_user_id ON c_sales_targets ((body #>> '{user_id}'));

-- c_reports.generated_by
CREATE INDEX IF NOT EXISTS ix_c_reports_generated_by ON c_reports ((body #>> '{generated_by}'));

-- c_reports.generated_at
CREATE INDEX IF NOT EXISTS ix_c_reports_generated_at ON c_reports ((body #>> '{generated_at}'));

-- c_customers.name
CREATE INDEX IF NOT EXISTS ix_c_customers_name ON c_customers ((body #>> '{name}'));

-- c_customers.email
CREATE INDEX IF NOT EXISTS ix_c_customers_email ON c_customers ((body #>> '{email}'));

-- c_contacts.name
CREATE INDEX IF NOT EXISTS ix_c_contacts_name ON c_contacts ((body #>> '{name}'));

-- c_contacts.email
CREATE INDEX IF NOT EXISTS ix_c_contacts_email ON c_contacts ((body #>> '{email}'));

-- c_contacts.customer_id
CREATE INDEX IF NOT EXISTS ix_c_contacts_customer_id ON c_contacts ((body #>> '{customer_id}'));

-- c_contacts.company
CREATE INDEX IF NOT EXISTS ix_c_contacts_company ON c_contacts ((body #>> '{company}'));

-- c_brands.name
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_brands_name ON c_brands ((body #>> '{name}'))
    WHERE ((body #>> '{name}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_brands_name not created: %', SQLERRM;
END
$crm$;

-- c_products.brand_id
CREATE INDEX IF NOT EXISTS ix_c_products_brand_id ON c_products ((body #>> '{brand_id}'));

-- c_products.category_id
CREATE INDEX IF NOT EXISTS ix_c_products_category_id ON c_products ((body #>> '{category_id}'));

-- c_products.sku
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_products_sku ON c_products ((body #>> '{sku}'))
    WHERE ((body #>> '{sku}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_products_sku not created: %', SQLERRM;
END
$crm$;

-- c_products.status
CREATE INDEX IF NOT EXISTS ix_c_products_status ON c_products ((body #>> '{status}'));

-- c_products.name
CREATE INDEX IF NOT EXISTS ix_c_products_name ON c_products ((body #>> '{name}'));

-- c_product_categories.name
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_product_categories_name ON c_product_categories ((body #>> '{name}'))
    WHERE ((body #>> '{name}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_product_categories_name not created: %', SQLERRM;
END
$crm$;

-- c_product_categories.parent_id
CREATE INDEX IF NOT EXISTS ix_c_product_categories_parent_id ON c_product_categories ((body #>> '{parent_id}'));

-- c_product_attributes.name
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_product_attributes_name ON c_product_attributes ((body #>> '{name}'))
    WHERE ((body #>> '{name}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_product_attributes_name not created: %', SQLERRM;
END
$crm$;

-- c_packages.name
CREATE INDEX IF NOT EXISTS ix_c_packages_name ON c_packages ((body #>> '{name}'));

-- c_inventory.product_id
CREATE INDEX IF NOT EXISTS ix_c_inventory_product_id ON c_inventory ((body #>> '{product_id}'));

-- c_inventory.shipment_id
CREATE INDEX IF NOT EXISTS ix_c_inventory_shipment_id ON c_inventory ((body #>> '{shipment_id}'));

-- c_inventory.status
CREATE INDEX IF NOT EXISTS ix_c_inventory_status ON c_inventory ((body #>> '{status}'));

-- c_inventory.created_at
CREATE INDEX IF NOT EXISTS ix_c_inventory_created_at ON c_inventory ((body #>> '{created_at}'));

-- c_amcs.status
CREATE INDEX IF NOT EXISTS ix_c_amcs_status ON c_amcs ((body #>> '{status}'));

-- c_amcs.end_date
CREATE INDEX IF NOT EXISTS ix_c_amcs_end_date ON c_amcs ((body #>> '{end_date}'));

-- c_amcs.customer_id
CREATE INDEX IF NOT EXISTS ix_c_amcs_customer_id ON c_amcs ((body #>> '{customer_id}'));

-- c_quotations.lead_id
CREATE INDEX IF NOT EXISTS ix_c_quotations_lead_id ON c_quotations ((body #>> '{lead_id}'));

-- c_quotations.created_by
CREATE INDEX IF NOT EXISTS ix_c_quotations_created_by ON c_quotations ((body #>> '{created_by}'));

-- c_quotations.status
CREATE INDEX IF NOT EXISTS ix_c_quotations_status ON c_quotations ((body #>> '{status}'));

-- c_quotations.quote_status
CREATE INDEX IF NOT EXISTS ix_c_quotations_quote_status ON c_quotations ((body #>> '{quote_status}'));

-- c_quotations.customer_id
CREATE INDEX IF NOT EXISTS ix_c_quotations_customer_id ON c_quotations ((body #>> '{customer_id}'));

-- c_quotations.project_id
CREATE INDEX IF NOT EXISTS ix_c_quotations_project_id ON c_quotations ((body #>> '{project_id}'));

-- c_quotations.created_at
CREATE INDEX IF NOT EXISTS ix_c_quotations_created_at ON c_quotations ((body #>> '{created_at}'));

-- c_quotations.due_date
CREATE INDEX IF NOT EXISTS ix_c_quotations_due_date ON c_quotations ((body #>> '{due_date}'));

-- c_quotations.share_token
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_quotations_share_token ON c_quotations ((body #>> '{share_token}'))
    WHERE ((body #>> '{share_token}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_quotations_share_token not created: %', SQLERRM;
END
$crm$;

-- c_purchase_orders.po_no
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_purchase_orders_po_no ON c_purchase_orders ((body #>> '{po_no}'))
    WHERE ((body #>> '{po_no}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_purchase_orders_po_no not created: %', SQLERRM;
END
$crm$;

-- c_purchase_orders.supplier_id
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_supplier_id ON c_purchase_orders ((body #>> '{supplier_id}'));

-- c_purchase_orders.customer_id
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_customer_id ON c_purchase_orders ((body #>> '{customer_id}'));

-- c_purchase_orders.quotation_id
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_quotation_id ON c_purchase_orders ((body #>> '{quotation_id}'));

-- c_purchase_orders.lead_id
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_lead_id ON c_purchase_orders ((body #>> '{lead_id}'));

-- c_purchase_orders.project_id
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_project_id ON c_purchase_orders ((body #>> '{project_id}'));

-- c_purchase_orders.direction
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_direction ON c_purchase_orders ((body #>> '{direction}'));

-- c_purchase_orders.status
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_status ON c_purchase_orders ((body #>> '{status}'));

-- c_purchase_orders.created_at
CREATE INDEX IF NOT EXISTS ix_c_purchase_orders_created_at ON c_purchase_orders ((body #>> '{created_at}'));

-- c_boqs.lead_id
CREATE INDEX IF NOT EXISTS ix_c_boqs_lead_id ON c_boqs ((body #>> '{lead_id}'));

-- c_boqs.status
CREATE INDEX IF NOT EXISTS ix_c_boqs_status ON c_boqs ((body #>> '{status}'));

-- c_work_orders.customer_id
CREATE INDEX IF NOT EXISTS ix_c_work_orders_customer_id ON c_work_orders ((body #>> '{customer_id}'));

-- c_work_orders.assigned_to
CREATE INDEX IF NOT EXISTS ix_c_work_orders_assigned_to ON c_work_orders ((body #>> '{assigned_to}'));

-- c_work_orders.status
CREATE INDEX IF NOT EXISTS ix_c_work_orders_status ON c_work_orders ((body #>> '{status}'));

-- c_work_orders.scheduled_date
CREATE INDEX IF NOT EXISTS ix_c_work_orders_scheduled_date ON c_work_orders ((body #>> '{scheduled_date}'));

-- c_shipments.status
CREATE INDEX IF NOT EXISTS ix_c_shipments_status ON c_shipments ((body #>> '{status}'));

-- c_shipments.eta
CREATE INDEX IF NOT EXISTS ix_c_shipments_eta ON c_shipments ((body #>> '{eta}'));

-- c_shipments.oem
CREATE INDEX IF NOT EXISTS ix_c_shipments_oem ON c_shipments ((body #>> '{oem}'));

-- c_shipments.created_at
CREATE INDEX IF NOT EXISTS ix_c_shipments_created_at ON c_shipments ((body #>> '{created_at}'));

-- c_bookings.service
CREATE INDEX IF NOT EXISTS ix_c_bookings_service ON c_bookings ((body #>> '{service}'));

-- c_bookings.date
CREATE INDEX IF NOT EXISTS ix_c_bookings_date ON c_bookings ((body #>> '{date}'));

-- c_design_tasks.lead_id
CREATE INDEX IF NOT EXISTS ix_c_design_tasks_lead_id ON c_design_tasks ((body #>> '{lead_id}'));

-- c_design_tasks.assigned_to
CREATE INDEX IF NOT EXISTS ix_c_design_tasks_assigned_to ON c_design_tasks ((body #>> '{assigned_to}'));

-- c_design_tasks.status
CREATE INDEX IF NOT EXISTS ix_c_design_tasks_status ON c_design_tasks ((body #>> '{status}'));

-- c_accounting.doc_no
CREATE INDEX IF NOT EXISTS ix_c_accounting_doc_no ON c_accounting ((body #>> '{doc_no}'));

-- c_accounting.type
CREATE INDEX IF NOT EXISTS ix_c_accounting_type ON c_accounting ((body #>> '{type}'));

-- c_accounting.status
CREATE INDEX IF NOT EXISTS ix_c_accounting_status ON c_accounting ((body #>> '{status}'));

-- c_accounting.date
CREATE INDEX IF NOT EXISTS ix_c_accounting_date ON c_accounting ((body #>> '{date}'));

-- c_invoices.invoice_no
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_invoices_invoice_no ON c_invoices ((body #>> '{invoice_no}'))
    WHERE ((body #>> '{invoice_no}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_invoices_invoice_no not created: %', SQLERRM;
END
$crm$;

-- c_invoices.customer_name
CREATE INDEX IF NOT EXISTS ix_c_invoices_customer_name ON c_invoices ((body #>> '{customer_name}'));

-- c_invoices.quotation_id
CREATE INDEX IF NOT EXISTS ix_c_invoices_quotation_id ON c_invoices ((body #>> '{quotation_id}'));

-- c_invoices.po_id
CREATE INDEX IF NOT EXISTS ix_c_invoices_po_id ON c_invoices ((body #>> '{po_id}'));

-- c_invoices.status
CREATE INDEX IF NOT EXISTS ix_c_invoices_status ON c_invoices ((body #>> '{status}'));

-- c_invoices.due_date
CREATE INDEX IF NOT EXISTS ix_c_invoices_due_date ON c_invoices ((body #>> '{due_date}'));

-- c_suppliers.name
CREATE INDEX IF NOT EXISTS ix_c_suppliers_name ON c_suppliers ((body #>> '{name}'));

-- c_brand_requests.user_id
CREATE INDEX IF NOT EXISTS ix_c_brand_requests_user_id ON c_brand_requests ((body #>> '{user_id}'));

-- c_brand_requests.brand
CREATE INDEX IF NOT EXISTS ix_c_brand_requests_brand ON c_brand_requests ((body #>> '{brand}'));

-- c_brand_requests.status
CREATE INDEX IF NOT EXISTS ix_c_brand_requests_status ON c_brand_requests ((body #>> '{status}'));

-- c_projects.project_no
DO $crm$
BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS ux_c_projects_project_no ON c_projects ((body #>> '{project_no}'))
    WHERE ((body #>> '{project_no}') IS NOT NULL);
EXCEPTION WHEN others THEN
    RAISE WARNING 'index ux_c_projects_project_no not created: %', SQLERRM;
END
$crm$;

-- c_projects.name
CREATE INDEX IF NOT EXISTS ix_c_projects_name ON c_projects ((body #>> '{name}'));

-- c_projects.created_by
CREATE INDEX IF NOT EXISTS ix_c_projects_created_by ON c_projects ((body #>> '{created_by}'));

-- c_projects.manager_id
CREATE INDEX IF NOT EXISTS ix_c_projects_manager_id ON c_projects ((body #>> '{manager_id}'));

-- c_projects.stage_id
CREATE INDEX IF NOT EXISTS ix_c_projects_stage_id ON c_projects ((body #>> '{stage_id}'));

-- c_projects.status
CREATE INDEX IF NOT EXISTS ix_c_projects_status ON c_projects ((body #>> '{status}'));

-- c_projects.lead_id
CREATE INDEX IF NOT EXISTS ix_c_projects_lead_id ON c_projects ((body #>> '{lead_id}'));

-- c_projects.customer_id
CREATE INDEX IF NOT EXISTS ix_c_projects_customer_id ON c_projects ((body #>> '{customer_id}'));

-- c_projects.created_at
CREATE INDEX IF NOT EXISTS ix_c_projects_created_at ON c_projects ((body #>> '{created_at}'));

-- c_project_contacts.project_id
CREATE INDEX IF NOT EXISTS ix_c_project_contacts_project_id ON c_project_contacts ((body #>> '{project_id}'));

-- c_project_documents.project_id
CREATE INDEX IF NOT EXISTS ix_c_project_documents_project_id ON c_project_documents ((body #>> '{project_id}'));

-- c_events.title
CREATE INDEX IF NOT EXISTS ix_c_events_title ON c_events ((body #>> '{title}'));

-- c_events.start_time
CREATE INDEX IF NOT EXISTS ix_c_events_start_time ON c_events ((body #>> '{start_time}'));

-- c_events.lead_id
CREATE INDEX IF NOT EXISTS ix_c_events_lead_id ON c_events ((body #>> '{lead_id}'));

-- c_campaigns.name
CREATE INDEX IF NOT EXISTS ix_c_campaigns_name ON c_campaigns ((body #>> '{name}'));

-- c_social_posts.title
CREATE INDEX IF NOT EXISTS ix_c_social_posts_title ON c_social_posts ((body #>> '{title}'));

-- c_social_posts.status
CREATE INDEX IF NOT EXISTS ix_c_social_posts_status ON c_social_posts ((body #>> '{status}'));

-- c_social_posts.scheduled_at
CREATE INDEX IF NOT EXISTS ix_c_social_posts_scheduled_at ON c_social_posts ((body #>> '{scheduled_at}'));

-- c_email_logs.event
CREATE INDEX IF NOT EXISTS ix_c_email_logs_event ON c_email_logs ((body #>> '{event}'));

-- c_email_logs.created_at
CREATE INDEX IF NOT EXISTS ix_c_email_logs_created_at ON c_email_logs ((body #>> '{created_at}'));

-- c_webhook_logs.event
CREATE INDEX IF NOT EXISTS ix_c_webhook_logs_event ON c_webhook_logs ((body #>> '{event}'));

-- c_webhook_logs.created_at
CREATE INDEX IF NOT EXISTS ix_c_webhook_logs_created_at ON c_webhook_logs ((body #>> '{created_at}'));

-- c_sync_logs.started_at
CREATE INDEX IF NOT EXISTS ix_c_sync_logs_started_at ON c_sync_logs ((body #>> '{started_at}'));

-- c_media.uploaded_at
CREATE INDEX IF NOT EXISTS ix_c_media_uploaded_at ON c_media ((body #>> '{uploaded_at}'));

-- c_media.entity
CREATE INDEX IF NOT EXISTS ix_c_media_entity ON c_media ((body #>> '{entity}'));

-- c_media.brand_id
CREATE INDEX IF NOT EXISTS ix_c_media_brand_id ON c_media ((body #>> '{brand_id}'));

-- c_media.product_id
CREATE INDEX IF NOT EXISTS ix_c_media_product_id ON c_media ((body #>> '{product_id}'));

-- ---------------------------------------------------------------------
-- Supabase access control
--
-- Supabase's default privileges grant anon/authenticated full access to new
-- tables in `public`. These tables hold bcrypt password hashes, customer PII and
-- revenue, so that grant is removed explicitly -- for the tables that exist now and
-- for anything created later. The backend connects over asyncpg as `postgres` and
-- authenticates with its own JWT, so it is unaffected.
-- ---------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;

-- Row level security stays OFF on purpose. The backend authenticates every
-- request itself (get_current_user in server.py) and connects as `postgres`,
-- which bypasses RLS, so enabling it would add no protection while making every
-- query look as though it were filtered when it is not.

GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Collected for reference: 864 tables in schema public matching c_*.

-- ===========================================================================
-- Done. Verify with:
--   SELECT count(*) FROM information_schema.tables
--    WHERE table_schema = 'public' AND table_name LIKE 'c\_%';
--   SELECT count(*) FROM information_schema.indexes
--    WHERE table_schema = 'public';
-- ===========================================================================
