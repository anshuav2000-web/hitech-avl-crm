import { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Bell, ChevronRight, Command, Menu, X
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { HitechLogo } from "@/components/Brand";
import { api } from "@/lib/api";

const PAGES = [
  { to: "/", label: "Dashboard" },
  { to: "/leads", label: "Leads" },
  { to: "/pipeline", label: "Pipeline" },
  { to: "/quotations", label: "Quotations" },
  { to: "/projects", label: "Projects" },
  { to: "/customers", label: "Customers" },
  { to: "/accounting", label: "Accounting" },
  { to: "/calendar", label: "Calendar" },
];

const inr = (n) =>
  Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

// Each search category needs to know where a hit navigates to, what to call it, and
// which secondary field is worth showing. Keeping this in one table means a new
// category on the API needs one line here, not another branch in the JSX.
const RESULT_META = {
  leads: {
    path: (i) => `/leads/${i.id}`,
    title: (i) => i.name || "Unnamed lead",
    sub: (i) => [i.company, i.stage].filter(Boolean).join(" \u00b7 "),
    amount: () => "",
  },
  customers: {
    path: (i) => "/customers",
    title: (i) => i.name || i.company || "Customer",
    sub: (i) => i.email || "",
    amount: () => "",
  },
  contacts: {
    path: () => "/contacts",
    title: (i) => i.name || "Contact",
    sub: (i) => [i.company, i.role].filter(Boolean).join(" \u00b7 "),
    amount: () => "",
  },
  quotations: {
    path: () => "/quotations",
    title: (i) => i.quote_no || "Quotation",
    sub: (i) => i.status || "",
    amount: (i) => `\u20b9${inr(i.total)}`,
  },
  purchase_orders: {
    path: () => "/purchase-orders",
    title: (i) => i.po_no || "PO",
    sub: (i) => [i.direction, i.status].filter(Boolean).join(" \u00b7 "),
    amount: (i) => `\u20b9${inr(i.total)}`,
  },
  projects: {
    path: (i) => `/projects/${i.id}`,
    title: (i) => i.name || "Project",
    sub: (i) => [i.project_no, i.status].filter(Boolean).join(" \u00b7 "),
    amount: (i) => (i.budget ? `\u20b9${inr(i.budget)}` : ""),
  },
  products: {
    path: () => "/catalog",
    title: (i) => i.name || "Product",
    sub: (i) => [i.brand, i.sku].filter(Boolean).join(" \u00b7 "),
    amount: () => "",
  },
  tasks: {
    path: () => "/tasks",
    title: (i) => i.title || "Task",
    sub: (i) => [i.status, i.due_date].filter(Boolean).join(" \u00b7 "),
    amount: () => "",
  },
  invoices: {
    path: () => "/accounting",
    title: (i) => i.invoice_no || "Invoice",
    sub: (i) => i.status || "",
    amount: (i) => `\u20b9${inr(i.total)}`,
  },
  events: {
    path: () => "/calendar",
    title: (i) => i.title || "Meeting",
    sub: (i) => i.start_time || "",
    amount: () => "",
  },
};

const metaFor = (key) => RESULT_META[key] || { path: () => "/", title: (i) => i.name || "Record", sub: () => "", amount: () => "" };
const resultPath = (key, item) => metaFor(key).path(item);
const resultTitle = (key, item) => metaFor(key).title(item);
const resultSub = (key, item) => metaFor(key).sub(item);
const resultAmount = (key, item) => metaFor(key).amount(item);

export default function AppHeader({ onToggleSidebar, sidebarOpen }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  // B10: the overlay used to filter a hard-coded page list and never called
  // /api/search, so "global search" could not find a single record.
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  // B11: the bell was a hard-coded red dot that never reflected reality.
  const [unread, setUnread] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!user?.id) return;
    let alive = true;
    const load = () =>
      api.get("/notifications/unread-count")
        .then(({ data }) => alive && setUnread(data?.unread_count ?? 0))
        .catch(() => {});
    load();
    const timer = setInterval(load, 60000);
    return () => { alive = false; clearInterval(timer); };
  }, [user?.id]);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) { setResults(null); return; }
    let alive = true;
    setSearching(true);
    const timer = setTimeout(() => {
      api.get("/search", { params: { q: term } })
        .then(({ data }) => alive && setResults(data))
        .catch(() => alive && setResults({ categories: [], total: 0 }))
        .finally(() => alive && setSearching(false));
    }, 250);
    return () => { alive = false; clearTimeout(timer); };
  }, [query]);

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((s) => !s);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (searchOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [searchOpen]);

  const breadcrumbs = pathname
    .split("/")
    .filter(Boolean)
    .map((seg, i, arr) => {
      const path = "/" + arr.slice(0, i + 1).join("/");
      const label = seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, " ");
      return { path, label };
    });

  const goTo = (to) => {
    setSearchOpen(false);
    setQuery("");
    navigate(to);
  };

  return (
    <>
      <header className="h-16 border-b border-slate-200 bg-white/90 backdrop-blur-xl flex items-center justify-between px-4 lg:px-6 sticky top-0 z-20 shadow-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <nav className="hidden md:flex items-center gap-1.5 text-xs">
            <Link to="/" className="flex items-center gap-2 mr-3">
              <HitechLogo className="h-6" />
            </Link>
            {breadcrumbs.map((b, i) => (
              <div key={b.path} className="flex items-center gap-1.5">
                {i > 0 && <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                {i === breadcrumbs.length - 1 ? (
                  <span className="font-bold text-slate-900">{b.label}</span>
                ) : (
                  <button
                    onClick={() => goTo(b.path)}
                    className="text-slate-600 hover:text-sky-600 font-medium transition-colors"
                  >
                    {b.label}
                  </button>
                )}
              </div>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          {/* Global Search Trigger */}
          <button
            onClick={() => setSearchOpen(true)}
            className="hidden sm:flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 hover:border-sky-300 hover:bg-sky-50/50 transition-all"
          >
            <Search className="w-3.5 h-3.5 text-slate-500" />
            <span className="font-medium">Search CRM</span>
            <kbd className="ml-3 px-1.5 py-0.5 rounded bg-white border border-slate-200 text-[10px] text-slate-500 font-mono shadow-sm">
              {navigator.platform.includes("Mac") ? "⌘" : "Ctrl"}K
            </kbd>
          </button>

          {/* Notifications */}
          <button
            onClick={() => goTo("/")}
            className="relative p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            aria-label={unread ? `${unread} unread notifications` : "No unread notifications"}
            data-testid="notification-bell"
          >
            <Bell className="w-4 h-4" />
            {unread > 0 ? (
              <span
                className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 bg-rose-500 text-white rounded-full text-[10px] font-bold flex items-center justify-center"
                data-testid="notification-badge"
              >
                {unread > 99 ? "99+" : unread}
              </span>
            ) : null}
          </button>

          {/* User Profile */}
          <div className="hidden lg:flex items-center gap-2.5 pl-3 border-l border-slate-200 ml-1">
            <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-display font-black text-xs shadow-sm">
              {user?.name?.[0]?.toUpperCase() || "A"}
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-bold text-slate-900 leading-tight">{user?.name}</span>
              <span className="text-[10px] uppercase font-semibold text-sky-600 leading-tight">{user?.role}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Global Search Overlay */}
      <AnimatePresence>
        {searchOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-start justify-center pt-[15vh]"
            onClick={() => setSearchOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.97, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: 8 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-xl bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden"
            >
              <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-slate-50">
                <Search className="w-4 h-4 text-sky-600 shrink-0" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") setSearchOpen(false);
                  }}
                  placeholder="Type a command or module name..."
                  className="flex-1 bg-transparent text-sm text-slate-900 placeholder:text-slate-400 outline-none font-medium"
                />
                <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-[10px] text-slate-500 font-mono">
                  ESC
                </kbd>
              </div>
              <div className="max-h-96 overflow-y-auto p-2" data-testid="search-results">
                {query.trim().length < 2 ? (
                  <div className="px-2 py-3">
                    <div className="text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-2 px-2">
                      Type 2+ characters to search records
                    </div>
                    <div className="space-y-1">
                      {PAGES.map((p) => (
                        <button
                          key={p.to}
                          onClick={() => goTo(p.to)}
                          className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                        >
                          <Command className="w-3.5 h-3.5 text-sky-600" />
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : searching ? (
                  <p className="px-3 py-6 text-center text-sm text-slate-400">Searching...</p>
                ) : results && results.total > 0 ? (
                  <div className="space-y-3">
                    <div className="px-2 text-[10px] uppercase tracking-widest text-slate-400 font-bold">
                      {results.total} result{results.total === 1 ? "" : "s"}
                    </div>
                    {results.categories.map((cat) => (
                      <div key={cat.key}>
                        <div className="px-2 text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-1">
                          {cat.label}
                        </div>
                        {cat.items.map((item) => (
                          <button
                            key={`${cat.key}-${item.id}`}
                            onClick={() => goTo(resultPath(cat.key, item))}
                            className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-sm text-slate-700 hover:bg-slate-100 transition-colors text-left"
                          >
                            <span className="font-semibold truncate">
                              {resultTitle(cat.key, item)}
                              {resultSub(cat.key, item) ? (
                                <span className="ml-2 font-normal text-xs text-slate-500 truncate">
                                  {resultSub(cat.key, item)}
                                </span>
                              ) : null}
                            </span>
                            <span className="ml-auto text-xs font-bold text-slate-500 shrink-0">
                              {resultAmount(cat.key, item)}
                            </span>
                          </button>
                        ))}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="px-3 py-6 text-center text-sm text-slate-400">
                    No matches for &ldquo;{query}&rdquo;
                  </p>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
