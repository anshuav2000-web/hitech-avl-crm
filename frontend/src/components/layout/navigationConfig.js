const NAVIGATION_CONFIG = [
  {
    id: "dashboard",
    label: "Dashboard",
    to: "/",
    icon: "LayoutDashboard",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: null,
  },
  {
    id: "crm",
    label: "CRM & Sales",
    icon: "Users",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "leads", label: "Leads", to: "/leads", icon: "Users", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "pipeline", label: "Pipeline", to: "/pipeline", icon: "KanbanSquare", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "qualification", label: "BANT Qualification", to: "/qualification", icon: "ShieldCheck", badge: "Auto", isNew: true, isBeta: false, roles: ["admin", "sales"] },
      { id: "follow-ups", label: "Follow-Up Scheduler", to: "/follow-ups", icon: "Calendar", badge: "Live", isNew: true, isBeta: false, roles: ["admin", "sales"] },
      { id: "quotations", label: "Quotations", to: "/quotations", icon: "Receipt", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "customers", label: "Customers", to: "/customers", icon: "UserCircle", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "contacts", label: "Contacts", to: "/contacts", icon: "UserIcon", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "tasks", label: "Tasks & To Dos", to: "/tasks", icon: "ClipboardList", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-opportunities", label: "Opportunities", to: "/module/opportunities", icon: "Target", badge: "New", isNew: true, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-companies", label: "Companies", to: "/module/companies", icon: "Building2", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-activities", label: "Activities & Calls", to: "/module/activities", icon: "Activity", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "proposals-projects",
    label: "Proposals & Projects",
    icon: "FolderKanban",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "projects", label: "Projects", to: "/projects", icon: "FolderKanban", badge: "Beta", isNew: false, isBeta: true, roles: ["admin", "sales"] },
      { id: "design-team", label: "Design Team CAD", to: "/design-team", icon: "Wrench", badge: "Stage", isNew: true, isBeta: false, roles: ["admin", "sales", "design_engineer"] },
      { id: "boq-generator", label: "BOQ Generator", to: "/boq-generator", icon: "Receipt", badge: "v2", isNew: true, isBeta: false, roles: ["admin", "sales"] },
      { id: "purchase-orders", label: "Purchase Orders (PO)", to: "/purchase-orders", icon: "Wallet", badge: "Approval", isNew: true, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-contracts", label: "Contracts", to: "/module/contracts", icon: "FileSignature", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-milestones", label: "Milestones", to: "/module/milestones", icon: "Flag", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-gantt", label: "Gantt Chart", to: "/module/gantt", icon: "BarChart3", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "products",
    label: "Products & Catalog",
    icon: "Package",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "products-list", label: "Products Catalog", to: "/catalog", icon: "Package", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "product-groups", label: "Packages & Bundles", to: "/packages", icon: "Boxes", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-categories", label: "Categories & Variants", to: "/module/categories", icon: "Layers", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "suppliers",
    label: "Suppliers & Brands",
    icon: "Store",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "suppliers-list", label: "Suppliers Directory", to: "/suppliers", icon: "Store", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "purchase-history", label: "Shipments & Imports", to: "/shipments", icon: "Ship", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-vendor-perf", label: "Vendor Performance", to: "/module/vendor-performance", icon: "TrendingUp", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "accounting",
    label: "Accounting & Finance",
    icon: "Wallet",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "invoices", label: "Invoices & Ledger", to: "/accounting", icon: "FileText", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-expenses", label: "Expenses & Payments", to: "/module/expenses", icon: "CreditCard", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-tax-reports", label: "Taxes & P&L Reports", to: "/module/tax-reports", icon: "BarChart3", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "time-management",
    label: "Time Management",
    icon: "Clock",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "my-calendar", label: "Calendar & Schedule", to: "/calendar", icon: "CalendarDays", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-timesheets", label: "Timesheets & Leave", to: "/module/timesheets", icon: "ClipboardList", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "work-orders",
    label: "Work Orders & Production",
    icon: "Wrench",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "wo-list", label: "Work Orders", to: "/work-orders", icon: "Wrench", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "amcs", label: "AMC & Maintenance", to: "/amcs", icon: "ShieldCheck", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-manufacturing", label: "Job Cards & Quality", to: "/module/manufacturing", icon: "Factory", badge: null, isNew: false, isBeta: false, roles: ["admin"] },
    ],
  },
  {
    id: "inventory",
    label: "Warehouse & Inventory",
    icon: "Warehouse",
    badge: "Beta",
    isNew: false,
    isBeta: true,
    roles: ["admin", "sales"],
    children: [
      { id: "inv-dashboard", label: "Inventory Dashboard", to: "/inventory", icon: "BarChart2", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "shipping", label: "Dispatch & Shipping", to: "/shipments", icon: "Ship", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-stocktakes", label: "Stocktakes & Auditing", to: "/module/stocktakes", icon: "ClipboardCheck", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "bookings",
    label: "Bookings & Services",
    icon: "CalendarCheck",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "booking-dashboard", label: "Appointments & Bookings", to: "/booking", icon: "CalendarCheck", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "digital-marketing",
    label: "Digital Marketing",
    icon: "Megaphone",
    badge: "New",
    isNew: true,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "campaigns", label: "Campaigns & Funnels", to: "/marketing", icon: "Megaphone", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "module-seo", label: "SEO & Analytics", to: "/module/seo", icon: "TrendingUp", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "social-media",
    label: "Social Media Hub",
    icon: "Share2",
    badge: "New",
    isNew: true,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "sm-dashboard", label: "Social Dashboard", to: "/social", icon: "LayoutDashboard", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
    ],
  },
  {
    id: "communications",
    label: "Communications",
    icon: "Mail",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin", "sales"],
    children: [
      { id: "emails", label: "Email Services", to: "/resend", icon: "Mail", badge: null, isNew: false, isBeta: false, roles: ["admin", "sales"] },
      { id: "webhooks", label: "Webhooks & Events", to: "/webhooks", icon: "Webhook", badge: null, isNew: false, isBeta: false, roles: ["admin"] },
    ],
  },
  {
    id: "company-settings",
    label: "Company Settings",
    icon: "Building2",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin"],
    children: [
      { id: "company-info", label: "Company Information", to: "/settings/company", icon: "Building2", badge: null, isNew: false, isBeta: false, roles: ["admin"] },
      { id: "roles", label: "Roles & Permissions", to: "/team", icon: "ShieldCheck", badge: null, isNew: false, isBeta: false, roles: ["admin"] },
    ],
  },
  {
    id: "system-settings",
    label: "System Settings",
    icon: "Settings2",
    badge: null,
    isNew: false,
    isBeta: false,
    roles: ["admin"],
    children: [
      { id: "system-settings-link", label: "General & Integrations", to: "/settings/system", icon: "Settings2", badge: null, isNew: false, isBeta: false, roles: ["admin"] },
      { id: "int-import", label: "Import Data", to: "/import", icon: "UploadCloud", badge: null, isNew: false, isBeta: false, roles: ["admin"] },
    ],
  },
];

export const FLAT_NAV_ITEMS = NAVIGATION_CONFIG.flatMap((section) =>
  section.children
    ? section.children.map((child) => ({
        ...child,
        parentId: section.id,
        parentLabel: section.label,
      }))
    : [
        {
          ...section,
          parentId: null,
          parentLabel: null,
        },
      ]
);

export const SECTION_IDS = new Set(NAVIGATION_CONFIG.map((s) => s.id));

export function getSectionById(id) {
  return NAVIGATION_CONFIG.find((s) => s.id === id) || null;
}

export function getItemById(id) {
  for (const section of NAVIGATION_CONFIG) {
    if (section.children) {
      const found = section.children.find((c) => c.id === id);
      if (found) return found;
    }
  }
  return null;
}

export function isItemActive(to, pathname) {
  if (!to) return false;
  if (to === "/") return pathname === "/";
  return pathname.startsWith(to);
}

export default NAVIGATION_CONFIG;
