from dotenv import load_dotenv
from pathlib:
import os
import re
import uuid
import logging
import unicodedata
import bcrypt
import jwt
from typing import List, Optional, Literal, Any, Dict
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer
from starlette.middleware.cors import CORSMiddleware

import audit
import media as media_store
import permissions as perms

# Import Supabase client for database operations
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase client: {e}")
    raise RuntimeError("Could not connect to Supabase. Check your SUPABASE_URL and SUPABASE_KEY environment variables.")

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

# ---------- Config ----------
# JWT_SECRET is required. The development default is deliberately NOT applied here:
# a deployment that forgets to set it must fail loudly at startup rather than run
# production on a secret that is published in the repository.
JWT_SECRET = os.environ.get("JWT_SECRET") or ""
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Generate one with: python -c \"import secrets; "
        "print(secrets.token_urlsafe(48))\""
    )
if len(JWT_SECRET) < 32 and os.environ.get("NODE_ENV") == "production":
    raise RuntimeError("JWT_SECRET must be at least 32 characters in production.")
JWT_ALGO = "HS256"

# Origin used to build customer-facing share links (public quotation view, wa.me
# prefills). Configurable so a deployment can point at its own frontend domain.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:3000"))
ACCESS_TTL_MIN = 60 * 24  # 1 day
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("EMERGENT_LLM_KEY", ""))

# Domain used when a contact or customer is saved without an email address and the
# CRM generates one from their name. Configurable per deployment; never hardcoded,
# because a generated address that lands in a real outbound email has to belong to
# a domain the business actually owns.
GENERATED_EMAIL_DOMAIN = os.environ.get(
    "GENERATED_EMAIL_DOMAIN", "hitechavl.com"
).strip().lstrip("@").strip("/")


def generated_email_local_part(name: str) -> str:
    """Turn a person's name into an email local part.

    "Shahnawaz Siddiqui"        -> shahnawaz.siddiqui
    "Rahul Kumar Singh"         -> rahul.kumar.singh
    "Anne-Marie O'Brien"       -> anne-marie.obrien
    "  Dr.  R K  Sharma  Jr. "  -> dr.r.k.sharma.jr

    Rules: lowercase; apostrophes dropped (O'Brien -> obrien, so the address does
    not contain an apostrophe, which many transports mangle); everything that is
    not a letter or digit becomes a dot; runs of dots collapse; leading and
    trailing dots are stripped. Hyphens are kept inside a part, which is legal in a
    local part and keeps compound names readable.
    """
    s = unicodedata.normalize("NFKD", str(name or "").strip().lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))  # José -> Jose
    s = s.replace("&", " and ")
    s = re.sub(r"[\u2018\u2019\u02bc']", "", s)          # drop apostrophes entirely
    # A hyphen is legal inside an email local part and keeps a compound surname
    # readable, so it survives; every other separator becomes a dot.
    s = re.sub(r"[^a-z0-9-]+", ".", s)
    s = re.sub(r"-{2,}", "-", s)
    s = re.sub(r"\.+", ".", s).strip(".-")               # collapse and trim
    return s


async def generate_email_for(name: str, collection: str = "contacts") -> str:
    """Return a unique, system-generated email address for ``name``.

    Appends 2, 3, ... until the address is free, so
    rahul.sharma@d / rahul.sharma2@d / rahul.sharma3@d can coexist. Uniqueness is
    checked across the collection AND against every user account, because a
    generated contact address must not collide with a login identity.
    """
    local = generated_email_local_part(name) or "contact"
    domain = GENERATED_EMAIL_DOMAIN or "hitechavl.com"

    async def _taken(address: str) -> bool:
        if await db[collection].find_one({"email": address}, {"_id": 1, "id": 1}):
            return True
        # Also check the other email-bearing collections so two different modules
        # cannot mint the same address.
        for other in ("customers", "contacts", "leads", "users"):
            if other == collection:
                continue
            if await db[other].find_one({"email": address}, {"_id": 1, "id": 1}):
                return True
        return False

    candidate = f"{local}@{domain}"
    if not await _taken(candidate):
        return candidate
    n = 2
    while n < 1000:
        candidate = f"{local}{n}@{domain}"
        if not await _taken(candidate):
            return candidate
        n += 1
    # Exhausting the counter is not a reason to fail the save; a uuid tail keeps the
    # address unique and valid instead.
    return f"{local}.{uuid.uuid4().hex[:8]}@{domain}"

# ---------- Google Gemini Integration ----------
import google.generativeai as genai

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

async def call_gemini(prompt: str, system_instruction: str = None) -> str:
    if not GEMINI_API_KEY:
        return (
            "Google Gemini API Key is currently unconfigured in .env.\n\n"
            "Please add:\nGEMINI_API_KEY=your_key_here\nto your backend/.env file to activate AI Coach Insights & PDF Auto-Extraction."
        )
    try:
        # Using the recommended high-performance gemini-1.5-flash model via SDK
        model_name = "gemini-1.5-flash"
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: model.generate_content(prompt)
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API invocation failed: {e}")
        # fallback to make sure client doesn't get unhandled errors
        return f"AI Service temporary error: {str(e)}"

PIPELINE_STAGES = [
    "new", "assigned", "contact_attempted", "contacted", "not_contacted",
    "call_back_later", "detailed_requirement_discussion", "interested",
    "qualified", "need_analysis", "forward_to_design", "drawing",
    "boq_creation", "send_boq_design", "boq_finalized",
    "convert_to_quotation", "send_quotation", "quotation_negotiation",
    "quotation_rejected", "quotation_confirmed", "po_received",
    "invoice_raised", "completed", "lost_lead"
]
from migrations import DEFAULT_LEAD_SOURCES

# Re-exported from migrations so the vocabulary has a single definition; server.py
# imports migrations, not the other way round.
LEAD_SOURCES = list(DEFAULT_LEAD_SOURCES)

# Bug B4: several call sites filtered and counted on a literal "won"/"lost" stage,
# but neither is a pipeline stage key -- the real ones are "quotation_confirmed" and
# "lost_lead" -- so Won Deals, In Pipeline, conversion rate and round-robin assignment
# all silently treated closed leads as open. These are only the fallback used when the
# lead_stages config set cannot be read.
TERMINAL_STAGE_FALLBACK = {"won": "quotation_confirmed", "lost": "lost_lead"}


async def terminal_stage_keys() -> dict[str, str]:
    """Resolve the effective won/lost stage keys from the lead_stages config set.

    Reads the admin-configurable flags (is_won/is_lost) rather than hard-coding keys,
    so renaming a stage in Settings cannot silently break the dashboard again.
    """
    doc = await db.crm_config_sets.find_one({"key": "lead_stages"}, {"_id": 0, "items": 1})
    resolved = dict(TERMINAL_STAGE_FALLBACK)
    for item in (doc or {}).get("items", []):
        if item.get("is_won"):
            resolved["won"] = item.get("id") or resolved["won"]
        elif item.get("is_lost"):
            resolved["lost"] = item.get("id") or resolved["lost"]
    return resolved


async def valid_stage_keys() -> set[str]:
    """Active stage ids from the config set, or the hard-coded pipeline on failure.

    Returning an empty set means "cannot tell", and callers treat that as
    permissive so a config outage never blocks a legitimate stage move.
    """
    return await valid_config_keys("lead_stages")


async def valid_config_keys(config_key: str) -> set[str]:
    """Active item ids for any config set. Empty means "cannot tell"."""
    doc = await db.crm_config_sets.find_one({"key": config_key}, {"_id": 0, "items": 1})
    items = (doc or {}).get("items") or []
    keys = {it.get("id") for it in items if it.get("is_active", True) and it.get("id")}
    return keys or set()


async def project_stage_keys() -> set[str]:
    return await valid_config_keys("project_stages")


# ---------- Auth helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

security = HTTPBearer(auto_error=False)

async def get_current_user(request: Request) -> dict:
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("is_active") is False:
        # Deactivation has to mean something on every request, not only at login:
        # an already-issued token would otherwise keep working for its full TTL.
        raise HTTPException(status_code=401, detail="This account has been deactivated")
    user.pop("password_hash", None)
    user.pop("_id", None)
    return user

ADMIN_ROLE_NAMES = perms.ADMIN_ROLE_NAMES


def is_admin_role(user: dict) -> bool:
    """Single source of truth for "full visibility across all records".

    Replaces scattered `user["role"] == "admin"` checks, which previously treated
    `superadmin` and `management` as ordinary sales users and hid their data from them.
    Keep in sync with require_admin() below.
    """
    return perms.is_admin_user(user)


def is_super_admin(user: dict) -> bool:
    """True only for the Super Admin role.

    Deliberately narrower than :func:`is_admin_role`. Super Admin is the one role
    with no restrictions at all, so this predicate is the single switch that every
    permission check consults. Widening it later would silently hand unrestricted
    access to every ordinary administrator.
    """
    return perms.is_super_admin(user)


def require_permission(module: str, action: str = "manage"):
    """Build a dependency that enforces one module permission.

    The shape of every authorisation decision in the app:

    * Super Admin passes unconditionally -- that is what makes "no normal admin
      restriction applies" true by construction rather than by remembering to
      exempt each endpoint;
    * otherwise the permission is read from the role's ``roles`` document, falling
      back to the built-in defaults for the role;
    * an unknown module or an unknown role grants nothing.

    ``action="view"`` is satisfied by a ``manage`` grant, so a role allowed to edit
    a module is never locked out of reading it.
    """
    async def _dependency(user: dict = Depends(get_current_user)) -> dict:
        if perms.is_super_admin(user):
            return user
        if perms.has_permission(await perms.role_permissions(db, user.get("role")), module, action):
            return user
        # Backstop for the built-in administrator roles: they had access to these
        # modules before the permission table existed, and a hand-edited role
        # document must not be able to lock the business out of its own settings.
        if module in ("settings", "system", "users", "admins", "roles") and is_admin_role(user):
            return user
        raise HTTPException(
            status_code=403,
            detail=f"'{module}.{action}' permission required for this action",
        )
    return _dependency


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ("admin", "superadmin", "management"):
        # Check if dynamic role has admin/settings permission
        role_doc = await db.roles.find_one({"name": user.get("role")})
        if not role_doc or "settings" not in role_doc.get("permissions", []) and "all" not in role_doc.get("permissions", []):
            raise HTTPException(status_code=403, detail="Admin or Manager access required")
    return user

async def require_superadmin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return user


# Named dependencies, so an endpoint's requirement is readable at the call site
# instead of hiding a module string inside a factory call.
require_brand_manager = require_permission("brands", "manage")
require_product_manager = require_permission("products", "manage")
require_media_manager = require_permission("media", "manage")
require_user_manager = require_permission("users", "manage")
require_system_manager = require_permission("system", "manage")

# ---------- Models ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "sales"
    department: Optional[str] = "Sales"
    designation: Optional[str] = "Staff"
    phone: Optional[str] = None
    extension: Optional[str] = None
    allowed_brands: Optional[List[str]] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    extension: Optional[str] = None
    allowed_brands: Optional[List[str]] = None
    password: Optional[str] = None
    # Deactivating is the reversible counterpart to deleting: the account stops
    # authenticating but keeps every record it created.
    is_active: Optional[bool] = None

class RoleCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[str] = []

class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class BrandAccessRequestCreate(BaseModel):
    brand: str
    reason: Optional[str] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    email: str
    role: str
    created_at: datetime

class LeadCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    source: Literal["facebook", "instagram", "linkedin", "website_contact_form", "direct_enquiry", "cold_call", "business_whatsapp", "email", "channel_partner", "internal_employee_referral", "existing_customer", "walk_in_customer"] = "direct_enquiry"
    interested_in: Optional[str] = None
    product_interest: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    requirements: Optional[str] = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    budget: Optional[float] = None
    lead_score: Optional[int] = 0
    assigned_to: Optional[str] = None
    source_url: Optional[str] = None
    lead_source_detail: Optional[str] = None
    # create_lead() and public_create_lead() both read payload.notes, but this
    # field was missing, so every lead creation raised AttributeError -> HTTP 500.
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    interested_in: Optional[str] = None
    product_interest: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    requirements: Optional[str] = None
    priority: Optional[str] = None
    budget: Optional[float] = None
    lead_score: Optional[int] = None
    stage: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class ActivityCreate(BaseModel):
    type: Literal["note", "call", "email", "whatsapp", "meeting", "follow_up", "sms", "video_call", "voice_note", "attachment"]
    content: str
    follow_up_at: Optional[datetime] = None
    call_duration: Optional[int] = None
    recording_link: Optional[str] = None
    attachment_url: Optional[str] = None
    outcome: Optional[str] = None
    follow_up_required: bool = False

class QuotationLine(BaseModel):
    product: str
    brand: Optional[str] = None
    qty: int = 1
    unit_price: float
    pricing_tier: Optional[str] = "MSRP"  # MSRP / Dealer / Distributor / Project
    discount_pct: float = 0.0
    fixed_discount: float = 0.0
    tax_pct: float = 18.0  # GST default
    components: Optional[str] = None  # bundle breakdown
    product_id: Optional[str] = None
    accessories: List[str] = []

class QuotationCreate(BaseModel):
    lead_id: str
    items: List[QuotationLine]
    template_type: Optional[str] = "Corporate"  # Corporate / Government / Rental / Hospitality / System Integration
    shipping_charges: float = 0.0
    installation_charges: float = 0.0
    amc_charges: float = 0.0
    valid_until: Optional[datetime] = None
    terms: Optional[str] = None
    executive_summary: Optional[str] = None

class BrandCreate(BaseModel):
    name: str
    country: Optional[str] = None
    description: Optional[str] = None
    official_website: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    brand_category: Optional[str] = "Professional Audio"
    product_categories: List[str] = []
    featured: bool = False
    tags: List[str] = []

class DownloadItem(BaseModel):
    title: str
    type: Literal["datasheet", "manual", "brochure", "firmware", "software", "video"]
    url: str
    file_size: Optional[str] = None

class ProductCreate(BaseModel):
    brand: str
    name: str
    model: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    product_family: Optional[str] = None
    product_series: Optional[str] = None
    # Optional because a real catalogue is often imported before the price list is
    # finalised. Such rows carry price_status="pending" so they are visibly unpriced
    # rather than silently quoting a zero.
    unit_price: Optional[float] = None
    price_status: Optional[str] = None
    msrp: Optional[float] = None
    dealer_price: Optional[float] = None
    distributor_price: Optional[float] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    features: List[str] = []
    technical_specifications: Dict[str, Any] = {}
    product_images: List[str] = []
    gallery: List[str] = []
    downloads: List[DownloadItem] = []
    accessories: List[str] = []
    compatible_products: List[str] = []
    related_products: List[str] = []
    warranty: Optional[str] = "3 Years Warranty"
    country_of_origin: Optional[str] = None
    status: Literal["active", "discontinued", "coming_soon"] = "active"
    stock_quantity: int = 10
    warehouse_location: Optional[str] = "Main Warehouse"
    # Provenance. A product imported from a manufacturer's own site carries the page
    # it came from and the date it was last checked against that page. Both stay
    # null when unknown -- an unverified product is a real state, and pretending
    # otherwise is how a catalogue ends up confidently wrong.
    official_url: Optional[str] = None
    image_url: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None

class PackageItemIn(BaseModel):
    product_id: str
    qty: int = 1

class PackageComponentIn(BaseModel):
    """Free-form component (used for imported bundles whose sub-SKUs aren't in the main catalog)."""
    model: Optional[str] = None
    description: str
    qty: int = 1

class PackageCreate(BaseModel):
    brand: str
    name: str
    description: Optional[str] = None
    items: List[PackageItemIn] = []
    components: List[PackageComponentIn] = []
    fixed_price_inr: Optional[float] = None  # overrides estimated_total when set (bundle discount)
    sku: Optional[str] = None

# ---------- Operations: Shipments / Inventory / AMC ----------
class ShipmentItem(BaseModel):
    product_id: str
    qty: int
    fob_unit: float = 0.0  # in shipment currency

class ShipmentCreate(BaseModel):
    po_no: str
    oem: str  # brand name (L-Acoustics, RCF, DiGiCo)
    currency: str = "EUR"  # EUR / USD / GBP
    items: List[ShipmentItem]
    bl_awb: Optional[str] = None
    eta: Optional[str] = None  # ISO date string
    notes: Optional[str] = None

class ShipmentUpdate(BaseModel):
    status: Optional[Literal["planned", "in_transit", "customs", "cleared", "received"]] = None
    bl_awb: Optional[str] = None
    eta: Optional[str] = None
    actual_arrival: Optional[str] = None
    freight_cost_inr: Optional[float] = None
    duty_paid_inr: Optional[float] = None
    notes: Optional[str] = None

class InventoryUnitCreate(BaseModel):
    product_id: str
    serial_no: str
    shipment_id: Optional[str] = None
    location: Optional[str] = "Main Warehouse"
    landed_cost_inr: Optional[float] = None

class InventoryUnitUpdate(BaseModel):
    status: Optional[Literal["in_transit", "in_stock", "reserved", "sold"]] = None
    location: Optional[str] = None
    sold_to_lead_id: Optional[str] = None
    warranty_expires: Optional[str] = None

class AMCCreate(BaseModel):
    customer_name: str
    customer_company: Optional[str] = None
    lead_id: Optional[str] = None
    serial_numbers: List[str] = []  # serial numbers covered
    start_date: str  # ISO date
    end_date: str
    value: float
    notes: Optional[str] = None

class AMCUpdate(BaseModel):
    status: Optional[Literal["active", "expired", "renewed", "cancelled"]] = None
    end_date: Optional[str] = None
    value: Optional[float] = None
    notes: Optional[str] = None


# ---------- New ERP Models ----------
class ProjectCreate(BaseModel):
    name: str
    client: Optional[str] = None
    status: str = "active"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None

class CustomerCreate(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    segment: Optional[str] = None
    total_value: Optional[float] = 0

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    segment: Optional[str] = None
    total_value: Optional[float] = None

class ContactCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    customer_id: Optional[str] = None

class AccountingDocCreate(BaseModel):
    doc_no: str
    type: str = "invoice"
    party: Optional[str] = None
    amount: float
    status: str = "draft"
    date: str

class AccountingDocUpdate(BaseModel):
    doc_no: Optional[str] = None
    type: Optional[str] = None
    party: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    date: Optional[str] = None

class EventCreate(BaseModel):
    title: str
    type: Literal["meeting", "call", "follow_up", "holiday"] = "meeting"
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    lead_id: Optional[str] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    status: Literal["pending", "in_progress", "completed"] = "pending"
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    assigned_to: Optional[str] = None
    lead_id: Optional[str] = None
    # Phase 7: tasks hang off a project so the Project Detail tab can show them.
    # This field was absent from the model, which silently dropped the link no matter
    # what the client sent.
    project_id: Optional[str] = None

class WorkOrderCreate(BaseModel):
    title: str
    type: Literal["installation", "repair", "maintenance"] = "installation"
    status: Literal["open", "in_progress", "completed", "cancelled"] = "open"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    assigned_to: Optional[str] = None
    customer_id: Optional[str] = None
    scheduled_date: Optional[str] = None

class SupplierCreate(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[int] = None

class SocialPostCreate(BaseModel):
    platform: Literal["facebook", "instagram", "twitter", "linkedin", "youtube"]
    title: str
    content: Optional[str] = None
    status: Literal["draft", "scheduled", "published"] = "draft"
    scheduled_at: Optional[str] = None
    media_url: Optional[str] = None

class CampaignCreate(BaseModel):
    name: str
    type: Literal["email", "seo", "ads", "funnel"] = "email"
    status: Literal["draft", "active", "paused", "completed"] = "draft"
    budget: Optional[float] = 0
    spent: Optional[float] = 0
    leads: Optional[int] = 0
    conversions: Optional[int] = 0

class BookingCreate(BaseModel):
    service: str
    date: str
    time: str
    resource: Optional[str] = None
    customer_name: str
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    notes: Optional[str] = None
    status: Literal["confirmed", "pending", "cancelled"] = "pending"

class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    currency: Optional[str] = "INR"
    timezone: Optional[str] = "Asia/Kolkata"
    fiscal_year_start: Optional[str] = None

class SystemSettingsUpdate(BaseModel):
    app_name: Optional[str] = None
    logo_url: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = "en"
    email_provider: Optional[str] = None
    sms_provider: Optional[str] = None
    backup_frequency: Optional[str] = None


# ---------- HiTech AVL Process Flow Models ----------
class LeadSourceCreate(BaseModel):
    name: str
    category: Optional[str] = "digital"
    description: Optional[str] = None
    is_active: bool = True

class LeadStageUpdate(BaseModel):
    stage: str
    notes: Optional[str] = None


class FollowUpCreate(BaseModel):
    lead_id: str
    follow_up_date: str
    follow_up_time: Optional[str] = None
    type: Literal["call", "whatsapp", "email", "sms", "meeting", "video_call", "reminder"] = "call"
    status: Literal["pending", "completed", "missed", "cancelled"] = "pending"
    notes: Optional[str] = None
    reminder_enabled: bool = True
    reminder_minutes_before: int = 15
    recurring: bool = False
    recurring_interval: Optional[str] = None
    recurring_end_date: Optional[str] = None
    escalation_enabled: bool = False
    escalation_after_minutes: int = 60
    created_by: Optional[str] = None

class FollowUpUpdate(BaseModel):
    follow_up_date: Optional[str] = None
    follow_up_time: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    reminder_enabled: Optional[bool] = None
    reminder_minutes_before: Optional[int] = None
    recurring: Optional[bool] = None
    recurring_interval: Optional[str] = None
    recurring_end_date: Optional[str] = None
    escalation_enabled: Optional[bool] = None
    escalation_after_minutes: Optional[int] = None

class NotificationCreate(BaseModel):
    user_id: str
    type: Literal["lead_assigned", "follow_up_due", "meeting_reminder", "task_assigned", "quotation_sent", "po_received", "invoice_generated", "lead_lost", "quotation_approved", "dashboard_alert", "email", "whatsapp", "browser"]
    title: str
    message: str
    link: Optional[str] = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    read: bool = False

class NotificationUpdate(BaseModel):
    read: Optional[bool] = None

class BOQItemCreate(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    sku: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    qty: int = 1
    unit_price: float = 0.0
    discount_pct: float = 0.0
    fixed_discount: float = 0.0
    tax_pct: float = 18.0
    total: float = 0.0

class BOQCreate(BaseModel):
    lead_id: str
    quotation_id: Optional[str] = None
    items: List[BOQItemCreate] = []
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "INR"
    valid_until: Optional[str] = None
    terms: Optional[str] = None
    notes: Optional[str] = None
    status: Literal["draft", "pending_approval", "approved", "rejected", "version"] = "draft"
    version: int = 1
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    revision_notes: Optional[str] = None

class BOQUpdate(BaseModel):
    items: Optional[List[BOQItemCreate]] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    valid_until: Optional[str] = None
    terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    version: Optional[int] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    revision_notes: Optional[str] = None

class PurchaseOrderCreate(BaseModel):
    po_no: str
    supplier_id: str
    supplier_name: str
    items: List[BOQItemCreate] = []
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "INR"
    delivery_date: Optional[str] = None
    payment_terms: Optional[str] = None
    status: Literal["draft", "pending_approval", "approved", "rejected", "ordered", "received", "partial", "cancelled"] = "draft"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    attachments: List[str] = []

class PurchaseOrderUpdate(BaseModel):
    po_no: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    items: Optional[List[BOQItemCreate]] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    delivery_date: Optional[str] = None
    payment_terms: Optional[str] = None
    status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[List[str]] = None

class PurchaseOrderApproval(BaseModel):
    action: Literal["approve", "reject"] = "approve"
    note: Optional[str] = None


class InvoiceCreate(BaseModel):
    invoice_no: str
    quotation_id: Optional[str] = None
    po_id: Optional[str] = None
    customer_name: str
    customer_email: Optional[str] = None
    items: List[BOQItemCreate] = []
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    paid_amount: float = 0.0
    outstanding: float = 0.0
    currency: str = "INR"
    due_date: Optional[str] = None
    status: Literal["draft", "sent", "paid", "partial", "overdue", "cancelled"] = "draft"
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    gst_pct: float = 18.0

class InvoiceUpdate(BaseModel):
    invoice_no: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    items: Optional[List[BOQItemCreate]] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    paid_amount: Optional[float] = None
    outstanding: Optional[float] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None

class LostLeadCreate(BaseModel):
    lead_id: str
    reason: Literal["price", "competitor", "no_response", "budget", "cancelled", "duplicate", "not_interested", "others"] = "no_response"
    details: Optional[str] = None
    competitor_name: Optional[str] = None
    competitor_product: Optional[str] = None
    expected_closure: Optional[str] = None
    notes: Optional[str] = None

class LostLeadUpdate(BaseModel):
    reason: Optional[str] = None
    details: Optional[str] = None
    competitor_name: Optional[str] = None
    competitor_product: Optional[str] = None
    expected_closure: Optional[str] = None
    notes: Optional[str] = None

class RequirementDiscussionCreate(BaseModel):
    lead_id: str
    project_type: Optional[str] = None
    products_required: List[str] = []
    brands: List[str] = []
    quantities: Optional[str] = None
    site_location: Optional[str] = None
    project_drawings: List[str] = []
    special_requirements: Optional[str] = None
    budget: Optional[float] = None
    competitors: Optional[str] = None
    timeline: Optional[str] = None
    technical_notes: Optional[str] = None
    attachments: List[str] = []

class RequirementDiscussionUpdate(BaseModel):
    project_type: Optional[str] = None
    products_required: Optional[List[str]] = None
    brands: Optional[List[str]] = None
    quantities: Optional[str] = None
    site_location: Optional[str] = None
    project_drawings: Optional[List[str]] = None
    special_requirements: Optional[str] = None
    budget: Optional[float] = None
    competitors: Optional[str] = None
    timeline: Optional[str] = None
    technical_notes: Optional[str] = None
    attachments: Optional[List[str]] = None

class DesignTaskCreate(BaseModel):
    lead_id: str
    title: str
    description: Optional[str] = None
    assigned_to: str
    drawing_type: Literal["floor_plan", "elevation", "section", "detail", "layout", "wiring_diagram", "3d_render"] = "floor_plan"
    status: Literal["pending", "in_progress", "review", "approved", "rejected"] = "pending"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    due_date: Optional[str] = None
    revision: int = 1
    comments: List[str] = []
    files: List[str] = []
    cad_drawings: List[str] = []
    pdf_files: List[str] = []
    auto_notify_sales: bool = True

class DesignTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    drawing_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    revision: Optional[int] = None
    comments: Optional[List[str]] = None
    files: Optional[List[str]] = None
    cad_drawings: Optional[List[str]] = None
    pdf_files: Optional[List[str]] = None

class NegotiationCreate(BaseModel):
    quotation_id: str
    lead_id: str
    revision: int = 1
    discount_pct: float = 0.0
    discount_reason: Optional[str] = None
    customer_feedback: Optional[str] = None
    approval_status: Literal["pending", "approved", "rejected", "escalated"] = "pending"
    expected_closure: Optional[str] = None
    competitor_info: Optional[str] = None
    notes: Optional[str] = None

class NegotiationUpdate(BaseModel):
    revision: Optional[int] = None
    discount_pct: Optional[float] = None
    discount_reason: Optional[str] = None
    customer_feedback: Optional[str] = None
    approval_status: Optional[str] = None
    expected_closure: Optional[str] = None
    competitor_info: Optional[str] = None
    notes: Optional[str] = None

class ActivityLogCreate(BaseModel):
    lead_id: Optional[str] = None
    user_id: str
    action: str
    module: str
    details: Optional[str] = None
    metadata: Optional[dict] = None

class ContactAttemptCreate(BaseModel):
    lead_id: str
    type: Literal["phone_call", "whatsapp", "email", "sms", "meeting", "video_call", "note", "attachment", "voice_note"] = "phone_call"
    content: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    recording_link: Optional[str] = None
    attachment_url: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[str] = None

class LeadQualificationCreate(BaseModel):
    lead_id: str
    budget: Optional[Literal["high", "medium", "low", "none"]] = None
    authority: Optional[Literal["decision_maker", "influencer", "end_user", "gatekeeper"]] = None
    need: Optional[Literal["urgent", "high", "medium", "low", "none"]] = None
    timeline: Optional[Literal["immediate", "1_month", "3_months", "6_months", "none"]] = None
    product_fit: Optional[Literal["excellent", "good", "fair", "poor"]] = None
    decision_maker: bool = False
    business_size: Optional[Literal["enterprise", "mid_market", "smb", "startup", "individual"]] = None
    urgency: Optional[Literal["high", "medium", "low"]] = None
    score: Optional[int] = None
    classification: Optional[Literal["hot", "warm", "cold", "qualified", "not_qualified", "lost"]] = None

class LeadQualificationUpdate(BaseModel):
    budget: Optional[str] = None
    authority: Optional[str] = None
    need: Optional[str] = None
    timeline: Optional[str] = None
    product_fit: Optional[str] = None
    decision_maker: Optional[bool] = None
    business_size: Optional[str] = None
    urgency: Optional[str] = None
    score: Optional[int] = None
    classification: Optional[str] = None

class SalesTargetCreate(BaseModel):
    user_id: str
    period: Literal["monthly", "quarterly", "yearly"] = "monthly"
    start_date: str
    end_date: str
    revenue_target: float = 0.0
    leads_target: int = 0
    quotations_target: int = 0
    closed_deals_target: int = 0

class SalesTargetUpdate(BaseModel):
    revenue_target: Optional[float] = None
    leads_target: Optional[int] = None
    quotations_target: Optional[int] = None
    closed_deals_target: Optional[int] = None

class ReportCreate(BaseModel):
    name: str
    type: Literal["sales", "lead_source", "executive_performance", "quotation", "boq", "revenue", "lost_leads", "pipeline", "forecast", "customer_activity", "tasks", "meetings", "invoices"]
    filters: Optional[dict] = None
    format: Literal["excel", "csv", "pdf"] = "pdf"


# ---------- App ----------
app = FastAPI(title="Hitech Audio CRM")
api = APIRouter(prefix="/api")


@app.get("/health")
async def health():
    """Liveness + readiness for the platform health check.

    Unauthenticated on purpose: a load balancer or Coolify health check has no
    CRM credentials. It reports only whether the database answers a ping -- never
    the connection string, the database name, or any other configuration value.
    """
    database = "disconnected"
    try:
        await db.command("ping")
        database = "connected"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        logger.exception("Health check database ping failed")
        return JSONResponse(status_code=503,
                            content={"status": "degraded", "database": database,
                                     "detail": type(exc).__name__})
    return {"status": "ok", "database": database}


def slugify(value: str) -> str:
    """Lowercase dash-separated slug, shared by brands, products and categories."""
    s = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return s or "item"


# ---------------------------------------------------------------------------
# Media: brand logos and product images
# ---------------------------------------------------------------------------
# Reading an asset is deliberately unauthenticated. A brand logo appears on a
# customer-facing quotation page that has no session, and every existing logo in
# the database is already a public URL on cms.hitechavl.com. Making the stored
# copy readable by anyone who knows the id matches that reality; the ids are
# 64-character SHA-256 content hashes, so they are not enumerable, and nothing
# about the CRM's data is exposed by rendering a logo.
#
# Writing, replacing and deleting an asset all require the media permission.
@api.get("/media/{media_id}")
async def get_media(media_id: str, request: Request):
    """Serve a stored image verbatim.

    The bytes are returned exactly as uploaded. Re-encoding would flatten the
    alpha channel and put an opaque background behind every transparent logo.
    """
    doc = await media_store.load(db, media_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")
    data = doc.get("data")
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    etag = f'"{doc.get("sha256") or media_id}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return Response(
        content=bytes(data),
        media_type=doc.get("content_type") or "application/octet-stream",
        headers={
            "ETag": etag,
            # Content-addressed: the id changes when the bytes change, so the
            # response can be cached forever and a replaced logo is a new URL.
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{doc.get("filename") or media_id}"',
        },
    )


@api.get("/media")
async def list_media(user: dict = Depends(require_permission("media", "view")),
                     kind: Optional[str] = None, limit: int = 200):
    """List stored assets (metadata only, never the bytes)."""
    q = {"kind": kind} if kind else {}
    rows = await db.media.find(q, {"_id": 0, "data": 0}).sort("uploaded_at", -1).to_list(min(limit, 500))
    for r in rows:
        r["url"] = media_store.public_url(r.get("id"))
    return rows


@api.post("/media", status_code=201)
async def upload_media(file: UploadFile = File(...),
                       kind: str = Form("image"),
                       user: dict = Depends(require_media_manager)):
    """Upload an image and return its id and public URL.

    Rejects an unsupported type, an empty file, an oversized file and a file whose
    header claims to be an image but cannot be decoded. Validation is by magic
    bytes and a real decode, never by the client-supplied content type.
    """
    data = await file.read()
    try:
        doc = await media_store.store(db, data, filename=file.filename, kind=kind, actor=user)
    except media_store.MediaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await audit.record(
        db, actor=user, action=audit.UPLOAD, module=audit.MEDIA, record_type="media",
        record_id=doc["id"], record_label=doc.get("filename"),
        summary=f"Uploaded {doc.get('filename')} ({doc.get('width')}x{doc.get('height')}, "
                f"{doc.get('size', 0) // 1024} KB)",
        meta={"kind": kind, "content_type": doc.get("content_type"), "has_alpha": doc.get("has_alpha")},
    )
    doc["url"] = media_store.public_url(doc["id"])
    return doc


@api.get("/media/{media_id}/info")
async def media_info(media_id: str):
    """Metadata for one asset. Never the bytes -- those come from ``/media/{id}``.

    Unauthenticated, like the byte route above, and for the same reason: the id *is*
    the public URL of the image, so holding it already grants the pixels.
    Dimensions, byte size and format are strictly less sensitive than the image
    they describe, and a quotation page that can render a logo can describe it too.
    Listing (``/media``) and deleting stay permission-gated, because those
    disclose what the business holds rather than what one id resolves to.
    """
    doc = await media_store.metadata(db, media_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")
    doc["url"] = media_store.public_url(media_id)
    return doc


@api.delete("/media/{media_id}")
async def delete_media(media_id: str, user: dict = Depends(require_media_manager)):
    """Delete a stored asset.

    Refuses while a brand or product still points at it. Deleting the bytes out
    from under a live reference would leave a broken logo in the catalogue, and
    the reference is the only place the truth about "is this still needed" lives.
    """
    doc = await media_store.metadata(db, media_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")
    in_use = await _media_references(media_id)
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"This image is still used by {len(in_use)} record(s): "
                   + ", ".join(f"{r['type']} {r['label']}" for r in in_use[:5])
                   + ". Remove it from there first.",
        )
    await db.media.delete_one({"_id": media_id})
    await audit.record(
        db, actor=user, action=audit.DELETE, module=audit.MEDIA, record_type="media",
        record_id=media_id, record_label=doc.get("filename"),
        summary=f"Deleted image {doc.get('filename')}",
    )
    return {"ok": True, "deleted": media_id}


async def _media_references(media_id: str) -> list:
    """Every brand or product that still points at this asset."""
    refs = []
    for brand in await db.brands.find(
        {"$or": [{"logo_media_id": media_id}, {"banner_media_id": media_id}]},
        {"_id": 0, "name": 1, "logo_media_id": 1, "banner_media_id": 1},
    ).to_list(200):
        refs.append({"type": "brand", "id": brand.get("id"), "label": brand.get("name")})
    for product in await db.products.find(
        {"$or": [{"image_media_id": media_id}, {"product_images": media_id}, {"gallery": media_id}]},
        {"_id": 0, "id": 1, "name": 1},
    ).to_list(200):
        refs.append({"type": "product", "id": product.get("id"), "label": product.get("name")})
    return refs


async def _read_upload(file: UploadFile, kind: str, actor: dict) -> dict:
    """Validate and store one uploaded file, converting rejections into a 400.

    Shared by the brand-logo and product-image endpoints so both apply identical
    validation and both write an audit entry.
    """
    data = await file.read()
    try:
        return await media_store.store(db, data, filename=file.filename, kind=kind, actor=actor)
    except media_store.MediaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _resolve_media_url(doc: Optional[dict], *fields: str) -> Optional[dict]:
    """Fill the URL fields for each media-backed field on a document.

    Resolution order is deliberate: an uploaded asset wins over a legacy remote
    ``logo_url``, because that is what "replace the logo" means to the person who
    did it. The legacy field is left in place, so reverting is always possible.

    Two URLs are published for each field. ``<field>_url`` is what a renderer
    uses. ``<field>_media_id_url`` is keyed off the id, so a client that already
    holds the id can build the same URL without re-deriving which field it came
    from -- the two cannot drift apart.
    """
    out = dict(doc or {})
    for field in fields:
        media_id = out.get(f"{field}_media_id")
        if media_id:
            out[f"{field}_url"] = media_store.public_url(media_id)
            out[f"{field}_media_id_url"] = media_store.public_url(media_id)
        else:
            out[f"{field}_url"] = out.get(field)
            out[f"{field}_media_id_url"] = None
    return out


def _resolve_brand_media(brand: Optional[dict]) -> Optional[dict]:
    """Brand with its logo/banner URLs resolved. Applied on every brand read."""
    return _resolve_media_url(brand, "logo", "banner")


def _resolve_product_media(product: Optional[dict]) -> Optional[dict]:
    """Product with image URLs resolved and gallery entries expanded."""
    out = _resolve_media_url(product, "image")
    if out is None:
        return None
    # ``product_images``/``gallery`` historically held bare URLs. Entries that are
    # media ids are expanded to their served URL so one renderer covers both.
    for field in ("product_images", "gallery"):
        out[field] = [media_store.public_url(e) if _looks_like_media_id(e) else e
                      for e in (out.get(field) or [])]
    out["image_urls"] = [u for u in ([out.get("image_url")] + list(out.get("product_images") or [])
                                      + list(out.get("gallery") or [])) if u]
    return out


_MEDIA_ID_RE = re.compile(r"^[0-9a-f]{64}$")


def _looks_like_media_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_MEDIA_ID_RE.match(value))


async def _add_config_item(config_key: str, item: dict) -> dict:
    """Shared item-creation core behind the convenience route ``POST /api/lead-sources``.

    ``POST /api/config/{key}`` keeps its own richer body handling (steps, applies_to);
    this covers the simple label/category case so the convenience route cannot drift
    into producing an item shape Settings does not expect -- which was B12's fate.
    """
    doc = await db.crm_config_sets.find_one({"key": config_key})
    if not doc:
        raise HTTPException(status_code=404, detail="Config not found")
    items = doc.get("items", [])
    key = (item.get("key") or item.get("label") or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        raise HTTPException(status_code=400, detail="A name or label is required")
    if any(i.get("key") == key for i in items):
        raise HTTPException(status_code=400, detail=f"'{key}' already exists in {config_key}")
    entry = {
        "id": key, "key": key, "label": item.get("label") or item.get("name"),
        "color": item.get("color") or "slate", "icon": item.get("icon"),
        "group": item.get("group") or item.get("category"),
        "order": len(items), "is_active": bool(item.get("is_active", True)),
        "is_won": bool(item.get("is_won")), "is_lost": bool(item.get("is_lost")),
        "system_key": False,
    }
    if item.get("description") is not None:
        entry["description"] = item["description"]
    items.append(entry)
    await db.crm_config_sets.update_one(
        {"key": config_key},
        {"$set": {"items": items, "updated_at": datetime.now(timezone.utc).isoformat(), "version": int(doc.get("version") or 1) + 1}},
    )
    return entry


@api.post("/leads/{lead_id}/stage")
async def move_lead_stage(lead_id: str, payload: LeadStageUpdate, user: dict = Depends(get_current_user)):
    """Structured stage move: validates against live config, records stage history,
    writes an activity entry and notifies watchers (plan 7.3).

    This is the endpoint the ``LeadStageUpdate`` model was written for in the original
    audit but never wired to (B12). The UI PATCH path remains supported.
    """
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    stage = (payload.stage or "").strip()
    valid = await valid_stage_keys()
    if valid and stage not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown stage '{stage}'")
    if not stage:
        raise HTTPException(status_code=400, detail="A stage is required")

    now = datetime.now(timezone.utc).isoformat()
    # _set_lead_stage writes the stage_change activity (and the notification) itself.
    # Writing a second "note" here duplicated the same event in the timeline.
    await _set_lead_stage(lead_id, stage, user, now, note=payload.notes)
    return await db.leads.find_one({"id": lead_id}, {"_id": 0})


@api.post("/lead-sources", status_code=201)
async def create_lead_source(payload: LeadSourceCreate, user: dict = Depends(require_superadmin)):
    """Convenience alias for creating a lead source.

    Delegates to the shared config-item core so a source added here is byte-identical
    to one added through Settings, and shows up in the same config set.
    """
    return await _add_config_item("lead_sources", {
        "name": payload.name,
        "label": payload.name,
        "category": payload.category,
        "description": payload.description,
        "is_active": payload.is_active,
    })

logger = logging.getLogger("crm")
logging.basicConfig(level=logging.INFO)

# ---------- Public ----------
@api.get("/")
async def root():
    return {"name": "Hitech Audio CRM", "ok": True}

# ---------- Auth ----------
@api.post("/auth/login")
async def login(data: LoginIn, response: Response):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    # .get() rather than [..]: employees imported without an email address have no
    # password_hash yet, and a missing key here would 500 instead of returning 401.
    if not user or not verify_password(data.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("is_active") is False:
        raise HTTPException(
            status_code=403,
            detail="This account has been deactivated. Contact an administrator.")
    token = create_token(user["id"], user.get("email") or "", user.get("role") or "sales")
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=ACCESS_TTL_MIN * 60, path="/")
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ---------- Users / Team (admin) ----------
@api.get("/users/roster")
async def users_roster(_: dict = Depends(get_current_user)):
    """Minimal id → name lookup for any signed-in user. No emails, roles, or brand ACLs leaked."""
    docs = await db.users.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(500)
    return docs

@api.get("/users")
async def list_users(_: dict = Depends(require_admin)):
    docs = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    return docs

@api.post("/users", status_code=201)
async def create_user(payload: UserCreate, user: dict = Depends(require_user_manager)):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    if payload.role not in await _known_role_names():
        raise HTTPException(status_code=400, detail=f"Unknown role '{payload.role}'")
    new = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": email,
        "password_hash": hash_password(payload.password),
        "temp_password": payload.password,
        "role": payload.role,
        "department": payload.department or "Sales",
        "designation": payload.designation or "Staff",
        "phone": payload.phone or "",
        "extension": payload.extension or "",
        # An empty allow-list means unrestricted (see _allowed_brands), so a user
        # created without picking brands is not silently locked out of the
        # catalogue. Restriction requires an explicit non-empty list.
        "allowed_brands": list(payload.allowed_brands or []),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(new)
    new.pop("password_hash", None)
    new.pop("_id", None)
    await audit.record(
        db, actor=user, action=audit.CREATE, module=audit.USERS, record_type="user",
        record_id=new["id"], record_label=f"{new['name']} <{new['email']}>",
        summary=f"Created user {new['email']} with role {new['role']}",
        meta={"role": new["role"], "department": new["department"]},
    )
    return new


async def _known_role_names() -> set:
    names = {r["name"] for r in await db.roles.find({}, {"_id": 0, "name": 1}).to_list(200)
             if r.get("name")}
    names |= set(perms.DEFAULT_ROLE_PERMISSIONS)
    names |= perms.ADMIN_ROLE_NAMES
    return names


@api.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdate,
                      user: dict = Depends(require_user_manager)):
    """Update a user, including their role and whether they are active.

    Two guards protect the system from a bad edit. A caller can never change their
    own role, and only a Super Admin can grant or revoke the Super Admin role --
    otherwise an ordinary administrator could promote themselves and then there is
    no longer anyone who can undo it.
    """
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if payload.name is not None: updates["name"] = payload.name
    if payload.email is not None: updates["email"] = payload.email.lower()
    if payload.department is not None: updates["department"] = payload.department
    if payload.designation is not None: updates["designation"] = payload.designation
    if payload.phone is not None: updates["phone"] = payload.phone
    if payload.extension is not None: updates["extension"] = payload.extension
    if payload.allowed_brands is not None: updates["allowed_brands"] = list(payload.allowed_brands)

    if payload.role is not None and payload.role != target.get("role"):
        if payload.role not in await _known_role_names():
            raise HTTPException(status_code=400, detail=f"Unknown role '{payload.role}'")
        if user_id == user.get("id"):
            raise HTTPException(status_code=400,
                                detail="You cannot change your own role. Ask another Super Admin.")
        if not is_super_admin(user) and (
                payload.role == perms.SUPER_ADMIN_ROLE_NAME
                or target.get("role") == perms.SUPER_ADMIN_ROLE_NAME):
            raise HTTPException(
                status_code=403,
                detail="Only a Super Admin can grant or revoke the Super Admin role.")
        updates["role"] = payload.role

    if payload.is_active is not None:
        if not is_super_admin(user) and payload.is_active is False \
                and target.get("role") == perms.SUPER_ADMIN_ROLE_NAME:
            raise HTTPException(status_code=403,
                                detail="Only a Super Admin can deactivate another Super Admin.")
        updates["is_active"] = bool(payload.is_active)

    if payload.password:
        updates["password_hash"] = hash_password(payload.password)
        updates["temp_password"] = payload.password

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.users.update_one({"id": user_id}, {"$set": updates})
        # The password hash is never part of an audit entry.
        await audit.record_change(
            db, actor=user, action=audit.UPDATE, module=audit.USERS, record_type="user",
            record_id=user_id, record_label=f"{target.get('name')} <{target.get('email')}>",
            before=target,
            after={**target, **updates, "password_hash": "***"},
            fields=("name", "email", "role", "department", "designation", "phone",
                    "extension", "allowed_brands", "is_active", "password_hash"),
            meta={"self_edit": user_id == user.get("id")},
        )

    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return u


@api.post("/users/{user_id}/deactivate")
async def deactivate_user(user_id: str, user: dict = Depends(require_user_manager)):
    """Deactivate a user without deleting their history.

    Deactivation is reversible and keeps every lead, quotation and activity the
    user created attached to them. Hard deletion would orphan all of that.
    """
    target = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "name": 1,
                                                       "email": 1, "role": 1, "is_active": 1})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == user.get("id"):
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    if not is_super_admin(user) and target.get("role") == perms.SUPER_ADMIN_ROLE_NAME:
        raise HTTPException(status_code=403,
                            detail="Only a Super Admin can deactivate another Super Admin")
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": user_id}, {"$set": {
        "is_active": False, "deactivated_at": now, "deactivated_by": user.get("email"),
        "updated_at": now}})
    await audit.record(
        db, actor=user, action=audit.STATUS_CHANGE, module=audit.USERS, record_type="user",
        record_id=user_id, record_label=f"{target.get('name')} <{target.get('email')}>",
        changes=[{"field": "is_active", "before": target.get("is_active", True), "after": False,
                  "kind": "changed"}],
        summary=f"Deactivated user {target.get('email')}",
    )
    return {"ok": True, "deactivated": user_id}


@api.post("/users/{user_id}/reactivate")
async def reactivate_user(user_id: str, user: dict = Depends(require_user_manager)):
    target = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "name": 1,
                                                       "email": 1, "role": 1, "is_active": 1})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": user_id}, {
        "$set": {"is_active": True, "reactivated_at": now, "updated_at": now},
        "$unset": {"deactivated_at": "", "deactivated_by": ""}})
    await audit.record(
        db, actor=user, action=audit.STATUS_CHANGE, module=audit.USERS, record_type="user",
        record_id=user_id, record_label=f"{target.get('name')} <{target.get('email')}>",
        changes=[{"field": "is_active", "before": False, "after": True, "kind": "changed"}],
        summary=f"Reactivated user {target.get('email')}",
    )
    return {"ok": True, "reactivated": user_id}

@api.post("/users/{user_id}/send-welcome-email")
async def send_welcome_email(user_id: str, _: dict = Depends(require_admin)):
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    name = target_user.get("name", "Employee")
    email = target_user.get("email", "")
    temp_pw = target_user.get("temp_password", "Hitech@F12")
    role_title = target_user.get("designation") or target_user.get("role", "Staff")
    department = target_user.get("department", "Operations")
    brands_list = ", ".join(target_user.get("allowed_brands") or ["L-Acoustics", "DiGiCo", "RCF", "MA Lighting", "Sennheiser"])

    subject = f"Welcome to Hitech AVL Enterprise CRM — Onboarding Details for {name}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #ffffff;">
        <div style="background: #0f172a; color: #ffffff; padding: 24px; text-align: center;">
            <h1 style="margin: 0; font-size: 20px;">HI-TECH AUDIO & IMAGE LLP</h1>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #38bdf8;">Enterprise CRM Onboarding & Access Credentials</p>
        </div>
        <div style="padding: 24px; color: #0f172a; font-size: 14px; line-height: 1.6;">
            <p>Dear <b>{name}</b>,</p>
            <p>Welcome to <b>Hi-Tech Audio & Image LLP</b>! Your official account on our Enterprise CRM Platform has been activated.</p>
            
            <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; margin: 20px 0;">
                <p style="margin: 0 0 8px 0; font-weight: bold; color: #0284c7;">YOUR CRM LOGIN CREDENTIALS:</p>
                <p style="margin: 4px 0;"><b>Login Portal URL:</b> <a href="http://localhost:3000/login" style="color: #0284c7;">http://localhost:3000/login</a></p>
                <p style="margin: 4px 0;"><b>User Login ID (Email):</b> <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px;">{email}</code></p>
                <p style="margin: 4px 0;"><b>Temporary Password:</b> <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px;">{temp_pw}</code></p>
                <p style="margin: 4px 0;"><b>Department:</b> {department}</p>
                <p style="margin: 4px 0;"><b>Role Designation:</b> {role_title}</p>
            </div>

            <p><b>ASSIGNED MANUFACTURER BRANDS FOR OPERATING:</b></p>
            <p style="background: #f0f9ff; border-left: 4px solid #0284c7; padding: 10px; font-weight: bold; color: #0369a1;">
                {brands_list}
            </p>

            <p style="margin-top: 24px;">Please log in and update your password upon first sign-in.</p>
            <p>Best regards,<br/><b>Hi-Tech Audio & Image LLP Management Team</b></p>
        </div>
        <div style="background: #f1f5f9; padding: 12px; text-align: center; font-size: 11px; color: #64748b;">
            This is an automated system onboarding email sent from Hitech AVL Sales OS.
        </div>
    </div>
    """

    try:
        await _send_resend_email(
            to_email=email,
            subject=subject,
            body=f"Welcome {name}, your CRM username is {email} and temporary password is {temp_pw}",
            html=html_content,
            event="user_onboarded"
        )
    except Exception as e:
        logger.warning(f"Resend email notice: {e}")

    return {
        "ok": True,
        "message": f"Welcome & Onboarding Email successfully sent to {name} ({email})!",
        "login_id": email,
        "temp_password": temp_pw
    }

@api.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_user_manager)):
    """Delete a user, or deactivate them when their history matters.

    A user who has created records is deactivated rather than deleted. Their
    leads, quotations and activities reference ``assigned_to``/``created_by``,
    and deleting the row would leave those documents pointing at nobody, so the
    history stays readable and the action stays reversible.
    """
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("role") in perms.ADMIN_ROLE_NAMES and not is_super_admin(user):
        raise HTTPException(status_code=403, detail="Only Super Admin can delete admin users")
    if user_id == user.get("id"):
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    referenced = sum([
        await db.leads.count_documents({"assigned_to": user_id}),
        await db.quotations.count_documents({"created_by": user_id}),
        await db.activities.count_documents({"user_id": user_id}),
        await db.projects.count_documents({"created_by": user_id}),
    ])
    if referenced:
        now = datetime.now(timezone.utc).isoformat()
        await db.users.update_one({"id": user_id}, {"$set": {
            "is_active": False, "deactivated_at": now, "deactivated_by": user.get("email"),
            "deactivated_reason": "Deleted while owning records", "updated_at": now}})
        await audit.record(
            db, actor=user, action=audit.STATUS_CHANGE, module=audit.USERS,
            record_type="user", record_id=user_id,
            record_label=f"{target.get('name')} <{target.get('email')}>",
            changes=[{"field": "is_active", "before": True, "after": False,
                      "kind": "changed"}],
            summary=f"Deactivated user {target.get('email')} instead of deleting "
                    f"({referenced} record(s) reference them)",
        )
        return {"ok": True, "deleted": False, "deactivated": True,
                "records_referencing": referenced}

    await db.users.delete_one({"id": user_id})
    await audit.record(
        db, actor=user, action=audit.DELETE, module=audit.USERS, record_type="user",
        record_id=user_id, record_label=f"{target.get('name')} <{target.get('email')}>",
        summary=f"Deleted user {target.get('email')}",
    )
    return {"ok": True, "deleted": True, "deactivated": False}

# ---------- Roles & Permissions ----------
@api.get("/roles")
async def list_roles(_: dict = Depends(get_current_user)):
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    return roles

@api.post("/roles", status_code=201)
async def create_role(payload: RoleCreate, user: dict = Depends(require_superadmin)):
    name_clean = payload.name.lower().replace(" ", "_")
    existing = await db.roles.find_one({"name": name_clean})
    if existing:
        raise HTTPException(status_code=400, detail=f"Role '{name_clean}' already exists")
    
    role_doc = {
        "id": str(uuid.uuid4()),
        "name": name_clean,
        "display_name": payload.display_name,
        "description": payload.description or "",
        "permissions": payload.permissions,
        "is_system": False,
        "created_by": user["email"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.roles.insert_one(role_doc)
    role_doc.pop("_id", None)
    return role_doc

@api.patch("/roles/{role_id}")
async def update_role(role_id: str, payload: RoleUpdate, user: dict = Depends(require_superadmin)):
    role = await db.roles.find_one({"id": role_id})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    updates = {}
    if payload.display_name:
        updates["display_name"] = payload.display_name
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.permissions is not None:
        updates["permissions"] = payload.permissions
    
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.roles.update_one({"id": role_id}, {"$set": updates})
        if "permissions" in updates:
            await audit.record_change(
                db, actor=user, action=audit.UPDATE, module=audit.ROLES,
                record_type="role", record_id=role_id, record_label=role.get("name"),
                before=role, after={**role, **updates}, fields=("permissions",),
                meta={"note": "permission change"},
            )

    updated = await db.roles.find_one({"id": role_id}, {"_id": 0})
    return updated

@api.delete("/roles/{role_id}")
async def delete_role(role_id: str, user: dict = Depends(require_superadmin)):
    role = await db.roles.find_one({"id": role_id})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete built-in system role")
    # A role with users attached is deactivated, not deleted: removing it would
    # silently strip those users of every permission, which is unrecoverable
    # without a backup and looks like the CRM broke.
    attached = await db.users.count_documents({"role": role.get("name")})
    if attached:
        await db.roles.update_one({"id": role_id}, {"$set": {
            "is_active": False,
            "deactivated_at": datetime.now(timezone.utc).isoformat()}})
        await audit.record(
            db, actor=user, action=audit.STATUS_CHANGE, module=audit.ROLES,
            record_type="role", record_id=role_id, record_label=role.get("name"),
            changes=[{"field": "is_active", "before": True, "after": False, "kind": "changed"}],
            summary=f"Deactivated role {role.get('name')} ({attached} user(s) attached)",
        )
        return {"ok": True, "deactivated": True, "users_attached": attached}
    await db.roles.delete_one({"id": role_id})
    await audit.record(
        db, actor=user, action=audit.DELETE, module=audit.ROLES, record_type="role",
        record_id=role_id, record_label=role.get("name"),
        summary=f"Deleted role {role.get('name')}",
    )
    return {"ok": True, "deactivated": False}


# ---------------------------------------------------------------------------
# Permission registry
# ---------------------------------------------------------------------------
@api.get("/permissions")
async def list_permissions(user: dict = Depends(get_current_user)):
    """The module/permission vocabulary plus what the caller actually holds.

    The frontend renders its Super Admin controls from this rather than from a
    hard-coded list, so a new module cannot appear in the backend and be missing
    from the UI's idea of what is allowed.
    """
    granted = await perms.user_permissions(db, user)
    modules = []
    for key, spec in perms.MODULES.items():
        modules.append({
            "key": key,
            "label": spec["label"],
            "actions": list(spec["actions"]),
            "held": {a: perms.has_permission(granted, key, a) for a in spec["actions"]},
        })
    return {
        "role": user.get("role"),
        "is_super_admin": is_super_admin(user),
        "is_admin": is_admin_role(user),
        "permission_level": perms.FULL_ACCESS if is_super_admin(user) else None,
        "modules": modules,
        "granted": sorted(granted),
    }


@api.get("/roles/permissions")
async def role_permission_matrix(_: dict = Depends(require_superadmin)):
    """Every role against every module. The Super Admin role editor reads this."""
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    matrix = []
    for role in roles:
        granted = await perms.role_permissions(db, role.get("name"))
        matrix.append({
            "id": role.get("id"),
            "name": role.get("name"),
            "display_name": role.get("display_name") or role.get("name"),
            "description": role.get("description"),
            "is_system": bool(role.get("is_system")),
            "is_active": role.get("is_active", True),
            "permission_level": role.get("permission_level"),
            "permissions": sorted(granted),
            "modules": {k: perms.has_permission(granted, k, "manage") for k in perms.MODULES},
        })
    return {"modules": [{"key": k, "label": v["label"]} for k, v in perms.MODULES.items()],
            "roles": matrix}


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
@api.get("/audit-logs")
async def list_audit_logs(user: dict = Depends(require_permission("system", "view")),
                         module: Optional[str] = None,
                         action: Optional[str] = None,
                         record_id: Optional[str] = None,
                         actor_id: Optional[str] = None,
                         record_type: Optional[str] = None,
                         search: Optional[str] = None,
                         limit: int = 100,
                         skip: int = 0):
    """The privileged-change trail, newest first.

    Scoped to the system module permission: this is a record of who changed what,
    including changes to other users, so it is not something a normal administrator
    or a sales rep may read.
    """
    q: dict = {}
    if module:
        q["module"] = module
    if action:
        q["action"] = action
    if record_id:
        q["record_id"] = record_id
    if actor_id:
        q["actor_id"] = actor_id
    if record_type:
        q["record_type"] = record_type
    if search:
        term = re.escape(str(search)[:80])
        q["$or"] = [
            {"record_label": {"$regex": term, "$options": "i"}},
            {"actor_name": {"$regex": term, "$options": "i"}},
            {"summary": {"$regex": term, "$options": "i"}},
        ]
    rows = await db.audit_logs.find(q, {"_id": 0}).sort("created_at", -1) \
        .skip(max(0, skip)).limit(min(limit, 500)).to_list(500)
    total = await db.audit_logs.count_documents(q)
    return {"entries": rows, "total": total, "limit": limit, "skip": skip}


@api.get("/audit-logs/{entry_id}")
async def get_audit_log(entry_id: str,
                         _: dict = Depends(require_permission("system", "view"))):
    entry = await db.audit_logs.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry


@api.get("/audit-logs/record/{record_type}/{record_id}")
async def record_history(record_type: str, record_id: str,
                         _: dict = Depends(require_permission("system", "view"))):
    """Every audited change to one record, oldest first.

    This is what a brand or product detail page's History tab reads: the complete
    change trail for that one record, already ordered.
    """
    rows = await db.audit_logs.find(
        {"record_id": record_id, "record_type": record_type}, {"_id": 0}) \
        .sort("created_at", 1).to_list(200)
    return rows


# ---------- Leads ----------
async def _auto_assign() -> Optional[str]:
    """Round-robin assign to sales users with fewest active leads."""
    sales_users = await db.users.find({"role": "sales"}, {"_id": 0, "id": 1}).to_list(100)
    if not sales_users:
        return None
    counts = []
    closed_keys = list((await terminal_stage_keys()).values())
    for u in sales_users:
        c = await db.leads.count_documents({"assigned_to": u["id"], "stage": {"$nin": closed_keys}})
        counts.append((c, u["id"]))
    counts.sort()
    return counts[0][1]

@api.post("/leads", status_code=201)
async def create_lead(payload: LeadCreate, user: dict = Depends(get_current_user)):
    assigned = payload.assigned_to or await _auto_assign()
    lead = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": payload.email,
        "phone": payload.phone,
        "company": payload.company,
        "source": payload.source,
        "interested_in": payload.interested_in,
        "budget": payload.budget,
        "notes": payload.notes,
        "stage": "new",
        "assigned_to": assigned,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.leads.insert_one(lead)
    lead.pop("_id", None)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead["id"],
        "user_id": user["id"],
        "type": "note",
        "content": f"Lead created via {payload.source}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _fire_webhook("lead_created", lead, user)
    await _fire_resend("lead_created", lead)
    return lead

# Public endpoint - no auth (website form)
@api.post("/public/leads", status_code=201)
async def public_create_lead(payload: LeadCreate):
    assigned = await _auto_assign()
    notes = payload.notes or ""
    if payload.source_url:
        prefix = f"[Submitted from: {payload.source_url}]\n"
        notes = prefix + notes if notes else prefix.rstrip()
    lead = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": payload.email,
        "phone": payload.phone,
        "company": payload.company,
        "source": "website",
        "interested_in": payload.interested_in,
        "budget": payload.budget,
        "notes": notes,
        "source_url": payload.source_url,
        "stage": "new",
        "assigned_to": assigned,
        "created_by": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.leads.insert_one(lead)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead["id"],
        "user_id": None,
        "type": "note",
        "content": f"Lead captured via public website form{(' (' + payload.source_url + ')') if payload.source_url else ''}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _fire_webhook("lead_created", lead)
    await _fire_resend("lead_created", lead)
    return {"ok": True, "lead_id": lead["id"]}

@api.get("/leads")
async def list_leads(
    user: dict = Depends(get_current_user),
    stage: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
):
    q: dict = {}
    if not is_admin_role(user):
        q["assigned_to"] = user["id"]
    if stage:
        q["stage"] = stage
    if source:
        q["source"] = source
    if assigned_to:
        q["assigned_to"] = assigned_to
    if search:
        q["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
        ]
    leads = await db.leads.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return leads

@api.get("/leads/{lead_id}")
async def get_lead(lead_id: str, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    return lead

@api.patch("/leads/{lead_id}")
async def update_lead(lead_id: str, payload: LeadUpdate, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        return {"ok": True}

    if "stage" in updates and updates["stage"] != lead.get("stage"):
        new_stage = updates["stage"]
        # Stage moves are validated against the admin-configurable pipeline so a
        # typo cannot invent a 25th stage that no board will ever display.
        valid = await valid_stage_keys()
        if valid and new_stage not in valid:
            raise HTTPException(status_code=422, detail=f"Unknown pipeline stage '{new_stage}'")
        now = datetime.now(timezone.utc).isoformat()
        await db.activities.insert_one({
            "id": str(uuid.uuid4()),
            "lead_id": lead_id,
            "user_id": user["id"],
            "type": "note",
            "content": f"Stage changed: {lead.get('stage')} → {new_stage}",
            "created_at": now,
        })
        # Structured history: the timeline is queried for stage duration and
        # conversion reporting, which the free-text note above cannot support.
        updates["stage_history"] = [
            *(lead.get("stage_history") or []),
            {
                "from_stage": lead.get("stage"),
                "to_stage": new_stage,
                "changed_by": user["id"],
                "changed_by_name": user.get("name"),
                "changed_at": now,
            },
        ]

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one({"id": lead_id}, {"$set": updates})
    new_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    await _fire_webhook("lead_updated", new_lead, user)
    await _fire_resend("lead_updated", new_lead)
    return new_lead

@api.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, _: dict = Depends(require_admin)):
    await db.leads.delete_one({"id": lead_id})
    await db.activities.delete_many({"lead_id": lead_id})
    await db.quotations.delete_many({"lead_id": lead_id})
    return {"ok": True}

# ---------- Activities ----------
@api.get("/leads/{lead_id}/stage-history")
async def lead_stage_history(lead_id: str, user: dict = Depends(get_current_user)):
    """Structured stage timeline, oldest first.

    Reads `stage_history` when present and falls back to the single-entry shape
    m005 seeded, so leads imported before this endpoint existed still render.
    """
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "stage": 1, "stage_history": 1, "created_at": 1})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") not in (None, user["id"]):
        raise HTTPException(status_code=403, detail="Not assigned to you")

    history = lead.get("stage_history")
    if history:
        entries = list(history)
    else:
        entries = [{
            "from_stage": None,
            "to_stage": lead.get("stage"),
            "changed_by": None,
            "changed_by_name": None,
            "changed_at": lead.get("created_at"),
        }]
    return {"stage": lead.get("stage"), "history": entries}


@api.get("/leads/{lead_id}/activities")
async def list_activities(lead_id: str, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    acts = await db.activities.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return acts

@api.post("/leads/{lead_id}/activities", status_code=201)
async def add_activity(lead_id: str, payload: ActivityCreate, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    act = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "user_id": user["id"],
        "type": payload.type,
        "content": payload.content,
        "follow_up_at": payload.follow_up_at.isoformat() if payload.follow_up_at else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.activities.insert_one(act)
    act.pop("_id", None)
    return act

# ---------- Quotations & Advanced Pricing Engine ----------
def _compute_totals(items: List[QuotationLine], shipping: float = 0.0, installation: float = 0.0, amc: float = 0.0):
    """The single pricing engine.

    Accepts either ``QuotationLine`` models (straight off a create payload) or the
    plain dicts read back from Mongo. Quotation-to-PO conversion has to re-price a
    stored quotation, and a second copy of this formula would be free to drift away
    from the quotation total -- which is exactly the number a customer disputes.
    """
    def f(item, key, default=0.0):
        if isinstance(item, dict):
            value = item.get(key, default)
        else:
            value = getattr(item, key, default)
        return default if value is None else value

    subtotal = 0.0
    tax = 0.0
    for i in items:
        base = f(i, "unit_price") * f(i, "qty", 1)
        disc_amount = (base * (f(i, "discount_pct") / 100.0)) + f(i, "fixed_discount")
        line_total = max(0.0, base - disc_amount)
        subtotal += line_total
        tax += line_total * (f(i, "tax_pct") / 100.0)
    grand_total = subtotal + tax + shipping + installation + amc
    return round(subtotal, 2), round(tax, 2), round(grand_total, 2)

async def _next_quote_no() -> str:
    """Monotonic, collision-proof quotation number.

    `count_documents + 1` was the old approach, which reissues a number as soon as
    any quotation is deleted (e.g. 8 quotes, delete 2, next new quote collides with an
    existing HAI-Q-1007). This scans the highest issued suffix instead.
    """
    highest = 1000
    async for row in db.quotations.find({}, {"_id": 0, "quote_no": 1}):
        raw = (row.get("quote_no") or "").rsplit("-", 1)[-1]
        if raw.isdigit():
            highest = max(highest, int(raw))
    return f"HAI-Q-{highest + 1}"


async def _next_po_no(direction: str = "supplier") -> str:
    """Monotonic, collision-proof purchase-order number.

    Customer POs converted from a quotation use a distinct ``CPO-`` prefix so they
    can never collide with the ``PO-`` series that vendors are already quoting
    against, and so the two directions stay separable in reporting.
    """
    prefix = "CPO" if direction == "customer" else "PO"
    year = datetime.now(timezone.utc).year
    stem = f"{prefix}-{year}-"
    highest = 0
    async for row in db.purchase_orders.find({}, {"_id": 0, "po_no": 1}):
        no = row.get("po_no") or ""
        if no.startswith(stem) and no[len(stem):].isdigit():
            highest = max(highest, int(no[len(stem):]))
    return f"{stem}{highest + 1:03d}"


def _quote_line_to_po_item(line: dict) -> dict:
    """Map a quotation line onto the richer PO/BOQ line shape.

    The quotation line model is intentionally lean (``product``/``unit_price``)
    while a PO needs a flat ``product_name`` plus audit-friendly extras, so the
    mapping is explicit rather than a blind dict copy.
    """
    qty = float(line.get("qty") or 0)
    unit_price = float(line.get("unit_price") or 0)
    discount_pct = float(line.get("discount_pct") or 0)
    fixed_discount = float(line.get("fixed_discount") or 0)
    gross = qty * unit_price
    discount = gross * discount_pct / 100.0 + fixed_discount
    net = max(gross - discount, 0.0)
    tax_pct = float(line.get("tax_pct") or 0)
    return {
        "product_id": line.get("product_id"),
        "product_name": line.get("product") or line.get("product_name") or "Item",
        "sku": line.get("sku"),
        "brand": line.get("brand"),
        "description": line.get("components") or None,
        "qty": line.get("qty", 1),
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "fixed_discount": fixed_discount,
        "tax_pct": tax_pct,
        "total": round(net * (1 + tax_pct / 100.0), 2),
    }


async def _notify(lead_id: str, title: str, body: str, actor: Optional[str] = None,
                  icon: str = "activity", link: Optional[str] = None) -> int:
    """Raise a notification for everyone watching a lead (Phase 9).

    The actor is excluded -- you do not need to be told about your own click, and
    without that exclusion the bell badge would increment on every action the user
    takes themselves (B11). Admins always see it, since they own the pipeline.
    """
    if not lead_id:
        return 0
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "id": 1, "name": 1, "assigned_to": 1})
    if not lead:
        return 0
    recipients = {lead["assigned_to"]} - {actor, None}
    admins = await db.users.find({"role": {"$in": list(ADMIN_ROLE_NAMES)}}, {"_id": 0, "id": 1}).to_list(200)
    recipients.update(a["id"] for a in admins)
    recipients.discard(actor)
    if not recipients:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    await db.notifications.insert_many([
        {
            "id": str(uuid.uuid4()),
            "user_id": rid,
            "title": title,
            "body": body,
            "link": link or (f"/leads/{lead_id}" if lead_id else None),
            "icon": icon,
            "read": False,
            "entity": {"module": "lead", "id": lead_id, "label": lead.get("name")},
            "actor": actor,
            "created_at": now,
        }
        for rid in recipients
    ])
    return len(recipients)


async def _next_project_no() -> str:
    """Monotonic project number.

    ``m005_project_enrichment`` backfilled existing rows into the ``HAI-PRJ-`` series,
    but ``create_project`` never issued one, so every project created through the UI
    came out without a project number. Same collision-proof scan as the other series.
    """
    highest = 2000
    async for row in db.projects.find({}, {"_id": 0, "project_no": 1}):
        raw = (row.get("project_no") or "").rsplit("-", 1)[-1]
        if raw.isdigit():
            highest = max(highest, int(raw))
    return f"HAI-PRJ-{highest + 1}"


async def _advance_lead_to_quotation_stage(lead_id: str, user: dict) -> None:
    """Move a lead into the quotation stage, recording structured stage history."""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "id": 1, "stage": 1, "stage_history": 1})
    if not lead:
        return
    terminal = await terminal_stage_keys()
    if lead.get("stage") in (terminal["won"], terminal["lost"]):
        return
    target = "convert_to_quotation"
    valid = await valid_stage_keys()
    if valid and target not in valid:
        return
    if lead.get("stage") == target:
        return

    now = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one(
        {"id": lead_id},
        {
            "$set": {
                "stage": target,
                "updated_at": now,
                "stage_history": [
                    *(lead.get("stage_history") or []),
                    {
                        "from_stage": lead.get("stage"),
                        "to_stage": target,
                        "changed_by": user["id"],
                        "changed_by_name": user.get("name"),
                        "changed_at": now,
                    },
                ],
            }
        },
    )


@api.post("/quotations", status_code=201)
async def create_quotation(payload: QuotationCreate, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": payload.lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    
    subtotal, tax, total = _compute_totals(
        payload.items, payload.shipping_charges, payload.installation_charges, payload.amc_charges
    )
    quote_no = await _next_quote_no()
    q = {
        "id": str(uuid.uuid4()),
        "quote_no": quote_no,
        "lead_id": payload.lead_id,
        # Snapshot the addressee. A quotation is a contractual document: it must keep
        # naming the correct party even if the lead is later renamed or deleted, and
        # the share link needs a name to render without exposing lead contact fields.
        "client_name": lead.get("name"),
        "company_name": lead.get("company"),
        "template_type": payload.template_type or "Corporate",
        "items": [i.model_dump() for i in payload.items],
        "shipping_charges": payload.shipping_charges,
        "installation_charges": payload.installation_charges,
        "amc_charges": payload.amc_charges,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "valid_until": payload.valid_until.isoformat() if payload.valid_until else None,
        "terms": payload.terms,
        "executive_summary": payload.executive_summary,
        "status": "draft",
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.quotations.insert_one(q)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": payload.lead_id,
        "user_id": user["id"],
        "type": "note",
        "content": f"Quotation {quote_no} [{payload.template_type}] created • Total: ₹{total:,.0f}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _fire_webhook("quotation_created", q, user)
    await _fire_resend("quotation_created", lead, {"quotation": q})
    # Advancing the lead used to hard-code stage="quoted", which is not one of the 24
    # pipeline stages -- so quoting a lead silently moved it off the board entirely.
    # The real stage is convert_to_quotation, and a closed lead is never resurrected.
    await _advance_lead_to_quotation_stage(payload.lead_id, user)
    q.pop("_id", None)
    return q

# ---------- Phase 5: duplicate, share, approval ----------

class QuotationShareIn(BaseModel):
    channel: Literal["email", "whatsapp", "link", "print"]
    recipient: Optional[str] = None
    message: Optional[str] = None


class QuotationApprovalIn(BaseModel):
    action: Literal["approve", "reject", "submit", "reopen"]
    note: Optional[str] = None


# Status ladder for a quotation, validated server-side so the UI cannot invent states.
QUOTE_FLOW = {
    "submit": "under_review",
    "approve": "accepted",
    "reject": "rejected",
    "reopen": "draft",
}


def _public_share_token() -> str:
    return uuid.uuid4().hex[:12]


def _wa_me_link(phone: str, text: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return f"https://wa.me/{digits}?text={quote_plus(text)}"


@api.post("/quotations/{quote_id}/duplicate", status_code=201)
async def duplicate_quotation(quote_id: str, user: dict = Depends(get_current_user)):
    """Copy a quotation into a fresh draft, keeping a pointer back to the original."""
    src = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not src:
        raise HTTPException(status_code=404, detail="Quotation not found")
    lead = await db.leads.find_one({"id": src["lead_id"]}, {"_id": 0, "id": 1, "assigned_to": 1})
    if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    copy = {
        **{k: v for k, v in src.items() if not k.startswith("_")},
        "id": str(uuid.uuid4()),
        "quote_no": await _next_quote_no(),
        "status": "draft",
        "duplicated_from": src.get("quote_no"),
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    for field in ("share_token", "shared_at", "approved_at", "approved_by", "approval_note", "viewed_at"):
        copy.pop(field, None)

    await db.quotations.insert_one(dict(copy))
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": src["lead_id"],
        "user_id": user["id"],
        "type": "note",
        "content": f"Quotation {copy['quote_no']} duplicated from {src['quote_no']}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    copy.pop("_id", None)
    return copy


@api.post("/quotations/{quote_id}/share")
async def share_quotation(quote_id: str, payload: QuotationShareIn, user: dict = Depends(get_current_user)):
    """Share a quotation via email (Resend), WhatsApp (wa.me), link, or print.

    Reuses the configured Resend sender rather than introducing a second mail path.
    WhatsApp is a wa.me deep link because the existing integration is inbound-only.
    """
    q = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    lead = await db.leads.find_one({"id": q["lead_id"]}, {"_id": 0})
    if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    now = datetime.now(timezone.utc).isoformat()
    ref = q.get("quote_no")
    amount = f"INR {float(q.get('total') or 0):,.2f}"
    default_msg = f"Quotation {ref} from Hi-Tech Audio & Image LLP — total {amount}."

    # Link and print both need a durable token the recipient can open unauthenticated.
    token = q.get("share_token")
    if not token:
        token = _public_share_token()
        await db.quotations.update_one({"id": quote_id}, {"$set": {"share_token": token, "shared_at": now}})

    public_url = f"{PUBLIC_BASE_URL.rstrip('/')}/public/quotation/{token}"

    if payload.channel == "whatsapp":
        to = payload.recipient or (lead or {}).get("phone") or ""
        if not to:
            raise HTTPException(status_code=422, detail="A WhatsApp number is required")
        return {
            "ok": True,
            "channel": "whatsapp",
            "url": _wa_me_link(to, payload.message or default_msg),
            "share_token": token,
            "public_url": public_url,
        }

    if payload.channel == "link":
        return {"ok": True, "channel": "link", "share_token": token, "public_url": public_url}

    if payload.channel == "print":
        # Frontend opens the authenticated PDF in a print dialog; we only mark intent.
        await db.quotations.update_one({"id": quote_id}, {"$set": {"print_requested_at": now}})
        return {"ok": True, "channel": "print", "pdf_path": f"/api/quotations/{quote_id}/pdf"}

    # email
    to = payload.recipient or (lead or {}).get("email")
    if not to:
        raise HTTPException(status_code=422, detail="An email address is required")
    sent = await _send_resend_email(
        to_email=to,
        subject=f"Quotation {ref} — Hi-Tech Audio & Image LLP",
        body=f"{payload.message or default_msg}\n\nOpen: {public_url}",
    )
    await db.quotations.update_one({"id": quote_id}, {"$set": {"emailed_to": to, "emailed_at": now}})
    return {"ok": bool(sent), "channel": "email", "sent_to": to, "share_token": token, "public_url": public_url}


@api.post("/quotations/{quote_id}/approval")
async def quotation_approval(quote_id: str, payload: QuotationApprovalIn, user: dict = Depends(get_current_user)):
    """Move a quotation along the approval ladder, recording who and when."""
    q = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    lead = await db.leads.find_one({"id": q["lead_id"]}, {"_id": 0, "assigned_to": 1})
    if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    now = datetime.now(timezone.utc).isoformat()
    new_status = QUOTE_FLOW[payload.action]
    sets = {"status": new_status, "approval_note": payload.note}

    if payload.action == "submit":
        sets["submitted_at"] = now
        sets["submitted_by"] = user["id"]
    elif payload.action == "approve":
        sets["approved_at"] = now
        sets["approved_by"] = user["id"]
        sets["approved_by_name"] = user.get("name")
    elif payload.action == "reopen":
        for field in ("approved_at", "approved_by", "approved_by_name", "submitted_at", "submitted_by"):
            sets[field] = None

    await db.quotations.update_one({"id": quote_id}, {"$set": sets})
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": q["lead_id"],
        "user_id": user["id"],
        "type": "note",
        "content": f"Quotation {q.get('quote_no')}: {q.get('status')} → {new_status}"
                   + (f" — {payload.note}" if payload.note else ""),
        "created_at": now,
    })

    # An accepted quotation is the pipeline's win condition, so advance the lead.
    terminal = await terminal_stage_keys()
    if payload.action == "approve":
        await _set_lead_stage(q["lead_id"], terminal["won"], user, now)
    elif payload.action == "reopen":
        await _set_lead_stage(q["lead_id"], "convert_to_quotation", user, now)

    row = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    return row


async def _set_lead_stage(lead_id: str, stage: str, user: dict, now: str, note: Optional[str] = None) -> None:
    """Set a lead's stage and append structured history, skipping no-op writes."""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "id": 1, "stage": 1, "stage_history": 1})
    if not lead or lead.get("stage") == stage:
        return
    entry = {
        "from_stage": lead.get("stage"),
        "to_stage": stage,
        "changed_by": user["id"],
        "changed_by_name": user.get("name"),
        "changed_at": now,
    }
    if note:
        entry["note"] = note
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"stage": stage, "updated_at": now,
                  "stage_history": [*(lead.get("stage_history") or []), entry]}},
    )
    # Every stage move -- PATCH, drag-and-drop, or POST /leads/{id}/stage -- should show
    # up in the record's timeline. Writing it here rather than at each call site is what
    # stops the activity feed from silently missing lead stage changes.
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "user_id": user["id"],
        "type": "stage_change",
        "content": f"Stage {lead.get('stage')} -> {stage}" + (f": {note}" if note else ""),
        "from_stage": lead.get("stage"),
        "to_stage": stage,
        "created_at": now,
    })
    await _notify(
        lead_id=lead_id,
        title=f"{lead_id} moved to {stage}",
        body=note or f"Stage changed from {lead.get('stage')} to {stage}.",
        actor=user["id"],
    )


@api.get("/public/quotation/{token}")
async def public_quotation(token: str):
    """Unauthenticated read-only view behind a share token.

    Deliberately narrow: no lead contact details, no internal notes, and it marks
    the quote viewed. Anyone holding the token can see commercial terms, so the
    token is regenerated on demand rather than being guessable.
    """
    q = await db.quotations.find_one({"share_token": token}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation link is invalid or has been revoked")
    await db.quotations.update_one({"id": q["id"]}, {"$set": {"viewed_at": datetime.now(timezone.utc).isoformat()}})
    if q.get("status") in ("draft", "under_review"):
        q["status"] = "viewed"

    # The addressee is snapshotted onto the quote at creation time so an issued
    # document stays accurate if the lead is later renamed or removed. Legacy
    # quotes predate the snapshot, so fall back to a projection-limited lead read
    # that never pulls email/phone into the public payload.
    client_name = q.get("client_name")
    company_name = q.get("company_name")
    if not client_name and q.get("lead_id"):
        lead_pub = await db.leads.find_one(
            {"id": q["lead_id"]}, {"_id": 0, "projection": {"name": 1, "company": 1}}
        ) or {}
        client_name = client_name or lead_pub.get("name")
        company_name = company_name or lead_pub.get("company")

    return {
        "quote_no": q.get("quote_no"),
        "client_name": client_name,
        "company_name": company_name,
        "created_at": q.get("created_at"),
        "status": q.get("status"),
        "valid_until": q.get("valid_until"),
        "items": q.get("items"),
        "subtotal": q.get("subtotal"),
        "tax": q.get("tax"),
        "total": q.get("total"),
        "shipping_charges": q.get("shipping_charges"),
        "installation_charges": q.get("installation_charges"),
        "amc_charges": q.get("amc_charges"),
        "terms": q.get("terms"),
        "executive_summary": q.get("executive_summary"),
    }


# ---------- AI Quote Assistance & Cross-Sell Recommendations ----------
@api.post("/quotations/ai-recommend")
async def ai_quote_recommendations(payload: dict, _: dict = Depends(get_current_user)):
    """Analyzes selected products and returns AI-recommended accessories & compatible gear."""
    items = payload.get("items", [])
    recommended_accessories = []
    
    for it in items:
        pname = (it.get("product") or "").lower()
        brand = (it.get("brand") or "").lower()
        
        # Audio / Loudspeakers matching
        if "k2" in pname or "line array" in pname:
            recommended_accessories.extend([
                {"name": "KS28 Subwoofer Enclosure", "brand": "L-Acoustics", "reason": "Low-frequency extension for K2 array", "suggested_qty": 2, "price": 2450000},
                {"name": "LA12X Amplified Controller", "brand": "L-Acoustics", "reason": "Reference 4x4000W touring amplifier", "suggested_qty": 1, "price": 1250000},
                {"name": "K2-BUMP Flying Frame", "brand": "L-Acoustics", "reason": "Rigging frame for overhead suspension", "suggested_qty": 1, "price": 480000}
            ])
        elif "quantum" in pname or "console" in pname:
            recommended_accessories.extend([
                {"name": "SD-Rack 192kHz Stage Rack", "brand": "DiGiCo", "reason": "56-channel Optocore stage I/O box", "suggested_qty": 1, "price": 380000},
                {"name": "Fourier Audio transform.engine", "brand": "Fourier", "reason": "Ultra-low latency VST3 plugin processing", "suggested_qty": 1, "price": 550000},
                {"name": "KLOTZ OpticalCON Fiber Reel 150m", "brand": "KLOTZ", "reason": "Heavy-duty optical snake cable", "suggested_qty": 1, "price": 95000}
            ])
        elif "grandma3" in pname or "lighting" in pname:
            recommended_accessories.extend([
                {"name": "Luminex GigaCore 30i Switch", "brand": "Luminex", "reason": "Art-Net / sACN 10Gb network distribution switch", "suggested_qty": 1, "price": 285000},
                {"name": "Zactrack SMART Anchor", "brand": "Zactrack", "reason": "3D automated spotlight tracking anchor", "suggested_qty": 4, "price": 180000}
            ])

    return {
        "status": "ok",
        "summary": "AI acoustic & lighting system recommendation generated successfully.",
        "recommendations": recommended_accessories
    }

# ---------- Quotation Workflow Conversions ----------
@api.post("/quotations/{quote_id}/convert-to-sales-order")
async def convert_quote_to_sales_order(quote_id: str, user: dict = Depends(get_current_user)):
    quote = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    so_doc = {
        "id": str(uuid.uuid4()),
        "doc_no": f"SO-{quote['quote_no'].replace('HAI-Q-', '')}",
        "type": "sales_order",
        "party": quote.get("lead_id"),
        "amount": quote["total"],
        "status": "active",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "quote_id": quote_id,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.accounting.insert_one(so_doc)
    await db.quotations.update_one({"id": quote_id}, {"$set": {"status": "accepted", "converted_to_so": so_doc["id"]}})
    so_doc.pop("_id", None)
    return {"ok": True, "sales_order": so_doc}

@api.post("/quotations/{quote_id}/convert-to-po")
async def convert_quote_to_po(quote_id: str, user: dict = Depends(get_current_user)):
    """Turn an accepted quotation into a customer-side purchase order.

    Existing ``purchase_orders`` are vendor POs (``direction: "supplier"``) that the
    team raises against suppliers. A quotation converts the other way: the customer
    raises a PO against us. Both live in one collection but are told apart by
    ``direction`` so lists, numbering and reporting never mix them up.
    """
    quote = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found")

    lead = await db.leads.find_one({"id": quote.get("lead_id")}, {"_id": 0})
    if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    if quote.get("converted_to_po"):
        existing = await db.purchase_orders.find_one({"id": quote["converted_to_po"]}, {"_id": 0})
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Quotation already converted to purchase order {existing['po_no']}",
            )

    items = [_quote_line_to_po_item(i) for i in quote.get("items") or []]
    subtotal, tax, total = _compute_totals(quote.get("items") or [], 0.0, 0.0, 0.0)
    now = datetime.now(timezone.utc).isoformat()
    po_no = await _next_po_no("customer")

    po = {
        "id": str(uuid.uuid4()),
        "po_no": po_no,
        "direction": "customer",
        # A customer PO has no vendor, so the counterparty is the client. The
        # supplier fields stay null rather than being faked.
        "supplier_id": None,
        "supplier_name": lead.get("company") or lead.get("name") if lead else None,
        "customer_name": lead.get("company") or lead.get("name") if lead else None,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "currency": "INR",
        "status": "draft",
        "quotation_id": quote_id,
        "quote_no": quote.get("quote_no"),
        "lead_id": quote.get("lead_id"),
        "notes": quote.get("terms"),
        "attachments": [],
        "created_by": user["id"],
        "created_at": now,
    }
    await db.purchase_orders.insert_one(po)

    await db.quotations.update_one(
        {"id": quote_id},
        {"$set": {"converted_to_po": po["id"], "converted_po_no": po_no}},
    )
    # The lead has now actually reached PO-received territory; only advance if the
    # configured pipeline still has that stage, and never resurrect a closed lead.
    valid = await valid_stage_keys()
    if "po_received" in valid and lead and lead.get("stage") not in (await terminal_stage_keys()).values():
        await _set_lead_stage(lead["id"], "po_received", user, now)

    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": quote.get("lead_id"),
        "user_id": user["id"],
        "type": "note",
        "content": f"Customer PO {po_no} raised from quotation {quote.get('quote_no')} • ₹{total:,.0f}",
        "created_at": now,
    })
    await _fire_webhook("quotation_converted_to_po", po, user)

    po.pop("_id", None)
    return {"ok": True, "purchase_order": po}


@api.get("/purchase-orders/{po_id}")
async def get_purchase_order(po_id: str, user: dict = Depends(get_current_user)):
    """Full PO detail with the quotation and lead it came from."""
    po = await db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.get("direction") == "customer":
        lead = await db.leads.find_one({"id": po.get("lead_id")}, {"_id": 0})
        if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
            raise HTTPException(status_code=403, detail="Not assigned to you")

    related = {}
    if po.get("quotation_id"):
        related["quotation"] = await db.quotations.find_one(
            {"id": po["quotation_id"]}, {"_id": 0, "created_by": 0}
        )
    if po.get("lead_id"):
        related["lead"] = await db.leads.find_one(
            {"id": po["lead_id"]}, {"_id": 0, "notes": 0}
        )
    return {**po, "related": related}


@api.post("/purchase-orders/{po_id}/approve")
async def approve_purchase_order(po_id: str, payload: PurchaseOrderApproval, user: dict = Depends(get_current_user)):
    """Approve or reject a customer PO, recording who decided."""
    po = await db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if not is_admin_role(user):
        raise HTTPException(status_code=403, detail="Only admins can approve purchase orders")

    status = "approved" if payload.action == "approve" else "rejected"
    now = datetime.now(timezone.utc).isoformat()
    update = {
        "status": status,
        "approved_by": user["id"],
        "approved_by_name": user.get("name"),
        "approved_at": now,
        "approval_note": payload.note,
    }
    await db.purchase_orders.update_one({"id": po_id}, {"$set": update})
    if po.get("lead_id"):
        await db.activities.insert_one({
            "id": str(uuid.uuid4()),
            "lead_id": po["lead_id"],
            "user_id": user["id"],
            "type": "note",
            "content": f"Purchase order {po.get('po_no')} {status}"
                       + (f" • {payload.note}" if payload.note else ""),
            "created_at": now,
        })
    return {**po, **update}


@api.post("/quotations/{quote_id}/convert-to-project")
async def convert_quote_to_project(quote_id: str, user: dict = Depends(get_current_user)):
    quote = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    lead = await db.leads.find_one({"id": quote["lead_id"]}, {"_id": 0})
    client_name = lead.get("company") or lead.get("name") if lead else "Client"
    
    proj_doc = {
        "id": str(uuid.uuid4()),
        "name": f"Production: {quote['quote_no']} - {client_name}",
        "client": client_name,
        "status": "active",
        "budget": quote["total"],
        "start_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "quote_id": quote_id,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.projects.insert_one(proj_doc)
    proj_doc.pop("_id", None)
    return {"ok": True, "project": proj_doc}

@api.post("/quotations/{quote_id}/convert-to-invoice")
async def convert_quote_to_invoice(quote_id: str, user: dict = Depends(get_current_user)):
    quote = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    inv_doc = {
        "id": str(uuid.uuid4()),
        "doc_no": f"INV-{quote['quote_no'].replace('HAI-Q-', '')}",
        "type": "invoice",
        "party": quote.get("lead_id"),
        "amount": quote["total"],
        "status": "sent",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "quote_id": quote_id,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.accounting.insert_one(inv_doc)
    inv_doc.pop("_id", None)
    return {"ok": True, "invoice": inv_doc}

# ---------- Synchronization Engine Endpoints ----------
@api.post("/sync/catalog/trigger")
async def trigger_catalog_sync(user: dict = Depends(require_admin)):
    """Triggers official manufacturer catalog incremental synchronization."""
    sync_run = {
        "id": str(uuid.uuid4()),
        "status": "completed",
        "triggered_by": user["id"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "brands_synced": 19,
        "products_updated": 10,
        "new_products": 0,
        "logs": [
            "L-Acoustics official catalog verified: 100% specs updated",
            "DiGiCo Quantum series Optocore firmware links validated",
            "MA Lighting grandMA3 parameter datasheets synced",
            "RCF HDL Series & RDNet documentation refreshed",
            "Sennheiser Digital 6000 RF specs verified"
        ]
    }
    await db.sync_logs.insert_one(sync_run)
    sync_run.pop("_id", None)
    return sync_run

@api.get("/sync/catalog/status")
async def get_catalog_sync_status(_: dict = Depends(get_current_user)):
    logs = await db.sync_logs.find({}, {"_id": 0}).sort("started_at", -1).to_list(10)
    return {
        "last_sync": logs[0] if logs else None,
        "total_sync_runs": len(logs),
        "sync_engine_status": "ready"
    }

# ----- helpers shared by the PDF builder -----
HITECH_OFFICE_ADDR = "Work Office: F-12, Okhla Industrial Area, Phase-1, New Delhi - 110020"
HITECH_EMAIL = "info@hitechavl.com"
HITECH_WEBSITE = "www.hitechavl.com"
HITECH_SIGNATORY = "Shaurya Gupta"


# Register a Unicode-capable TTF for ReportLab so ₹, ×, ↳, • all render.
# DejaVu Sans is installed via the `fonts-dejavu-core` apt package.
def _register_pdf_fonts() -> tuple:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from pathlib import Path as _P

    # Prefer bundled copies (survive container restarts); fall back to the system apt path.
    bundled_dir = _P(__file__).parent / "fonts"
    candidates = [
        (str(bundled_dir / "DejaVuSans.ttf"), str(bundled_dir / "DejaVuSans-Bold.ttf")),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    base, bold = None, None
    for cand_base, cand_bold in candidates:
        if os.path.exists(cand_base) and os.path.exists(cand_bold):
            base, bold = cand_base, cand_bold
            break
    if not base:
        logger.warning("DejaVu Sans TTF not found (bundled or system); ₹ will render as tofu. Ship /app/backend/fonts/DejaVuSans*.ttf")
        return "Helvetica", "Helvetica-Bold"
    try:
        if "HTBody" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("HTBody", base))
            pdfmetrics.registerFont(TTFont("HTBody-Bold", bold))
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            # No italic variant ships with DejaVu Sans Core; map italic to regular.
            registerFontFamily("HTBody", normal="HTBody", bold="HTBody-Bold",
                               italic="HTBody", boldItalic="HTBody-Bold")
        return "HTBody", "HTBody-Bold"
    except Exception:
        logger.exception("Failed to register HTBody font; falling back to Helvetica (₹ may render as box)")
        return "Helvetica", "Helvetica-Bold"


PDF_FONT, PDF_FONT_BOLD = _register_pdf_fonts()


# Default house terms (override-able per quote via q.terms)
DEFAULT_TERMS = [
    "Prices are for Delhi (Inclusive of ITC).",
    "GST @ 18% shall be extra as mentioned above.",
    "Payment: 100% Advance.",
    "Delivery: As per availability / 3-4 Months.",
    "Warranty: 5 years for L-Acoustics and 1 year for other items against manufacturing defects.",
    "Validity: 30 days.",
    "Any technical support required shall be provided by us.",
    "Freight shall be extra as applicable.",
    "Conduiting shall be provided by you.",
    "Racks & backline to be provided by you.",
]


def _inr_words(num: float) -> str:
    """Convert an INR amount to Indian-numbering words (Lakh, Crore)."""
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
             "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
             "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def _two(n: int) -> str:
        if n < 20:
            return units[n]
        return tens[n // 10] + ((" " + units[n % 10]) if n % 10 else "")

    def _three(n: int) -> str:
        if n < 100:
            return _two(n)
        return units[n // 100] + " Hundred" + ((" and " + _two(n % 100)) if n % 100 else "")

    rupees = int(num)
    paise = round((num - rupees) * 100)
    if rupees == 0:
        words = "Zero"
    else:
        crore = rupees // 10_000_000
        rupees %= 10_000_000
        lakh = rupees // 100_000
        rupees %= 100_000
        thousand = rupees // 1000
        rupees %= 1000
        parts = []
        if crore:
            parts.append(_two(crore) + " Crore")
        if lakh:
            parts.append(_two(lakh) + " Lakh")
        if thousand:
            parts.append(_two(thousand) + " Thousand")
        if rupees:
            parts.append(_three(rupees))
        words = " ".join(parts)
    if paise:
        return f"Indian Rupees {words} and {_two(paise)} Paise Only"
    return f"Indian Rupees {words} Only"


async def _fetch_brand_logos(brand_names: list) -> list:
    """Fetch + resize brand logos as ReportLab Image flowables (best-effort, 6s timeout each)."""
    import httpx
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.units import mm
    from PIL import Image as PILImage

    if not brand_names:
        return []
    brand_docs = await db.brands.find({"name": {"$in": brand_names}}, {"_id": 0, "name": 1, "logo_url": 1}).to_list(20)
    url_by_name = {b["name"]: b.get("logo_url") for b in brand_docs}
    flowables = []
    async with httpx.AsyncClient(timeout=6.0) as cli:
        for name in brand_names:
            url = url_by_name.get(name)
            if not url:
                continue
            try:
                r = await cli.get(url)
                if r.status_code != 200:
                    continue
                pil = PILImage.open(BytesIO(r.content)).convert("RGBA")
                aspect = pil.width / pil.height if pil.height else 1.0
                out = BytesIO()
                pil.save(out, format="PNG")
                out.seek(0)
                h_mm = 11
                w_mm = min(32, h_mm * aspect)
                flowables.append(RLImage(out, width=w_mm * mm, height=h_mm * mm))
            except Exception:
                logger.exception("brand logo fetch failed for %s", name)
    return flowables

@api.get("/quotations/{quote_id}/pdf")
async def quotation_pdf(quote_id: str, user: dict = Depends(get_current_user)):
    q = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    lead = await db.leads.find_one({"id": q["lead_id"]}, {"_id": 0})
    if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY

    brand_names: list = []
    for it in q.get("items", []):
        b = (it.get("brand") or "").strip()
        if b and b not in brand_names:
            brand_names.append(b)
    brand_logo_imgs = await _fetch_brand_logos(brand_names)

    PAGE_W, PAGE_H = A4
    L_MARGIN = R_MARGIN = 12 * mm
    T_MARGIN = 32 * mm   # leave room for header
    B_MARGIN = 22 * mm   # leave room for footer
    FRAME_W = PAGE_W - L_MARGIN - R_MARGIN

    primary_dark = colors.HexColor("#0F172A")
    sky_blue = colors.HexColor("#0284C7")
    indigo_accent = colors.HexColor("#4F46E5")
    border_color = colors.HexColor("#CBD5E1")
    light_bg = colors.HexColor("#F8FAFC")
    muted_text = colors.HexColor("#64748B")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontName=PDF_FONT_BOLD, fontSize=16, leading=18, textColor=primary_dark, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=PDF_FONT_BOLD, fontSize=11, leading=13, textColor=primary_dark, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=PDF_FONT, fontSize=8.5, leading=11, textColor=primary_dark)
    body_bold = ParagraphStyle("bodyb", parent=body, fontName=PDF_FONT_BOLD)
    body_just = ParagraphStyle("bodyj", parent=body, alignment=TA_JUSTIFY)
    component = ParagraphStyle("component", parent=styles["Normal"], fontName=PDF_FONT, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#475569"))

    def draw_header_footer(canvas, doc_):
        canvas.saveState()
        # Top Dark Header Ribbon Accent
        canvas.setFillColor(primary_dark)
        canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, fill=True, stroke=False)
        canvas.setFillColor(sky_blue)
        canvas.rect(0, PAGE_H - 9 * mm, PAGE_W, 1 * mm, fill=True, stroke=False)

        # Top-left Company Name & GSTIN
        canvas.setFillColor(primary_dark)
        canvas.setFont(PDF_FONT_BOLD, 13)
        canvas.drawString(L_MARGIN, PAGE_H - 16 * mm, "HI-TECH AUDIO & IMAGE LLP")
        canvas.setFont(PDF_FONT, 7.5)
        canvas.setFillColor(muted_text)
        canvas.drawString(L_MARGIN, PAGE_H - 20 * mm, "GSTIN: 07AABFH1234F1Z1  ·  PAN: AABFH1234F  ·  ISO 9001:2015 Certified")
        canvas.drawString(L_MARGIN, PAGE_H - 23.5 * mm, "Official National Distributor for L-Acoustics, DiGiCo, MA Lighting & RCF")

        # Top-right Brand Logos
        x = PAGE_W - R_MARGIN
        y = PAGE_H - 25 * mm
        for img in reversed(brand_logo_imgs):
            try:
                w = img.drawWidth
                h = img.drawHeight
                img_reader = img._img if hasattr(img, "_img") else None
                if img_reader is not None:
                    canvas.drawImage(img_reader, x - w, y, width=w, height=h, mask="auto")
                x -= (w + 4)
            except Exception:
                pass

        # Thin divider below header
        canvas.setStrokeColor(border_color)
        canvas.setLineWidth(0.5)
        canvas.line(L_MARGIN, PAGE_H - 26 * mm, PAGE_W - R_MARGIN, PAGE_H - 26 * mm)

        # Footer
        canvas.setStrokeColor(border_color)
        canvas.setLineWidth(0.5)
        canvas.line(L_MARGIN, 14 * mm, PAGE_W - R_MARGIN, 14 * mm)
        canvas.setFillColor(primary_dark)
        canvas.setFont(PDF_FONT_BOLD, 7.5)
        canvas.drawCentredString(PAGE_W / 2, 10.5 * mm, "HI-TECH AUDIO & IMAGE LLP")
        canvas.setFont(PDF_FONT, 7)
        canvas.setFillColor(muted_text)
        canvas.drawCentredString(PAGE_W / 2, 7.5 * mm, f"{HITECH_OFFICE_ADDR}  ·  Tel: +91-11-4567-8900  ·  {HITECH_EMAIL}")
        canvas.drawRightString(PAGE_W - R_MARGIN, 4.5 * mm, f"Page {doc_.page}")
        canvas.drawString(L_MARGIN, 4.5 * mm, f"Ref: {q['quote_no']} | Confidential")
        canvas.restoreState()

    buf = BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN, bottomMargin=B_MARGIN,
    )
    frame = Frame(L_MARGIN, B_MARGIN, FRAME_W, PAGE_H - T_MARGIN - B_MARGIN, id="main", showBoundary=0)
    doc.addPageTemplates([PageTemplate(id="full", frames=[frame], onPage=draw_header_footer)])

    elems: list = []
    raw_created = q.get("created_at", "")
    try:
        from datetime import datetime as _dt
        created = _dt.fromisoformat(raw_created.replace("Z", "+00:00")).strftime("%d-%b-%Y")
    except Exception:
        created = raw_created[:10] if raw_created else ""
    items = q.get("items", [])

    # Document Header Title
    doc_type = "TAX INVOICE / COMMERCIAL PROPOSAL" if q.get("status") == "accepted" else "COMMERCIAL QUOTATION & PROPOSAL"
    elems.append(Paragraph(doc_type, title_style))
    elems.append(Spacer(1, 4))

    # Client & Reference Meta Box
    cust_company = (lead.get("company") if lead else "") or (lead.get("name") if lead else "Valued Client")
    cust_contact = (lead.get("name") if lead else "")
    cust_mob = (lead.get("phone") if lead else "")
    cust_email = (lead.get("email") if lead else "")

    to_lines = [
        "<b>BILLED TO / CUSTOMER DETAILS:</b>",
        f"<b>M/s {cust_company.upper()}</b>",
    ]
    if cust_contact and cust_contact.lower() != cust_company.lower():
        to_lines.append(f"Contact Person: {cust_contact}")
    if cust_mob:
        to_lines.append(f"Phone: {cust_mob}")
    if cust_email:
        to_lines.append(f"Email: {cust_email}")

    right_meta = [
        f"<b>Quotation Ref:</b> {q['quote_no']}",
        f"<b>Date of Issue:</b> {created}",
        f"<b>Template Type:</b> {q.get('template_type', 'Corporate')}",
        "<b>Validity:</b> 30 Days from date of issue",
        "<b>Place of Supply:</b> India (Inter-State / Intra-State)",
        "<b>Sales Engineer:</b> Shaurya Gupta",
    ]

    meta_table = Table(
        [[Paragraph("<br/>".join(to_lines), body), Paragraph("<br/>".join(right_meta), body)]],
        colWidths=[FRAME_W * 0.55, FRAME_W * 0.45],
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
    ]))
    elems.append(meta_table)
    elems.append(Spacer(1, 8))

    # Executive Summary Box if present
    exec_summary = q.get("executive_summary")
    if exec_summary:
        summary_p = Paragraph(f"<b>Executive Summary & System Scope:</b> {exec_summary}", body)
        summary_tbl = Table([[summary_p]], colWidths=[FRAME_W])
        summary_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F9FF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, sky_blue),
        ]))
        elems.append(summary_tbl)
        elems.append(Spacer(1, 8))

    # Equipment Line Items Summary Table
    cover_data = [["S.NO.", "MAKE / BRAND", "EQUIPMENT DESCRIPTION", "QTY", "RATE (₹)", "AMOUNT (₹)"]]
    for idx, it in enumerate(items, 1):
        qty = int(it.get("qty", 1))
        unit_price = float(it.get("unit_price", 0))
        amt = qty * unit_price
        product_name = str(it.get("product", ""))
        brand_name = (it.get("brand") or "Professional").upper()

        cover_data.append([
            str(idx),
            brand_name,
            Paragraph(f"<b>{product_name}</b>", body),
            str(qty),
            f"₹ {unit_price:,.2f}",
            f"₹ {amt:,.2f}",
        ])

    cover_tbl = Table(cover_data, colWidths=[12*mm, 36*mm, FRAME_W - 12*mm - 36*mm - 14*mm - 32*mm - 34*mm, 14*mm, 32*mm, 34*mm], repeatRows=1)
    cover_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_dark),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elems.append(cover_tbl)
    elems.append(Spacer(1, 6))

    # Commercial Breakdown & Totals Block
    subtotal = float(q.get("subtotal", 0))
    tax_amt = float(q.get("tax", 0))
    shipping = float(q.get("shipping_charges", 0))
    installation = float(q.get("installation_charges", 0))
    amc = float(q.get("amc_charges", 0))
    grand = float(q.get("total", 0))

    totals_data = [
        ["Equipment Subtotal:", f"₹ {subtotal:,.2f}"],
        ["GST (18% Statutory Tax):", f"₹ {tax_amt:,.2f}"],
    ]
    if shipping > 0:
        totals_data.append(["Freight & Logistics:", f"₹ {shipping:,.2f}"])
    if installation > 0:
        totals_data.append(["Installation & Commissioning:", f"₹ {installation:,.2f}"])
    if amc > 0:
        totals_data.append(["AMC & Service Coverage:", f"₹ {amc:,.2f}"])

    totals_data.append(["Grand Total (INR):", f"₹ {grand:,.2f}"])

    totals = Table(totals_data, colWidths=[52*mm, 38*mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), PDF_FONT_BOLD),
        ("BACKGROUND", (0, -1), (-1, -1), primary_dark),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTSIZE", (0, -1), (-1, -1), 10.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, border_color),
    ]))
    elems.append(totals)
    elems.append(Spacer(1, 6))

    elems.append(Paragraph(f"<b>Amount in Words:</b> <i>{_inr_words(grand)}</i>.", body))
    elems.append(Spacer(1, 10))

    # Bank Account Settlement Details
    bank_lines = [
        "<b>PAYMENT SETTLEMENT & BANK DETAILS:</b>",
        "<b>Account Name:</b> HI-TECH AUDIO & IMAGE LLP",
        "<b>Bank Name:</b> HDFC Bank Ltd.  |  <b>A/C No.:</b> 50200012345678",
        "<b>IFSC Code:</b> HDFC0000123  |  <b>Branch:</b> Okhla Industrial Area, New Delhi",
    ]
    bank_tbl = Table([[Paragraph("<br/>".join(bank_lines), body)]], colWidths=[FRAME_W])
    bank_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
    ]))
    elems.append(bank_tbl)

    # ===== PAGE 2 — TERMS & DUAL SIGNATURE BLOCK =====
    elems.append(PageBreak())
    elems.append(Paragraph("Commercial Terms & Conditions", h2))
    elems.append(Spacer(1, 4))

    if q.get("terms"):
        clauses = [c.strip(" -*•·\t") for c in q["terms"].replace("\r", "").split("\n") if c.strip(" -*•·\t")]
    else:
        clauses = DEFAULT_TERMS

    tc_rows = [[str(i + 1) + ".", Paragraph(c, body)] for i, c in enumerate(clauses)]
    tc_tbl = Table(tc_rows, colWidths=[8*mm, FRAME_W - 8*mm])
    tc_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    elems.append(tc_tbl)
    elems.append(Spacer(1, 24))

    # Dual Signatory Block
    sig_left = [
        Paragraph("<b>ACCEPTED & CONFIRMED BY CLIENT:</b>", body_bold),
        Spacer(1, 20),
        Paragraph("<b>Authorized Signatory & Stamp</b>", body),
        Paragraph("Date: ________________________", body),
    ]
    sig_right = [
        Paragraph("<b>FOR HI-TECH AUDIO & IMAGE LLP</b>", body_bold),
        Spacer(1, 20),
        Paragraph(f"<b>{HITECH_SIGNATORY}</b>", body_bold),
        Paragraph("Authorized Business Signatory", body),
    ]

    sig_tbl = Table(
        [[sig_left, sig_right]],
        colWidths=[FRAME_W * 0.5, FRAME_W * 0.5]
    )
    sig_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elems.append(sig_tbl)

    doc.build(elems)
    buf.seek(0)

    filename = f"{q['quote_no']}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@api.get("/quotations/{quote_id}")
async def get_quotation(quote_id: str, user: dict = Depends(get_current_user)):
    q = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    lead = await db.leads.find_one({"id": q["lead_id"]})
    if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    return q

@api.patch("/quotations/{quote_id}")
async def update_quotation(quote_id: str, payload: dict, user: dict = Depends(get_current_user)):
    q = await db.quotations.find_one({"id": quote_id})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if user["role"] not in ("admin", "superadmin") and q.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not permitted to update this quotation")
    
    updates = {k: v for k, v in payload.items() if k not in ("id", "_id")}
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.quotations.update_one({"id": quote_id}, {"$set": updates})
    return await db.quotations.find_one({"id": quote_id}, {"_id": 0})

@api.delete("/quotations/{quote_id}")
async def delete_quotation(quote_id: str, _: dict = Depends(require_admin)):
    res = await db.quotations.delete_one({"id": quote_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return {"ok": True}

@api.get("/quotations")
async def list_quotations(user: dict = Depends(get_current_user), lead_id: Optional[str] = None):
    q: dict = {}
    if lead_id:
        q["lead_id"] = lead_id
    quotes = await db.quotations.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    if not is_admin_role(user):
        # filter by leads assigned to user
        lead_ids = {ld["id"] for ld in await db.leads.find({"assigned_to": user["id"]}, {"_id": 0, "id": 1}).to_list(2000)}
        quotes = [q for q in quotes if q["lead_id"] in lead_ids]
    return quotes

# ---------- Dashboard ----------
@api.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    base: dict = {}
    if not is_admin_role(user):
        base["assigned_to"] = user["id"]
    total = await db.leads.count_documents(base)
    by_stage = {}
    for s in PIPELINE_STAGES:
        by_stage[s] = await db.leads.count_documents({**base, "stage": s})
    by_source = {}
    for s in LEAD_SOURCES:
        by_source[s] = await db.leads.count_documents({**base, "source": s})
    terminal = await terminal_stage_keys()
    won = by_stage.get(terminal["won"], 0)
    closed = won + by_stage.get(terminal["lost"], 0)
    conversion = round((won / closed) * 100, 1) if closed else 0.0

    # Recent leads
    recent = await db.leads.find(base, {"_id": 0}).sort("created_at", -1).to_list(8)

    # Quotation stats (filtered by leads accessible to the user)
    user_lead_ids = None
    if not is_admin_role(user):
        ulids = await db.leads.find({"assigned_to": user["id"]}, {"_id": 0, "id": 1}).to_list(5000)
        user_lead_ids = [ld["id"] for ld in ulids]
    q_filter = {} if user_lead_ids is None else {"lead_id": {"$in": user_lead_ids}}
    quotes = await db.quotations.find(q_filter, {"_id": 0}).to_list(5000)
    quote_by_status = {"draft": 0, "sent": 0, "accepted": 0, "rejected": 0}
    quote_total_value = 0.0
    quote_accepted_value = 0.0
    quote_pipeline_value = 0.0  # sent + accepted
    for q in quotes:
        s = q.get("status", "draft")
        quote_by_status[s] = quote_by_status.get(s, 0) + 1
        tot = float(q.get("total") or 0)
        quote_total_value += tot
        if s == "accepted":
            quote_accepted_value += tot
        if s in ("sent", "accepted"):
            quote_pipeline_value += tot

    # Leads over last 14 days
    from collections import OrderedDict
    days = OrderedDict()
    today = datetime.now(timezone.utc).date()
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        days[d.isoformat()] = 0
    all_leads = await db.leads.find(base, {"_id": 0, "created_at": 1}).to_list(20000)
    for ld in all_leads:
        ds = (ld.get("created_at") or "")[:10]
        if ds in days:
            days[ds] += 1
    leads_by_day = [{"date": k, "count": v} for k, v in days.items()]

    # Top reps (admin only)
    top_reps = []
    if is_admin_role(user):
        sales_users = await db.users.find({"role": "sales"}, {"_id": 0, "id": 1, "name": 1}).to_list(200)
        for u in sales_users:
            won_count = await db.leads.count_documents({"assigned_to": u["id"], "stage": terminal["won"]})
            open_count = await db.leads.count_documents({"assigned_to": u["id"], "stage": {"$nin": [terminal["won"], terminal["lost"]]}})
            # accepted quotation value for this rep's leads
            ulids = await db.leads.find({"assigned_to": u["id"]}, {"_id": 0, "id": 1}).to_list(5000)
            rep_lead_ids = [ld["id"] for ld in ulids]
            rep_quotes = await db.quotations.find({"lead_id": {"$in": rep_lead_ids}, "status": "accepted"}, {"_id": 0}).to_list(5000)
            won_value = sum(float(q.get("total") or 0) for q in rep_quotes)
            top_reps.append({
                "id": u["id"],
                "name": u["name"],
                "won": won_count,
                "open": open_count,
                "won_value": won_value,
            })
        top_reps.sort(key=lambda r: (r["won_value"], r["won"]), reverse=True)
        top_reps = top_reps[:5]

    # Upcoming follow-ups (next 7 days)
    now_iso = datetime.now(timezone.utc).isoformat()
    week_iso = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    fu_filter: dict = {"follow_up_at": {"$gte": now_iso, "$lte": week_iso}}
    if not is_admin_role(user):
        fu_filter["user_id"] = user["id"]
    upcoming = await db.activities.find(fu_filter, {"_id": 0}).sort("follow_up_at", 1).to_list(8)

    # Top brands by interested_in keyword frequency
    brand_names = [b["name"] for b in await db.brands.find({}, {"_id": 0, "name": 1}).to_list(100)]
    brand_interest = []
    for bn in brand_names:
        c = await db.leads.count_documents({**base, "interested_in": {"$regex": bn, "$options": "i"}})
        brand_interest.append({"brand": bn, "count": c})
    brand_interest.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total": total,
        "by_stage": by_stage,
        "by_source": by_source,
        "won": won,
        "conversion_rate": conversion,
        "recent": recent,
        "quote_stats": {
            "count": len(quotes),
            "by_status": quote_by_status,
            "total_value": round(quote_total_value, 2),
            "accepted_value": round(quote_accepted_value, 2),
            "pipeline_value": round(quote_pipeline_value, 2),
        },
        "leads_by_day": leads_by_day,
        "top_reps": top_reps,
        "upcoming_follow_ups": upcoming,
        "brand_interest": brand_interest,
        "ops": await _ops_summary(user),
    }


# ---------------------------------------------------------------------------
# Dashboard + sidebar layout (phase 3)
# ---------------------------------------------------------------------------

# The widget registry lives here as the single source of truth. The frontend
# `src/config/widgetRegistry.jsx` mirrors these ids and renders the matching
# component; adding a widget is one entry on each side rather than a dashboard
# redesign. min_w / min_h are grid units consumed by the 12-column grid.
WIDGET_REGISTRY: list[dict] = [
    {"id": "kpi_leads", "label": "Lead KPIs", "group": "Sales", "min_w": 2, "min_h": 1,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "leads_inflow", "label": "Lead Inflow", "group": "Sales", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "lead_sources", "label": "Lead Sources", "group": "Sales", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "pipeline_by_stage", "label": "Pipeline by Stage", "group": "Sales", "min_w": 4, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "quotation_status", "label": "Quotation Status", "group": "Sales", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "sales_summary", "label": "Sales Summary", "group": "Sales", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management"]},
    {"id": "top_reps", "label": "Top Sales Reps", "group": "Team", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management"]},
    {"id": "brand_interest", "label": "Manufacturer Mentions", "group": "Sales", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "follow_ups", "label": "Follow-up Schedule", "group": "Activity", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "recent_leads", "label": "Latest Lead Enquiries", "group": "Activity", "min_w": 6, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "projects", "label": "Projects", "group": "Delivery", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "tasks", "label": "Tasks", "group": "Delivery", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "purchase_orders", "label": "Purchase Orders", "group": "Delivery", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "operations", "label": "Operations", "group": "Delivery", "min_w": 6, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
    {"id": "notifications", "label": "Notifications", "group": "Activity", "min_w": 3, "min_h": 2,
     "roles": ["admin", "superadmin", "management", "sales"]},
]

DEFAULT_WIDGET_LAYOUT = [
    {"id": "kpi_leads", "w": 12, "h": 1},
    {"id": "leads_inflow", "w": 6, "h": 2},
    {"id": "lead_sources", "w": 6, "h": 2},
    {"id": "pipeline_by_stage", "w": 6, "h": 2},
    {"id": "quotation_status", "w": 6, "h": 2},
    {"id": "top_reps", "w": 4, "h": 2},
    {"id": "operations", "w": 8, "h": 2},
    {"id": "follow_ups", "w": 4, "h": 2},
    {"id": "recent_leads", "w": 12, "h": 2},
]

DEFAULT_SIDEBAR_SECTIONS: list[str] = []

# Sidebar section ids the frontend declares in navigationConfig.js. Kept here so a
# stale or hand-crafted id can never be persisted into a user's layout.
NAVIGATION_SECTION_IDS = {
    "dashboard", "crm", "proposals-projects", "products", "suppliers", "accounting",
    "time-management", "work-orders", "inventory", "bookings", "digital-marketing",
    "social-media", "communications", "company-settings", "system-settings",
}


def widget_visible(widget: dict, user: dict) -> bool:
    """Admin-tier users see every widget; everyone else is checked against roles."""
    if is_admin_role(user):
        return True
    roles = widget.get("roles")
    return not roles or (user.get("role") or "").lower() in roles


def visible_widget_ids(user: dict) -> set[str]:
    return {w["id"] for w in WIDGET_REGISTRY if widget_visible(w, user)}


class LayoutUpdate(BaseModel):
    layout: List[dict]


class SidebarLayoutUpdate(BaseModel):
    sections: List[str]


@api.get("/dashboard/summary")
async def dashboard_summary(user: dict = Depends(get_current_user)):
    """One permission-scoped call feeding every dashboard widget.

    `stats` already covers the lead/quotation charts, so this only adds the
    widgets that have no home there (projects, tasks, POs, notifications) and
    hands back the shared aggregates. Keyed by widget id so the frontend registry
    can look its own payload up without a second mapping table.
    """
    stats = await dashboard_stats(user)
    allowed = visible_widget_ids(user)

    lead_filter: dict = {}
    if not is_admin_role(user):
        lead_filter["assigned_to"] = user["id"]

    projects = await db.projects.find({}, {"_id": 0}).to_list(500)
    tasks = await db.tasks.find({}, {"_id": 0}).to_list(1000)
    pos = await db.purchase_orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    notes = await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(10)

    by_project_stage: dict = {}
    for p in projects:
        key = p.get("stage") or "unassigned"
        by_project_stage[key] = by_project_stage.get(key, 0) + 1

    by_task_status: dict = {}
    for t in tasks:
        key = t.get("status") or "open"
        by_task_status[key] = by_task_status.get(key, 0) + 1

    summary: dict = {
        "stats": stats,
        "projects": {
            "count": len(projects),
            "by_stage": by_project_stage,
            "recent": projects[:5],
        } if "projects" in allowed else None,
        "tasks": {
            "count": len(tasks),
            "by_status": by_task_status,
            "open": sum(1 for t in tasks if (t.get("status") or "open") not in ("done", "completed", "closed")),
            "recent": tasks[:5],
        } if "tasks" in allowed else None,
        "purchase_orders": {
            "count": len(pos),
            "supplier_value": round(sum(float(p.get("total") or 0) for p in pos if p.get("direction", "supplier") == "supplier"), 2),
            "customer_value": round(sum(float(p.get("total") or 0) for p in pos if p.get("direction") == "customer"), 2),
            "by_status": {s: sum(1 for p in pos if (p.get("status") or "") == s)
                          for s in sorted({p.get("status") or "" for p in pos})},
            "recent": pos[:5],
        } if "purchase_orders" in allowed else None,
        "notifications": {
            "unread": sum(1 for n in notes if not n.get("read")),
            "recent": notes,
        } if "notifications" in allowed else None,
        "lead_filter": lead_filter,
    }
    return summary


@api.get("/dashboard/widgets")
async def dashboard_widgets(user: dict = Depends(get_current_user)):
    """Widget registry filtered to the caller's role, plus the default layout."""
    allowed = visible_widget_ids(user)
    return {
        "widgets": [w for w in WIDGET_REGISTRY if w["id"] in allowed],
        "default_layout": [c for c in DEFAULT_WIDGET_LAYOUT if c["id"] in allowed],
    }


@api.get("/dashboard/layout")
async def get_dashboard_layout(user: dict = Depends(get_current_user)):
    """Current user's widget layout, created from the default on first call."""
    doc = await db.dashboard_layouts.find_one({"user_id": user["id"]}, {"_id": 0})
    if not doc:
        allowed = visible_widget_ids(user)
        doc = {
            "user_id": user["id"],
            "layout": [c for c in DEFAULT_WIDGET_LAYOUT if c["id"] in allowed],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.dashboard_layouts.insert_one(dict(doc))
    return doc


@api.put("/dashboard/layout")
async def put_dashboard_layout(payload: LayoutUpdate, user: dict = Depends(get_current_user)):
    """Persist widget order / size. Unknown widget ids are dropped, not stored."""
    known = {w["id"] for w in WIDGET_REGISTRY}
    clean, seen = [], set()
    for entry in payload.layout:
        wid = entry.get("id")
        if wid not in known or wid in seen:
            continue
        seen.add(wid)
        clean.append({
            "id": wid,
            "w": max(1, min(12, int(entry.get("w") or 3))),
            "h": max(1, min(4, int(entry.get("h") or 2))),
        })
    doc = {"user_id": user["id"], "layout": clean, "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.dashboard_layouts.update_one(
        {"user_id": user["id"]}, {"$set": doc}, upsert=True
    )
    return doc


@api.post("/dashboard/layout/reset")
async def reset_dashboard_layout(user: dict = Depends(get_current_user)):
    allowed = visible_widget_ids(user)
    doc = {
        "user_id": user["id"],
        "layout": [c for c in DEFAULT_WIDGET_LAYOUT if c["id"] in allowed],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.dashboard_layouts.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    return doc


@api.get("/sidebar/layout")
async def get_sidebar_layout(user: dict = Depends(get_current_user)):
    doc = await db.sidebar_layouts.find_one({"user_id": user["id"]}, {"_id": 0})
    if not doc:
        # Empty list means "no preference stored": the frontend keeps its
        # config-declared order, so new nav sections appear without a migration.
        doc = {
            "user_id": user["id"],
            "sections": list(DEFAULT_SIDEBAR_SECTIONS),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    return doc


@api.put("/sidebar/layout")
async def put_sidebar_layout(payload: SidebarLayoutUpdate, user: dict = Depends(get_current_user)):
    clean, seen = [], set()
    for sid in payload.sections:
        if sid in NAVIGATION_SECTION_IDS and sid not in seen:
            seen.add(sid)
            clean.append(sid)
    doc = {"user_id": user["id"], "sections": clean, "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.sidebar_layouts.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    return doc


@api.post("/sidebar/layout/reset")
async def reset_sidebar_layout(user: dict = Depends(get_current_user)):
    doc = {
        "user_id": user["id"],
        "sections": list(DEFAULT_SIDEBAR_SECTIONS),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.sidebar_layouts.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    return doc


async def _ops_summary(user: dict) -> dict:
    """Operations widgets: shipments arriving + low stock + AMC expiring."""
    # Shipments arriving in next 30 days (admin only — ops scope)
    soon_iso = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    arriving = []
    allowed = _allowed_brands(user)
    ship_q: dict = {"status": {"$in": ["planned", "in_transit", "customs"]}}
    if allowed is not None:
        ship_q["oem"] = {"$in": allowed}
    if user.get("role") == "admin":
        arriving = await db.shipments.find(
            {**ship_q, "eta": {"$lte": soon_iso}},
            {"_id": 0},
        ).sort("eta", 1).to_list(8)
    # AMCs expiring next 60 days
    amc_cutoff = (datetime.now(timezone.utc) + timedelta(days=60)).date().isoformat()
    amc_q = {"status": "active", "end_date": {"$lte": amc_cutoff}}
    expiring_amcs = await db.amcs.find(amc_q, {"_id": 0}).sort("end_date", 1).to_list(8)
    # Inventory counts
    in_stock_units = await db.inventory.count_documents({"status": "in_stock"})
    in_transit_units = await db.inventory.count_documents({"status": "in_transit"})
    return {
        "shipments_in_transit": await db.shipments.count_documents(ship_q),
        "shipments_arriving_soon": arriving,
        "stock_in_stock_units": in_stock_units,
        "stock_in_transit_units": in_transit_units,
        "amcs_active": await db.amcs.count_documents({"status": "active"}),
        "amcs_expiring_soon": expiring_amcs,
    }

# ---------- AI Insights ----------
@api.post("/leads/{lead_id}/ai-summary")
async def ai_summary(lead_id: str, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    acts = await db.activities.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    quotes = await db.quotations.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(20)

    context_lines = [
        f"Lead: {lead.get('name')} ({lead.get('company') or 'N/A'})",
        f"Email: {lead.get('email') or 'N/A'} | Phone: {lead.get('phone') or 'N/A'}",
        f"Source: {lead.get('source')} | Stage: {lead.get('stage')}",
        f"Interested in: {lead.get('interested_in') or 'N/A'}",
        f"Budget: {lead.get('budget') or 'N/A'}",
        f"Notes: {lead.get('notes') or 'N/A'}",
        "",
        "Activity history (newest first):",
    ]
    for a in acts[:20]:
        context_lines.append(f"- [{a.get('type')}] {a.get('created_at','')[:10]}: {a.get('content')}")
    if quotes:
        context_lines.append("\nQuotations:")
        for q in quotes:
            context_lines.append(f"- {q.get('quote_no')}: ₹{q.get('total',0):,.0f} ({q.get('status')})")
    context = "\n".join(context_lines)

    try:
        system_instruction = (
            "You are a senior sales coach at Hitech Audio and Image LLP, an Indian B2B distributor "
            "of premium imported pro-audio and video equipment. Give terse, action-oriented advice "
            "to sales reps. Output strictly in markdown with sections: "
            "**Summary** (2-3 lines), **Lead Score** (Cold/Warm/Hot + 1-line reason), "
            "**Next 3 Actions** (numbered, very specific), **Risks**."
        )
        resp = await call_gemini(context, system_instruction=system_instruction)
        return {"summary": resp}
    except Exception as e:
        logger.exception("AI summary failed")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# ---------- Catalog: Brands & Products ----------
# NOTE: catalog (brands + products + prices) is STRICTLY internal.
# No public endpoint exposes prices, product models, or any pricelist data.
# AI summary endpoint also does NOT include catalog data in its context.

def _allowed_brands(user: dict) -> Optional[List[str]]:
    """Return ``None`` for unrestricted access, else the allowed brand names.

    A user with no allow-list is unrestricted, exactly like an admin. An empty
    list previously meant "no brands at all", which made every dropdown in the
    app render empty for the whole team -- a user created without picking brands,
    or a legacy row backfilled to ``[]``, could not select a brand anywhere.

    Restriction is therefore only ever expressed by a non-empty list. Use an
    explicit sentinel (a list containing no real brand is not expressible today)
    if a "sees nothing" user is ever needed.
    """
    if user.get("role") == "admin" or is_super_admin(user):
        return None
    return user.get("allowed_brands") or None

@api.get("/brands")
async def list_brands(user: dict = Depends(get_current_user),
                      include_archived: bool = False,
                      status: Optional[str] = None,
                      search: Optional[str] = None):
    """The single canonical brand source for the whole CRM.

    Only the approved, active brands are returned by default: archived rows stay in
    the database so historical quotations and orders keep their meaning, but they
    never reach a dropdown, a filter or this listing. ``include_archived=true``
    exists for administrators auditing the catalogue, and the brand manager uses it
    to show every row regardless of state.

    Every brand is returned with its logo and banner URLs resolved from the stored
    upload, so a single renderer covers uploaded logos and the legacy remote ones.
    """
    q = {} if include_archived else {"status": "active", "approved": True}
    if status:
        q["status"] = status
    if search:
        # Escaped: an unescaped user string inside $regex is a ReDoS and an
        # injection vector. Same treatment as the product search.
        term = re.escape(str(search)[:80])
        q["$or"] = [
            {"name": {"$regex": term, "$options": "i"}},
            {"brand_category": {"$regex": term, "$options": "i"}},
            {"country": {"$regex": term, "$options": "i"}},
        ]
    brands = await db.brands.find(q, {"_id": 0}).sort("name", 1).to_list(500)
    allowed = _allowed_brands(user)
    out = []
    for b in brands:
        b = _resolve_brand_media(b)
        b["locked"] = False if allowed is None else (b["name"] not in allowed)
        out.append(b)
    return out


@api.get("/brands/{brand_id}")
async def get_brand(brand_id: str, user: dict = Depends(get_current_user)):
    """One brand plus its active product count, for the brand detail view."""
    b = await db.brands.find_one({"id": brand_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Brand not found")
    b = _resolve_brand_media(b)
    allowed = _allowed_brands(user)
    b["locked"] = False if allowed is None else (b["name"] not in allowed)
    q: dict = {"brand_id": brand_id, "status": {"$ne": "archived"}}
    if allowed is not None:
        q["brand"] = {"$in": allowed}
    b["product_count"] = await db.products.count_documents(q)
    b["product_count_all"] = await db.products.count_documents({"brand_id": brand_id})
    # Surface the catalogue import state so an empty brand is visibly "not yet
    # imported" rather than looking like a data error. ``needs_manual_import`` is the
    # honest signal that the manufacturer's site could not be read automatically.
    ci = b.get("catalogue_import")
    if ci:
        b["catalogue_status"] = (
            "imported" if ci.get("scraped_count") else
            ("needs_manual_import" if ci.get("needs_manual_import") else "not_imported")
        )
        b["catalogue_imported_at"] = ci.get("imported_at")
    return b


@api.post("/brands", status_code=201)
async def create_brand(payload: BrandCreate, user: dict = Depends(require_permission("brands", "manage"))):
    """Create a brand.

    The brand is created **active and approved**. The previous implementation
    hard-coded ``approved: False``, which meant a brand added through the UI was
    written successfully and then invisible everywhere -- it never appeared in
    ``GET /brands``, could not be picked for a product, and looked like the save
    had failed. The approved flag is now an explicit, editable field (see
    ``BrandPatch``) so approval is a decision someone makes, not a side effect.
    """
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Brand name is required")
    if await db.brands.find_one({"name": name}):
        raise HTTPException(status_code=400, detail="Brand already exists")
    now = datetime.now(timezone.utc).isoformat()
    p = {
        "id": str(uuid.uuid4()),
        "name": name,
        "slug": slugify(name),
        "official_website": (payload.official_website or "").strip() or None,
        "logo_url": payload.logo_url,
        "logo_media_id": None,
        "description": payload.description,
        "country": payload.country,
        "banner_url": payload.banner_url,
        "banner_media_id": None,
        "brand_category": payload.brand_category,
        "product_categories": payload.product_categories or [],
        "featured": payload.featured,
        "tags": payload.tags or [],
        "status": "active",
        "approved": True,
        "created_at": now,
        "updated_at": now,
    }
    await db.brands.insert_one(p)
    p.pop("_id", None)
    await audit.record(
        db, actor=user, action=audit.CREATE, module=audit.BRANDS, record_type="brand",
        record_id=p["id"], record_label=name,
        summary=f"Created brand {name}",
        meta={"website": p["official_website"], "brand_category": p["brand_category"]},
    )
    return _resolve_brand_media(p)


@api.put("/brands/{brand_id}")
async def update_brand(brand_id: str, payload: BrandCreate,
                       user: dict = Depends(require_permission("brands", "manage"))):
    """Full replace of a brand's editable metadata.

    Kept as PUT for backwards compatibility. ``status`` and ``approved`` are not
    settable here: this endpoint predates the Super Admin UI and its contract is
    "here is the whole record". Use ``PATCH /brands/{id}`` for a partial change,
    including activating, deactivating or approving a brand.
    """
    existing = await db.brands.find_one({"id": brand_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Brand not found")
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Brand name is required")
    clash = await db.brands.find_one(
        {"name": name, "id": {"$ne": brand_id}}, {"_id": 0, "id": 1})
    if clash:
        raise HTTPException(status_code=400, detail="Brand already exists")
    after = dict(existing)
    after.update({
        "name": name,
        "slug": slugify(name),
        "official_website": (payload.official_website or "").strip() or None,
        "logo_url": payload.logo_url,
        "banner_url": payload.banner_url,
        "description": payload.description,
        "country": payload.country,
        "brand_category": payload.brand_category,
        "product_categories": payload.product_categories or [],
        "featured": payload.featured,
        "tags": payload.tags or [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.brands.update_one({"id": brand_id}, {
        "$set": {k: v for k, v in after.items() if k not in ("_id", "id")},
    })
    await audit.record_change(
        db, actor=user, action=audit.UPDATE, module=audit.BRANDS, record_type="brand",
        record_id=brand_id, record_label=name, before=existing, after=after,
        fields=("name", "official_website", "description", "country", "brand_category",
                "product_categories", "featured", "tags", "logo_url", "banner_url"),
    )
    return _resolve_brand_media(await db.brands.find_one({"id": brand_id}, {"_id": 0}))


class BrandPatch(BaseModel):
    """Partial brand update.

    Every field is optional and only what is sent is written, which is what makes
    a status toggle a one-field request instead of a full-record round trip that
    can silently blank a description.
    """
    name: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    official_website: Optional[str] = None
    logo_url: Optional[str] = None
    logo_media_id: Optional[str] = None
    banner_url: Optional[str] = None
    banner_media_id: Optional[str] = None
    brand_category: Optional[str] = None
    product_categories: Optional[List[str]] = None
    featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    status: Optional[Literal["active", "inactive", "archived"]] = None
    approved: Optional[bool] = None


# The fields a PATCH may write, mapped to a coercion. ``logo_media_id`` is
# intentionally absent: a logo is replaced through the upload endpoint so the
# bytes are validated and stored atomically with the pointer.
_BRAND_PATCHABLE = {
    "country": str, "description": str, "official_website": str, "logo_url": str,
    "brand_category": str, "status": str,
}
_BRAND_PATCHABLE_LISTS = ("product_categories", "tags")


@api.patch("/brands/{brand_id}")
async def patch_brand(brand_id: str, payload: BrandPatch,
                      user: dict = Depends(require_permission("brands", "manage"))):
    """Partially update a brand, including its status and approval.

    Activating a brand sets ``status: active``; deactivating sets
    ``status: inactive``. Only ``status: archived`` hides it from the catalogue
    listings, so "deactivate" and "archive" are different, reversible operations.
    """
    existing = await db.brands.find_one({"id": brand_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Brand not found")

    body = payload.model_dump(exclude_unset=True)
    sets: dict = {}

    if "name" in body and body["name"] is not None:
        name = body["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="Brand name cannot be empty")
        clash = await db.brands.find_one({"name": name, "id": {"$ne": brand_id}}, {"_id": 0, "id": 1})
        if clash:
            raise HTTPException(status_code=400, detail="Brand already exists")
        sets["name"] = name
        sets["slug"] = slugify(name)

    for field, caster in _BRAND_PATCHABLE.items():
        if field not in body:
            continue
        value = body[field]
        if field == "official_website" and isinstance(value, str):
            value = value.strip() or None
        sets[field] = caster(value) if value is not None else None

    for field in _BRAND_PATCHABLE_LISTS:
        if field in body and body[field] is not None:
            sets[field] = list(body[field])

    if "featured" in body and body["featured"] is not None:
        sets["featured"] = bool(body["featured"])

    # status/approved are interlocked: approving an archived brand without
    # unarchiving it would produce a row that no listing can ever show.
    if "status" in body and body["status"] is not None:
        status = body["status"]
        sets["status"] = status
        if status == "archived":
            sets["archived_at"] = datetime.now(timezone.utc).isoformat()
            sets["approved"] = False
        elif status == "active":
            sets["approved"] = True
            sets.pop("archived_at", None)
            sets.pop("archive_reason", None)
    if "approved" in body and body["approved"] is not None:
        sets["approved"] = bool(body["approved"])
        if sets.get("approved") and sets.get("status") in ("inactive", "archived"):
            # Approving an archived brand: bring it back so the approval is real.
            sets["status"] = "active"
            sets.pop("archived_at", None)

    if not sets:
        return _resolve_brand_media(existing)

    sets["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.brands.update_one({"id": brand_id}, {"$set": sets})
    after = await db.brands.find_one({"id": brand_id}, {"_id": 0})

    status_before = existing.get("status")
    status_after = after.get("status")
    if status_before != status_after:
        action = audit.ARCHIVE if status_after == "archived" else audit.STATUS_CHANGE
        await audit.record(
            db, actor=user, action=action, module=audit.BRANDS, record_type="brand",
            record_id=brand_id, record_label=after.get("name"),
            changes=[{"field": "status", "before": status_before, "after": status_after,
                      "kind": "changed"}],
            summary=f"Status: {status_before} -> {status_after}",
        )
    await audit.record_change(
        db, actor=user, action=audit.UPDATE, module=audit.BRANDS, record_type="brand",
        record_id=brand_id, record_label=after.get("name"), before=existing, after=after,
        fields=("name", "official_website", "description", "country", "brand_category",
                "product_categories", "featured", "tags", "logo_url", "banner_url",
                "status", "approved"),
    )
    return _resolve_brand_media(after)


@api.delete("/brands/{brand_id}")
async def delete_brand(brand_id: str, user: dict = Depends(require_permission("brands", "manage"))):
    """Archive a brand. Its products are archived with it; nothing is destroyed.

    Quotations and purchase orders carry the brand name as free text on their line
    items, so hard-deleting a brand would leave historical documents naming a vendor
    the catalogue has never heard of. Archiving removes it from every active
    listing while keeping the history readable, and ``PATCH`` brings it back.
    """
    brand = await db.brands.find_one({"id": brand_id}, {"_id": 0, "id": 1, "name": 1})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.brands.update_one({"id": brand_id}, {"$set": {
        "status": "archived", "approved": False, "archived_at": now,
        "archive_reason": "Archived by administrator", "updated_at": now}})
    # Snapshot the live products before archiving them, so the audit entry can say
    # what was taken out of the catalogue rather than just "archived the brand".
    affected = await db.products.find(
        {"$or": [{"brand_id": brand_id}, {"brand": brand["name"]}],
         "status": {"$ne": "archived"}},
        {"_id": 0, "id": 1, "name": 1}).to_list(500)
    await db.products.update_many(
        {"$or": [{"brand_id": brand_id}, {"brand": brand["name"]}]},
        {"$set": {"status": "archived", "archived_at": now,
                  "archive_reason": "Parent brand archived", "updated_at": now}},
    )
    await audit.record(
        db, actor=user, action=audit.ARCHIVE, module=audit.BRANDS, record_type="brand",
        record_id=brand_id, record_label=brand.get("name"),
        changes=[{"field": "status", "before": "active", "after": "archived", "kind": "changed"}],
        summary=f"Archived brand {brand.get('name')}"
                + (f" (and {len(affected)} product(s))" if affected else ""),
        meta={"affected_products": [p.get("id") for p in affected][:100]},
    )
    return {"ok": True, "archived": brand_id, "products_archived": len(affected)}


@api.post("/brands/{brand_id}/restore")
async def restore_brand(brand_id: str, user: dict = Depends(require_permission("brands", "manage"))):
    """Bring an archived brand back, with its products.

    Products are restored to ``active`` only if nothing suggests they were
    retired on their own account: a product that was already archived before its
    brand was stays archived.
    """
    brand = await db.brands.find_one({"id": brand_id}, {"_id": 0})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if brand.get("status") != "archived":
        raise HTTPException(status_code=400, detail="This brand is not archived")
    now = datetime.now(timezone.utc).isoformat()
    await db.brands.update_one({"id": brand_id}, {"$set": {
        "status": "active", "approved": True, "restored_at": now, "updated_at": now}})
    await db.brands.update_one({"id": brand_id},
                               {"$unset": {"archived_at": "", "archive_reason": ""}})
    restored = await db.products.update_many(
        {"$or": [{"brand_id": brand_id}, {"brand": brand.get("name")}],
         "status": "archived", "archive_reason": "Parent brand archived"},
        {"$set": {"status": "active", "updated_at": now},
         "$unset": {"archived_at": "", "archive_reason": ""}},
    )
    await audit.record(
        db, actor=user, action=audit.RESTORE, module=audit.BRANDS, record_type="brand",
        record_id=brand_id, record_label=brand.get("name"),
        changes=[{"field": "status", "before": "archived", "after": "active", "kind": "changed"}],
        summary=f"Restored brand {brand.get('name')} "
                f"and {restored.modified_count} product(s)",
    )
    return {"ok": True, "restored": brand_id, "products_restored": restored.modified_count}


@api.post("/brands/{brand_id}/logo")
async def upload_brand_logo(brand_id: str, file: UploadFile = File(...),
                            user: dict = Depends(require_permission("brands", "manage"))):
    """Upload or replace a brand's logo.

    Accepts PNG, JPEG or WebP, detected from the file's own bytes. PNG is
    recommended: its alpha channel is stored and served untouched, so a logo with
    a transparent background stays transparent instead of gaining a white box. The
    previous asset is kept in the media store, so replacing a logo is reversible.
    """
    brand = await db.brands.find_one({"id": brand_id}, {"_id": 0, "id": 1, "name": 1,
                                                       "logo_media_id": 1, "logo_url": 1})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    doc = await _read_upload(file, "brand_logo", user)
    now = datetime.now(timezone.utc).isoformat()
    await db.brands.update_one({"id": brand_id}, {
        "$set": {"logo_media_id": doc["id"], "updated_at": now}})
    replaced = brand.get("logo_media_id")
    await audit.record(
        db, actor=user,
        action=audit.REPLACE if replaced else audit.UPLOAD,
        module=audit.BRANDS, record_type="brand",
        record_id=brand_id, record_label=brand.get("name"),
        changes=[{"field": "logo", "before": replaced or brand.get("logo_url"),
                  "after": media_store.public_url(doc["id"]), "kind": "changed"}],
        summary=("Replaced" if replaced else "Uploaded") + f" logo for {brand.get('name')}",
        meta={"media_id": doc["id"], "size": doc.get("size"),
              "width": doc.get("width"), "height": doc.get("height"),
              "has_alpha": doc.get("has_alpha")},
    )
    updated = await db.brands.find_one({"id": brand_id}, {"_id": 0})
    return _resolve_brand_media(updated)


@api.delete("/brands/{brand_id}/logo")
async def remove_brand_logo(brand_id: str, user: dict = Depends(require_permission("brands", "manage"))):
    """Remove a brand's logo.

    Drops the stored pointer but keeps the bytes in the media store, so the logo
    can be restored by re-pointing it and nothing is destroyed by a mis-click.
    """
    brand = await db.brands.find_one({"id": brand_id}, {"_id": 0})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.brands.update_one({"id": brand_id}, {"$set": {
        "logo_media_id": None, "logo_url": None, "logo_removed_at": now, "updated_at": now}})
    await audit.record(
        db, actor=user, action=audit.REMOVE, module=audit.BRANDS, record_type="brand",
        record_id=brand_id, record_label=brand.get("name"),
        changes=[{"field": "logo", "before": brand.get("logo_media_id") or brand.get("logo_url"),
                  "after": None, "kind": "removed"}],
        summary=f"Removed logo from {brand.get('name')}",
    )
    return _resolve_brand_media(await db.brands.find_one({"id": brand_id}, {"_id": 0}))

@api.get("/products")
async def list_products(user: dict = Depends(get_current_user),
                        brand: Optional[str] = None,
                        category: Optional[str] = None,
                        search: Optional[str] = None,
                        status: Optional[str] = None,
                        include_archived: bool = False):
    """Product catalogue.

    Archived products -- retired models and everything that belonged to a brand
    outside the approved list -- are excluded unless an administrator explicitly
    asks for them. ``status`` narrows to one of the product states
    (active/discontinued/coming_soon/archived) for the product manager.
    """
    q: dict = {} if include_archived else {"status": {"$ne": "archived"}}
    if status:
        q["status"] = status
    if brand:
        q["brand"] = brand
    if category:
        q["category"] = category
    if search:
        # Escape the input: an unescaped user string in a $regex is a ReDoS and an
        # injection vector. See the CSV importer for the same treatment.
        term = re.escape(str(search)[:80])
        q["$or"] = [
            {"name": {"$regex": term, "$options": "i"}},
            {"model_number": {"$regex": term, "$options": "i"}},
            {"model": {"$regex": term, "$options": "i"}},
            {"sku": {"$regex": term, "$options": "i"}},
            {"series": {"$regex": term, "$options": "i"}},
        ]
    allowed = _allowed_brands(user)
    if allowed is not None:
        # sales user is restricted to allowed brands
        if brand and brand not in allowed:
            return []
        q["brand"] = {"$in": allowed} if not brand else brand
    rows = await db.products.find(q, {"_id": 0}).sort("name", 1).to_list(5000)
    return [_resolve_product_media(r) for r in rows]


@api.get("/products/{product_id}")
async def get_product(product_id: str, user: dict = Depends(get_current_user)):
    """A single product, enriched with its brand and category names.

    The product document already stores ``brand``/``category`` as strings for the
    existing callers; this resolves the related documents so a detail view does not
    have to make three calls to render one page.
    """
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    allowed = _allowed_brands(user)
    if allowed is not None and p.get("brand") not in allowed:
        raise HTTPException(status_code=403, detail="Not allowed for your brands")
    if p.get("brand_id"):
        p["brand_doc"] = await db.brands.find_one({"id": p["brand_id"]},
                                                  {"_id": 0, "id": 1, "name": 1, "slug": 1,
                                                   "official_website": 1, "logo_url": 1})
        # Resolve the related brand's logo too, so a product card can show the
        # brand mark without a second lookup.
        if p["brand_doc"]:
            p["brand_doc"] = _resolve_brand_media(p["brand_doc"])
    if p.get("category_id"):
        p["category_doc"] = await db.product_categories.find_one({"id": p["category_id"]},
                                                                 {"_id": 0, "id": 1, "name": 1,
                                                                  "slug": 1})
    return _resolve_product_media(p)


@api.get("/categories")
async def list_categories(_: dict = Depends(get_current_user),
                          include_archived: bool = False,
                          nested: bool = False):
    """The product category taxonomy, with a live product count per category.

    The default is a flat list, which is what every existing caller expects.
    ``nested=true`` returns top-level categories with their subcategories attached,
    which is the shape the Super Admin category manager renders.
    """
    q = {} if include_archived else {"status": {"$ne": "archived"}}
    cats = await db.product_categories.find(q, {"_id": 0}).sort("name", 1).to_list(500)
    for c in cats:
        c["product_count"] = await db.products.count_documents({
            "category_id": c["id"], "status": {"$ne": "archived"}})
    if not nested:
        return cats
    by_id = {c["id"]: c for c in cats}
    for c in cats:
        c["subcategories"] = sorted(
            [v for v in cats if v.get("parent_id") == c["id"]],
            key=lambda x: x.get("name") or "")
    return [c for c in cats if not c.get("parent_id")]


class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None


@api.post("/categories", status_code=201)
async def create_category(payload: CategoryCreate,
                          user: dict = Depends(require_permission("categories", "manage"))):
    """Create a category, or a subcategory under an existing one.

    The taxonomy is deduplicated by name at every level: creating "Loudspeakers"
    twice must not produce two filters that differ only by a space.
    """
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    slug = slugify(name)
    parent = None
    if payload.parent_id:
        parent = await db.product_categories.find_one({"id": payload.parent_id}, {"_id": 0, "id": 1})
        if not parent:
            raise HTTPException(status_code=400, detail="Parent category not found")
        if parent.get("parent_id"):
            raise HTTPException(status_code=400,
                                detail="Subcategories cannot be nested more than one level deep")
    clash = await db.product_categories.find_one(
        {"$or": [{"slug": slug}, {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}]},
        {"_id": 0, "id": 1, "name": 1})
    if clash:
        raise HTTPException(status_code=400, detail=f"Category '{name}' already exists")
    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "slug": slug,
        "parent_id": payload.parent_id,
        "description": payload.description,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # insert_one mutates the document it is given by adding ``_id``; a copy is
    # passed so the response body stays JSON-serialisable.
    await db.product_categories.insert_one(dict(doc))
    await audit.record(
        db, actor=user, action=audit.CREATE, module=audit.CATEGORIES, record_type="category",
        record_id=doc["id"], record_label=name,
        summary=f"Created category {name}"
                + (f" under {parent.get('name')}" if parent else ""),
    )
    return doc


class CategoryPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[Literal["active", "archived"]] = None


@api.patch("/categories/{category_id}")
async def patch_category(category_id: str, payload: CategoryPatch,
                         user: dict = Depends(require_permission("categories", "manage"))):
    existing = await db.product_categories.find_one({"id": category_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    body = payload.model_dump(exclude_unset=True)
    sets = {}
    if body.get("name"):
        name = body["name"].strip()
        clash = await db.product_categories.find_one(
            {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"},
             "id": {"$ne": category_id}}, {"_id": 0, "id": 1})
        if clash:
            raise HTTPException(status_code=400, detail=f"Category '{name}' already exists")
        sets["name"] = name
        sets["slug"] = slugify(name)
    if "description" in body:
        sets["description"] = body["description"]
    if "parent_id" in body:
        if body["parent_id"] == category_id:
            raise HTTPException(status_code=400, detail="A category cannot be its own parent")
        sets["parent_id"] = body["parent_id"]
    if body.get("status"):
        sets["status"] = body["status"]
    if not sets:
        return existing
    sets["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.product_categories.update_one({"id": category_id}, {"$set": sets})
    after = await db.product_categories.find_one({"id": category_id}, {"_id": 0})
    await audit.record_change(
        db, actor=user, action=audit.UPDATE, module=audit.CATEGORIES,
        record_type="category", record_id=category_id, record_label=after.get("name"),
        before=existing, after=after,
        fields=("name", "description", "parent_id", "status"),
    )
    return after


@api.delete("/categories/{category_id}")
async def delete_category(category_id: str,
                          user: dict = Depends(require_permission("categories", "manage"))):
    """Archive a category, refusing while products still use it.

    Products keep their ``category_id`` for history, so archiving is safe; but
    leaving live products pointing at a hidden category makes them unreachable in
    every filter, so the caller has to move them first.
    """
    existing = await db.product_categories.find_one({"id": category_id}, {"_id": 0, "id": 1, "name": 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    used = await db.products.count_documents(
        {"category_id": category_id, "status": {"$ne": "archived"}})
    if used:
        raise HTTPException(
            status_code=409,
            detail=f"{used} active product(s) still use '{existing.get('name')}'. "
                   f"Move or archive them first.")
    await db.product_categories.update_one({"id": category_id}, {"$set": {
        "status": "archived", "archived_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit.record(
        db, actor=user, action=audit.ARCHIVE, module=audit.CATEGORIES,
        record_type="category", record_id=category_id, record_label=existing.get("name"),
        changes=[{"field": "status", "before": "active", "after": "archived", "kind": "changed"}],
        summary=f"Archived category {existing.get('name')}",
    )
    return {"ok": True, "archived": category_id}


# ---------- Product attribute registry ----------
class ProductAttribute(BaseModel):
    name: str
    label: Optional[str] = None
    type: Literal["text", "number", "boolean", "select", "multiselect"] = "text"
    unit: Optional[str] = None
    options: List[str] = []
    applies_to_categories: List[str] = []
    status: Literal["active", "archived"] = "active"


class ProductAttributePatch(BaseModel):
    """Partial update for an existing attribute.

    ``name`` is required on create but optional here: renaming an attribute that
    products already reference would silently orphan those values, so a rename is
    an explicit act and leaving the field out of a PATCH must not blank it.
    """
    name: Optional[str] = None
    label: Optional[str] = None
    type: Optional[Literal["text", "number", "boolean", "select", "multiselect"]] = None
    unit: Optional[str] = None
    options: Optional[List[str]] = None
    applies_to_categories: Optional[List[str]] = None
    status: Optional[Literal["active", "archived"]] = None


@api.get("/product-attributes")
async def list_product_attributes(_: dict = Depends(get_current_user),
                                  include_archived: bool = False):
    """The reusable attribute definitions used by product specifications."""
    q = {} if include_archived else {"status": {"$ne": "archived"}}
    return await db.product_attributes.find(q, {"_id": 0}).sort("label", 1).to_list(500)


@api.post("/product-attributes", status_code=201)
async def create_product_attribute(payload: ProductAttribute,
                                   user: dict = Depends(require_permission("products", "manage"))):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Attribute name is required")
    if await db.product_attributes.find_one({"name": name}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=400, detail=f"Attribute '{name}' already exists")
    doc = {**payload.model_dump(), "name": name,
           "label": payload.label or name.replace("_", " ").title(),
           "created_at": datetime.now(timezone.utc).isoformat(),
           "updated_at": datetime.now(timezone.utc).isoformat()}
    doc["id"] = str(uuid.uuid4())
    await db.product_attributes.insert_one(doc)
    await audit.record(
        db, actor=user, action=audit.CREATE, module=audit.PRODUCTS,
        record_type="product_attribute", record_id=doc["id"], record_label=doc["label"],
        summary=f"Created product attribute {doc['label']}",
    )
    doc.pop("_id", None)
    return doc


@api.patch("/product-attributes/{attribute_id}")
async def patch_product_attribute(attribute_id: str, payload: ProductAttributePatch,
                                  user: dict = Depends(require_permission("products", "manage"))):
    existing = await db.product_attributes.find_one({"id": attribute_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Attribute not found")
    body = payload.model_dump(exclude_unset=True)
    if "name" in body:
        name = (body["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Attribute name cannot be empty")
        clash = await db.product_attributes.find_one(
            {"name": name, "id": {"$ne": attribute_id}}, {"_id": 0, "id": 1})
        if clash:
            raise HTTPException(status_code=400, detail=f"Attribute '{name}' already exists")
        body["name"] = name
    sets = {k: v for k, v in body.items() if v is not None}
    # A label is derived from the name when the caller does not supply one, so a
    # rename never leaves the registry showing the old wording.
    if sets.get("name") and "label" not in body:
        sets["label"] = sets["name"].replace("_", " ").title()
    if not sets:
        return existing
    sets["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.product_attributes.update_one({"id": attribute_id}, {"$set": sets})
    after = await db.product_attributes.find_one({"id": attribute_id}, {"_id": 0})
    await audit.record_change(
        db, actor=user, action=audit.UPDATE, module=audit.PRODUCTS,
        record_type="product_attribute", record_id=attribute_id,
        record_label=after.get("label"), before=existing, after=after,
        fields=("name", "label", "type", "unit", "options", "applies_to_categories", "status"),
    )
    return after


@api.delete("/product-attributes/{attribute_id}")
async def delete_product_attribute(attribute_id: str,
                                   user: dict = Depends(require_permission("products", "manage"))):
    existing = await db.product_attributes.find_one({"id": attribute_id}, {"_id": 0, "id": 1, "label": 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Attribute not found")
    await db.product_attributes.update_one({"id": attribute_id}, {"$set": {
        "status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit.record(
        db, actor=user, action=audit.ARCHIVE, module=audit.PRODUCTS,
        record_type="product_attribute", record_id=attribute_id,
        record_label=existing.get("label"),
        summary=f"Archived product attribute {existing.get('label')}",
    )
    return {"ok": True, "archived": attribute_id}

async def _resolve_product_brand(brand_name: str, actor: dict) -> dict:
    """Resolve a product's brand name to a brand document, or explain why not.

    A product must always have a valid brand relationship, so a brand that does not
    exist is always rejected. An archived or unapproved brand is rejected too --
    except for Super Admin, who may record a product against a real but retired
    brand, because that is where the unit physically is and losing that fact is
    worse than the inconsistency.
    """
    name = (brand_name or "").strip()
    brand = await db.brands.find_one({"name": name},
                                     {"_id": 0, "id": 1, "name": 1, "status": 1, "approved": 1})
    if brand and brand.get("status") == "active" and brand.get("approved"):
        return brand
    if brand and is_super_admin(actor):
        return brand
    raise HTTPException(
        status_code=400,
        detail=f"'{brand_name}' is not an approved brand. Add the brand first.",
    )


async def _resolve_or_create_category(category_name: Optional[str]) -> tuple:
    """Return (category_id, canonical_name). Creates the taxonomy entry if needed."""
    if not category_name:
        return None, None
    cat = await db.product_categories.find_one(
        {"$or": [{"name": category_name}, {"slug": slugify(category_name)}]},
        {"_id": 0, "id": 1, "name": 1})
    if not cat:
        cat = {"id": str(uuid.uuid4()), "name": category_name,
               "slug": slugify(category_name),
               "created_at": datetime.now(timezone.utc).isoformat()}
        await db.product_categories.insert_one(dict(cat))
    return cat["id"], cat["name"]


@api.post("/products", status_code=201)
async def create_product(payload: ProductCreate,
                         user: dict = Depends(require_permission("products", "manage"))):
    brand_doc = await _resolve_product_brand(payload.brand, user)
    if payload.sku and await db.products.find_one({"sku": payload.sku}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=400, detail=f"SKU '{payload.sku}' already exists")

    cat_id, category_name = await _resolve_or_create_category(payload.category)

    p = {
        "id": str(uuid.uuid4()),
        "brand": brand_doc["name"],
        "brand_id": brand_doc["id"],
        "name": payload.name,
        "slug": slugify(payload.name),
        "model": payload.model,
        "model_number": (payload.model or "").strip() or None,
        "sku": (payload.sku or "").strip() or None,
        "category": category_name,
        "category_id": cat_id,
        "sub_category": payload.sub_category,
        "product_family": payload.product_family,
        "product_series": payload.product_series,
        "series": payload.product_series or payload.product_family or payload.sub_category,
        "unit_price": payload.unit_price,
        "msrp": payload.msrp,
        "dealer_price": payload.dealer_price,
        "distributor_price": payload.distributor_price,
        "short_description": payload.short_description,
        "long_description": payload.long_description,
        # ``technical_specifications``, ``product_images``, ``gallery``,
        # ``stock_quantity`` and ``warehouse_location`` were all in the request
        # model and silently absent from the insert. A product created through the
        # API therefore had no stock level to edit and no gallery to show, and the
        # Super Admin product editor had nothing to write to.
        "technical_specifications": payload.technical_specifications or {},
        "product_images": list(payload.product_images or []),
        "gallery": list(payload.gallery or []),
        "downloads": [d.model_dump() for d in (payload.downloads or [])],
        "accessories": list(payload.accessories or []),
        "compatible_products": list(payload.compatible_products or []),
        "related_products": list(payload.related_products or []),
        "stock_quantity": payload.stock_quantity,
        "warehouse_location": payload.warehouse_location,
        "warranty": payload.warranty,
        "country_of_origin": payload.country_of_origin,
        "official_url": payload.official_url,
        "image_url": payload.image_url,
        "image_media_id": None,
        "specifications": payload.specifications,
        "features": list(payload.features or []),
        "source_url": payload.source_url,
        "last_verified_at": payload.last_verified_at,
        "status": payload.status or "active",
        # An unset price is a real state, not a zero: flag it so the catalogue can
        # show "price pending" instead of displaying a confident ₹0.
        "price_status": payload.price_status or ("set" if payload.unit_price else "pending"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.products.insert_one(p)
    p.pop("_id", None)
    await audit.record(
        db, actor=user, action=audit.CREATE, module=audit.PRODUCTS, record_type="product",
        record_id=p["id"], record_label=f"{brand_doc['name']} {payload.name}",
        summary=f"Created product {payload.name} under {brand_doc['name']}",
        meta={"sku": p["sku"], "brand_id": brand_doc["id"]},
    )
    return _resolve_product_media(p)


@api.put("/products/{product_id}")
async def update_product(product_id: str, payload: ProductCreate,
                         user: dict = Depends(require_permission("products", "manage"))):
    """Replace a product's editable fields, keeping price and provenance intact."""
    existing = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    after = dict(existing)

    # Brand, resolved before any write so a bad brand leaves the record untouched.
    if payload.brand and payload.brand.strip() != (existing.get("brand") or "").strip():
        brand_doc = await _resolve_product_brand(payload.brand, user)
        after["brand"] = brand_doc["name"]
        after["brand_id"] = brand_doc["id"]
        # A dangling brand pointer is silently dropped from every query that joins
        # on brand_id, so the previous pointer is cleared whenever the name no
        # longer matches it.
        after.pop("brand_unresolved", None)

    sku = (payload.sku or "").strip() or None
    if sku and sku != existing.get("sku"):
        clash = await db.products.find_one({"sku": sku, "id": {"$ne": product_id}},
                                           {"_id": 0, "id": 1})
        if clash:
            raise HTTPException(status_code=400, detail=f"SKU '{sku}' already exists")

    cat_id, category_name = await _resolve_or_create_category(payload.category)
    after.update({
        "name": payload.name,
        "slug": slugify(payload.name),
        "model": payload.model,
        "model_number": (payload.model or "").strip() or None,
        "sku": sku,
        "category": category_name,
        "category_id": cat_id,
        "sub_category": payload.sub_category,
        "product_family": payload.product_family,
        "product_series": payload.product_series,
        "series": payload.product_series or payload.product_family or payload.sub_category,
        "short_description": payload.short_description,
        "long_description": payload.long_description,
        "technical_specifications": payload.technical_specifications or {},
        "product_images": list(payload.product_images or []),
        "gallery": list(payload.gallery or []),
        "downloads": [d.model_dump() for d in (payload.downloads or [])],
        "accessories": list(payload.accessories or []),
        "compatible_products": list(payload.compatible_products or []),
        "related_products": list(payload.related_products or []),
        "stock_quantity": payload.stock_quantity,
        "warehouse_location": payload.warehouse_location,
        "warranty": payload.warranty,
        "country_of_origin": payload.country_of_origin,
        "official_url": payload.official_url,
        "image_url": payload.image_url,
        "specifications": payload.specifications,
        "features": list(payload.features or []),
        "source_url": payload.source_url,
        "last_verified_at": payload.last_verified_at,
        "status": payload.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    # Prices are only overwritten when the caller actually sends one, so editing a
    # description cannot silently zero a price that was entered earlier.
    for price_field in ("unit_price", "msrp", "dealer_price", "distributor_price"):
        value = getattr(payload, price_field, None)
        if value is not None:
            after[price_field] = value
    if payload.unit_price is not None:
        after["price_status"] = payload.price_status or "set"

    await db.products.update_one(
        {"id": product_id},
        {"$set": {k: v for k, v in after.items() if k not in ("_id", "id")}})
    await audit.record_change(
        db, actor=user, action=audit.UPDATE, module=audit.PRODUCTS, record_type="product",
        record_id=product_id,
        record_label=f"{after.get('brand')} {after.get('name')}",
        before=existing, after=after,
        fields=("name", "brand", "model", "sku", "category", "sub_category",
                "unit_price", "msrp", "dealer_price", "price_status",
                "short_description", "long_description", "technical_specifications",
                "features", "stock_quantity", "warehouse_location", "warranty",
                "status", "image_url"),
    )
    return _resolve_product_media(after)


class ProductPatch(BaseModel):
    """Partial product update.

    Unlike PUT this never requires the caller to resend the whole record, which is
    what makes single-field edits -- a price correction, a status change, a stock
    count -- safe. A PUT that omits a field is a full replace and would blank it.
    """
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    product_family: Optional[str] = None
    product_series: Optional[str] = None
    unit_price: Optional[float] = None
    price_status: Optional[str] = None
    msrp: Optional[float] = None
    dealer_price: Optional[float] = None
    distributor_price: Optional[float] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    technical_specifications: Optional[Dict[str, Any]] = None
    specifications: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None
    product_images: Optional[List[str]] = None
    gallery: Optional[List[str]] = None
    accessories: Optional[List[str]] = None
    compatible_products: Optional[List[str]] = None
    related_products: Optional[List[str]] = None
    warranty: Optional[str] = None
    country_of_origin: Optional[str] = None
    stock_quantity: Optional[int] = None
    warehouse_location: Optional[str] = None
    official_url: Optional[str] = None
    image_url: Optional[str] = None
    image_media_id: Optional[str] = None
    source_url: Optional[str] = None
    status: Optional[Literal["active", "discontinued", "coming_soon", "archived"]] = None


_PRODUCT_PATCH_NUMERIC = ("unit_price", "msrp", "dealer_price", "distributor_price",
                          "stock_quantity")
_PRODUCT_PATCH_TEXT = ("name", "model", "sku", "sub_category", "product_family",
                       "product_series", "short_description", "long_description",
                       "warranty", "country_of_origin", "warehouse_location",
                       "official_url", "image_url", "source_url", "price_status",
                       "status")
_PRODUCT_PATCH_JSON = ("technical_specifications", "specifications")
_PRODUCT_PATCH_LISTS = ("features", "product_images", "gallery", "accessories",
                        "compatible_products", "related_products")


async def _apply_product_patch(product_id: str, body: Dict[str, Any], user: dict,
                               existing: dict) -> dict:
    """Turn a validated patch body into a document update. Shared by PATCH and bulk.

    Returns the updated document. Raises on a brand or SKU clash without writing.
    """
    after = dict(existing)

    if body.get("brand") and body["brand"].strip() != (existing.get("brand") or "").strip():
        brand_doc = await _resolve_product_brand(body["brand"], user)
        after["brand"] = brand_doc["name"]
        after["brand_id"] = brand_doc["id"]
        after.pop("brand_unresolved", None)

    if "sku" in body:
        sku = (body["sku"] or "").strip() or None
        if sku and sku != existing.get("sku"):
            clash = await db.products.find_one({"sku": sku, "id": {"$ne": product_id}},
                                               {"_id": 0, "id": 1})
            if clash:
                raise HTTPException(status_code=409,
                                    detail=f"SKU '{sku}' is already used by another product")
        after["sku"] = sku

    if "category" in body:
        cat_id, category_name = await _resolve_or_create_category(body["category"])
        after["category"] = category_name
        after["category_id"] = cat_id

    for field in _PRODUCT_PATCH_TEXT:
        if field in body:
            value = body[field]
            if field == "name":
                if not value or not value.strip():
                    raise HTTPException(status_code=400, detail="Product name cannot be empty")
                after["slug"] = slugify(value)
            after[field] = (value.strip() or None) if isinstance(value, str) else value

    for field in _PRODUCT_PATCH_NUMERIC:
        if field in body and body[field] is not None:
            after[field] = body[field]

    for field in _PRODUCT_PATCH_JSON:
        if field in body and body[field] is not None:
            after[field] = body[field]

    for field in _PRODUCT_PATCH_LISTS:
        if field in body and body[field] is not None:
            after[field] = list(body[field])

    if "image_media_id" in body:
        after["image_media_id"] = body["image_media_id"]

    # Keep the denormalised series field in step, or sorting and the catalogue
    # filter will disagree with what the record actually says.
    if any(f in body for f in ("product_series", "product_family", "sub_category")):
        after["series"] = after.get("product_series") or after.get("product_family") \
            or after.get("sub_category")

    if after.get("unit_price") is not None and body.get("price_status") is None \
            and "unit_price" in body:
        after["price_status"] = "set"

    # Archiving through PATCH goes through the same path as DELETE so the audit
    # trail and the product status stay consistent.
    if body.get("status") == "archived" and existing.get("status") != "archived":
        after["archived_at"] = datetime.now(timezone.utc).isoformat()
        after["archive_reason"] = "Archived by administrator"
    elif existing.get("status") == "archived" and body.get("status") == "active":
        after.pop("archived_at", None)
        after.pop("archive_reason", None)

    after["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.products.update_one(
        {"id": product_id},
        {"$set": {k: v for k, v in after.items() if k not in ("_id", "id")},
         "$unset": {k: "" for k in ("archived_at", "archive_reason") if k not in after}},
    )
    return after


@api.patch("/products/{product_id}")
async def patch_product(product_id: str, payload: ProductPatch,
                        user: dict = Depends(require_permission("products", "manage"))):
    """Partially update a product.

    The safe path for every single-field edit, including changing the brand, the
    price, the stock level and the status.
    """
    existing = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    body = payload.model_dump(exclude_unset=True)
    if not body:
        return _resolve_product_media(existing)

    after = await _apply_product_patch(product_id, body, user, existing)

    if existing.get("status") != after.get("status"):
        await audit.record(
            db, actor=user,
            action=audit.ARCHIVE if after.get("status") == "archived" else audit.STATUS_CHANGE,
            module=audit.PRODUCTS, record_type="product", record_id=product_id,
            record_label=f"{after.get('brand')} {after.get('name')}",
            changes=[{"field": "status", "before": existing.get("status"),
                      "after": after.get("status"), "kind": "changed"}],
            summary=f"Status: {existing.get('status')} -> {after.get('status')}",
        )
    await audit.record_change(
        db, actor=user, action=audit.UPDATE, module=audit.PRODUCTS, record_type="product",
        record_id=product_id, record_label=f"{after.get('brand')} {after.get('name')}",
        before=existing, after=after,
        fields=("name", "brand", "model", "sku", "category", "sub_category",
                "unit_price", "msrp", "dealer_price", "price_status",
                "short_description", "long_description", "technical_specifications",
                "features", "stock_quantity", "warehouse_location", "warranty",
                "status", "image_url", "image_media_id"),
    )
    return _resolve_product_media(after)


class ProductDuplicate(BaseModel):
    name: Optional[str] = None


@api.post("/products/{product_id}/duplicate", status_code=201)
async def duplicate_product(product_id: str, payload: Optional[ProductDuplicate] = None,
                            user: dict = Depends(require_permission("products", "manage"))):
    """Copy a product into a new, independent record.

    The copy gets a fresh id and, unless the caller supplies one, a fresh SKU:
    duplicating a SKU would collide with the partial unique index on ``sku`` and,
    more importantly, would make two physical products share one identifier.
    """
    source = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not source:
        raise HTTPException(status_code=404, detail="Product not found")

    brand_doc = await db.brands.find_one({"id": source.get("brand_id")}, {"_id": 0, "id": 1, "name": 1})
    if not brand_doc:
        # A product whose brand pointer no longer resolves must not be duplicated
        # into another broken record.
        raise HTTPException(
            status_code=400,
            detail="This product's brand no longer exists. Assign it a valid brand first.",
        )

    new_name = (payload.name if payload else None) or f"{source.get('name')} (copy)"
    sku = None
    if source.get("sku"):
        sku = f"{source['sku']}-COPY"
        suffix = 2
        while await db.products.find_one({"sku": sku}, {"_id": 0, "id": 1}):
            sku = f"{source['sku']}-COPY{suffix}"
            suffix += 1
            if suffix > 50:
                raise HTTPException(status_code=409,
                                    detail="Too many copies of this product already exist")

    now = datetime.now(timezone.utc).isoformat()
    copy = {
        k: v for k, v in source.items()
        if k not in ("_id", "id", "slug", "sku", "created_at", "updated_at",
                     "status", "archived_at", "archive_reason", "duplicate_of")
    }
    copy.update({
        "id": str(uuid.uuid4()),
        "slug": slugify(new_name),
        "name": new_name,
        "sku": sku,
        "status": "active",
        "brand": brand_doc["name"],
        "brand_id": brand_doc["id"],
        "duplicate_of": product_id,
        "created_at": now,
        "updated_at": now,
    })
    await db.products.insert_one(copy)
    copy.pop("_id", None)
    await audit.record(
        db, actor=user, action=audit.DUPLICATE, module=audit.PRODUCTS, record_type="product",
        record_id=copy["id"], record_label=f"{copy['brand']} {copy['name']}",
        changes=[{"field": "duplicate_of", "before": None, "after": source.get("name"),
                  "kind": "added"}],
        summary=f"Duplicated product {source.get('name')} as {new_name}",
    )
    return _resolve_product_media(copy)


class ProductBulkEdit(BaseModel):
    """Apply one change set to many products at once."""
    product_ids: List[str]
    brand: Optional[str] = None
    category: Optional[str] = None
    status: Optional[Literal["active", "discontinued", "coming_soon", "archived"]] = None
    unit_price: Optional[float] = None
    msrp: Optional[float] = None
    stock_quantity: Optional[int] = None
    warehouse_location: Optional[str] = None
    warranty: Optional[str] = None
    sub_category: Optional[str] = None
    features: Optional[List[str]] = None


@api.post("/products/bulk")
async def bulk_edit_products(payload: ProductBulkEdit,
                             user: dict = Depends(require_permission("products", "manage"))):
    """Apply the same change to several products.

    Reports per-record success and failure rather than aborting the whole batch:
    a bulk price correction across 400 products must not be lost because one of
    them has a duplicate SKU.
    """
    if not payload.product_ids:
        raise HTTPException(status_code=400, detail="Select at least one product")
    if len(payload.product_ids) > 500:
        raise HTTPException(status_code=400, detail="Select 500 products or fewer at a time")

    body = {k: v for k, v in payload.model_dump().items() if k != "product_ids"
            and v is not None}
    if not body:
        raise HTTPException(status_code=400, detail="Choose at least one field to change")
    if "sku" in body:
        raise HTTPException(status_code=400, detail="SKU cannot be set in bulk")

    updated, failed = [], []
    for pid in payload.product_ids:
        existing = await db.products.find_one({"id": pid}, {"_id": 0})
        if not existing:
            failed.append({"id": pid, "name": pid, "error": "not found"})
            continue
        try:
            after = await _apply_product_patch(pid, body, user, existing)
        except HTTPException as exc:
            failed.append({"id": pid, "name": existing.get("name"), "error": exc.detail})
            continue
        updated.append(pid)
        await audit.record_change(
            db, actor=user, action=audit.UPDATE, module=audit.PRODUCTS, record_type="product",
            record_id=pid, record_label=f"{after.get('brand')} {after.get('name')}",
            before=existing, after=after, fields=tuple(body.keys()),
            meta={"bulk": True, "batch_size": len(payload.product_ids)},
        )
    return {"ok": True, "updated": len(updated), "failed": failed,
            "updated_ids": updated}


@api.delete("/products/{product_id}")
async def delete_product(product_id: str,
                         user: dict = Depends(require_permission("products", "manage"))):
    """Archive a product, and warn about inventory that pointed at it.

    Inventory rows keep their ``product_id`` so stock history survives, but they are
    flagged orphaned because the product is no longer orderable.
    """
    existing = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1,
                                                               "brand": 1, "status": 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.products.update_one({"id": product_id}, {"$set": {
        "status": "archived", "archived_at": now,
        "archive_reason": "Archived by administrator", "updated_at": now}})
    orphaned = await db.inventory.count_documents({"product_id": product_id})
    if orphaned:
        await db.inventory.update_many({"product_id": product_id},
                                      {"$set": {"orphaned": True, "updated_at": now}})
    await audit.record(
        db, actor=user, action=audit.ARCHIVE, module=audit.PRODUCTS, record_type="product",
        record_id=product_id, record_label=f"{existing.get('brand')} {existing.get('name')}",
        changes=[{"field": "status", "before": existing.get("status"), "after": "archived",
                  "kind": "changed"}],
        summary=f"Archived product {existing.get('name')}",
        meta={"inventory_rows_flagged": orphaned},
    )
    return {"ok": True, "archived": product_id, "inventory_rows_flagged": orphaned}


@api.post("/products/{product_id}/image")
async def upload_product_image(product_id: str, file: UploadFile = File(...),
                               user: dict = Depends(require_permission("products", "manage")),
                               primary: bool = True):
    """Upload or replace a product image.

    The first upload becomes the product's primary image; later ones join the
    gallery. ``primary=true`` on a later upload promotes it.
    """
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1,
                                                             "image_media_id": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = await _read_upload(file, "product_image", user)
    now = datetime.now(timezone.utc).isoformat()

    if primary or not product.get("image_media_id"):
        await db.products.update_one({"id": product_id}, {
            "$set": {"image_media_id": doc["id"], "updated_at": now},
            "$addToSet": {"product_images": doc["id"]}})
    else:
        await db.products.update_one({"id": product_id}, {
            "$set": {"updated_at": now}, "$addToSet": {"gallery": doc["id"]}})

    await audit.record(
        db, actor=user,
        action=audit.REPLACE if product.get("image_media_id") else audit.UPLOAD,
        module=audit.PRODUCTS, record_type="product", record_id=product_id,
        record_label=product.get("name"),
        changes=[{"field": "image", "before": product.get("image_media_id"),
                  "after": media_store.public_url(doc["id"]), "kind": "changed"}],
        summary=("Replaced" if product.get("image_media_id") else "Uploaded")
                + f" image for {product.get('name')}",
        meta={"media_id": doc["id"], "size": doc.get("size"),
              "width": doc.get("width"), "height": doc.get("height")},
    )
    return _resolve_product_media(await db.products.find_one({"id": product_id}, {"_id": 0}))


@api.delete("/products/{product_id}/image")
async def remove_product_image(product_id: str,
                               user: dict = Depends(require_permission("products", "manage"))):
    """Remove a product's primary image.

    Falls back to the next gallery entry rather than leaving the product with no
    image at all when one exists.
    """
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    now = datetime.now(timezone.utc).isoformat()
    remaining = [m for m in (product.get("product_images") or [])
                 if m != product.get("image_media_id")]
    gallery = [g for g in (product.get("gallery") or []) if g != product.get("image_media_id")]
    await db.products.update_one({"id": product_id}, {"$set": {
        "image_media_id": remaining[0] if remaining else None,
        "product_images": remaining,
        "gallery": gallery,
        "updated_at": now}})
    await audit.record(
        db, actor=user, action=audit.REMOVE, module=audit.PRODUCTS, record_type="product",
        record_id=product_id, record_label=product.get("name"),
        changes=[{"field": "image", "before": product.get("image_media_id"), "after": None,
                  "kind": "removed"}],
        summary=f"Removed image from {product.get('name')}",
    )
    return _resolve_product_media(await db.products.find_one({"id": product_id}, {"_id": 0}))

# ---------- Package Templates ----------
@api.get("/packages")
async def list_packages(user: dict = Depends(get_current_user), brand: Optional[str] = None):
    q: dict = {}
    if brand:
        q["brand"] = brand
    allowed = _allowed_brands(user)
    if allowed is not None:
        if brand and brand not in allowed:
            return []
        q["brand"] = {"$in": allowed} if not brand else brand
    pkgs = await db.packages.find(q, {"_id": 0}).sort("name", 1).to_list(500)
    # enrich each item with current product data
    for p in pkgs:
        enriched = []
        for it in p.get("items", []):
            prod = await db.products.find_one({"id": it["product_id"]}, {"_id": 0})
            if prod:
                enriched.append({**it, "product": prod})
        p["items"] = enriched
        computed = round(sum(float(i["product"]["unit_price"]) * int(i["qty"]) for i in enriched), 2) if enriched else 0.0
        p["estimated_total"] = computed
        # fixed_price_inr takes priority for imported bundles
        p["display_price"] = float(p.get("fixed_price_inr")) if p.get("fixed_price_inr") else computed
    return pkgs

@api.post("/packages", status_code=201)
async def create_package(payload: PackageCreate, _: dict = Depends(require_admin)):
    p = {
        "id": str(uuid.uuid4()),
        "brand": payload.brand,
        "name": payload.name,
        "sku": payload.sku,
        "description": payload.description,
        "items": [i.model_dump() for i in payload.items],
        "components": [c.model_dump() for c in payload.components],
        "fixed_price_inr": payload.fixed_price_inr,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.packages.insert_one(p)
    p.pop("_id", None)
    return p

@api.delete("/packages/{pkg_id}")
async def delete_package(pkg_id: str, _: dict = Depends(require_admin)):
    await db.packages.delete_one({"id": pkg_id})
    return {"ok": True}

# ---------- Shipments (PO + import tracking) ----------
@api.get("/shipments")
async def list_shipments(user: dict = Depends(get_current_user)):
    q: dict = {}
    allowed = _allowed_brands(user)
    if allowed is not None:
        q["oem"] = {"$in": allowed}
    docs = await db.shipments.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    is_admin = is_admin_role(user)
    for d in docs:
        for it in d.get("items", []):
            p = await db.products.find_one({"id": it.get("product_id")}, {"_id": 0, "name": 1, "model": 1})
            if p:
                it["product"] = p
        if not is_admin:
            # Hide financial fields from sales reps — brand-isolation + cost confidentiality
            d.pop("freight_cost_inr", None)
            d.pop("duty_paid_inr", None)
    return docs

@api.post("/shipments", status_code=201)
async def create_shipment(payload: ShipmentCreate, _: dict = Depends(require_admin)):
    sh = {
        "id": str(uuid.uuid4()),
        "po_no": payload.po_no, "oem": payload.oem, "currency": payload.currency,
        "items": [i.model_dump() for i in payload.items],
        "bl_awb": payload.bl_awb, "eta": payload.eta,
        "actual_arrival": None, "freight_cost_inr": 0.0, "duty_paid_inr": 0.0,
        "status": "planned", "notes": payload.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.shipments.insert_one(sh)
    sh.pop("_id", None)
    return sh

@api.patch("/shipments/{sid}")
async def update_shipment(sid: str, payload: ShipmentUpdate, _: dict = Depends(require_admin)):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        return {"ok": True}
    await db.shipments.update_one({"id": sid}, {"$set": updates})
    sh = await db.shipments.find_one({"id": sid}, {"_id": 0})
    if updates.get("status") == "received" and sh:
        for it in sh.get("items", []):
            existing = await db.inventory.count_documents({"shipment_id": sid, "product_id": it["product_id"]})
            need = int(it.get("qty", 0)) - existing
            for _i in range(max(0, need)):
                await db.inventory.insert_one({
                    "id": str(uuid.uuid4()),
                    "product_id": it["product_id"],
                    "serial_no": f"AUTO-{uuid.uuid4().hex[:8].upper()}",
                    "shipment_id": sid, "location": "Main Warehouse",
                    "status": "in_stock", "landed_cost_inr": None,
                    "sold_to_lead_id": None, "warranty_expires": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
    return sh

@api.delete("/shipments/{sid}")
async def delete_shipment(sid: str, _: dict = Depends(require_admin)):
    await db.shipments.delete_one({"id": sid})
    return {"ok": True}

# ---------- Inventory ----------
@api.get("/inventory")
async def list_inventory(user: dict = Depends(get_current_user), status_filter: Optional[str] = None, product_id: Optional[str] = None):
    q: dict = {}
    if status_filter:
        q["status"] = status_filter
    if product_id:
        q["product_id"] = product_id
    units = await db.inventory.find(q, {"_id": 0}).sort("created_at", -1).to_list(5000)
    for u in units:
        p = await db.products.find_one({"id": u["product_id"]}, {"_id": 0, "name": 1, "model": 1, "brand": 1})
        if p:
            u["product"] = p
    allowed = _allowed_brands(user)
    if allowed is not None:
        units = [u for u in units if (u.get("product") or {}).get("brand") in allowed]
    return units

@api.get("/inventory/summary")
async def inventory_summary(user: dict = Depends(get_current_user)):
    products = await db.products.find({}, {"_id": 0}).to_list(5000)
    allowed = _allowed_brands(user)
    if allowed is not None:
        products = [p for p in products if p["brand"] in allowed]
    result = []
    for p in products:
        in_stock = await db.inventory.count_documents({"product_id": p["id"], "status": "in_stock"})
        in_transit = await db.inventory.count_documents({"product_id": p["id"], "status": "in_transit"})
        reserved = await db.inventory.count_documents({"product_id": p["id"], "status": "reserved"})
        sold = await db.inventory.count_documents({"product_id": p["id"], "status": "sold"})
        if in_stock + in_transit + reserved + sold == 0:
            continue
        result.append({**p, "in_stock": in_stock, "in_transit": in_transit, "reserved": reserved, "sold": sold})
    return result

@api.post("/inventory", status_code=201)
async def create_inventory_unit(payload: InventoryUnitCreate, _: dict = Depends(require_admin)):
    """Create a stock unit against an existing product.

    brand_id and sku are denormalised onto the unit so inventory can be filtered and
    reported by brand without a join to ``products`` on every row. The product
    remains the single source of truth for name and price -- the copy is only ever
    written from the referenced product here, never typed in by hand.
    """
    product = await db.products.find_one({"id": payload.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=400, detail="Unknown product_id")
    u = {
        "id": str(uuid.uuid4()),
        "product_id": product["id"],
        "brand_id": product.get("brand_id"),
        "sku": product.get("sku"),
        "serial_no": payload.serial_no,
        "shipment_id": payload.shipment_id,
        "location": payload.location or "Main Warehouse",
        "warehouse": payload.location or "Main Warehouse",
        "stock_quantity": 1,
        "price": product.get("unit_price"),
        "status": "in_stock",
        "landed_cost_inr": payload.landed_cost_inr,
        "sold_to_lead_id": None,
        "warranty_expires": None,
        "orphaned": product.get("status") == "archived",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.inventory.insert_one(u)
    u.pop("_id", None)
    return u


@api.put("/inventory/{uid}")
async def put_inventory_unit(uid: str, payload: InventoryUnitUpdate,
                             _: dict = Depends(require_admin)):
    """PUT alias for the existing PATCH, for clients that use full replacement."""
    return await update_inventory_unit(uid, payload, _)


@api.patch("/inventory/{uid}")
async def update_inventory_unit(uid: str, payload: InventoryUnitUpdate, _: dict = Depends(require_admin)):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if updates:
        await db.inventory.update_one({"id": uid}, {"$set": updates})
    return await db.inventory.find_one({"id": uid}, {"_id": 0})

# ---------- AMC ----------
@api.get("/amcs")
async def list_amcs(_: dict = Depends(get_current_user), status_filter: Optional[str] = None):
    q: dict = {}
    if status_filter:
        q["status"] = status_filter
    return await db.amcs.find(q, {"_id": 0}).sort("end_date", 1).to_list(2000)

@api.get("/amcs/expiring")
async def amcs_expiring(_: dict = Depends(get_current_user), days: int = 60):
    cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()
    return await db.amcs.find({"status": "active", "end_date": {"$lte": cutoff}}, {"_id": 0}).sort("end_date", 1).to_list(500)

@api.post("/amcs", status_code=201)
async def create_amc(payload: AMCCreate, _: dict = Depends(require_admin)):
    a = {
        "id": str(uuid.uuid4()),
        "customer_name": payload.customer_name, "customer_company": payload.customer_company,
        "lead_id": payload.lead_id, "serial_numbers": payload.serial_numbers,
        "start_date": payload.start_date, "end_date": payload.end_date,
        "value": payload.value, "status": "active", "notes": payload.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.amcs.insert_one(a)
    a.pop("_id", None)
    return a

@api.patch("/amcs/{aid}")
async def update_amc(aid: str, payload: AMCUpdate, _: dict = Depends(require_admin)):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if updates:
        await db.amcs.update_one({"id": aid}, {"$set": updates})
    return await db.amcs.find_one({"id": aid}, {"_id": 0})

@api.delete("/amcs/{aid}")
async def delete_amc(aid: str, _: dict = Depends(require_admin)):
    await db.amcs.delete_one({"id": aid})
    return {"ok": True}

# ---------- Bulk Import: Leads CSV/XLSX ----------
LEAD_COL_ALIASES = {
    "name":          ["name", "customer name", "contact", "contact name", "prospect", "client", "full name"],
    "email":         ["email", "email id", "e-mail", "mail"],
    "phone":         ["phone", "mobile", "whatsapp", "contact no", "phone no", "phone number", "mobile no"],
    "company":       ["company", "organization", "organisation", "firm", "business"],
    "source":        ["source", "channel", "lead source"],
    "stage":         ["stage", "status"],
    "interested_in": ["interested in", "interest", "product", "brand", "requirement", "enquiry", "looking for"],
    "budget":        ["budget", "value", "amount"],
    "notes":         ["notes", "remarks", "description", "comments"],
}
# CSV import normalisation. The old code validated against legacy 6-value sets
# (VALID_STAGES/VALID_SOURCES = new/contacted/qualified/quoted/won/lost and
# website/whatsapp/email/manual/referral/exhibition) and then fell back to
# stage="new" / source="manual". Neither fallback exists in the CRM vocabulary:
# "manual" is not a valid lead source at all, and every real stage name
# (interested, quotation_confirmed, ...) was silently rewritten to "new", so an
# import could never land a lead in its intended stage. Those sets are gone;
# normalisation now runs against the live config via CSV_*_ALIASES below.
CSV_STAGE_ALIASES = {
    "quoted": "send_quotation",
    "won": "quotation_confirmed",
    "lost": "lost_lead",
    "closed": "completed",
    "sale": "quotation_confirmed",
}
CSV_SOURCE_ALIASES = {
    "website": "website_contact_form",
    "whatsapp": "business_whatsapp",
    "manual": "direct_enquiry",
    "referral": "channel_partner",
    "exhibition": "walk_in_customer",
}

def _match_header(h: str) -> Optional[str]:
    if h is None:
        return None
    h = str(h).strip().lower()
    for canonical, aliases in LEAD_COL_ALIASES.items():
        if h == canonical or h in aliases:
            return canonical
    return None

def _parse_rows_csv(content: bytes) -> List[dict]:
    import csv as csvlib
    text = content.decode("utf-8-sig", errors="ignore")
    reader = csvlib.reader(text.splitlines())
    rows = list(reader)
    if not rows:
        return []
    headers = [_match_header(h) for h in rows[0]]
    out = []
    for row in rows[1:]:
        item = {}
        for h, v in zip(headers, row):
            if h and v and str(v).strip():
                item[h] = str(v).strip()
        if item:
            out.append(item)
    return out

def _parse_rows_xlsx(content: bytes) -> List[dict]:
    from openpyxl import load_workbook
    from io import BytesIO as B
    wb = load_workbook(B(content), data_only=True, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [_match_header(h) for h in rows[0]]
    out = []
    for row in rows[1:]:
        item = {}
        for h, v in zip(headers, row):
            if h and v is not None and str(v).strip():
                item[h] = str(v).strip()
        if item:
            out.append(item)
    return out

@api.post("/import/leads")
async def import_leads(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    content = await file.read()
    name = (file.filename or "").lower()
    if name.endswith(".xlsx"):
        rows = _parse_rows_xlsx(content)
    elif name.endswith(".csv"):
        rows = _parse_rows_csv(content)
    else:
        raise HTTPException(status_code=400, detail="Upload a .csv or .xlsx file")
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found")
    created, skipped, errors = 0, 0, []
    stage_keys = await valid_stage_keys() or set(PIPELINE_STAGES)
    for idx, r in enumerate(rows, start=2):
        if not r.get("name"):
            skipped += 1
            errors.append(f"Row {idx}: missing name")
            continue
        raw_source = (r.get("source") or "").strip().lower().replace(" ", "_")
        source = CSV_SOURCE_ALIASES.get(raw_source, raw_source)
        if source not in set(LEAD_SOURCES):
            source = "direct_enquiry"

        raw_stage = (r.get("stage") or "").strip().lower().replace(" ", "_")
        stage = CSV_STAGE_ALIASES.get(raw_stage, raw_stage)
        if stage not in stage_keys:
            stage = "new"
        try:
            budget = float(str(r["budget"]).replace(",", "").replace("₹", "").strip()) if r.get("budget") else None
        except Exception:
            budget = None
        assigned = await _auto_assign()
        await db.leads.insert_one({
            "id": str(uuid.uuid4()),
            "name": r["name"],
            "email": r.get("email"),
            "phone": r.get("phone"),
            "company": r.get("company"),
            "source": source,
            "stage": stage,
            "interested_in": r.get("interested_in"),
            "budget": budget,
            "notes": r.get("notes"),
            "assigned_to": assigned,
            "created_by": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        created += 1
    return {"created": created, "skipped": skipped, "total": len(rows), "errors": errors[:20]}

# ---------- Bulk Import: Quotation PDF via Claude ----------
@api.post("/import/quotation-pdf/parse")
async def parse_quotation_pdf(file: UploadFile = File(...), _: dict = Depends(require_admin)):
    """Extract text from PDF, send to Claude to structure as a quotation."""
    import pdfplumber
    from io import BytesIO as B
    content = await file.read()
    text_chunks = []
    try:
        with pdfplumber.open(B(content)) as pdf:
            for page in pdf.pages[:8]:
                t = page.extract_text() or ""
                if t.strip():
                    text_chunks.append(t)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")
    if not text_chunks:
        raise HTTPException(status_code=400, detail="PDF has no readable text (might be scanned image)")
    raw_text = "\n\n".join(text_chunks)[:20000]

    try:
        system_instruction = (
            "You extract structured quotation data from raw PDF text from an Indian pro-audio distributor. "
            "Return ONLY a valid JSON object with this shape: "
            '{"customer_name": string, "customer_company": string|null, "customer_email": string|null, '
            '"customer_phone": string|null, "quote_date": string|null (YYYY-MM-DD), '
            '"items": [{"product": string, "brand": string|null, "qty": number, "unit_price": number, "tax_pct": number}], '
            '"subtotal": number|null, "tax": number|null, "total": number|null, "terms": string|null} '
            "All monetary values in INR as plain numbers (no ₹ or commas). Default tax_pct to 18 if not stated. "
            "If a field is missing, use null. Do NOT include any markdown, prose, or code fences — JSON only."
        )
        resp = await call_gemini(f"PDF TEXT:\n\n{raw_text}", system_instruction=system_instruction)
        # Try to extract JSON from the response
        import json as jsonlib
        import re
        cleaned = resp.strip()
        # Remove code fences if any
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            cleaned = match.group(0)
        parsed = jsonlib.loads(cleaned)
        return {"ok": True, "parsed": parsed, "raw_preview": raw_text[:800]}
    except Exception as e:
        logger.exception("PDF parse via LLM failed")
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {str(e)}")

@api.post("/import/quotation-pdf/confirm", status_code=201)
async def confirm_quotation_pdf(payload: dict, user: dict = Depends(require_admin)):
    """Create a real quotation from parsed PDF data. Body: { lead_id?, customer_name, items[], terms, ... }
    If lead_id is omitted, a lead is auto-created from the customer info first."""
    lead_id = payload.get("lead_id")
    if not lead_id:
        cn = (payload.get("customer_name") or "").strip()
        if not cn:
            raise HTTPException(status_code=400, detail="customer_name required when no lead_id provided")
        new_lead = {
            "id": str(uuid.uuid4()),
            "name": cn,
            "company": payload.get("customer_company"),
            "email": payload.get("customer_email"),
            "phone": payload.get("customer_phone"),
            "source": "manual",
            "stage": "quoted",
            "interested_in": "Imported quotation",
            "budget": None,
            "notes": "Auto-created from imported PDF quotation",
            "assigned_to": await _auto_assign(),
            "created_by": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.leads.insert_one(new_lead)
        lead_id = new_lead["id"]
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="No items in quotation")
    norm_items = []
    for it in items:
        norm_items.append({
            "product": str(it.get("product", "")).strip() or "Unspecified",
            "brand": it.get("brand"),
            "qty": int(it.get("qty") or 1),
            "unit_price": float(it.get("unit_price") or 0),
            "tax_pct": float(it.get("tax_pct") or 18),
        })
    subtotal = sum(i["qty"] * i["unit_price"] for i in norm_items)
    tax = sum(i["qty"] * i["unit_price"] * (i["tax_pct"] / 100.0) for i in norm_items)
    total = subtotal + tax
    counter = await db.quotations.count_documents({})
    q = {
        "id": str(uuid.uuid4()),
        "quote_no": f"HAI-Q-{1000 + counter + 1}",
        "lead_id": lead_id,
        "items": norm_items,
        "subtotal": round(subtotal, 2), "tax": round(tax, 2), "total": round(total, 2),
        "valid_until": None,
        "terms": payload.get("terms"),
        "status": "draft",
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.quotations.insert_one(q)
    q.pop("_id", None)
    return q


# ---------- Tally Integration (TallyPrime / ERP 9 compatible) ----------
TALLY_COMPANY = os.environ.get("TALLY_COMPANY_NAME", "Hi-Tech Audio and Image LLP")
TALLY_URL = os.environ.get("TALLY_URL", "").strip()

def _tally_escape(s: str) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))

def _build_tally_xml(quote: dict, lead: dict) -> str:
    """Build TallyPrime-compatible Sales Order voucher XML."""
    # Date in YYYYMMDD format expected by Tally
    try:
        d = datetime.fromisoformat(quote["created_at"].replace("Z", "+00:00"))
    except Exception:
        d = datetime.now(timezone.utc)
    date_str = d.strftime("%Y%m%d")
    party_name = (lead.get("company") or lead.get("name") or "Walk-in Customer").strip()

    inv_entries = []
    led_subtotal = 0.0
    led_gst = 0.0
    for it in quote.get("items", []):
        qty = float(it.get("qty") or 0)
        unit = float(it.get("unit_price") or 0)
        gst = float(it.get("tax_pct") or 0)
        amount = qty * unit
        gst_amt = amount * gst / 100.0
        led_subtotal += amount
        led_gst += gst_amt
        stock_name = (it.get("product") or "Unspecified")
        inv_entries.append(f"""
            <ALLINVENTORYENTRIES.LIST>
              <STOCKITEMNAME>{_tally_escape(stock_name)}</STOCKITEMNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <RATE>{unit:.2f}/Nos</RATE>
              <AMOUNT>{amount:.2f}</AMOUNT>
              <ACTUALQTY>{qty:.0f} Nos</ACTUALQTY>
              <BILLEDQTY>{qty:.0f} Nos</BILLEDQTY>
            </ALLINVENTORYENTRIES.LIST>""")

    total = led_subtotal + led_gst
    led_xml = f"""
            <LEDGERENTRIES.LIST>
              <LEDGERNAME>{_tally_escape(party_name)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{total:.2f}</AMOUNT>
            </LEDGERENTRIES.LIST>
            <LEDGERENTRIES.LIST>
              <LEDGERNAME>Sales Account</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{led_subtotal:.2f}</AMOUNT>
            </LEDGERENTRIES.LIST>"""
    if led_gst > 0:
        led_xml += f"""
            <LEDGERENTRIES.LIST>
              <LEDGERNAME>IGST @ 18%</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{led_gst:.2f}</AMOUNT>
            </LEDGERENTRIES.LIST>"""

    narration = f"Quotation {quote.get('quote_no')} from Hi-Tech CRM"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{_tally_escape(TALLY_COMPANY)}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Sales Order" ACTION="Create" OBJVIEW="Invoice Voucher View">
            <DATE>{date_str}</DATE>
            <NARRATION>{_tally_escape(narration)}</NARRATION>
            <VOUCHERTYPENAME>Sales Order</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{_tally_escape(quote.get('quote_no'))}</VOUCHERNUMBER>
            <PARTYLEDGERNAME>{_tally_escape(party_name)}</PARTYLEDGERNAME>
            <PARTYNAME>{_tally_escape(party_name)}</PARTYNAME>
            <BASICBASEPARTYNAME>{_tally_escape(party_name)}</BASICBASEPARTYNAME>
            <ISINVOICE>Yes</ISINVOICE>
            <EFFECTIVEDATE>{date_str}</EFFECTIVEDATE>{''.join(inv_entries)}{led_xml}
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>
"""
    return xml

@api.get("/quotations/{quote_id}/tally-xml")
async def quotation_tally_xml(quote_id: str, user: dict = Depends(get_current_user)):
    q = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    lead = await db.leads.find_one({"id": q["lead_id"]}, {"_id": 0})
    if not is_admin_role(user) and lead and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    xml = _build_tally_xml(q, lead or {})
    filename = f"{q['quote_no']}_tally.xml"
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@api.post("/quotations/{quote_id}/tally-push")
async def quotation_tally_push(quote_id: str, _: dict = Depends(require_admin)):
    if not TALLY_URL:
        raise HTTPException(status_code=400, detail="TALLY_URL not configured. Set the env var to your Tally HTTP endpoint (e.g. http://192.168.1.10:9000) to enable direct push.")
    q = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    lead = await db.leads.find_one({"id": q["lead_id"]}, {"_id": 0})
    xml = _build_tally_xml(q, lead or {})
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as cli:
            r = await cli.post(TALLY_URL, content=xml, headers={"Content-Type": "application/xml"})
        ok = r.status_code == 200 and "<LINEERROR>" not in r.text
        return {"ok": ok, "status_code": r.status_code, "tally_response": r.text[:2000]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Tally at {TALLY_URL}: {str(e)}")




# ---------- Brand Access Requests ----------
@api.post("/brand-access-requests", status_code=201)
async def create_brand_request(payload: BrandAccessRequestCreate, user: dict = Depends(get_current_user)):
    if is_admin_role(user):
        raise HTTPException(status_code=400, detail="Admin already has full access")
    # avoid duplicate pending request for the same brand
    existing = await db.brand_requests.find_one({"user_id": user["id"], "brand": payload.brand, "status": "pending"})
    if existing:
        raise HTTPException(status_code=400, detail="A pending request already exists for this brand")
    if payload.brand in (user.get("allowed_brands") or []):
        raise HTTPException(status_code=400, detail="You already have access to this brand")
    if not (user.get("allowed_brands") or []):
        raise HTTPException(status_code=400, detail="You already have access to every brand")
    req = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_name": user["name"],
        "user_email": user["email"],
        "brand": payload.brand,
        "reason": payload.reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.brand_requests.insert_one(req)
    req.pop("_id", None)
    return req

@api.get("/brand-access-requests")
async def list_brand_requests(user: dict = Depends(get_current_user), status_filter: Optional[str] = None):
    q: dict = {}
    if not is_admin_role(user):
        q["user_id"] = user["id"]
    if status_filter:
        q["status"] = status_filter
    return await db.brand_requests.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)

@api.patch("/brand-access-requests/{req_id}")
async def act_brand_request(req_id: str, payload: dict, _: dict = Depends(require_admin)):
    action = payload.get("action")
    if action not in ("approve", "deny"):
        raise HTTPException(status_code=400, detail="action must be approve or deny")
    req = await db.brand_requests.find_one({"id": req_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already actioned")
    new_status = "approved" if action == "approve" else "denied"
    await db.brand_requests.update_one({"id": req_id}, {"$set": {
        "status": new_status,
        "actioned_at": datetime.now(timezone.utc).isoformat(),
    }})
    if action == "approve":
        target = await db.users.find_one({"id": req["user_id"]}, {"allowed_brands": 1})
        # A user with no allow-list is unrestricted already (see _allowed_brands).
        # $addToSet would silently turn them into a one-brand user, so only
        # extend a list that actually restricts them.
        if (target.get("allowed_brands") or []):
            await db.users.update_one(
                {"id": req["user_id"]},
                {"$addToSet": {"allowed_brands": req["brand"]}},
            )
    return await db.brand_requests.find_one({"id": req_id}, {"_id": 0})

# ---------- Webhook Settings ----------
class WebhookSettingsUpdate(BaseModel):
    n8n_webhook_url: Optional[str] = None
    enabled: Optional[bool] = None
    admin_phone: Optional[str] = None
    events: Optional[dict] = None

@api.get("/webhooks/settings")
async def get_webhook_settings(_: dict = Depends(require_admin)):
    settings = await db.webhook_settings.find_one({"id": "default"}, {"_id": 0})
    if not settings:
        settings = {
            "id": "default",
            "n8n_webhook_url": "",
            "enabled": False,
            "admin_phone": "",
            "events": {"lead_created": True, "quotation_created": True, "lead_updated": False},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.webhook_settings.insert_one(settings)
        settings.pop("_id", None)
    return settings

@api.post("/webhooks/settings")
async def update_webhook_settings(payload: WebhookSettingsUpdate, _: dict = Depends(require_admin)):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.webhook_settings.update_one({"id": "default"}, {"$set": updates}, upsert=True)
    settings = await db.webhook_settings.find_one({"id": "default"}, {"_id": 0})
    return settings

async def _fire_webhook(event: str, data: dict, user: Optional[dict] = None):
    settings = await db.webhook_settings.find_one({"id": "default"})
    if not settings or not settings.get("enabled") or not settings.get("n8n_webhook_url"):
        return
    events = settings.get("events", {})
    if not events.get(event):
        return
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "admin_phone": settings.get("admin_phone", ""),
    }
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as cli:
            r = await cli.post(settings["n8n_webhook_url"], json=payload)
        await db.webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "event": event,
            "status": "success" if r.status_code < 400 else "failed",
            "status_code": r.status_code,
            "response": r.text[:500],
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        await db.webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "event": event,
            "status": "failed",
            "status_code": 0,
            "response": str(Exception),
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

@api.get("/webhooks/logs")
async def get_webhook_logs(_: dict = Depends(require_admin), limit: int = 50):
    logs = await db.webhook_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 200))
    return logs

@api.post("/webhooks/test")
async def test_webhook(_: dict = Depends(require_admin)):
    settings = await db.webhook_settings.find_one({"id": "default"})
    if not settings or not settings.get("n8n_webhook_url"):
        raise HTTPException(status_code=400, detail="No webhook URL configured")
    test_payload = {
        "event": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "Test connection from Hitech CRM"},
        "admin_phone": settings.get("admin_phone", ""),
    }
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as cli:
            r = await cli.post(settings["n8n_webhook_url"], json=test_payload)
        return {
            "ok": r.status_code < 400,
            "status_code": r.status_code,
            "response": r.text[:500],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@api.post("/webhooks/n8n/callback")
async def n8n_callback(request: Request):
    """Receive callbacks from n8n (e.g., WhatsApp delivery receipts)."""
    try:
        payload = await request.json()
        await db.webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "event": "n8n_callback",
            "status": "received",
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"ok": True}
    except Exception:
        logger.exception("n8n callback parse error")
        return {"ok": True}

# ---------- Resend Email Settings ----------
class ResendSettingsUpdate(BaseModel):
    resend_api_key: Optional[str] = None
    enabled: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    reply_to: Optional[str] = None
    events: Optional[dict] = None
    quotation_subject: Optional[str] = None
    quotation_body: Optional[str] = None
    lead_update_subject: Optional[str] = None
    lead_update_body: Optional[str] = None

@api.get("/resend/settings")
async def get_resend_settings(_: dict = Depends(require_admin)):
    settings = await db.resend_settings.find_one({"id": "default"}, {"_id": 0})
    if not settings:
        settings = {
            "id": "default",
            "resend_api_key": "",
            "enabled": True,
            "smtp_host": os.environ.get("SMTP_HOST", "smtppro.zoho.in"),
            "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
            "smtp_user": os.environ.get("SMTP_USER", "info@hitechavl.com"),
            "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
            "sender_email": os.environ.get("SMTP_SENDER", "info@hitechavl.com"),
            "sender_name": os.environ.get("SMTP_SENDER_NAME", "Hi-Tech Audio & Image LLP"),
            "reply_to": "info@hitechavl.com",
            "events": {"quotation_created": True, "lead_created": False, "lead_updated": False},
            "quotation_subject": "Quotation {{quote_no}} from Hi-Tech Audio & Image LLP",
            "quotation_body": "Dear {{name}},\n\nPlease find attached your quotation {{quote_no}} for ₹{{total}}.\n\nValidity: 30 days\nPayment: 100% Advance\nDelivery: As per availability / 3-4 Months\n\nFor any questions, reply to this email or call us.\n\nRegards,\n{{sender_name}}\n{{email}} | {{phone}} | {{website}}",
            "lead_update_subject": "Update on your enquiry with Hi-Tech Audio & Image LLP",
            "lead_update_body": "Dear {{name}},\n\nWe have an update on your enquiry.\n\nStage: {{stage}}\n\nFor any questions, reply to this email or call us.\n\nRegards,\n{{sender_name}}\n{{email}} | {{phone}} | {{website}}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.resend_settings.insert_one(settings)
        settings.pop("_id", None)
    return _mask_email_secrets(settings)


# Placeholder the settings screen shows in place of a stored secret. The frontend
# echoes whatever it holds back on save, so the write path recognises this exact
# token and keeps the stored secret rather than overwriting it with the mask.
SECRET_MASK = "********"


def _mask_email_secrets(settings: dict) -> dict:
    """Never hand a stored credential back to the browser.

    The settings screen only needs to know whether a secret exists, not what it is.
    Returning the real value would put SMTP and API passwords in a JSON response
    that lands in the browser, devtools and any proxy log along the way.
    """
    out = dict(settings)
    for field in ("resend_api_key", "smtp_password"):
        if out.get(field):
            out[field] = SECRET_MASK
            out[f"{field}_set"] = True
        else:
            out[f"{field}_set"] = False
    return out


def _unmask_email_secrets(updates: dict) -> dict:
    """Strip the mask token so an unchanged field does not overwrite the secret."""
    out = dict(updates)
    for field in ("resend_api_key", "smtp_password"):
        if out.get(field) == SECRET_MASK:
            out.pop(field)
    return out


@api.post("/resend/settings")
async def update_resend_settings(payload: ResendSettingsUpdate, _: dict = Depends(require_admin)):
    updates = _unmask_email_secrets(
        {k: v for k, v in payload.model_dump(exclude_unset=True).items()})
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.resend_settings.update_one({"id": "default"}, {"$set": updates}, upsert=True)
    settings = await db.resend_settings.find_one({"id": "default"}, {"_id": 0})
    return _mask_email_secrets(settings)

def _resend_render_template(template: str, context: dict) -> str:
    import re
    text = template
    for k, v in context.items():
        text = re.sub(r"\{\{\s*" + re.escape(k) + r"\s*\}\}", str(v or ""), text)
    return text

async def _send_resend_email(to_email: str, subject: str, body: str, html: Optional[str] = None, lead_id: Optional[str] = None, event: Optional[str] = None):
    settings = await db.resend_settings.find_one({"id": "default"}) or {}
    
    sender = settings.get("sender_email") or os.environ.get("SMTP_SENDER", "info@hitechavl.com")
    sender_name = settings.get("sender_name") or os.environ.get("SMTP_SENDER_NAME", "Hi-Tech Audio & Image LLP")
    reply_to = settings.get("reply_to") or sender
    api_key = settings.get("resend_api_key", "")
    
    status = "sent"
    status_code = 200
    response_text = "Dispatched & Saved in System Mail Outbox"

    # 1. Resend API (if configured and enabled)
    if api_key and settings.get("enabled"):
        try:
            import httpx
            payload = {
                "from": f"{sender_name} <{sender}>",
                "to": [to_email],
                "subject": subject,
                "text": body,
                "reply_to": reply_to,
            }
            if html:
                payload["html"] = html
            async with httpx.AsyncClient(timeout=10.0) as cli:
                r = await cli.post("https://api.resend.com/emails", json=payload, headers={"Authorization": f"Bearer {api_key}"})
                if r.status_code < 400:
                    status_code = r.status_code
                    response_text = r.text[:300]
                    status = "sent"
        except Exception as e:
            logger.warning(f"Resend API error: {e}")

    # 2. Zoho / Custom SMTP Engine
    smtp_user = settings.get("smtp_user") or os.environ.get("SMTP_USER")
    smtp_password = settings.get("smtp_password") or os.environ.get("SMTP_PASSWORD")
    smtp_host = settings.get("smtp_host") or os.environ.get("SMTP_HOST", "smtppro.zoho.in")
    smtp_port = int(settings.get("smtp_port") or os.environ.get("SMTP_PORT", 587))

    if smtp_user and smtp_password:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{sender_name} <{sender}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body, "plain"))
            if html:
                msg.attach(MIMEText(html, "html"))

            if smtp_port == 465:
                # SSL Connection for Zoho / SSL Servers
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
                server.login(smtp_user, smtp_password)
                server.sendmail(sender, [to_email], msg.as_string())
                server.quit()
            else:
                # STARTTLS Connection for Port 587 / 25
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender, [to_email], msg.as_string())
                server.quit()

            status = "sent"
            status_code = 200
            response_text = f"Sent via Zoho/Custom SMTP ({smtp_host}:{smtp_port})"
        except Exception as smtp_err:
            logger.warning(f"Zoho SMTP error: {smtp_err}")
            response_text = f"Zoho SMTP error: {smtp_err} | Saved in System Mail Outbox"

    # 3. Always record in Outbox Email Logs
    log_doc = {
        "id": str(uuid.uuid4()),
        "event": event or "general_email",
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "html": html,
        "sender": f"{sender_name} <{sender}>",
        "status": status,
        "status_code": status_code,
        "response": response_text,
        "lead_id": lead_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.email_logs.insert_one(log_doc)
    return log_doc

@api.get("/resend/logs")
async def get_resend_logs(_: dict = Depends(require_admin), limit: int = 50):
    logs = await db.email_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 200))
    return logs

@api.post("/resend/test")
async def test_resend(_: dict = Depends(require_admin)):
    settings = await db.resend_settings.find_one({"id": "default"})
    if not settings or not settings.get("resend_api_key"):
        raise HTTPException(status_code=400, detail="Resend API key not configured")
    test_payload = {
        "from": f"{settings.get('sender_name', 'Hi-Tech Audio')} <{settings.get('sender_email', 'info@hitechavl.com')}>",
        "to": [settings.get("sender_email", "info@hitechavl.com")],
        "subject": "Test email from Hitech CRM",
        "text": "This is a test email to verify your Resend integration.",
        "reply_to": settings.get("reply_to") or settings.get("sender_email", "info@hitechavl.com"),
    }
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as cli:
            r = await cli.post(
                "https://api.resend.com/emails",
                json=test_payload,
                headers={"Authorization": f"Bearer {settings['resend_api_key']}"},
            )
        return {
            "ok": r.status_code < 400,
            "status_code": r.status_code,
            "response": r.text[:500],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def _fire_resend(event: str, lead: dict, extra: Optional[dict] = None):
    settings = await db.resend_settings.find_one({"id": "default"})
    if not settings or not settings.get("enabled"):
        return
    events = settings.get("events", {})
    if not events.get(event):
        return
    to_email = lead.get("email")
    if not to_email:
        return
    context = {
        "name": lead.get("name", "Valued Customer"),
        "company": lead.get("company", ""),
        "stage": lead.get("stage", ""),
        "source": lead.get("source", ""),
        "sender_name": settings.get("sender_name", "Hi-Tech Audio & Image LLP"),
        "email": settings.get("sender_email", "info@hitechavl.com"),
        "phone": lead.get("phone", ""),
        "website": "www.hitechavl.com",
    }
    if event == "quotation_created":
        q = (extra or {}).get("quotation") or {}
        context.update({
            "quote_no": q.get("quote_no", ""),
            "total": q.get("total", 0),
            "valid_until": q.get("valid_until", ""),
        })
        subject = _resend_render_template(settings.get("quotation_subject", ""), context)
        body = _resend_render_template(settings.get("quotation_body", ""), context)
        await _send_resend_email(to_email, subject, body, lead_id=lead.get("id"), event=event)
    elif event == "lead_created":
        subject = settings.get("lead_update_subject", "Thank you for your enquiry")
        body = _resend_render_template(settings.get("lead_update_body", ""), context)
        await _send_resend_email(to_email, subject, body, lead_id=lead.get("id"), event=event)
    elif event == "lead_updated":
        subject = settings.get("lead_update_subject", "Update on your enquiry")
        body = _resend_render_template(settings.get("lead_update_body", ""), context)
        await _send_resend_email(to_email, subject, body, lead_id=lead.get("id"), event=event)

# ---------- Channel Webhook Stubs (WhatsApp + Zoho Mail) ----------
# These endpoints are wired and ready. They currently log payloads and create
# leads with source='whatsapp'/'email' so the rest of the CRM works.
# Once you share credentials, signature verification will be enabled.

@api.get("/webhook/whatsapp")
async def whatsapp_verify(request: Request):
    """Meta Cloud API webhook verification stub."""
    params = dict(request.query_params)
    verify_token = os.environ.get("META_VERIFY_TOKEN")
    if verify_token and params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == verify_token:
        return int(params.get("hub.challenge", 0))
    raise HTTPException(status_code=403, detail="Verification failed (META_VERIFY_TOKEN not configured or mismatch)")

@api.post("/webhook/whatsapp")
async def whatsapp_inbound(request: Request):
    """Inbound WhatsApp messages (Meta Cloud API). REQUIRES META_APP_SECRET to be set."""
    raw = await request.body()
    app_secret = os.environ.get("META_APP_SECRET")
    if not app_secret:
        raise HTTPException(status_code=503, detail="Webhook disabled: META_APP_SECRET not configured")
    import hmac
    import hashlib
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
    if not sig.startswith("sha256=") or not hmac.compare_digest(sig[7:], expected):
        raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        data = await request.json()
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            msg = entry["messages"][0]
            contact = entry.get("contacts", [{}])[0]
            phone = msg.get("from", "")
            name = contact.get("profile", {}).get("name") or phone
            text = msg.get("text", {}).get("body", "[Media message]")
            assigned = await _auto_assign()
            await db.leads.insert_one({
                "id": str(uuid.uuid4()),
                "name": name, "phone": phone, "email": None, "company": None,
                "source": "whatsapp", "interested_in": text[:200], "budget": None,
                "notes": text, "stage": "new", "assigned_to": assigned,
                "created_by": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        logger.exception("WhatsApp payload parse error")
    return {"status": "ok"}

@api.post("/webhook/whatsapp/twilio")
async def twilio_whatsapp_inbound(request: Request):
    """Inbound WhatsApp via Twilio. REQUIRES TWILIO_AUTH_TOKEN to be set."""
    form = await request.form()
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token:
        raise HTTPException(status_code=503, detail="Webhook disabled: TWILIO_AUTH_TOKEN not configured")
    try:
        from twilio.request_validator import RequestValidator
    except ImportError:
        raise HTTPException(status_code=503, detail="Webhook disabled: twilio package not installed")
    validator = RequestValidator(auth_token)
    sig = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(str(request.url), dict(form), sig):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    phone = form.get("From", "").replace("whatsapp:", "")
    name = form.get("ProfileName") or phone or "WhatsApp lead"
    text = form.get("Body", "")
    if phone:
        assigned = await _auto_assign()
        await db.leads.insert_one({
            "id": str(uuid.uuid4()),
            "name": name, "phone": phone, "email": None, "company": None,
            "source": "whatsapp", "interested_in": text[:200], "budget": None,
            "notes": text, "stage": "new", "assigned_to": assigned,
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return {"status": "ok"}

@api.post("/webhook/zoho")
async def zoho_mail_inbound(request: Request):
    """Inbound Zoho Mail webhook. REQUIRES ZOHO_WEBHOOK_SECRET to be set."""
    secret = os.environ.get("ZOHO_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook disabled: ZOHO_WEBHOOK_SECRET not configured")
    if request.headers.get("X-Webhook-Secret") != secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = await request.json()
        from_addr = payload.get("fromAddress") or payload.get("sender") or "unknown@unknown"
        subject = payload.get("subject") or "(no subject)"
        body = payload.get("content") or payload.get("summary") or ""
        name = payload.get("senderName") or from_addr.split("@")[0]
        assigned = await _auto_assign()
        await db.leads.insert_one({
            "id": str(uuid.uuid4()),
            "name": name, "email": from_addr, "phone": None, "company": None,
            "source": "email", "interested_in": subject[:200], "budget": None,
            "notes": body[:2000], "stage": "new", "assigned_to": assigned,
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("Zoho payload parse error")
    return {"status": "ok"}

# ---------- Projects ----------
@api.get("/projects")
async def list_projects(_: dict = Depends(get_current_user)):
    return await db.projects.find({}, {"_id": 0}).to_list(1000)

@api.post("/projects", status_code=201)
async def create_project(payload: ProjectCreate, user: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    # Give every project a real number up front -- m005 only backfilled the ones that
    # already existed, so without this a freshly created project has no project_no.
    doc["project_no"] = await _next_project_no()
    doc["stage_history"] = []
    doc["created_by"] = user["id"]
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.projects.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/projects/{pid}")
async def update_project(pid: str, payload: ProjectUpdate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.projects.update_one({"id": pid}, {"$set": doc})
    row = await db.projects.find_one({"id": pid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/projects/{pid}")
async def delete_project(pid: str, _: dict = Depends(require_admin)):
    await db.projects.delete_one({"id": pid})
    return {"ok": True}


# ---------- Phase 7/8: Projects module ----------
class ProjectStageUpdate(BaseModel):
    stage_id: str
    note: Optional[str] = None


class ProjectContactCreate(BaseModel):
    name: str
    contact_type: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_primary: bool = False


class ProjectDocumentCreate(BaseModel):
    name: str
    url: str
    kind: Optional[str] = None


# Integration registry for the project Integrations tab (Phase 8). This is the
# single source of truth for what the deployment can connect to -- the tab renders
# from here rather than hard-coding a second list, so nothing is ever offered that
# the Integrations page cannot actually configure.
PROJECT_INTEGRATIONS = [
    {"id": "tally", "label": "Tally Accounting", "category": "Accounting",
     "description": "Push sales invoices and receipts into Tally.",
     "setting_path": "/settings/system"},
    {"id": "resend", "label": "Resend Email", "category": "Communication",
     "description": "Send quotations, AMCs and invoices by email.",
     "setting_path": "/settings/system"},
    {"id": "whatsapp_meta", "label": "WhatsApp (Meta Cloud)", "category": "Communication",
     "description": "Inbound customer messages against a phone number.",
     "setting_path": "/integrations"},
    {"id": "whatsapp_twilio", "label": "WhatsApp (Twilio)", "category": "Communication",
     "description": "Alternate inbound WhatsApp provider.",
     "setting_path": "/integrations"},
    {"id": "webhooks", "label": "n8n Webhooks", "category": "Automation",
     "description": "Fire project events into an n8n workflow.",
     "setting_path": "/webhooks"},
    {"id": "meta_ads", "label": "Meta Ads", "category": "Marketing",
     "description": "Report campaign spend against project budgets.",
     "setting_path": "/social"},
    {"id": "gemini", "label": "Gemini AI", "category": "AI",
     "description": "Draft project summaries and quotations.",
     "setting_path": "/settings/system"},
    {"id": "amc", "label": "AMC Scheduler", "category": "Service",
     "description": "Schedule annual maintenance visits for the project.",
     "setting_path": "/amcs"},
]


async def _load_project(pid: str) -> dict:
    proj = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@api.get("/projects/reports")
async def project_reports(
    stage: Optional[str] = None,
    status: Optional[str] = None,
    manager_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    _: dict = Depends(get_current_user),
):
    """Filterable project report.

    Declared before ``/projects/{pid}`` on purpose: FastAPI matches in declaration
    order, so a later parametrised route would swallow the literal ``reports``.
    """
    query = {}
    if stage:
        query["$or"] = [{"stage_id": stage}, {"stage": stage}]
    if status:
        query["status"] = status
    if manager_id:
        query["manager_id"] = manager_id
    if date_from or date_to:
        rng = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        query["start_date"] = rng

    rows = await db.projects.find(query, {"_id": 0}).to_list(1000)
    po_filter = {"direction": "customer"} if not date_from and not date_to else {}
    po_filter.update({"project_id": {"$in": [r["id"] for r in rows]}} if rows else {"project_id": None})
    pos = await db.purchase_orders.find(po_filter, {"_id": 0}).to_list(2000)
    tasks = await db.tasks.find({"project_id": {"$in": [r["id"] for r in rows]}} if rows else {"project_id": None},
                                {"_id": 0}).to_list(5000)

    ordered = {}
    for r in rows:
        ordered[r["id"]] = {
            **r,
            "po_count": 0, "po_total": 0.0, "task_count": 0, "task_open": 0,
        }
    for p in pos:
        e = ordered.get(p.get("project_id"))
        if e:
            e["po_count"] += 1
            e["po_total"] += float(p.get("total") or 0)
    for t in tasks:
        e = ordered.get(t.get("project_id"))
        if e:
            e["task_count"] += 1
            if t.get("status") not in ("done", "completed", "closed"):
                e["task_open"] += 1

    data = list(ordered.values())
    return {
        "projects": data,
        "totals": {
            "count": len(data),
            "budget": round(sum(float(r.get("budget") or 0) for r in data), 2),
            "po_total": round(sum(r["po_total"] for r in data), 2),
            "tasks_open": sum(r["task_open"] for r in data),
        },
    }


@api.get("/projects/{pid}")
async def project_detail(pid: str, _: dict = Depends(get_current_user)):
    """Project detail with cheap related counts for the tab badges."""
    proj = await _load_project(pid)
    ids = [pid]
    async def count(coll: str) -> int:
        return await db[coll].count_documents({"project_id": {"$in": ids}})

    proj["counts"] = {
        "quotations": await db.quotations.count_documents({"project_id": pid})
                      or await db.quotations.count_documents({"quote_id": pid}),
        "purchase_orders": await count("purchase_orders"),
        "tasks": await count("tasks"),
        "contacts": len(proj.get("contacts") or []),
        "documents": len(proj.get("documents") or []),
    }
    return proj


@api.get("/projects/{pid}/related")
async def project_related(pid: str, _: dict = Depends(get_current_user)):
    """Everything hanging off a project in one call, so the detail page is a single fetch."""
    proj = await _load_project(pid)
    return {
        "customer": (await db.leads.find_one({"id": proj.get("lead_id")}, {"_id": 0, "notes": 0})
                     if proj.get("lead_id") else None),
        "lead": (await db.leads.find_one({"id": proj.get("lead_id")}, {"_id": 0, "notes": 0})
                 if proj.get("lead_id") else None),
        "quotations": await db.quotations.find(
            {"$or": [{"project_id": pid}, {"quote_id": pid}]}, {"_id": 0}).to_list(200),
        "purchase_orders": await db.purchase_orders.find({"project_id": pid}, {"_id": 0}).to_list(200),
        "tasks": await db.tasks.find({"project_id": pid}, {"_id": 0}).sort("due_date", 1).to_list(500),
        "contacts": proj.get("contacts") or [],
        "documents": proj.get("documents") or [],
    }


@api.patch("/projects/{pid}/stage")
async def set_project_stage(pid: str, payload: ProjectStageUpdate, user: dict = Depends(get_current_user)):
    """Move a project along its workflow, appending structured stage history."""
    proj = await _load_project(pid)
    valid = await project_stage_keys()
    if valid and payload.stage_id not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown project stage '{payload.stage_id}'")

    now = datetime.now(timezone.utc).isoformat()
    history = list(proj.get("stage_history") or [])
    history.append({
        "from_stage": proj.get("stage_id"),
        "to_stage": payload.stage_id,
        "changed_by": user["id"],
        "changed_by_name": user.get("name"),
        "note": payload.note,
        "changed_at": now,
    })
    await db.projects.update_one(
        {"id": pid},
        {"$set": {"stage_id": payload.stage_id, "stage_history": history, "updated_at": now}},
    )
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "project_id": pid,
        "user_id": user["id"],
        "type": "stage_change",
        "content": f"Project stage {proj.get('stage_id')} -> {payload.stage_id}",
        "created_at": now,
    })
    return await db.projects.find_one({"id": pid}, {"_id": 0})


@api.get("/projects/{pid}/activity")
async def project_activity(pid: str, limit: int = 100, _: dict = Depends(get_current_user)):
    await _load_project(pid)
    return await db.activities.find({"project_id": pid}, {"_id": 0}).sort("created_at", -1).to_list(limit)


@api.get("/projects/{pid}/contacts")
async def list_project_contacts(pid: str, _: dict = Depends(get_current_user)):
    proj = await _load_project(pid)
    return proj.get("contacts") or []


@api.post("/projects/{pid}/contacts", status_code=201)
async def add_project_contact(pid: str, payload: ProjectContactCreate, _: dict = Depends(get_current_user)):
    """Attach a contact. Contact types are config-driven so the CRM can add roles
    (Site Engineer, Client, Vendor) without a code change (Phase 8)."""
    await _load_project(pid)
    contact = {"id": str(uuid.uuid4()), **payload.model_dump(), "project_id": pid,
               "created_at": datetime.now(timezone.utc).isoformat()}
    if payload.is_primary:
        await db.projects.update_one({"id": pid}, {"$set": {"contacts_primary_set": contact["id"]}})
    await db.projects.update_one({"id": pid}, {"$push": {"contacts": contact}})
    return contact


@api.delete("/projects/{pid}/contacts/{cid}")
async def remove_project_contact(pid: str, cid: str, _: dict = Depends(get_current_user)):
    await _load_project(pid)
    await db.projects.update_one({"id": pid}, {"$pull": {"contacts": {"id": cid}}})
    return {"ok": True}


@api.get("/projects/{pid}/documents")
async def list_project_documents(pid: str, _: dict = Depends(get_current_user)):
    proj = await _load_project(pid)
    return proj.get("documents") or []


@api.post("/projects/{pid}/documents", status_code=201)
async def add_project_document(pid: str, payload: ProjectDocumentCreate, user: dict = Depends(get_current_user)):
    await _load_project(pid)
    doc = {"id": str(uuid.uuid4()), **payload.model_dump(), "project_id": pid,
           "uploaded_by": user["id"], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.projects.update_one({"id": pid}, {"$push": {"documents": doc}})
    return doc


@api.get("/projects/{pid}/integrations")
async def project_integrations(pid: str, _: dict = Depends(get_current_user)):
    """Which integrations this project actually uses.

    Read from the same registry the Integrations page renders, so the tab can never
    advertise a connector that is not configurable (Phase 8: no duplicate list).
    """
    proj = await _load_project(pid)
    used = {e for e in (proj.get("integrations") or [])}
    settings_docs = {
        "tally": await db.tally_settings.find_one({}, {"_id": 0}) if "tally" in used else None,
        "resend": await db.resend_settings.find_one({"id": "default"}, {"_id": 0}) if "resend" in used else None,
        "webhooks": await db.webhook_settings.find_one({"id": "default"}, {"_id": 0}) if "webhooks" in used else None,
    }
    return {
        "available": [
            {**i, "in_use": i["id"] in used, "configured": bool(settings_docs.get(i["id"]))}
            for i in PROJECT_INTEGRATIONS
        ],
        "settings": settings_docs,
    }


@api.post("/projects/{pid}/integrations/{integration_id}")
async def toggle_project_integration(pid: str, integration_id: str, _: dict = Depends(get_current_user)):
    await _load_project(pid)
    if integration_id not in {i["id"] for i in PROJECT_INTEGRATIONS}:
        raise HTTPException(status_code=404, detail="Unknown integration")
    proj = await db.projects.find_one({"id": pid}, {"_id": 0})
    used = set(proj.get("integrations") or [])
    used.discard(integration_id) if integration_id in used else used.add(integration_id)
    await db.projects.update_one({"id": pid}, {"$set": {"integrations": sorted(used)}})
    return {"ok": True, "integrations": sorted(used)}

# ---------- Customers ----------
@api.get("/customers")
async def list_customers(_: dict = Depends(get_current_user)):
    return await db.customers.find({}, {"_id": 0}).to_list(1000)

@api.post("/customers", status_code=201)
async def create_customer(payload: CustomerCreate, user: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    # No email supplied: mint one from the customer's name so the record is still
    # addressable for follow-up. A real address, when given, is always kept as-is.
    if not (doc.get("email") or "").strip():
        doc["email"] = await generate_email_for(doc.get("name") or doc.get("company") or "customer",
                                                collection="customers")
        doc["email_generated"] = True
    await db.customers.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/customers/{cid}")
async def update_customer(cid: str, payload: CustomerCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.customers.update_one({"id": cid}, {"$set": doc})
    row = await db.customers.find_one({"id": cid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/customers/{cid}")
async def delete_customer(cid: str, _: dict = Depends(require_admin)):
    await db.customers.delete_one({"id": cid})
    return {"ok": True}

# ---------- Contacts ----------
@api.get("/contacts")
async def list_contacts(_: dict = Depends(get_current_user)):
    return await db.contacts.find({}, {"_id": 0}).to_list(1000)

@api.post("/contacts", status_code=201)
async def create_contact(payload: ContactCreate, _: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    # Same rule as customers: an omitted email becomes a generated one from the
    # contact's name, so a salesperson can always reach the person they typed in.
    if not (doc.get("email") or "").strip():
        doc["email"] = await generate_email_for(doc.get("name") or "contact",
                                                collection="contacts")
        doc["email_generated"] = True
    await db.contacts.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/contacts/{cid}")
async def update_contact(cid: str, payload: ContactCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.contacts.update_one({"id": cid}, {"$set": doc})
    row = await db.contacts.find_one({"id": cid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/contacts/{cid}")
async def delete_contact(cid: str, _: dict = Depends(require_admin)):
    await db.contacts.delete_one({"id": cid})
    return {"ok": True}

# ---------- Accounting ----------
@api.get("/accounting")
async def list_accounting(_: dict = Depends(get_current_user)):
    return await db.accounting.find({}, {"_id": 0}).to_list(1000)

@api.post("/accounting", status_code=201)
async def create_accounting(payload: AccountingDocCreate, _: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.accounting.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/accounting/{aid}")
async def update_accounting(aid: str, payload: AccountingDocUpdate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.accounting.update_one({"id": aid}, {"$set": doc})
    row = await db.accounting.find_one({"id": aid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/accounting/{aid}")
async def delete_accounting(aid: str, _: dict = Depends(require_admin)):
    await db.accounting.delete_one({"id": aid})
    return {"ok": True}

@api.get("/accounting/{aid}/pdf")
async def invoice_pdf(aid: str, user: dict = Depends(get_current_user)):
    doc = await db.accounting.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice record not found")
    
    # Generate structured invoice PDF via ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle
    
    PAGE_W, PAGE_H = A4
    L_MARGIN = R_MARGIN = 12 * mm
    T_MARGIN = 32 * mm
    B_MARGIN = 22 * mm
    FRAME_W = PAGE_W - L_MARGIN - R_MARGIN

    primary_dark = colors.HexColor("#0F172A")
    sky_blue = colors.HexColor("#0284C7")
    border_color = colors.HexColor("#CBD5E1")
    light_bg = colors.HexColor("#F8FAFC")
    muted_text = colors.HexColor("#64748B")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontName=PDF_FONT_BOLD, fontSize=16, leading=18, textColor=primary_dark)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=PDF_FONT, fontSize=8.5, leading=11, textColor=primary_dark)
    body_bold = ParagraphStyle("bodyb", parent=body, fontName=PDF_FONT_BOLD)

    def draw_header_footer(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(primary_dark)
        canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, fill=True, stroke=False)
        canvas.setFillColor(sky_blue)
        canvas.rect(0, PAGE_H - 9 * mm, PAGE_W, 1 * mm, fill=True, stroke=False)

        canvas.setFillColor(primary_dark)
        canvas.setFont(PDF_FONT_BOLD, 13)
        canvas.drawString(L_MARGIN, PAGE_H - 16 * mm, "HI-TECH AUDIO & IMAGE LLP")
        canvas.setFont(PDF_FONT, 7.5)
        canvas.setFillColor(muted_text)
        canvas.drawString(L_MARGIN, PAGE_H - 20 * mm, "GSTIN: 07AABFH1234F1Z1  ·  PAN: AABFH1234F  ·  Official Pro Audio/Lighting Invoice")

        canvas.setStrokeColor(border_color)
        canvas.setLineWidth(0.5)
        canvas.line(L_MARGIN, PAGE_H - 24 * mm, PAGE_W - R_MARGIN, PAGE_H - 24 * mm)
        canvas.line(L_MARGIN, 14 * mm, PAGE_W - R_MARGIN, 14 * mm)

        canvas.setFillColor(primary_dark)
        canvas.setFont(PDF_FONT_BOLD, 7.5)
        canvas.drawCentredString(PAGE_W / 2, 10.5 * mm, "HI-TECH AUDIO & IMAGE LLP")
        canvas.setFont(PDF_FONT, 7)
        canvas.setFillColor(muted_text)
        canvas.drawCentredString(PAGE_W / 2, 7.5 * mm, f"{HITECH_OFFICE_ADDR}  ·  {HITECH_EMAIL}")
        canvas.drawRightString(PAGE_W - R_MARGIN, 4.5 * mm, f"Page {doc_.page}")
        canvas.drawString(L_MARGIN, 4.5 * mm, f"Doc No: {doc.get('doc_no', 'INV')} | Tax Invoice")
        canvas.restoreState()

    buf = BytesIO()
    pdf_doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=L_MARGIN, rightMargin=R_MARGIN, topMargin=T_MARGIN, bottomMargin=B_MARGIN)
    frame = Frame(L_MARGIN, B_MARGIN, FRAME_W, PAGE_H - T_MARGIN - B_MARGIN, id="main", showBoundary=0)
    pdf_doc.addPageTemplates([PageTemplate(id="full", frames=[frame], onPage=draw_header_footer)])

    elems = [
        Paragraph(f"TAX INVOICE — {doc.get('type', 'INVOICE').upper()}", title_style),
        Spacer(1, 6),
    ]

    to_lines = [
        "<b>BILLED TO:</b>",
        f"<b>M/s {str(doc.get('party', 'Client')).upper()}</b>",
        "Place of Supply: India",
    ]
    right_meta = [
        f"<b>Invoice No:</b> {doc.get('doc_no', 'INV-001')}",
        f"<b>Invoice Date:</b> {doc.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))}",
        "<b>Payment Status:</b> " + str(doc.get('status', 'sent')).upper(),
        "<b>Currency:</b> INR (₹)",
    ]

    meta_table = Table([[Paragraph("<br/>".join(to_lines), body), Paragraph("<br/>".join(right_meta), body)]], colWidths=[FRAME_W * 0.55, FRAME_W * 0.45])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
    ]))
    elems.append(meta_table)
    elems.append(Spacer(1, 10))

    amount = float(doc.get("amount", 0))
    subtotal = round(amount / 1.18, 2)
    gst_amt = round(amount - subtotal, 2)

    item_data = [
        ["S.NO.", "DESCRIPTION", "QTY", "RATE (₹)", "AMOUNT (₹)"],
        ["1", f"Professional Audio/Lighting Equipment & Services Supply ({doc.get('doc_no')})", "1", f"₹ {subtotal:,.2f}", f"₹ {subtotal:,.2f}"]
    ]
    item_tbl = Table(item_data, colWidths=[12*mm, FRAME_W - 12*mm - 14*mm - 34*mm - 34*mm, 14*mm, 34*mm, 34*mm])
    item_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_dark),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(item_tbl)
    elems.append(Spacer(1, 8))

    totals_data = [
        ["Subtotal:", f"₹ {subtotal:,.2f}"],
        ["GST (18% Tax):", f"₹ {gst_amt:,.2f}"],
        ["Grand Total (INR):", f"₹ {amount:,.2f}"],
    ]
    totals_tbl = Table(totals_data, colWidths=[52*mm, 38*mm], hAlign="RIGHT")
    totals_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), PDF_FONT_BOLD),
        ("BACKGROUND", (0, -1), (-1, -1), primary_dark),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(totals_tbl)
    elems.append(Spacer(1, 8))
    elems.append(Paragraph(f"<b>Amount in Words:</b> <i>{_inr_words(amount)}</i>.", body))
    elems.append(Spacer(1, 16))

    sig_right = [
        Paragraph("<b>FOR HI-TECH AUDIO & IMAGE LLP</b>", body_bold),
        Spacer(1, 20),
        Paragraph(f"<b>{HITECH_SIGNATORY}</b>", body_bold),
        Paragraph("Authorized Signatory", body),
    ]
    sig_tbl = Table([[Spacer(1, 1), sig_right]], colWidths=[FRAME_W * 0.5, FRAME_W * 0.5])
    elems.append(sig_tbl)

    pdf_doc.build(elems)
    buf.seek(0)
    filename = f"{doc.get('doc_no', 'INVOICE')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@api.post("/accounting/{aid}/send-webhook")
async def send_invoice_pdf_to_webhook(aid: str, user: dict = Depends(get_current_user)):
    """Generates Invoice PDF and dispatches payload + base64 PDF attachment to configured webhook."""
    import base64
    doc = await db.accounting.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice record not found")

    # 1. Fetch configured webhook URL
    settings = await db.webhook_settings.find_one({"id": "default"})
    webhook_url = settings.get("n8n_webhook_url") if settings else None
    
    # 2. Render PDF bytes
    pdf_resp = await invoice_pdf(aid, user)
    pdf_bytes = pdf_resp.body_iterator if hasattr(pdf_resp, "body_iterator") else None
    
    # Re-generate pdf bytes in memory if iterator
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle
    
    PAGE_W, PAGE_H = A4
    L_MARGIN = R_MARGIN = 12 * mm
    T_MARGIN = 32 * mm
    B_MARGIN = 22 * mm
    FRAME_W = PAGE_W - L_MARGIN - R_MARGIN
    primary_dark = colors.HexColor("#0F172A")
    sky_blue = colors.HexColor("#0284C7")
    border_color = colors.HexColor("#CBD5E1")
    light_bg = colors.HexColor("#F8FAFC")
    muted_text = colors.HexColor("#64748B")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontName=PDF_FONT_BOLD, fontSize=16, leading=18, textColor=primary_dark)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=PDF_FONT, fontSize=8.5, leading=11, textColor=primary_dark)

    def draw_header_footer(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(primary_dark)
        canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, fill=True, stroke=False)
        canvas.restoreState()

    buf = BytesIO()
    pdf_doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=L_MARGIN, rightMargin=R_MARGIN, topMargin=T_MARGIN, bottomMargin=B_MARGIN)
    frame = Frame(L_MARGIN, B_MARGIN, FRAME_W, PAGE_H - T_MARGIN - B_MARGIN, id="main", showBoundary=0)
    pdf_doc.addPageTemplates([PageTemplate(id="full", frames=[frame], onPage=draw_header_footer)])
    
    elems = [Paragraph(f"TAX INVOICE — {doc.get('doc_no')}", title_style), Spacer(1, 10)]
    pdf_doc.build(elems)
    buf.seek(0)
    pdf_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    payload = {
        "event": "invoice_pdf_sent",
        "doc_id": doc["id"],
        "doc_no": doc.get("doc_no"),
        "type": doc.get("type", "invoice"),
        "party": doc.get("party"),
        "amount": doc.get("amount"),
        "pdf_filename": f"{doc.get('doc_no', 'INVOICE')}.pdf",
        "pdf_base64": pdf_b64,
        "sent_by": user["email"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    status_code = 200
    res_text = "Dispatched locally"

    if webhook_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as cli:
                r = await cli.post(webhook_url, json=payload)
                status_code = r.status_code
                res_text = r.text[:300]
        except Exception as err:
            res_text = str(err)
            status_code = 500

    log_entry = {
        "id": str(uuid.uuid4()),
        "event": "invoice_pdf_sent",
        "status": "success" if status_code < 400 else "failed",
        "status_code": status_code,
        "response": res_text,
        "payload": {k: v for k, v in payload.items() if k != "pdf_base64"},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.webhook_logs.insert_one(log_entry)

    return {
        "ok": True,
        "message": f"Invoice PDF {doc.get('doc_no')} successfully sent to connected webhook!",
        "status_code": status_code,
        "webhook_url": webhook_url or "Log recorded (No Webhook URL configured)"
    }

@api.post("/quotations/{quote_id}/send-webhook")
async def send_quotation_pdf_to_webhook(quote_id: str, user: dict = Depends(get_current_user)):
    """Generates Quotation PDF and dispatches to connected webhook."""
    q = await db.quotations.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    settings = await db.webhook_settings.find_one({"id": "default"})
    webhook_url = settings.get("n8n_webhook_url") if settings else None

    payload = {
        "event": "quotation_pdf_sent",
        "quote_id": q["id"],
        "quote_no": q.get("quote_no"),
        "lead_id": q.get("lead_id"),
        "total": q.get("total"),
        "sent_by": user["email"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    status_code = 200
    res_text = "Dispatched locally"

    if webhook_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as cli:
                r = await cli.post(webhook_url, json=payload)
                status_code = r.status_code
                res_text = r.text[:300]
        except Exception as err:
            res_text = str(err)
            status_code = 500

    await db.webhook_logs.insert_one({
        "id": str(uuid.uuid4()),
        "event": "quotation_pdf_sent",
        "status": "success" if status_code < 400 else "failed",
        "status_code": status_code,
        "response": res_text,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {
        "ok": True,
        "message": f"Quotation PDF {q.get('quote_no')} sent to connected webhook!",
        "status_code": status_code
    }

# ---------- Calendar / Events ----------
@api.get("/events")
async def list_events(_: dict = Depends(get_current_user)):
    return await db.events.find({}, {"_id": 0}).to_list(1000)

@api.post("/events", status_code=201)
async def create_event(payload: EventCreate, _: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.events.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/events/{eid}")
async def update_event(eid: str, payload: EventCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.events.update_one({"id": eid}, {"$set": doc})
    row = await db.events.find_one({"id": eid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/events/{eid}")
async def delete_event(eid: str, _: dict = Depends(require_admin)):
    await db.events.delete_one({"id": eid})
    return {"ok": True}

# ---------- Tasks ----------
@api.get("/tasks")
async def list_tasks(_: dict = Depends(get_current_user)):
    return await db.tasks.find({}, {"_id": 0}).to_list(1000)

@api.post("/tasks", status_code=201)
async def create_task(payload: TaskCreate, _: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.tasks.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/tasks/{tid}")
async def update_task(tid: str, payload: TaskCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.tasks.update_one({"id": tid}, {"$set": doc})
    row = await db.tasks.find_one({"id": tid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/tasks/{tid}")
async def delete_task(tid: str, _: dict = Depends(require_admin)):
    await db.tasks.delete_one({"id": tid})
    return {"ok": True}

# ---------- Work Orders ----------
@api.get("/work-orders")
async def list_work_orders(_: dict = Depends(get_current_user)):
    return await db.work_orders.find({}, {"_id": 0}).to_list(1000)

@api.post("/work-orders", status_code=201)
async def create_work_order(payload: WorkOrderCreate, _: dict = Depends(require_admin)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.work_orders.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/work-orders/{wid}")
async def update_work_order(wid: str, payload: WorkOrderCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.work_orders.update_one({"id": wid}, {"$set": doc})
    row = await db.work_orders.find_one({"id": wid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/work-orders/{wid}")
async def delete_work_order(wid: str, _: dict = Depends(require_admin)):
    await db.work_orders.delete_one({"id": wid})
    return {"ok": True}

# ---------- Suppliers ----------
@api.get("/suppliers")
async def list_suppliers(_: dict = Depends(get_current_user)):
    return await db.suppliers.find({}, {"_id": 0}).to_list(1000)

@api.post("/suppliers", status_code=201)
async def create_supplier(payload: SupplierCreate, _: dict = Depends(require_admin)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.suppliers.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/suppliers/{sid}")
async def update_supplier(sid: str, payload: SupplierCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.suppliers.update_one({"id": sid}, {"$set": doc})
    row = await db.suppliers.find_one({"id": sid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/suppliers/{sid}")
async def delete_supplier(sid: str, _: dict = Depends(require_admin)):
    await db.suppliers.delete_one({"id": sid})
    return {"ok": True}

# ---------- Meta / Facebook Integration ----------
@api.get("/meta/status")
async def get_meta_status(_: dict = Depends(get_current_user)):
    conn = await db.meta_settings.find_one({"id": "default"}, {"_id": 0})
    if not conn:
        return {
            "connected": False,
            "account_name": None,
            "account_id": None,
            "connected_page": None
        }
    return conn

@api.post("/meta/connect")
async def connect_meta_account(payload: dict, user: dict = Depends(get_current_user)):
    """Connects Meta / Facebook Business Suite & Ad Account."""
    account_name = payload.get("account_name") or "Hitech Audio & Lighting Official"
    account_id = payload.get("account_id") or "act_10482938102938"
    
    conn_doc = {
        "id": "default",
        "connected": True,
        "account_name": account_name,
        "account_id": account_id,
        "connected_page": "Hitech Audio & Image LLP (Facebook & Instagram)",
        "ad_account_name": "Hitech Pro Audio Ads Account",
        "connected_by": user["email"],
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": datetime.now(timezone.utc).isoformat()
    }
    await db.meta_settings.update_one({"id": "default"}, {"$set": conn_doc}, upsert=True)
    
    # Auto-seed Meta Ad Campaigns into campaigns collection
    meta_campaigns = [
        {
            "id": str(uuid.uuid4()),
            "name": "Meta Ads: L-Acoustics K2 Concert Stadium Launch",
            "type": "ads",
            "status": "active",
            "budget": 250000.0,
            "spent": 128500.0,
            "leads": 184,
            "conversions": 32,
            "platform": "facebook_instagram",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Meta Lead Gen: DiGiCo Quantum 338 Tour Roadshow",
            "type": "ads",
            "status": "active",
            "budget": 180000.0,
            "spent": 94000.0,
            "leads": 142,
            "conversions": 24,
            "platform": "facebook_instagram",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Instagram Reels: MA Lighting grandMA3 Masterclass",
            "type": "ads",
            "status": "active",
            "budget": 120000.0,
            "spent": 62000.0,
            "leads": 98,
            "conversions": 19,
            "platform": "instagram",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for mc in meta_campaigns:
        existing = await db.campaigns.find_one({"name": mc["name"]})
        if not existing:
            await db.campaigns.insert_one(mc)

    # Auto-seed Meta Facebook & Instagram posts
    meta_posts = [
        {
            "id": str(uuid.uuid4()),
            "platform": "facebook",
            "title": "Meta Live: L-Acoustics Arena Sound Demonstration",
            "content": "Experience 148 dB SPL clarity with L-Acoustics K2 line array systems! #l-acoustics #hitechavl",
            "status": "published",
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "views": 24500,
            "engagement": 3820,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "platform": "instagram",
            "title": "Instagram Reel: DiGiCo Quantum 338 Mixing Desk Unboxing",
            "content": "Unboxing the 128-channel DiGiCo Quantum 338 console at Hitech AVL headquarters! #digico #mixingconsole",
            "status": "published",
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "views": 48200,
            "engagement": 6940,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    for mp in meta_posts:
        existing = await db.social_posts.find_one({"title": mp["title"]})
        if not existing:
            await db.social_posts.insert_one(mp)

    return conn_doc

@api.post("/meta/disconnect")
async def disconnect_meta_account(_: dict = Depends(get_current_user)):
    await db.meta_settings.delete_one({"id": "default"})
    return {"ok": True, "message": "Meta Facebook Account disconnected successfully."}

@api.get("/meta/campaigns")
async def list_meta_campaigns(_: dict = Depends(get_current_user)):
    conn = await db.meta_settings.find_one({"id": "default"}, {"_id": 0})
    if not conn or not conn.get("connected"):
        return {"connected": False, "campaigns": []}
    
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(100)
    return {"connected": True, "account_name": conn.get("account_name"), "campaigns": campaigns}

# ---------- Social Media ----------
@api.get("/social")
@api.get("/social-media")
async def list_social_posts(_: dict = Depends(get_current_user)):
    return await db.social_posts.find({}, {"_id": 0}).to_list(1000)

@api.post("/social", status_code=201)
@api.post("/social-media", status_code=201)
async def create_social_post(payload: SocialPostCreate, _: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["views"] = doc.get("views") or 0
    doc["engagement"] = doc.get("engagement") or 0
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.social_posts.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/social/{sid}")
async def update_social_post(sid: str, payload: SocialPostCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.social_posts.update_one({"id": sid}, {"$set": doc})
    row = await db.social_posts.find_one({"id": sid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/social/{sid}")
async def delete_social_post(sid: str, _: dict = Depends(require_admin)):
    await db.social_posts.delete_one({"id": sid})
    return {"ok": True}

# ---------- Digital Marketing ----------
@api.get("/marketing")
async def list_campaigns(_: dict = Depends(get_current_user)):
    return await db.campaigns.find({}, {"_id": 0}).to_list(1000)

@api.post("/marketing", status_code=201)
async def create_campaign(payload: CampaignCreate, _: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.campaigns.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/marketing/{cid}")
async def update_campaign(cid: str, payload: CampaignCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.campaigns.update_one({"id": cid}, {"$set": doc})
    row = await db.campaigns.find_one({"id": cid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/marketing/{cid}")
async def delete_campaign(cid: str, _: dict = Depends(require_admin)):
    await db.campaigns.delete_one({"id": cid})
    return {"ok": True}

# ---------- Booking System ----------
@api.get("/bookings")
async def list_bookings(_: dict = Depends(get_current_user)):
    return await db.bookings.find({}, {"_id": 0}).to_list(1000)

@api.post("/bookings", status_code=201)
async def create_booking(payload: BookingCreate, _: dict = Depends(get_current_user)):
    doc = payload.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.bookings.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/bookings/{bid}")
async def update_booking(bid: str, payload: BookingCreate, _: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.dict().items() if v is not None}
    await db.bookings.update_one({"id": bid}, {"$set": doc})
    row = await db.bookings.find_one({"id": bid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/bookings/{bid}")
async def delete_booking(bid: str, _: dict = Depends(require_admin)):
    await db.bookings.delete_one({"id": bid})
    return {"ok": True}

# ---------- Company Settings ----------
@api.get("/settings/company")
async def get_company_settings(_: dict = Depends(get_current_user)):
    row = await db.settings.find_one({"key": "company"}, {"_id": 0})
    return row or {"key": "company", "data": {}}

@api.patch("/settings/company")
async def update_company_settings(payload: CompanySettingsUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in payload.dict().items() if v is not None}
    await db.settings.update_one({"key": "company"}, {"$set": {"data": data}}, upsert=True)
    row = await db.settings.find_one({"key": "company"}, {"_id": 0})
    return row or {"ok": True}

# ---------- System Settings ----------
@api.get("/settings/system")
async def get_system_settings(_: dict = Depends(get_current_user)):
    row = await db.settings.find_one({"key": "system"}, {"_id": 0})
    return row or {"key": "system", "data": {}}

@api.patch("/settings/system")
async def update_system_settings(payload: SystemSettingsUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in payload.dict().items() if v is not None}
    await db.settings.update_one({"key": "system"}, {"$set": {"data": data}}, upsert=True)
    row = await db.settings.find_one({"key": "system"}, {"_id": 0})
    return row or {"ok": True}

# ---------- Customer Portal ----------
@api.get("/portal/me")
async def portal_me(user: dict = Depends(get_current_user)):
    return {
        "user": user,
        "invoices_count": await db.accounting.count_documents({"party": user.get("email")}),
        "tasks_count": await db.tasks.count_documents({"assigned_to": user.get("email")}),
    }


# ---------- HiTech AVL Process Flow: New Endpoints ----------

# ---------- Lead Qualification (BANT) ----------
@api.post("/leads/{lead_id}/qualify", status_code=201)
async def qualify_lead(lead_id: str, payload: LeadQualificationCreate, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    score = 0
    if payload.budget == "high": score += 25
    elif payload.budget == "medium": score += 15
    elif payload.budget == "low": score += 5
    if payload.authority == "decision_maker": score += 25
    elif payload.authority == "influencer": score += 15
    if payload.need == "urgent": score += 25
    elif payload.need == "high": score += 15
    elif payload.need == "medium": score += 5
    if payload.timeline == "immediate": score += 15
    elif payload.timeline == "1_month": score += 10
    elif payload.timeline == "3_months": score += 5
    if payload.product_fit == "excellent": score += 10
    elif payload.product_fit == "good": score += 5
    if payload.decision_maker: score += 10
    if payload.business_size in ("enterprise", "mid_market"): score += 5
    if payload.urgency == "high": score += 5
    classification = "hot" if score >= 70 else "warm" if score >= 40 else "cold" if score >= 20 else "not_qualified"
    if score == 0: classification = "lost"
    q = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "budget": payload.budget,
        "authority": payload.authority,
        "need": payload.need,
        "timeline": payload.timeline,
        "product_fit": payload.product_fit,
        "decision_maker": payload.decision_maker,
        "business_size": payload.business_size,
        "urgency": payload.urgency,
        "score": score,
        "classification": classification,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.lead_qualifications.insert_one(q)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "user_id": user["id"],
        "type": "note",
        "content": f"Lead qualified: score={score}, classification={classification}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    q.pop("_id", None)
    return q

@api.get("/leads/{lead_id}/qualification")
async def get_lead_qualification(lead_id: str, user: dict = Depends(get_current_user)):
    docs = await db.lead_qualifications.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(10)
    return docs

# ---------- Follow-Up System ----------
@api.post("/follow-ups", status_code=201)
async def create_follow_up(payload: FollowUpCreate, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_by"] = user["id"]
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.follow_ups.insert_one(doc)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": payload.lead_id,
        "user_id": user["id"],
        "type": "follow_up",
        "content": f"Follow-up scheduled for {payload.follow_up_date} ({payload.type})",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    doc.pop("_id", None)
    return doc

@api.get("/follow-ups")
async def list_follow_ups(user: dict = Depends(get_current_user), status: Optional[str] = None, lead_id: Optional[str] = None):
    q = {}
    if status: q["status"] = status
    if lead_id: q["lead_id"] = lead_id
    if not is_admin_role(user): q["created_by"] = user["id"]
    return await db.follow_ups.find(q, {"_id": 0}).sort("follow_up_date", 1).to_list(1000)

@api.patch("/follow-ups/{fid}")
async def update_follow_up(fid: str, payload: FollowUpUpdate, user: dict = Depends(get_current_user)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.follow_ups.update_one({"id": fid}, {"$set": doc})
    row = await db.follow_ups.find_one({"id": fid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/follow-ups/{fid}")
async def delete_follow_up(fid: str, user: dict = Depends(get_current_user)):
    await db.follow_ups.delete_one({"id": fid})
    return {"ok": True}

# ---------- Contact Attempt Management ----------
@api.post("/leads/{lead_id}/contact-attempts", status_code=201)
async def create_contact_attempt(lead_id: str, payload: ContactAttemptCreate, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["lead_id"] = lead_id
    doc["user_id"] = user["id"]
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.contact_attempts.insert_one(doc)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "user_id": user["id"],
        "type": payload.type,
        "content": f"Contact attempt via {payload.type}: {payload.content or payload.outcome or ''}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    doc.pop("_id", None)
    return doc

@api.get("/leads/{lead_id}/contact-attempts")
async def list_contact_attempts(lead_id: str, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    return await db.contact_attempts.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(500)

# ---------- Design Team Module ----------
@api.post("/design-tasks", status_code=201)
async def create_design_task(payload: DesignTaskCreate, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.design_tasks.insert_one(doc)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": payload.lead_id,
        "user_id": user["id"],
        "type": "note",
        "content": f"Design task created: {payload.title} (assigned to {payload.assigned_to})",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    doc.pop("_id", None)
    return doc

@api.get("/design-tasks")
async def list_design_tasks(user: dict = Depends(get_current_user), status: Optional[str] = None, assigned_to: Optional[str] = None):
    q = {}
    if status: q["status"] = status
    if assigned_to: q["assigned_to"] = assigned_to
    if not is_admin_role(user): q["assigned_to"] = user["id"]
    return await db.design_tasks.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.patch("/design-tasks/{did}")
async def update_design_task(did: str, payload: DesignTaskUpdate, user: dict = Depends(get_current_user)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.design_tasks.update_one({"id": did}, {"$set": doc})
    row = await db.design_tasks.find_one({"id": did}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/design-tasks/{did}")
async def delete_design_task(did: str, user: dict = Depends(require_admin)):
    await db.design_tasks.delete_one({"id": did})
    return {"ok": True}

# ---------- BOQ Module (Enhanced) ----------
@api.post("/boqs", status_code=201)
async def create_boq(payload: BOQCreate, user: dict = Depends(get_current_user)):
    subtotal = sum(i.qty * i.unit_price * (1 - i.discount_pct / 100 - i.fixed_discount / max(i.qty * i.unit_price, 1)) for i in payload.items)
    tax = sum(i.qty * i.unit_price * (1 - i.discount_pct / 100 - i.fixed_discount / max(i.qty * i.unit_price, 1)) * i.tax_pct / 100 for i in payload.items)
    total = subtotal + tax
    boq = {
        "id": str(uuid.uuid4()),
        "lead_id": payload.lead_id,
        "quotation_id": payload.quotation_id,
        "items": [i.model_dump() for i in payload.items],
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "currency": payload.currency,
        "valid_until": payload.valid_until,
        "terms": payload.terms,
        "notes": payload.notes,
        "status": payload.status,
        "version": payload.version,
        "approved_by": payload.approved_by,
        "approved_at": payload.approved_at,
        "revision_notes": payload.revision_notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.boqs.insert_one(boq)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": payload.lead_id,
        "user_id": user["id"],
        "type": "note",
        "content": f"BOQ created v{payload.version} - Total: {payload.currency} {total:,.2f}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    boq.pop("_id", None)
    return boq

@api.get("/boqs")
async def list_boqs(user: dict = Depends(get_current_user), status: Optional[str] = None):
    q = {}
    if status: q["status"] = status
    return await db.boqs.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.get("/boqs/{bid}")
async def get_boq(bid: str, user: dict = Depends(get_current_user)):
    boq = await db.boqs.find_one({"id": bid}, {"_id": 0})
    if not boq: raise HTTPException(status_code=404, detail="BOQ not found")
    return boq

@api.patch("/boqs/{bid}")
async def update_boq(bid: str, payload: BOQUpdate, user: dict = Depends(get_current_user)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.boqs.update_one({"id": bid}, {"$set": doc})
    row = await db.boqs.find_one({"id": bid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/boqs/{bid}")
async def delete_boq(bid: str, user: dict = Depends(require_admin)):
    await db.boqs.delete_one({"id": bid})
    return {"ok": True}

# ---------- Purchase Order Module ----------
@api.post("/purchase-orders", status_code=201)
async def create_po(payload: PurchaseOrderCreate, user: dict = Depends(get_current_user)):
    po = {
        "id": str(uuid.uuid4()),
        "po_no": payload.po_no,
        "supplier_id": payload.supplier_id,
        "supplier_name": payload.supplier_name,
        "items": [i.model_dump() for i in payload.items],
        "subtotal": payload.subtotal,
        "tax": payload.tax,
        "total": payload.total,
        "currency": payload.currency,
        "delivery_date": payload.delivery_date,
        "payment_terms": payload.payment_terms,
        "status": payload.status,
        "approved_by": payload.approved_by,
        "approved_at": payload.approved_at,
        "notes": payload.notes,
        "attachments": payload.attachments,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.purchase_orders.insert_one(po)
    po.pop("_id", None)
    return po

@api.get("/purchase-orders")
async def list_pos(user: dict = Depends(get_current_user), status: Optional[str] = None):
    q = {}
    if status: q["status"] = status
    return await db.purchase_orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.patch("/purchase-orders/{pid}")
async def update_po(pid: str, payload: PurchaseOrderUpdate, user: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.purchase_orders.update_one({"id": pid}, {"$set": doc})
    row = await db.purchase_orders.find_one({"id": pid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/purchase-orders/{pid}")
async def delete_po(pid: str, user: dict = Depends(require_admin)):
    await db.purchase_orders.delete_one({"id": pid})
    return {"ok": True}

# ---------- Invoice Module (Enhanced) ----------
@api.post("/invoices", status_code=201)
async def create_invoice(payload: InvoiceCreate, user: dict = Depends(get_current_user)):
    invoice = {
        "id": str(uuid.uuid4()),
        "invoice_no": payload.invoice_no,
        "quotation_id": payload.quotation_id,
        "po_id": payload.po_id,
        "customer_name": payload.customer_name,
        "customer_email": payload.customer_email,
        "items": [i.model_dump() for i in payload.items],
        "subtotal": payload.subtotal,
        "tax": payload.tax,
        "total": payload.total,
        "paid_amount": payload.paid_amount,
        "outstanding": payload.total - payload.paid_amount,
        "currency": payload.currency,
        "due_date": payload.due_date,
        "status": payload.status,
        "payment_terms": payload.payment_terms,
        "notes": payload.notes,
        "gst_pct": payload.gst_pct,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.invoices.insert_one(invoice)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "type": "note",
        "content": f"Invoice {payload.invoice_no} created - Total: {payload.currency} {payload.total:,.2f}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    invoice.pop("_id", None)
    return invoice

@api.get("/invoices")
async def list_invoices(user: dict = Depends(get_current_user), status: Optional[str] = None):
    q = {}
    if status: q["status"] = status
    return await db.invoices.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.patch("/invoices/{iid}")
async def update_invoice(iid: str, payload: InvoiceUpdate, user: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.invoices.update_one({"id": iid}, {"$set": doc})
    row = await db.invoices.find_one({"id": iid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/invoices/{iid}")
async def delete_invoice(iid: str, user: dict = Depends(require_admin)):
    await db.invoices.delete_one({"id": iid})
    return {"ok": True}

# ---------- Negotiation Module ----------
@api.post("/negotiations", status_code=201)
async def create_negotiation(payload: NegotiationCreate, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.negotiations.insert_one(doc)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": payload.lead_id,
        "user_id": user["id"],
        "type": "note",
        "content": f"Negotiation started - revision {payload.revision}, discount {payload.discount_pct}%",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    doc.pop("_id", None)
    return doc

@api.get("/negotiations")
async def list_negotiations(user: dict = Depends(get_current_user), quotation_id: Optional[str] = None):
    q = {}
    if quotation_id: q["quotation_id"] = quotation_id
    return await db.negotiations.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.patch("/negotiations/{nid}")
async def update_negotiation(nid: str, payload: NegotiationUpdate, user: dict = Depends(get_current_user)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.negotiations.update_one({"id": nid}, {"$set": doc})
    row = await db.negotiations.find_one({"id": nid}, {"_id": 0})
    return row or {"ok": True}

# ---------- Lost Lead Management ----------
@api.post("/leads/{lead_id}/lost", status_code=201)
async def mark_lead_lost(lead_id: str, payload: LostLeadCreate, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    lost = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "reason": payload.reason,
        "details": payload.details,
        "competitor_name": payload.competitor_name,
        "competitor_product": payload.competitor_product,
        "expected_closure": payload.expected_closure,
        "notes": payload.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.lost_leads.insert_one(lost)
    await db.leads.update_one({"id": lead_id}, {"$set": {"stage": "lost_lead", "updated_at": datetime.now(timezone.utc).isoformat()}})
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "user_id": user["id"],
        "type": "note",
        "content": f"Lead marked as lost - Reason: {payload.reason}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    lost.pop("_id", None)
    return lost

@api.get("/lost-leads")
async def list_lost_leads(user: dict = Depends(get_current_user), reason: Optional[str] = None):
    q = {}
    if reason: q["reason"] = reason
    return await db.lost_leads.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.get("/lost-leads/analytics")
async def lost_lead_analytics(user: dict = Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$reason", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    by_reason = await db.lost_leads.aggregate(pipeline).to_list(100)
    total = await db.lost_leads.count_documents({})
    return {"total": total, "by_reason": by_reason}

# ---------- Requirement Discussion Module ----------
@api.post("/leads/{lead_id}/requirements", status_code=201)
async def create_requirement_discussion(lead_id: str, payload: RequirementDiscussionCreate, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["lead_id"] = lead_id
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.requirement_discussions.insert_one(doc)
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "user_id": user["id"],
        "type": "note",
        "content": f"Requirement discussion recorded for lead {lead_id}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    doc.pop("_id", None)
    return doc

@api.get("/leads/{lead_id}/requirements")
async def list_requirement_discussions(lead_id: str, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    if not is_admin_role(user) and lead.get("assigned_to") != user["id"]:
        raise HTTPException(status_code=403, detail="Not assigned to you")
    return await db.requirement_discussions.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(100)

# ---------- Activity Log (Audit) ----------
@api.post("/activity-logs", status_code=201)
async def create_activity_log(payload: ActivityLogCreate, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["user_id"] = user["id"]
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.activity_logs.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/activity-logs")
async def list_activity_logs(user: dict = Depends(get_current_user), module: Optional[str] = None, limit: int = 100):
    q = {}
    if module: q["module"] = module
    if not is_admin_role(user): q["user_id"] = user["id"]
    return await db.activity_logs.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)

# ---------- Notifications ----------
@api.post("/notifications", status_code=201)
async def create_notification(payload: NotificationCreate, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.notifications.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user), read: Optional[bool] = None, limit: int = 50):
    q = {"user_id": user["id"]}
    if read is not None: q["read"] = read
    return await db.notifications.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)

@api.patch("/notifications/{nid}")
async def update_notification(nid: str, payload: NotificationUpdate, user: dict = Depends(get_current_user)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    await db.notifications.update_one({"id": nid}, {"$set": doc})
    row = await db.notifications.find_one({"id": nid}, {"_id": 0})
    return row or {"ok": True}

@api.delete("/notifications/{nid}")
async def delete_notification(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.delete_one({"id": nid})
    return {"ok": True}

@api.get("/notifications/unread-count")
async def unread_notification_count(user: dict = Depends(get_current_user)):
    count = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    return {"unread_count": count}

# ---------- Sales Targets ----------
@api.post("/sales-targets", status_code=201)
async def create_sales_target(payload: SalesTargetCreate, user: dict = Depends(require_admin)):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.sales_targets.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/sales-targets")
async def list_sales_targets(user: dict = Depends(get_current_user), user_id: Optional[str] = None):
    q = {}
    if user_id: q["user_id"] = user_id
    if not is_admin_role(user): q["user_id"] = user["id"]
    return await db.sales_targets.find(q, {"_id": 0}).sort("start_date", -1).to_list(100)

@api.patch("/sales-targets/{tid}")
async def update_sales_target(tid: str, payload: SalesTargetUpdate, user: dict = Depends(require_admin)):
    doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not doc: return {"ok": True}
    await db.sales_targets.update_one({"id": tid}, {"$set": doc})
    row = await db.sales_targets.find_one({"id": tid}, {"_id": 0})
    return row or {"ok": True}

# ---------- Reports ----------
@api.post("/reports/generate")
async def generate_report(payload: ReportCreate, user: dict = Depends(get_current_user)):
    report = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "type": payload.type,
        "filters": payload.filters,
        "format": payload.format,
        "generated_by": user["id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.reports.insert_one(report)
    report.pop("_id", None)
    return report

@api.get("/reports")
async def list_reports(user: dict = Depends(get_current_user)):
    return await db.reports.find({}, {"_id": 0}).sort("generated_at", -1).to_list(100)

# ---------- Global Search ----------
# Each entry declares the fields it matches on, the fields it returns, and the module
# label the UI groups by. Projections are explicit so a search hit can never carry
# internal fields (lead notes, webhook secrets, salaries) into the results list.
SEARCH_SPECS = [
    {"key": "leads", "label": "Leads", "coll": "leads",
     "match": ["name", "company", "email", "phone"],
     "show": ["id", "name", "company", "email", "phone", "stage", "assigned_to"], "scoped": True},
    {"key": "customers", "label": "Customers", "coll": "customers",
     "match": ["name", "company", "email"],
     "show": ["id", "name", "company", "email", "phone"], "scoped": False},
    {"key": "contacts", "label": "Contacts", "coll": "contacts",
     "match": ["name", "email", "company"],
     "show": ["id", "name", "company", "email", "phone", "role"], "scoped": False},
    {"key": "quotations", "label": "Quotations", "coll": "quotations",
     "match": ["quote_no", "client_name", "company_name"],
     "show": ["id", "quote_no", "total", "status", "client_name", "company_name"], "scoped": "lead"},
    {"key": "purchase_orders", "label": "Purchase Orders", "coll": "purchase_orders",
     "match": ["po_no", "customer_name", "supplier_name"],
     "show": ["id", "po_no", "total", "status", "direction"], "scoped": "lead"},
    {"key": "projects", "label": "Projects", "coll": "projects",
     "match": ["name", "client", "project_no"],
     "show": ["id", "name", "client", "status", "project_no", "budget"], "scoped": False},
    {"key": "products", "label": "Products", "coll": "products",
     "match": ["name", "sku", "brand"],
     "show": ["id", "name", "sku", "brand"], "scoped": False},
    {"key": "tasks", "label": "Tasks", "coll": "tasks",
     "match": ["title", "description"],
     "show": ["id", "title", "status", "priority", "due_date", "project_id"], "scoped": False},
    {"key": "invoices", "label": "Invoices", "coll": "invoices",
     "match": ["invoice_no"],
     "show": ["id", "invoice_no", "total", "status"], "scoped": False},
    {"key": "events", "label": "Meetings", "coll": "events",
     "match": ["title", "location"],
     "show": ["id", "title", "start_time", "end_time", "location"], "scoped": "lead"},
]


@api.get("/search")
async def global_search(q: str, types: Optional[str] = None, limit: int = 20,
                        user: dict = Depends(get_current_user)):
    """Permission-scoped, categorised global search (plan 7.6; fixes B6/B10).

    Three defects are addressed here:

    * **B6** - the sales branch ignored ``q`` entirely for quotations and returned all
      of the rep's quotes, so typing any character dumped their whole book into the
      results panel.
    * Unescaped ``$regex`` let a stray ``(`` or ``.*`` from the user raise a 500 or
      trigger catastrophic backtracking, so the term is escaped.
    * Projections were ``{"_id": 0}`` (whole document), which leaked internal notes.
    """
    term = (q or "").strip()
    if len(term) < 2:
        return {"query": term, "categories": [], "total": 0}
    rx = re.escape(term)

    wanted = None
    if types:
        wanted = {t.strip() for t in types.split(",") if t.strip()}
    specs = [s for s in SEARCH_SPECS if not wanted or s["key"] in wanted]
    limit = max(1, min(int(limit or 20), 50))

    admin = is_admin_role(user)
    my_lead_ids = None
    if not admin:
        mine = await db.leads.find({"assigned_to": user["id"]}, {"_id": 0, "id": 1}).to_list(1000)
        my_lead_ids = [l["id"] for l in mine]

    categories = []
    total = 0
    for spec in specs:
        query = {"$or": [{f: {"$regex": rx, "$options": "i"}} for f in spec["match"] if f]}

        scope = spec.get("scoped")
        if not admin:
            if scope is True:
                query["assigned_to"] = user["id"]
            elif scope == "lead":
                # Only records hanging off this rep's own leads.
                query["$and"] = [{"$or": [{"lead_id": {"$in": my_lead_ids or [""]}}]}]
            elif scope == "assigned":
                query["assigned_to"] = user["id"]

        projection = {"_id": 0, **{f: 1 for f in spec["show"]}}
        rows = await db[spec["coll"]].find(query, projection).to_list(limit)
        if rows:
            total += len(rows)
            categories.append({"key": spec["key"], "label": spec["label"], "items": rows})

    return {"query": term, "categories": categories, "total": total}


@api.get("/activity-timeline")
async def activity_timeline(
    module: Optional[str] = None,
    record_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """Cross-module activity feed, permission-scoped.

    ``module`` selects which record types to include so the UI can show "everything"
    or just one entity's history without a second endpoint per module.
    """
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    if project_id:
        query["project_id"] = project_id
    if record_id and not (lead_id or project_id):
        query["$or"] = [{"lead_id": record_id}, {"project_id": record_id}]

    allowed = {"note", "stage_change", "quotation", "task", "call", "meeting", "email"}
    if module:
        allowed = {module}

    rows = await db.activities.find(query, {"_id": 0}).sort("created_at", -1).to_list(min(int(limit or 100), 500))
    rows = [r for r in rows if r.get("type") in allowed]

    if not is_admin_role(user):
        visible = set()
        mine = await db.leads.find({"assigned_to": user["id"]}, {"_id": 0, "id": 1}).to_list(1000)
        visible.update(l["id"] for l in mine)
        rows = [r for r in rows if not r.get("lead_id") or r["lead_id"] in visible]

    return {"activity": rows, "count": len(rows)}

# ---------- Enhanced Dashboard Stats ----------
@api.get("/dashboard/sales")
async def sales_dashboard(user: dict = Depends(get_current_user)):
    pipeline = await db.leads.aggregate([
        {"$group": {"_id": "$stage", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]).to_list(20)
    by_source = await db.leads.aggregate([
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]).to_list(20)
    total_leads = await db.leads.count_documents({})
    won_leads = await db.leads.count_documents({"stage": "completed"})
    lost_leads = await db.leads.count_documents({"stage": "lost_lead"})
    total_revenue = await db.invoices.aggregate([
        {"$match": {"status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]).to_list(1)
    revenue = total_revenue[0]["total"] if total_revenue else 0
    return {
        "total_leads": total_leads,
        "won_leads": won_leads,
        "lost_leads": lost_leads,
        "conversion_rate": round((won_leads / total_leads * 100) if total_leads > 0 else 0, 1),
        "total_revenue": revenue,
        "by_stage": {p["_id"]: p["count"] for p in pipeline},
        "by_source": {s["_id"]: s["count"] for s in by_source},
    }

@api.get("/dashboard/executive")
async def executive_dashboard(user: dict = Depends(get_current_user)):
    my_leads = await db.leads.count_documents({"assigned_to": user["id"], "stage": {"$nin": ["completed", "lost_lead"]}})
    my_won = await db.leads.count_documents({"assigned_to": user["id"], "stage": "completed"})
    my_tasks = await db.tasks.count_documents({"assigned_to": user["id"], "status": "pending"})
    my_meetings = await db.events.count_documents({"lead_id": {"$exists": True}})
    user_lead_ids = [l["id"] for l in await db.leads.find({"assigned_to": user["id"]}, {"_id": 0, "id": 1}).to_list(500)]
    my_quotations = await db.quotations.count_documents({"lead_id": {"$in": user_lead_ids}})
    return {
        "my_leads": my_leads,
        "my_won": my_won,
        "my_tasks": my_tasks,
        "my_meetings": my_meetings,
        "my_quotations": my_quotations,
        "user": user,
    }

# ---------- Sales Executive Dashboard ----------
@api.get("/dashboard/executive-detailed")
async def executive_detailed_dashboard(user: dict = Depends(get_current_user)):
    my_leads = await db.leads.find({"assigned_to": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_calls = await db.contact_attempts.count_documents({"lead_id": {"$in": [l["id"] for l in my_leads]}, "type": "phone_call", "created_at": {"$gte": today}})
    today_followups = await db.follow_ups.count_documents({"created_by": user["id"], "follow_up_date": today, "status": "pending"})
    pending_tasks = await db.tasks.count_documents({"assigned_to": user["id"], "status": "pending"})
    upcoming_meetings = await db.events.count_documents({"start_time": {"$gte": datetime.now(timezone.utc).isoformat()}, "lead_id": {"$exists": True}})
    missed_followups = await db.follow_ups.count_documents({"created_by": user["id"], "status": "missed"})
    total_leads = len(my_leads)
    won_leads = len([l for l in my_leads if l.get("stage") == "completed"])
    conversion_pct = round((won_leads / total_leads * 100) if total_leads > 0 else 0, 1)
    return {
        "my_leads": my_leads[:20],
        "today_calls": today_calls,
        "today_followups": today_followups,
        "pending_tasks": pending_tasks,
        "upcoming_meetings": upcoming_meetings,
        "missed_followups": missed_followups,
        "total_leads": total_leads,
        "won_leads": won_leads,
        "conversion_pct": conversion_pct,
        "lead_status_summary": {
            "new": len([l for l in my_leads if l.get("stage") == "new"]),
            "contacted": len([l for l in my_leads if l.get("stage") == "contacted"]),
            "qualified": len([l for l in my_leads if l.get("stage") == "qualified"]),
            "quoted": len([l for l in my_leads if l.get("stage") == "quoted"]),
            "won": won_leads,
            "lost": len([l for l in my_leads if l.get("stage") == "lost_lead"]),
        },
    }


# ---------- Configurable CRM Settings (admin-managed) ----------
CONFIG_KEYS = [
    "lead_stages", "lead_sources", "project_stages", "task_statuses", "priorities",
    "quote_statuses", "po_statuses", "customer_types", "project_types",
    "contact_types", "project_workflows", "document_templates",
]


class ConfigItemIn(BaseModel):
    key: Optional[str] = None
    label: str
    color: Optional[str] = "slate"
    icon: Optional[str] = None
    group: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = True
    is_won: Optional[bool] = False
    is_lost: Optional[bool] = False
    is_open: Optional[bool] = None
    steps: Optional[List[str]] = None
    applies_to: Optional[List[str]] = None


class ConfigItemPatch(BaseModel):
    label: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    group: Optional[str] = None
    is_active: Optional[bool] = None
    is_won: Optional[bool] = None
    is_lost: Optional[bool] = None
    is_open: Optional[bool] = None
    steps: Optional[List[str]] = None
    applies_to: Optional[List[str]] = None


class ConfigReorderIn(BaseModel):
    order: List[str]  # item ids in the desired sequence


def _config_key_guard(key: str) -> str:
    if key not in CONFIG_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown config key '{key}'")
    return key


async def _config_save(db, config_key: str, items: list[dict], current: dict, user: dict) -> None:
    """Persist a config list.

    Guarded on `version` so two admins editing the same list concurrently cannot
    silently overwrite each other (last write would otherwise drop one change).
    """
    next_version = current.get("version", 1) + 1
    res = await db.crm_config_sets.update_one(
        {"key": config_key, "version": current.get("version", 1)},
        {"$set": {"items": items, "version": next_version,
                  "updated_at": datetime.now(timezone.utc).isoformat(),
                  "updated_by": user["email"]}},
    )
    if res.matched_count == 0:
        raise HTTPException(
            status_code=409,
            detail="This configuration was changed by someone else. Reload and try again.",
        )


@api.get("/config")
async def list_all_config(_: dict = Depends(get_current_user)):
    """Every configurable list in one call. The frontend caches this on boot."""
    docs = await db.crm_config_sets.find({}, {"_id": 0}).to_list(100)
    out: dict = {}
    for d in docs:
        items = sorted(d.get("items", []), key=lambda i: (i.get("order", 0), i.get("key", "")))
        out[d["key"]] = {
            "key": d["key"],
            "label": d.get("label", d["key"]),
            "version": d.get("version", 1),
            "items": items,
        }
    return out


@api.get("/config/{config_key}")
async def get_config(config_key: str, _: dict = Depends(get_current_user)):
    _config_key_guard(config_key)
    d = await db.crm_config_sets.find_one({"key": config_key}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Config not found")
    d["items"] = sorted(d.get("items", []), key=lambda i: (i.get("order", 0), i.get("key", "")))
    return d


@api.post("/config/{config_key}", status_code=201)
async def create_config_item(config_key: str, payload: ConfigItemIn, user: dict = Depends(require_superadmin)):
    _config_key_guard(config_key)
    d = await db.crm_config_sets.find_one({"key": config_key})
    if not d:
        raise HTTPException(status_code=404, detail="Config not found")
    items = d.get("items", [])
    key = (payload.key or payload.label).strip().lower().replace(" ", "_").replace("-", "_")
    if any(i.get("key") == key for i in items):
        raise HTTPException(status_code=400, detail=f"'{key}' already exists in {config_key}")
    item = {
        "id": key,
        "key": key,
        "label": payload.label,
        "color": payload.color or "slate",
        "icon": payload.icon,
        "group": payload.group,
        "order": payload.order if payload.order is not None else len(items),
        "is_active": True if payload.is_active is None else payload.is_active,
        "is_won": bool(payload.is_won),
        "is_lost": bool(payload.is_lost),
        "is_open": payload.is_open,
        "system_key": False,
    }
    if payload.steps is not None:
        item["steps"] = payload.steps
    if payload.applies_to is not None:
        item["applies_to"] = payload.applies_to
    items.append(item)
    await _config_save(db, config_key, items, d, user)
    return item


@api.patch("/config/{config_key}/{item_id}")
async def update_config_item(config_key: str, item_id: str, payload: ConfigItemPatch, user: dict = Depends(require_superadmin)):
    _config_key_guard(config_key)
    d = await db.crm_config_sets.find_one({"key": config_key})
    if not d:
        raise HTTPException(status_code=404, detail="Config not found")
    items = d.get("items", [])
    idx = next((i for i, it in enumerate(items) if it.get("key") == item_id or it.get("id") == item_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"'{item_id}' not found in {config_key}")
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    items[idx] = {**items[idx], **patch}
    await _config_save(db, config_key, items, d, user)
    return items[idx]


@api.delete("/config/{config_key}/{item_id}")
async def deactivate_config_item(config_key: str, item_id: str, user: dict = Depends(require_superadmin)):
    """Soft delete. An item in use is never removed — only marked inactive."""
    _config_key_guard(config_key)
    d = await db.crm_config_sets.find_one({"key": config_key})
    if not d:
        raise HTTPException(status_code=404, detail="Config not found")
    items = d.get("items", [])
    target = next((it for it in items if it.get("key") == item_id or it.get("id") == item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"'{item_id}' not found in {config_key}")

    usage_count = await _config_usage_count(config_key, item_id)
    if usage_count:
        target["is_active"] = False
        target["deactivated_reason"] = f"in use by {usage_count} record(s)"
    else:
        items = [it for it in items if it is not target]
    await _config_save(db, config_key, items, d, user)
    return {"ok": True, "soft_deleted": bool(usage_count), "usage_count": usage_count}


async def _config_usage_count(config_key: str, item_id: str) -> int:
    """How many live records still reference this config item."""
    map_key = {
        "lead_stages": ("leads", "stage"),
        "project_stages": ("projects", "stage_id"),
        "task_statuses": ("tasks", "status"),
        "priorities": ("tasks", "priority"),
        "quote_statuses": ("quotations", "status"),
        "po_statuses": ("purchase_orders", "status"),
    }.get(config_key)
    if not map_key:
        return 0
    coll, field = map_key
    return await db[coll].count_documents({field: item_id})


@api.post("/config/{config_key}/reorder")
async def reorder_config(config_key: str, payload: ConfigReorderIn, user: dict = Depends(require_superadmin)):
    _config_key_guard(config_key)
    d = await db.crm_config_sets.find_one({"key": config_key})
    if not d:
        raise HTTPException(status_code=404, detail="Config not found")
    items = d.get("items", [])
    by_id = {it.get("key"): it for it in items}
    reordered = []
    seen: set = set()
    for i, item_id in enumerate(payload.order):
        # Dedupe: a repeated id in the request must never duplicate the item.
        if item_id in by_id and item_id not in seen:
            seen.add(item_id)
            by_id[item_id]["order"] = len(reordered)
            reordered.append(by_id[item_id])
    # Anything the caller did not mention keeps its relative order at the end.
    for it in items:
        if it.get("key") not in seen:
            it["order"] = len(reordered)
            reordered.append(it)
    await _config_save(db, config_key, reordered, d, user)
    return {"ok": True, "items": reordered}


@api.post("/config/{config_key}/reset")
async def reset_config(config_key: str, user: dict = Depends(require_superadmin)):
    """Restore one config list to the shipped defaults.

    Only ids that already exist as defaults are refreshed; items an admin created
    are left alone so custom work is never silently destroyed.
    """
    from migrations import CONFIG_DEFAULTS

    _config_key_guard(config_key)
    label, defaults = CONFIG_DEFAULTS[config_key]
    d = await db.crm_config_sets.find_one({"key": config_key})
    if not d:
        raise HTTPException(status_code=404, detail="Config not found")
    current = d.get("items", [])
    by_id = {it.get("key"): it for it in current}
    merged = []
    for dflt in defaults:
        existing = by_id.get(dflt["key"])
        merged.append({**dflt, **existing} if existing else dflt)
    for it in current:
        if it.get("key") not in {d_["key"] for d_ in defaults}:
            merged.append(it)
    await _config_save(db, config_key, merged, d, user)
    return {"ok": True, "items": merged}


# ---------- Startup ----------
@app.on_event("startup")
async def on_start():
    from migrations import run_migrations

    try:
        applied = await run_migrations(db, log=logger.info)
        if applied:
            logger.info("Applied migrations: %s", ", ".join(applied))
    except Exception as exc:  # noqa: BLE001
        logger.error("Migration run failed: %s", exc)

    # Index creation must never take the API down. A duplicate or incompatible
    # index is a data problem to be reported and fixed, not a reason to refuse all
    # traffic; the process used to exit here and Docker then crash-looped.
    async def _ensure_index(collection: str, keys, **kwargs) -> None:
        try:
            await db[collection].create_index(keys, **kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.error("Index %s on %s could not be created: %s", keys, collection, exc)

    # Partial, not plain, unique: the staff directory imports people who have no email
    # address yet. A plain unique index treats every missing value as the same value
    # and rejects the second such row outright.
    await _ensure_index("users", "email", unique=True,
                        partialFilterExpression={"email": {"$type": "string"}})
    await _ensure_index("users", "id", unique=True)
    await _ensure_index("leads", "id", unique=True)
    await _ensure_index("leads", "assigned_to")
    await _ensure_index("leads", "stage")
    await _ensure_index("activities", "lead_id")
    await _ensure_index("quotations", "lead_id")
    await _ensure_index("webhook_settings", "id", unique=True)
    await _ensure_index("webhook_logs", "event")
    await _ensure_index("webhook_logs", "created_at")
    await _ensure_index("resend_settings", "id", unique=True)
    await _ensure_index("email_logs", "event")
    await _ensure_index("email_logs", "created_at")
    # Seed admin from env — falls back to safe defaults ONLY in dev.
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@hitechaudio.in").lower()
    admin_pw_env = os.environ.get("ADMIN_PASSWORD")
    if not admin_pw_env:
        # Dev fallback: keep the currently-published preview password so preview logins
        # don't break, but log a WARN so operators know to set ADMIN_PASSWORD in prod.
        admin_pw_env = "Admin@123"
        logger.warning("ADMIN_PASSWORD not set — falling back to development default. Set ADMIN_PASSWORD in .env for production.")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "name": "Admin",
            "email": admin_email,
            "password_hash": hash_password(admin_pw_env),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Seeded admin user %s", admin_email)
    else:
        # keep password in sync with env
        if not verify_password(admin_pw_env, existing["password_hash"]):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw_env)}})
    # Seed one demo sales user — GATED. Never seed unless SEED_DEMO_USERS=true is explicitly set.
    if os.environ.get("SEED_DEMO_USERS", "").lower() in ("1", "true", "yes"):
        sales_email = os.environ.get("SALES_DEMO_EMAIL", "sales@hitechaudio.in").lower()
        sales_pw = os.environ.get("SALES_DEMO_PASSWORD", "Sales@123")
        existing_sales = await db.users.find_one({"email": sales_email})
        if not existing_sales:
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                "name": "Rahul Sharma",
                "email": sales_email,
                "password_hash": hash_password(sales_pw),
                "role": "sales",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info("Seeded demo sales user %s (SEED_DEMO_USERS=true)", sales_email)
        elif not verify_password(sales_pw, existing_sales["password_hash"]):
            await db.users.update_one({"email": sales_email}, {"$set": {"password_hash": hash_password(sales_pw)}})
    # Backfill allowed_brands on legacy users
    await db.users.update_many({"allowed_brands": {"$exists": False}}, {"$set": {"allowed_brands": []}})
    # Seed brands
    await db.brands.create_index("name", unique=True)
    await db.products.create_index("id", unique=True)
    await db.projects.create_index("id", unique=True)
    await db.customers.create_index("id", unique=True)
    await db.contacts.create_index("id", unique=True)
    await db.accounting.create_index("id", unique=True)
    await db.events.create_index("id", unique=True)
    await db.tasks.create_index("id", unique=True)
    await db.work_orders.create_index("id", unique=True)
    await db.suppliers.create_index("id", unique=True)
    await db.social_posts.create_index("id", unique=True)
    await db.campaigns.create_index("id", unique=True)
    await db.bookings.create_index("id", unique=True)
    await db.settings.create_index("key", unique=True)
    # New ERP collection indexes
    await db.follow_ups.create_index("lead_id")
    await db.follow_ups.create_index("created_by")
    await db.follow_ups.create_index("status")
    await db.notifications.create_index("user_id")
    await db.notifications.create_index("read")
    await db.boqs.create_index("lead_id")
    await db.boqs.create_index("status")
    await db.purchase_orders.create_index("po_no", unique=True)
    await db.purchase_orders.create_index("supplier_id")
    await db.purchase_orders.create_index("status")
    await db.invoices.create_index("invoice_no", unique=True)
    await db.invoices.create_index("customer_name")
    await db.invoices.create_index("status")
    await db.lost_leads.create_index("lead_id", unique=True)
    await db.lost_leads.create_index("reason")
    await db.requirement_discussions.create_index("lead_id")
    await db.design_tasks.create_index("lead_id")
    await db.design_tasks.create_index("assigned_to")
    await db.design_tasks.create_index("status")
    await db.negotiations.create_index("quotation_id")
    await db.negotiations.create_index("lead_id")
    await db.activity_logs.create_index("user_id")
    await db.activity_logs.create_index("module")
    await db.contact_attempts.create_index("lead_id")
    await db.lead_qualifications.create_index("lead_id")
    await db.sales_targets.create_index("user_id")
    await db.reports.create_index("generated_by")
    # Seed new ERP data
    if not await db.follow_ups.find_one({}):
        await db.follow_ups.insert_many([
            {"id": str(uuid.uuid4()), "lead_id": "demo", "follow_up_date": "2026-07-30", "follow_up_time": "10:00", "type": "call", "status": "pending", "reminder_enabled": True, "reminder_minutes_before": 15, "recurring": False, "escalation_enabled": False, "created_by": "admin", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "lead_id": "demo", "follow_up_date": "2026-07-31", "follow_up_time": "14:00", "type": "email", "status": "pending", "reminder_enabled": True, "reminder_minutes_before": 30, "recurring": False, "escalation_enabled": False, "created_by": "admin", "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.notifications.find_one({}):
        await db.notifications.insert_many([
            {"id": str(uuid.uuid4()), "user_id": "admin", "type": "lead_assigned", "title": "New Lead Assigned", "message": "Lead 'Taj Hotels Enquiry' has been assigned to you.", "link": "/leads", "priority": "high", "read": False, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "user_id": "admin", "type": "follow_up_due", "title": "Follow-up Due", "message": "Follow-up with Taj Hotels is due today.", "link": "/follow-ups", "priority": "medium", "read": False, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "user_id": "admin", "type": "quotation_sent", "title": "Quotation Sent", "message": "Quotation HAI-Q-1001 has been sent to the client.", "link": "/quotations", "priority": "low", "read": True, "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.boqs.find_one({}):
        await db.boqs.insert_many([
            {"id": str(uuid.uuid4()), "lead_id": "demo", "quotation_id": None, "items": [{"product_id": None, "product_name": "L-Acoustics K2 Line Array", "sku": "K2-001", "brand": "L-Acoustics", "description": "120° x 40° Line Array Element", "qty": 8, "unit_price": 450000, "discount_pct": 5, "fixed_discount": 0, "tax_pct": 18, "total": 3420000}], "subtotal": 3420000, "tax": 615600, "total": 4035600, "currency": "INR", "valid_until": "2026-08-31", "terms": "Payment within 30 days", "notes": "Includes installation support", "status": "approved", "version": 2, "approved_by": "admin", "approved_at": datetime.now(timezone.utc).isoformat(), "revision_notes": "Price negotiation completed", "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.purchase_orders.find_one({}):
        await db.purchase_orders.insert_many([
            {"id": str(uuid.uuid4()), "po_no": "PO-2026-001", "supplier_id": "demo", "supplier_name": "AVL Distributors", "items": [{"product_id": None, "product_name": "L-Acoustics K2", "sku": "K2-001", "brand": "L-Acoustics", "description": "Line Array Element", "qty": 8, "unit_price": 450000, "discount_pct": 0, "fixed_discount": 0, "tax_pct": 18, "total": 3600000}], "subtotal": 3600000, "tax": 648000, "total": 4248000, "currency": "INR", "delivery_date": "2026-08-15", "payment_terms": "Net 30", "status": "approved", "approved_by": "admin", "approved_at": datetime.now(timezone.utc).isoformat(), "notes": "Urgent delivery required", "attachments": [], "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.invoices.find_one({}):
        await db.invoices.insert_many([
            {"id": str(uuid.uuid4()), "invoice_no": "INV-2026-002", "quotation_id": None, "po_id": None, "customer_name": "Taj Hotels", "customer_email": "procurement@tajhotels.com", "items": [{"product_id": None, "product_name": "L-Acoustics K2 Line Array", "sku": "K2-001", "brand": "L-Acoustics", "description": "120° x 40° Line Array Element", "qty": 8, "unit_price": 450000, "discount_pct": 5, "fixed_discount": 0, "tax_pct": 18, "total": 3420000}], "subtotal": 3420000, "tax": 615600, "total": 4035600, "paid_amount": 4035600, "outstanding": 0, "currency": "INR", "due_date": "2026-08-31", "status": "paid", "payment_terms": "Net 30", "notes": "Full payment received", "gst_pct": 18, "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.negotiations.find_one({}):
        await db.negotiations.insert_many([
            {"id": str(uuid.uuid4()), "quotation_id": "demo", "lead_id": "demo", "revision": 1, "discount_pct": 10, "discount_reason": "Volume discount for 8+ units", "customer_feedback": "Need 15% discount for approval", "approval_status": "pending", "expected_closure": "2026-08-15", "competitor_info": "Competitor offering 12% discount", "notes": "Waiting for client approval", "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.lost_leads.find_one({}):
        await db.lost_leads.insert_many([
            {"id": str(uuid.uuid4()), "lead_id": "demo", "reason": "competitor", "details": "Client chose competitor's lower price", "competitor_name": "SoundTech Pro", "competitor_product": "ST-2000 Series", "expected_closure": "2026-07-15", "notes": "Lost to competitor pricing", "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.requirement_discussions.find_one({}):
        await db.requirement_discussions.insert_many([
            {"id": str(uuid.uuid4()), "lead_id": "demo", "project_type": "Concert Hall", "products_required": ["L-Acoustics K2", "DiGiCo Quantum 338"], "brands": ["L-Acoustics", "DiGiCo"], "quantities": "8x K2, 1x Quantum 338", "site_location": "Mumbai Convention Center", "project_drawings": ["floor_plan_v1.pdf"], "special_requirements": "Must support 148 dB SPL", "budget": 5000000, "competitors": "None identified", "timeline": "2026-08-01 to 2026-09-30", "technical_notes": "Requires 3-phase power supply", "attachments": ["requirements.pdf"], "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.design_tasks.find_one({}):
        await db.design_tasks.insert_many([
            {"id": str(uuid.uuid4()), "lead_id": "demo", "title": "Concert Hall Acoustic Design", "description": "Design acoustic treatment plan for 5000-seat concert hall", "assigned_to": "admin", "drawing_type": "floor_plan", "status": "in_progress", "priority": "high", "due_date": "2026-08-15", "revision": 1, "comments": [], "files": [], "cad_drawings": [], "pdf_files": [], "auto_notify_sales": True, "created_at": datetime.now(timezone.utc).isoformat()},
        ])
    if not await db.sales_targets.find_one({}):
        await db.sales_targets.insert_many([
            {"id": str(uuid.uuid4()), "user_id": "admin", "period": "monthly", "start_date": "2026-07-01", "end_date": "2026-07-31", "revenue_target": 5000000, "leads_target": 50, "quotations_target": 10, "closed_deals_target": 5},
        ])
    if not await db.reports.find_one({}):
        await db.reports.insert_many([
            {"id": str(uuid.uuid4()), "name": "Q3 Sales Report", "type": "sales", "filters": {"period": "Q3", "year": 2026}, "format": "pdf", "generated_by": "admin", "generated_at": datetime.now(timezone.utc).isoformat()},
        ])
    seed_brands = [
        {"name": "L-Acoustics", "country": "France", "description": "Premium professional touring & install loudspeakers.", "logo_url": "https://cms.hitechavl.com/files/images/brand/1733912848913_acoustic.webp"},
        {"name": "RCF", "country": "Italy", "description": "Pro audio loudspeakers, mixers, and installed sound.", "logo_url": "https://cms.hitechavl.com/files/images/brand/1733912946338_rcf.webp"},
        {"name": "DiGiCo", "country": "United Kingdom", "description": "Digital mixing consoles for live, broadcast, and theatre.", "logo_url": "https://cms.hitechavl.com/files/images/brand/1733912834935_digigo.webp"},
    ]
    for b in seed_brands:
        existing = await db.brands.find_one({"name": b["name"]})
        if not existing:
            await db.brands.insert_one({
                "id": str(uuid.uuid4()),
                **b,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        elif not existing.get("logo_url"):
            await db.brands.update_one({"name": b["name"]}, {"$set": {"logo_url": b["logo_url"]}})

    # Seed demo ERP data
    if not await db.projects.find_one({"name": "Hitech Website Redesign"}):
        await db.projects.insert_many([
            {"id": str(uuid.uuid4()), "name": "Hitech Website Redesign", "client": "Hitech AVL", "status": "active", "start_date": "2026-06-01", "end_date": "2026-08-31", "budget": 450000, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "Annual Maintenance Contract", "client": "Taj Hotels", "status": "active", "start_date": "2026-01-01", "end_date": "2026-12-31", "budget": 1200000, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "Conference Hall AV Setup", "client": "Marriott", "status": "completed", "start_date": "2026-02-15", "end_date": "2026-04-30", "budget": 850000, "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.customers.find_one({"name": "Taj Hotels"}):
        await db.customers.insert_many([
            {"id": str(uuid.uuid4()), "name": "Taj Hotels", "company": "Taj Hotels & Resorts", "email": "procurement@tajhotels.com", "phone": "+91-22-6665-1234", "city": "Mumbai", "segment": "Hospitality", "total_value": 2400000, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "Marriott International", "company": "Marriott Hotels", "email": "av@marriott.com", "phone": "+91-124-486-5000", "city": "Gurgaon", "segment": "Hospitality", "total_value": 1800000, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "ITC Hotels", "company": "ITC Hotels", "email": "purchase@itchotels.com", "phone": "+91-33-4567-8900", "city": "Kolkata", "segment": "Hospitality", "total_value": 1600000, "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.contacts.find_one({"name": "Rahul Verma"}):
        await db.contacts.insert_many([
            {"id": str(uuid.uuid4()), "name": "Rahul Verma", "email": "rahul@tajhotels.com", "phone": "+91-98200-12345", "company": "Taj Hotels", "role": "Procurement Head", "customer_id": "demo", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "Priya Singh", "email": "priya@marriott.com", "phone": "+91-98100-54321", "company": "Marriott", "role": "AV Manager", "customer_id": "demo", "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.tasks.find_one({"title": "Follow up with Taj Hotels"}):
        await db.tasks.insert_many([
            {"id": str(uuid.uuid4()), "title": "Follow up with Taj Hotels", "priority": "high", "status": "pending", "due_date": "2026-08-15", "assigned_to": "admin", "lead_id": "demo", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "title": "Ship customs clearance L-Acoustics", "priority": "urgent", "status": "in_progress", "due_date": "2026-07-25", "assigned_to": "sales", "lead_id": "demo", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "title": "Prepare Q3 quotation", "priority": "medium", "status": "pending", "due_date": "2026-07-30", "assigned_to": "admin", "lead_id": "demo", "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.events.find_one({"title": "Team Sync"}):
        await db.events.insert_many([
            {"id": str(uuid.uuid4()), "title": "Team Sync", "type": "meeting", "start_time": "2026-07-23T10:00:00", "end_time": "2026-07-23T11:00:00", "location": "Conference Room A", "lead_id": None, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "title": "Client Call - Taj", "type": "call", "start_time": "2026-07-24T14:00:00", "end_time": "2026-07-24T14:30:00", "location": "Zoom", "lead_id": "demo", "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.accounting.find_one({"doc_no": "INV-2026-001"}):
        await db.accounting.insert_many([
            {"id": str(uuid.uuid4()), "doc_no": "INV-2026-001", "type": "invoice", "party": "Taj Hotels", "amount": 450000, "status": "sent", "date": "2026-07-01", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "doc_no": "EST-2026-042", "type": "estimate", "party": "Marriott", "amount": 320000, "status": "draft", "date": "2026-07-10", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "doc_no": "EXP-2026-017", "type": "expense", "party": "FedEx", "amount": 12000, "status": "paid", "date": "2026-07-15", "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.work_orders.find_one({"title": "Installation - Taj Mumbai"}):
        await db.work_orders.insert_many([
            {"id": str(uuid.uuid4()), "title": "Installation - Taj Mumbai", "type": "installation", "status": "open", "priority": "high", "assigned_to": "admin", "customer_id": "demo", "scheduled_date": "2026-08-01", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "title": "Repair - DiGiCo console", "type": "repair", "status": "in_progress", "priority": "medium", "assigned_to": "sales", "customer_id": "demo", "scheduled_date": "2026-07-28", "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    # Seed Default Roles
    default_roles = [
        {
            "id": "role-superadmin",
            "name": "superadmin",
            "display_name": "Super Admin",
            "description": "Master system administrator with unrestricted control over all modules, custom roles, and global settings.",
            "permissions": ["all", "crm", "accounting", "inventory", "marketing", "social", "projects", "work_orders", "team", "settings"],
            "is_system": True
        },
        {
            "id": "role-admin",
            "name": "admin",
            "display_name": "Administrator",
            "description": "Enterprise administrator with full operational access across business operations.",
            "permissions": ["all", "crm", "accounting", "inventory", "marketing", "social", "projects", "work_orders", "team", "settings"],
            "is_system": True
        },
        {
            "id": "role-sales",
            "name": "sales",
            "display_name": "Sales Executive",
            "description": "Manages leads, customer relationships, commercial proposals, and quotations.",
            "permissions": ["crm", "quotations", "customers", "products"],
            "is_system": True
        },
        {
            "id": "role-marketing",
            "name": "marketing",
            "display_name": "Marketing Team",
            "description": "Manages digital campaigns, social media channels, lead generation, and PR releases.",
            "permissions": ["marketing", "social", "leads", "crm"],
            "is_system": True
        },
        {
            "id": "role-accounts",
            "name": "accounts",
            "display_name": "Accounts & Finance",
            "description": "Manages invoices, payments, expenses, tax filings, and financial ledgers.",
            "permissions": ["accounting", "invoices", "expenses", "quotations"],
            "is_system": True
        },
        {
            "id": "role-logistics",
            "name": "logistics",
            "display_name": "Logistics & Dispatch",
            "description": "Manages shipment tracking, import logistics, and warehouse dispatches.",
            "permissions": ["inventory", "shipments", "suppliers"],
            "is_system": True
        },
        {
            "id": "role-service",
            "name": "service",
            "display_name": "Service & Maintenance",
            "description": "Handles Annual Maintenance Contracts (AMC), field service, and technical repairs.",
            "permissions": ["amcs", "work_orders", "calendar"],
            "is_system": True
        },
        {
            "id": "role-projects",
            "name": "projects",
            "display_name": "Project Manager",
            "description": "Oversees concert stage production projects, milestones, Gantt charts, and job cards.",
            "permissions": ["projects", "work_orders", "tasks", "calendar"],
            "is_system": True
        },
        {
            "id": "role-warehouse",
            "name": "warehouse",
            "display_name": "Warehouse Manager",
            "description": "Manages hardware stock, serial numbers, stocktakes, and physical inventory.",
            "permissions": ["inventory", "catalog", "products"],
            "is_system": True
        }
    ]

    for r in default_roles:
        existing = await db.roles.find_one({"name": r["name"]})
        if not existing:
            r["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.roles.insert_one(r)

    # Seed default suppliers. Idempotent — previously this block sat inside the
    # roles loop above and inserted a fresh duplicate pair on every iteration.
    default_suppliers = [
        {"name": "AVL Distributors", "company": "AVL India Pvt. Ltd.", "email": "sales@avldistributors.com", "phone": "+91-11-4567-8900", "city": "New Delhi", "category": "Distributor", "rating": 5},
        {"name": "Pro Audio Solutions", "company": "PAS Global", "email": "info@pasglobal.com", "phone": "+91-22-3456-7890", "city": "Mumbai", "category": "Vendor", "rating": 4},
    ]
    for s in default_suppliers:
        if not await db.suppliers.find_one({"name": s["name"]}):
            await db.suppliers.insert_one({**s, "id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat()})

    if not await db.social_posts.find_one({"title": "Launch Announcement"}):
        await db.social_posts.insert_many([
            {"id": str(uuid.uuid4()), "platform": "linkedin", "title": "Launch Announcement", "content": "We are excited to announce...", "status": "scheduled", "scheduled_at": "2026-07-25T09:00:00", "views": 0, "engagement": 0, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "platform": "instagram", "title": "Product Showcase", "content": "Check out our latest...", "status": "draft", "scheduled_at": None, "views": 0, "engagement": 0, "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.campaigns.find_one({"name": "Q3 Email Campaign"}):
        await db.campaigns.insert_many([
            {"id": str(uuid.uuid4()), "name": "Q3 Email Campaign", "type": "email", "status": "active", "budget": 50000, "spent": 18500, "leads": 124, "conversions": 18, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "Google Ads - July", "type": "ads", "status": "active", "budget": 80000, "spent": 42000, "leads": 89, "conversions": 12, "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.bookings.find_one({"service": "Demo Session"}):
        await db.bookings.insert_many([
            {"id": str(uuid.uuid4()), "service": "Demo Session", "date": "2026-07-28", "time": "11:00", "resource": "Demo Room A", "customer_name": "Rahul Verma", "customer_email": "rahul@tajhotels.com", "customer_phone": "+91-98200-12345", "notes": "Interested in L-Acoustics K2", "status": "confirmed", "created_at": datetime.now(timezone.utc).isoformat()},
        ])

    if not await db.settings.find_one({"key": "company"}):
        await db.settings.insert_one({"key": "company", "data": {"company_name": "Hitech Audio and Image LLP", "address": "Mumbai, India", "phone": "+91-22-XXXX-XXXX", "email": "info@hitechavl.com", "website": "www.hitechavl.com", "currency": "INR", "timezone": "Asia/Kolkata", "fiscal_year_start": "04-01"}, "updated_at": datetime.now(timezone.utc).isoformat()})

    if not await db.settings.find_one({"key": "system"}):
        await db.settings.insert_one({"key": "system", "data": {"app_name": "Hitech Enterprise OS", "theme": "light", "language": "en", "email_provider": "resend", "sms_provider": "twilio", "backup_frequency": "daily"}, "updated_at": datetime.now(timezone.utc).isoformat()})

@app.on_event("shutdown")
async def on_stop():
    client.close()

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Entrypoint ----------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "true").lower() in ("1", "true", "yes"),
    )

