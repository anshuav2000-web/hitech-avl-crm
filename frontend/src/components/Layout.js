import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, KanbanSquare, Receipt, UserCog,
  LogOut, Package, Boxes, Plug, Ship, Warehouse, ShieldCheck, UploadCloud, Webhook, Mail,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { HitechLogo } from "@/components/Brand";

const sections = [
  {
    title: "Workspace",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
      { to: "/leads", label: "Leads", icon: Users, testid: "nav-leads" },
      { to: "/pipeline", label: "Pipeline", icon: KanbanSquare, testid: "nav-pipeline" },
      { to: "/quotations", label: "Quotations", icon: Receipt, testid: "nav-quotations" },
    ],
  },
  {
    title: "Catalog",
    items: [
      { to: "/catalog", label: "Products", icon: Package, testid: "nav-catalog" },
      { to: "/packages", label: "Packages", icon: Boxes, testid: "nav-packages" },
    ],
  },
  {
    title: "Operations",
    items: [
      { to: "/shipments", label: "Shipments", icon: Ship, testid: "nav-shipments" },
      { to: "/inventory", label: "Inventory", icon: Warehouse, testid: "nav-inventory" },
      { to: "/amcs", label: "AMC", icon: ShieldCheck, testid: "nav-amcs" },
    ],
  },
];

const adminItems = [
  { to: "/team", label: "Team", icon: UserCog, testid: "nav-team" },
  { to: "/integrations", label: "Integrations", icon: Plug, testid: "nav-integrations" },
  { to: "/webhooks", label: "Webhooks", icon: Webhook, testid: "nav-webhooks" },
  { to: "/resend", label: "Email", icon: Mail, testid: "nav-resend" },
  { to: "/import", label: "Import Data", icon: UploadCloud, testid: "nav-import" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-[#F8FAFC]">
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col" data-testid="sidebar">
        <div className="px-5 py-6 border-b border-slate-200">
          <Link to="/" className="block">
            <HitechLogo className="h-9" />
          </Link>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-3 overflow-y-auto no-scrollbar">
          {sections.map((sec) => (
            <div key={sec.title}>
              <div className="label-eyebrow px-3 mb-1.5">{sec.title}</div>
              <div className="space-y-0.5">
                {sec.items.map(({ to, label, icon: Icon, testid }) => (
                  <NavLink
                    key={to} to={to} end={to === "/"} data-testid={testid}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
                        isActive ? "bg-slate-900 text-white shadow-sm" : "text-slate-700 hover:bg-slate-100 hover:translate-x-0.5"
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
          {user?.role === "admin" && (
            <div>
              <div className="label-eyebrow px-3 mb-1.5">Admin</div>
              <div className="space-y-0.5">
                {adminItems.map(({ to, label, icon: Icon, testid }) => (
                  <NavLink
                    key={to} to={to} data-testid={testid}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
                        isActive ? "bg-slate-900 text-white shadow-sm" : "text-slate-700 hover:bg-slate-100 hover:translate-x-0.5"
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          )}
        </nav>

        <div className="border-t border-slate-200 p-3">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-9 h-9 rounded-md text-white flex items-center justify-center font-display font-bold text-sm" style={{ background: "#DC2626" }}>
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-slate-900 truncate" data-testid="current-user-name">{user?.name}</div>
              <div className="text-[11px] text-slate-500 uppercase tracking-wider">{user?.role}</div>
            </div>
            <button onClick={handleLogout} data-testid="logout-btn" className="p-2 hover:bg-slate-100 rounded-md text-slate-600 hover:text-slate-900 transition-colors" title="Logout">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  );
}
