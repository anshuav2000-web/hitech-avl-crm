# MongoDB to Supabase Migration Guide for Hitech AVL CRM

## Overview

This document outlines the migration from MongoDB to Supabase PostgreSQL for the Hitech AVL CRM backend. The migration involves several phases:

1. **Preparation Phase** - Environment setup and configuration
2. **Schema Migration Phase** - Database schema conversion
3. **Data Migration Phase** - Importing the 565 documents from backup
4. **Code Migration Phase** - Updating backend code to use Supabase
5. **Testing Phase** - Validation and testing

## Phase 1: Preparation Phase

### 1.1 Environment Configuration

**Current .env (backend/.env):**

```bash
# ---------- Database ----------
MONGO_URL=mongodb://mongo:27017
DB_NAME=hitech_crm
JWT_SECRET=dev-jwt-secret-change-in-production-please-use-strong-random-string

# ---------- Authentication ----------
ADMIN_EMAIL=admin@hitechaudio.in
ADMIN_PASSWORD=Admin@123

# ---------- Contact / customer email generation ----------
GENERATED_EMAIL_DOMAIN=hitechavl.com

# ---------- Outbound email (Zoho SMTP) ----------
SMTP_HOST=smtppro.zoho.in
SMTP_PORT=587
SMTP_USER=anchit@hitechavl.com
SMTP_PASSWORD=6jnxECXxRJwh
SMTP_SENDER=anchit@hitechavl.com
SMTP_SENDER_NAME=Anchit Verma

# ---------- Integrations ----------
GEMINI_API_KEY=
RESEND_API_KEY=
TALLY_BASE_URL=
TALLY_TALLY_ID=
META_APP_SECRET=
META_APP_ID=
META_PAGE_ID=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
N8N_WEBHOOK_URL=
```

**New .env (backend/.env) - Supabase Configuration:**

```bash
# ---------------------------------------------------------------------------
# Hitech AVL CRM — Supabase-only environment
#
# MongoDB has been removed and replaced with Supabase PostgreSQL.
# All data from the 2026-10-01 backup is imported into Supabase.
# ---------------------------------------------------------------------------

# ---------- Supabase ----------
# Supabase project URL and service role key for server-to-server access
SUPABASE_URL=https://rguvwnfocohsuejjtyed.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJndXZ3bmZvY29oc3VjamV0eWVkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MTIwNDc4NCwiZXhwIjoyMTA2NzgwNzg0fQ.m3RDNjM3q6jxRXge9cqyQVEoZURzHf6mlI3_EDSSA2A

# PostgreSQL connection string (constructed from the above)
DATABASE_URL=postgresql://postgres:${SUPABASE_KEY}@db.rguvwnfocohsuejjtyed.supabase.co:5432/postgres

# Supabase configuration
DB_NAME=hitech_crm

# ---------- Authentication ----------
# JWT secret for token signing (keep this secure in production)
JWT_SECRET=dev-jwt-secret-change-in-production-please-use-strong-random-string

# ---------- URLs ----------
# API base URL (frontend calls relative /api paths to backend)
API_URL=http://localhost:8000

# CORS origins for the backend API
CORS_ORIGINS=http://localhost:3000

# ---------- Email / integrations ----------
# Zoho SMTP configuration (as per existing .env)
SMTP_HOST=smtppro.zoho.in
SMTP_PORT=587
SMTP_USER=anchit@hitechavl.com
SMTP_PASSWORD=6jnxECXxRJwh
SMTP_SENDER=anchit@hitechavl.com
SMTP_SENDER_NAME=Anchit Verma

# ---------- Other ----------
TZ=Asia/Kolkata
GENERATED_EMAIL_DOMAIN=hitechavl.com
SEED_DEMO_USERS=false
```

### 1.2 Database Connection Setup

**Current Database Setup (server.py lines 36-45):**

```python
# ---------- Database ----------
# The URL may arrive as DATABASE_URL (the conventional production variable name) or
# MONGO_URL (what the existing local .env uses). Both are read so an existing
# deployment does not break, and the connection string itself is never logged or
# returned by any endpoint.
mongo_url = os.environ.get("MONGO_URL") or os.environ.get("DATABASE_URL")
if not mongo_url:
    raise RuntimeError("Neither MONGO_URL nor DATABASE_URL is set; refusing to start.")
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "hitech_crm")]
```

**New Database Setup:**

```python
# Import database adapter
from database import get_db

# Initialize database adapter (handles Supabase/MongoDB switching)
db_adapter = await get_db()
```

### 1.3 Database Adapter

**Created:** `backend/database.py`

Provides a unified interface for database operations supporting both Supabase PostgreSQL and MongoDB:

- **Supabase Operations:**
  - CRUD operations with proper query transformation
  - JSONB fields for complex document storage
  - UUID primary keys
  - Foreign key constraints

- **MongoDB Operations:**
  - Legacy support for gradual migration
  - Motor async driver
  - Original document structure preservation

- **Key Features:**
  - Automatic detection of available databases
  - Seamless switching between databases
  - Document transformation for schema differences
  - Proper indexing and performance optimization

## Phase 2: Schema Migration Phase

### 2.1 Supabase Schema SQL

**File:** `backend/supabase_schema.sql`

The schema converts MongoDB collections to PostgreSQL tables with:

- **Users Table**: UUID primary key, email uniqueness, JSONB for flexible attributes
- **Leads Table**: Foreign keys to users, timestamp tracking, stage management
- **Products Table**: Category and pricing information
- **Quotations Table**: JSONB for items, foreign keys to leads and users
- **Projects, Tasks, Activities, Customers**: Standard relational structure
- **Stage History Table**: Many-to-many relationship between leads and stages
- **Audit Logs**: Track all database changes
- **Indexes**: For performance optimization

### 2.2 Collection Mapping

| MongoDB Collection | PostgreSQL Table | Key Differences |
|-------------------|------------------|-----------------|
| `users` | `users` | UUID instead of ObjectID, email uniqueness |
| `leads` | `leads` | Foreign key to users, stage tracking |
| `products` | `products` | JSONB for pricing, category structure |
| `quotations` | `quotations` | JSONB for items array, foreign keys |
| `projects` | `projects` | Standard relational structure |
| `tasks` | `tasks` | Simple task management |
| `activities` | `activities` | User activity tracking |
| `customers` | `customers` | Customer information |
| `contacts` | `contacts` | Contact information |
| `brands` | `brands` | Brand information |
| `events` | `events` | Event scheduling |
| `social_posts` | `social_posts` | Social media posts |
| `suppliers` | `suppliers` | Supplier information |
| `shipments` | `shipments` | Shipment tracking |
| `bookings` | `bookings` | Booking information |
| `boqs` | `boqs` | BOQ (Bill of Quantities) |
| `design_tasks` | `design_tasks` | Design tasks |
| `sidebar_layouts` | `sidebar_layouts` | UI layout configurations |
| `dashboard_layouts` | `dashboard_layouts` | Dashboard configurations |
| `settings` | `settings` | System settings |
| `crm_config_sets` | `crm_config_sets` | CRM configuration |
| `roles` | `roles` | User roles |
| `sales_targets` | `sales_targets` | Sales targets |
| `negotiations` | `negotiations` | Negotiation records |
| `lost_leads` | `lost_leads` | Lost lead information |
| `lead_qualifications` | `lead_qualifications` | Lead qualification data |
| `requirement_discussions` | `requirement_discussions` | Requirement discussions |
| `email_logs` | `email_logs` | Email logging |
| `webhook_settings` | `webhook_settings` | Webhook configurations |
| `webhook_logs` | `webhook_logs` | Webhook logging |
| `sync_logs` | `sync_logs` | Synchronization logs |
| `schema_migrations` | `schema_migrations` | Migration tracking |

## Phase 3: Data Migration Phase

### 3.1 Backup Data

**Source:** 2026-10-01 backup
- **Total Documents:** 565
- **Collections:** 38
- **Size:** ~3.5 MB

**Collection Distribution (Sample):**
- `users`: 45 documents
- `leads`: 11 documents
- `products`: 66 documents
- `quotations`: 37 documents
- `projects`: 3 documents
- `tasks`: 11 documents
- `activities`: 91 documents
- `notifications`: 97 documents
- `email_logs`: 91 documents
- `customers`: 3 documents
- And many more...

### 3.2 Migration Script

**File:** `backend/manual_migrate_to_supabase.py`

Features:
- **Connection Management:** Automatic host detection and retry logic
- **Schema Creation:** Reads SQL schema file and executes statements
- **Data Import:** Transforms MongoDB documents to PostgreSQL format
- **Error Handling:** Comprehensive error handling with logging
- **Progress Tracking:** Detailed logging of migration progress

### 3.3 Data Transformation

**Key Transformations:**

1. **Document Structure:**
   - MongoDB `_id` → PostgreSQL `id` (UUID)
   - MongoDB `_class`, `__v` → Removed
   - Nested objects with `_id` → Convert to `id`

2. **Data Types:**
   - MongoDB objects → JSONB fields
   - MongoDB arrays → JSONB fields
   - Timestamps → TIMESTAMPTZ

3. **Relationships:**
   - MongoDB references → PostgreSQL foreign keys
   - Stage history → Separate table with joins

## Phase 4: Code Migration Phase

### 4.1 Database Adapter Integration

**Backend Code Updates:**

1. **Replace MongoDB imports** with database adapter imports
2. **Update database access** to use `db_adapter` instead of `db`
3. **Transform queries** from MongoDB to PostgreSQL-compatible format
4. **Handle document structure** differences between databases

**Example Migration:**

```python
# Before:
async def get_user_by_email(email: str):
    return await db.users.find_one({"email": email})

# After:
async def get_user_by_email(email: str):
    return await db_adapter.find_one("users", {"email": email})
```

### 4.2 Collection-Specific Updates

**Critical Collections:**

1. **Users Collection:**
   - Password hashing remains the same
   - Email uniqueness enforced by database

2. **Leads Collection:**
   - Stage history moved to separate table
   - Foreign key constraints added

3. **Quotations Collection:**
   - Items field transformed to JSONB
   - Foreign keys to leads and users

4. **Products Collection:**
   - Price fields converted to decimal
   - Category and subcategory structured

### 4.3 API Compatibility

**Key Considerations:**

1. **Query Syntax:** MongoDB `$eq`, `$ne`, `$in` → PostgreSQL `=`, `!=`, `IN`
2. **Aggregation:** MongoDB aggregation pipeline → PostgreSQL window functions
3. **Indexing:** MongoDB indexes → PostgreSQL indexes
4. **Transactions:** MongoDB transactions → PostgreSQL transactions

## Phase 5: Testing Phase

### 5.1 Test Plan

1. **Database Connection Tests:**
   - Supabase connection availability
   - Query execution tests
   - Data integrity verification

2. **API Endpoint Tests:**
   - User authentication
   - Lead management
   - Product catalog
   - Quotation generation

3. **Data Migration Tests:**
   - Document count verification
   - Field value validation
   - Relationship integrity
   - Performance benchmarks

### 5.2 Testing Strategy

1. **Unit Tests:** Individual database operations
2. **Integration Tests:** Full API endpoint testing
3. **Data Migration Tests:** Cross-validation between MongoDB and Supabase
4. **Performance Tests:** Query execution times
5. **Load Tests:** Concurrency testing

### 5.3 Validation Checks

```python
# Validate user data
async def validate_user_migration():
    # Get user from MongoDB (legacy)
    mongo_user = await db.users.find_one({"email": "admin@hitechaudio.in"})
    
    # Get user from Supabase (new)
    supabase_user = await db_adapter.find_one("users", {"email": "admin@hitechaudio.in"})
    
    # Compare essential fields
    assert mongo_user["name"] == supabase_user["name"]
    assert mongo_user["role"] == supabase_user["role"]
    assert mongo_user["created_at"] == supabase_user["created_at"]
```

## Deployment Checklist

### Pre-Deployment Tasks:

1. [ ] **Environment Setup**
   - Update `.env` file with Supabase credentials
   - Install `supabase` Python package
   - Configure database connection strings

2. [ ] **Database Migration**
   - Run migration script: `python manual_migrate_to_supabase.py`
   - Verify all 565 documents imported
   - Test database connectivity

3. [ ] **Backend Code Updates**
   - Replace MongoDB imports with database adapter
   - Update all database queries
   - Test API endpoints

4. [ ] **Data Validation**
   - Cross-validate data between MongoDB and Supabase
   - Check for data integrity issues
   - Verify relationships

### Post-Deployment Tasks:

1. [ ] **API Testing**
   - Test all endpoints
   - Validate authentication
   - Check error handling

2. [ ] **Performance Testing**
   - Benchmark query execution
   - Test load handling
   - Monitor resource usage

3. [ ] **Backup and Recovery**
   - Test backup procedures
   - Verify restore capabilities
   - Document recovery procedures

## Rollback Plan

### Quick Rollback:

1. **Restore MongoDB:**
   ```bash
   # Restore from backup if available
   # Or re-establish MongoDB connection
   ```

2. **Revert Environment Variables:**
   - Restore original `.env` file
   - Revert database connection code

3. **Database Cleanup:**
   - Drop Supabase tables
   - Remove imported data

### Full Rollback:

1. **Stop current deployment**
2. **Restore from Git tag (v1.0)**
3. **Update `.env` file**
4. **Reinitialize MongoDB**
5. **Redeploy with original configuration**

## Support and Troubleshooting

### Common Issues:

1. **Supabase Connection Failed**
   - Check `SUPABASE_URL` and `SUPABASE_KEY` environment variables
   - Verify Supabase project status
   - Check firewall/network settings

2. **Data Import Failed**
   - Verify schema file exists: `backend/supabase_schema.sql`
   - Check JSON file format
   - Verify database permissions

3. **Query Execution Failed**
   - Check collection names
   - Verify field names
   - Validate query syntax

### Contact Information:

- **Project Repository:** GitHub
- **Support Email:** support@hitechavl.com
- **Documentation:** Wiki and API docs
- **Emergency Contact:** +91-XXXXXXXXXX

## Conclusion

The migration from MongoDB to Supabase PostgreSQL will:

1. **Improve Performance:** PostgreSQL is optimized for structured data
2. **Enhance Reliability:** Better transaction support and ACID compliance
3. **Simplify Operations:** Easier backup, recovery, and monitoring
4. **Future-Proof:** Better support for complex queries and analytics

The migration process follows a phased approach to minimize risk and ensure data integrity. All existing functionality will be preserved while improving the underlying database infrastructure.

---

**Next Steps:**
1. Set up Supabase credentials in `.env` file
2. Run the migration script: `python backend/manual_migrate_to_supabase.py`
3. Update backend code to use the database adapter
4. Test all API endpoints
5. Deploy to production