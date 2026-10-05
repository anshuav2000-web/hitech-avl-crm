# Supabase Database Connection Details for Hitech AVL CRM

This document contains the connection details for the Supabase PostgreSQL database.

### Connection String (Primary)
```
postgresql://postgres:Hitechavl@2026@db.rguvwnfocohsuejjtyed.supabase.co:5432/postgres
```

### Individual Connection Parameters
- **Host:** db.rguvwnfocohsuejjtyed.supabase.co
- **Port:** 5432
- **Database:** postgres
- **Username:** postgres
- **Password:** Hitechavl@2026

### Alternative Connection (Using Supabase URL)
```
SUPABASE_URL=https://rguvwnfocohsuejjtyed.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJndXZ3bmZvY29oc3VjamV0eWVkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MTIwNDc4NCwiZXhwIjoyMTA2NzgwNzg0fQ.m3RDNjM3q6jxRXge9cqyQVEoZURzHf6mlI3_EDSSA2A
```

## Coolify Deployment Instructions

### Step 1: Configure Environment Variables in Coolify

Go to your Coolify application and set the following environment variables:

#### Supabase Connection (Choose One):

**Option A: Using Supabase URL and Key**
```
SUPABASE_URL=https://rguvwnfocohsuejjtyed.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJndXZ3bmZvY29oc3VjamV0eWVkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MTIwNDc4NCwiZXhwIjoyMTA2NzgwNzg0fQ.m3RDNjM3q6jxRXge9cqyQVEoZURzHf6mlI3_EDSSA2A
```

**Option B: Using Direct PostgreSQL Connection**
```
DATABASE_URL=postgresql://postgres:Hitechavl@2026@db.rguvwnfocohsuejjtyed.supabase.co:5432/postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Hitechavl@2026
DB_NAME=hitech_crm
```

#### Common Environment Variables:
```
JWT_SECRET=your_secure_jwt_secret_here
ADMIN_EMAIL=admin@hitechaudio.in
ADMIN_PASSWORD=Admin@123
CORS_ORIGINS=https://your-frontend-domain.com
SMTP_HOST=smtppro.zoho.in
SMTP_PORT=587
SMTP_USER=anchit@hitechavl.com
SMTP_PASSWORD=6jnxECXxRJwh
SMTP_SENDER=anchit@hitechavl.com
SMTP_SENDER_NAME=Anchit Verma
GENERATED_EMAIL_DOMAIN=hitechavl.com
TZ=Asia/Kolkata
```

### Step 2: Database Migration

After deploying to Coolify, execute the Supabase schema:

```bash
# Connect to Supabase PostgreSQL and execute schema:
psql 'postgresql://postgres:Hitechavl@2026@db.rguvwnfocohsuejjtyed.supabase.co:5432/postgres' < backend/supabase_schema.sql
```

### Step 3: Import Data

```bash
# Import data using the migration script:
python backend/manual_migrate_to_supabase.py
```

### Step 4: Application Startup

```bash
# Start the application in Coolify
# The application will automatically start after deployment
```

## Docker Compose Deployment

If you're using Docker Compose, create/update `.env` file:

```bash
cat > .env << EOF
SUPABASE_URL=https://rguvwnfocohsuejjtyed.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJndXZ3bmZvY29oc3VjamV0eWVkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MTIwNDc4NCwiZXhwIjoyMTA2NzgwNzg0fQ.m3RDNjM3q6jxRXge9cqyQVEoZURzHf6mlI3_EDSSA2A
DATABASE_URL=postgresql://postgres:Hitechavl@2026@db.rguvwnfocohsuejjtyed.supabase.co:5432/postgres
EOF
```

Then run:
```bash
docker-compose up -d
```

## Health Check

After deployment, you can check the application health:

```bash
# Check if the application is running
curl http://localhost:8000/health
```

Or use the PostgreSQL connection to verify database connectivity:

```bash
psql 'postgresql://postgres:Hitechavl@2026@db.rguvwnfocohsuejjtyed.supabase.co:5432/postgres' -c "SELECT 1"
```

## Troubleshooting

### Common Issues:

1. **Connection Failed**
   - Verify credentials are correct
   - Check if Supabase PostgreSQL is running
   - Ensure network connectivity

2. **Migration Script Failed**
   - Check if Supabase schema is executed
   - Verify backup files exist
   - Check file permissions

3. **Application Not Starting**
   - Check environment variables
   - Verify database connection
   - Check logs for error messages

### Environment Variable Validation:
```bash
# Test Supabase connection
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:Hitechavl@2026@db.rguvwnfocohsuejjtyed.supabase.co:5432/postgres')
print('✅ Supabase connection successful')
conn.close()
"
```

## Support

For issues with Supabase deployment:
1. **Database Issues:** Check Supabase dashboard
2. **Connection Issues:** Verify credentials
3. **Migration Issues:** Check backup files
4. **Application Issues:** Check application logs

## Next Steps

1. **Deploy to Coolify** with the environment variables above
2. **Execute Supabase schema** using the SQL file
3. **Import data** using the migration script
4. **Test application** functionality
5. **Monitor system** after deployment

---

**Note:** The migration scripts and documentation are available in the GitHub repository. The database connection details provided are for your Supabase PostgreSQL instance.

**Status:** 🔧 **Deployment Preparation Complete** - Ready for Coolify deployment with Supabase PostgreSQL connection

---
EOF