import {
  LayoutDashboard, Users, KanbanSquare, Receipt, FolderKanban, UserCircle,
  LogOut, Package, Boxes, Truck, Warehouse, ShieldCheck, CalendarDays,
  ClipboardList, Store, Wallet, Clock, Wrench, Tag, Settings2,
  Search, Star, Pin, ChevronLeft, ChevronRight, Bell, Sparkles,
  Ship, Mail, MessageSquare, Target, CheckSquare, UserPlus, Building2,
  Handshake, Activity, Phone, FileText, FolderOpen, GitBranch, Flag,
  BarChart3, CalendarClock, CalendarX, UserCheck,
  Factory, Settings as SettingsIcon, IdCard, CheckCircle2,
  ShoppingCart, FileSignature, CreditCard, Percent, FileMinus, FilePlus,
  Landmark, Layers, MapPin, Hash, PackageCheck, List, RefreshCw,
  HandCoins, ClipboardCheck, Repeat, AlertTriangle, TrendingUp,
  CalendarCheck, Briefcase, Globe, Image, BarChart2, Inbox, Type,
  Share2, UserCircle2, Info, Palette, Database as DbIcon,
  Code2, ScrollText, HardDrive, KeyRound, Cog, Timer, Webhook,
  UploadCloud, GitMerge, Award, SearchIcon, FileSearch,
  PanelLeftClose, PanelLeftOpen, MoreHorizontal,
  User as UserIcon, BookOpen, RotateCcw, Plus as PlusIcon, Calendar as CalendarIcon, MessageSquare as MsgSquareIcon,
} from "lucide-react";
import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { HitechLogo } from "@/components/Brand";
import NAVIGATION_CONFIG, { getItemById, getSectionById, isItemActive } from "./navigationConfig";

const ICON_MAP = {
  LayoutDashboard, Users, KanbanSquare, Receipt, FolderKanban, UserCircle,
  LogOut, Package, Boxes, Truck, Warehouse, ShieldCheck, CalendarDays,
  ClipboardList, Store, Wallet, Clock, Wrench, Tag, Settings2,
  Search, Star, Pin, ChevronLeft, ChevronRight, Bell, Sparkles,
  Ship, Mail, MessageSquare, Target, CheckSquare, UserPlus, Building2,
  Handshake, Activity, Phone, FileText, FolderOpen, GitBranch, Flag,
  BarChart3, CalendarClock, CalendarX, UserCheck,
  Factory, SettingsIcon, IdCard, CheckCircle2,
  ShoppingCart, FileSignature, CreditCard, Percent, FileMinus, FilePlus,
  Landmark, Layers, MapPin, Hash, PackageCheck, List, RefreshCw,
  HandCoins, ClipboardCheck, Repeat, AlertTriangle, TrendingUp,
  CalendarCheck, Briefcase, Globe, Image, BarChart2, Inbox, Type,
  Share2, UserCircle2, Info, Palette, DbIcon,
  Code2, ScrollText, HardDrive, KeyRound, Cog, Timer, Webhook,
  UploadCloud, GitMerge, Award, SearchIcon, FileSearch,
  PanelLeftClose, PanelLeftOpen, MoreHorizontal,
  UserIcon, BookOpen, RotateCcw, PlusIcon, CalendarIcon, MsgSquareIcon,
};

const RECENT_KEY = "hai_recent_pages_v2";
const FAVORITES_KEY = "hai_favorites_v2";
const EXPANDED_KEY = "hai_expanded_sections_v2";
const SIDEBAR_MODE_KEY = "hai_sidebar_mode_v2";

// Kept in sync with server.py ADMIN_ROLE_NAMES and the App.js route guard.
const ADMIN_ROLES = ["admin", "superadmin", "management"];

function getRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch { return []; }
}
function pushRecent(path, label) {
  try {
    const list = getRecent().filter((r) => r.path !== path);
    list.unshift({ path, label, at: Date.now() });
    localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, 15)));
  } catch {}
}
function getFavorites() {
  try { return JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]"); } catch { return []; }
}
function toggleFavorite(id, label) {
  try {
    const favs = getFavorites();
    const idx = favs.findIndex((f) => f.id === id);
    if (idx >= 0) favs.splice(idx, 1);
    else favs.push({ id, label, at: Date.now() });
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
    return favs;
  } catch { return []; }
}
function getExpanded() {
  try { return JSON.parse(localStorage.getItem(EXPANDED_KEY) || "{}"); } catch { return {}; }
}
function setExpanded(expanded) {
  try { localStorage.setItem(EXPANDED_KEY, JSON.stringify(expanded)); } catch {}
}

function getInitialMode() {
  try { return localStorage.getItem(SIDEBAR_MODE_KEY) || "full"; } catch { return "full"; }
}

function LucideIcon({ name, className }) {
  const Icon = ICON_MAP[name] || ICON_MAP["LayoutDashboard"];
  return <Icon className={className || "w-4 h-4"} />;
}

export default function AppSidebar({ onMobileClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState(getInitialMode);
  const [search, setSearch] = useState("");
  const [recent, setRecent] = useState(getRecent());
  const [favorites, setFavorites] = useState(getFavorites());
  const [expandedSections, setExpandedSections] = useState(() => {
    const saved = getExpanded();
    return saved;
  });
  const searchInputRef = useRef(null);

  const isMini = mode === "mini";
  const isFull = mode === "full";

  useEffect(() => {
    const handler = () => {
      setRecent(getRecent());
      setFavorites(getFavorites());
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  useEffect(() => {
    localStorage.setItem(SIDEBAR_MODE_KEY, mode);
  }, [mode]);

  const handleToggleSection = useCallback((sectionId) => {
    setExpandedSections((prev) => {
      const next = { ...prev, [sectionId]: !prev[sectionId] };
      setExpanded(next);
      return next;
    });
  }, []);

  const handleNavigate = useCallback((item) => {
    if (item.to) {
      pushRecent(item.to, item.label);
      setRecent(getRecent());
    }
    setSearch("");
    onMobileClose?.();
  }, [onMobileClose]);

  const handleToggleFavorite = useCallback((e, id, label) => {
    e.preventDefault();
    e.stopPropagation();
    const favs = toggleFavorite(id, label);
    setFavorites(favs);
  }, []);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login");
  }, [logout, navigate]);

  const cycleMode = useCallback(() => {
    setMode((m) => (m === "full" ? "mini" : m === "mini" ? "collapsed" : "full"));
  }, []);

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return null;
    const results = [];
    NAVIGATION_CONFIG.forEach((section) => {
      if (!section.children) {
        if (section.label.toLowerCase().includes(q) || section.id.toLowerCase().includes(q)) {
          results.push({ item: section, section, level: 0 });
        }
      } else {
        section.children.forEach((child) => {
          if (child.label.toLowerCase().includes(q) || child.id.toLowerCase().includes(q)) {
            results.push({ item: child, section, level: 1 });
          }
        });
      }
    });
    return results;
  }, [search]);

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "b") {
        e.preventDefault();
        cycleMode();
      }
      if (e.key === "Escape" && search) {
        setSearch("");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [cycleMode, search]);

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white text-slate-900">
      {/* Logo Header */}
      <div className="flex items-center gap-3 h-16 px-4 border-b border-slate-200 shrink-0 bg-slate-50/50">
        <Link to="/" onClick={() => handleNavigate({ id: "dashboard", label: "Dashboard", to: "/" })} className="shrink-0">
          <HitechLogo className="h-8" />
        </Link>
        {isFull && (
          <button
            onClick={cycleMode}
            className="ml-auto p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-200/60 transition-colors"
            title="Collapse sidebar (Ctrl+B)"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        )}
        {isMini && (
          <button
            onClick={cycleMode}
            className="absolute -right-3 top-5 z-50 p-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 hover:text-slate-900 hover:bg-slate-100 shadow-md transition-colors"
            title="Expand sidebar (Ctrl+B)"
          >
            <PanelLeftOpen className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Search Input */}
      <AnimatePresence>
        {isFull && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="px-3 py-2 border-b border-slate-200 bg-slate-50/30"
          >
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                ref={searchInputRef}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search menu..."
                className="w-full bg-slate-100 border border-slate-200 rounded-xl pl-8 pr-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 outline-none focus:border-sky-500 focus:bg-white transition-all font-medium"
              />
              {search && (
                <button
                  onClick={() => { setSearch(""); searchInputRef.current?.focus(); }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 hover:text-slate-800 px-1 font-bold"
                >
                  ESC
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto no-scrollbar py-2 space-y-1 px-2">
        {search ? (
          <SearchResults
            results={filteredItems || []}
            onNavigate={handleNavigate}
            search={search}
            isMini={isMini}
            favorites={favorites}
            onToggleFavorite={handleToggleFavorite}
          />
        ) : (
          <>
            {/* Favorites */}
            {isFull && favorites.length > 0 && (
              <FavoritesSection
                favorites={favorites}
                onNavigate={handleNavigate}
                onToggleFavorite={handleToggleFavorite}
                currentPath={location.pathname}
              />
            )}

            {/* Main sections */}
            {NAVIGATION_CONFIG.map((section) => {
              if (!user) return null;
              const userRole = (user.role || "").toLowerCase();
              // Must match the backend's is_admin_role() (admin/superadmin/management).
              // This list omitted "management", so a management user failed
              // `section.roles.includes(userRole)` on every section and the whole
              // sidebar rendered empty -- despite the API granting them full access.
              const isSuperOrAdmin = ADMIN_ROLES.includes(userRole);

              const canAccessChild = (c) => isSuperOrAdmin || !c.roles || c.roles.includes(userRole);
              // A section is reachable if the role can open the section itself OR if it
              // can see any single child. The old check only looked at section.roles, so
              // `design-team` (roles admin/sales/design_engineer) was unreachable: its
              // parent `crm` section lists only admin/sales, hiding the whole group from
              // a design_engineer even though the child was granted to them.
              const canAccessSection =
                isSuperOrAdmin ||
                !section.roles ||
                section.roles.includes(userRole) ||
                (section.children || []).some(canAccessChild);
              if (!canAccessSection) return null;

              const hasChildren = section.children && section.children.length > 0;
              const isExpanded = expandedSections[section.id];
              const visibleChildren = hasChildren ? section.children.filter(canAccessChild) : [];

              if (hasChildren && visibleChildren.length === 0) return null;

              return (
                <Section
                  key={section.id}
                  section={section}
                  visibleChildren={visibleChildren}
                  isExpanded={isExpanded}
                  onToggle={() => handleToggleSection(section.id)}
                  isMini={isMini}
                  isFull={isFull}
                  currentPath={location.pathname}
                  onNavigate={handleNavigate}
                  favorites={favorites}
                  onToggleFavorite={handleToggleFavorite}
                />
              );
            })}

            {/* Recent */}
            {isFull && recent.length > 0 && (
              <RecentSection
                recent={recent}
                onNavigate={handleNavigate}
                currentPath={location.pathname}
              />
            )}
          </>
        )}
      </nav>

      {/* Bottom User Area */}
      <div className="border-t border-slate-200 p-2 shrink-0 space-y-1 bg-slate-50/50">
        {mode === "collapsed" && (
          <button
            onClick={cycleMode}
            className="w-full flex items-center justify-center py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 transition-colors"
            title="Expand sidebar (Ctrl+B)"
          >
            <PanelLeftOpen className="w-4 h-4" />
          </button>
        )}

        <div className={`flex items-center gap-2.5 px-2 py-1.5 ${mode === 'collapsed' ? 'justify-center' : ''}`}>
          <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center font-display font-black text-xs shrink-0 shadow-xs">
            {user?.name?.[0]?.toUpperCase() || "A"}
          </div>
          {isFull && (
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-slate-900 truncate">{user?.name}</div>
              <div className="text-[10px] uppercase font-semibold tracking-wider text-sky-600">{user?.role}</div>
            </div>
          )}
          {isFull && (
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors shrink-0"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <motion.aside
      animate={{ width: isMini ? 72 : isFull ? 260 : 72 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="hidden lg:flex flex-col h-screen border-r border-slate-200 bg-white relative z-30 select-none shadow-xs"
    >
      {sidebarContent}
    </motion.aside>
  );
}

function Section({ section, visibleChildren: prefiltered, isExpanded, onToggle, isMini, isFull, currentPath, onNavigate, favorites, onToggleFavorite }) {
  const hasChildren = section.children && section.children.length > 0;
  // Bug B3: this used to recompute the filter with a hard-coded `roles.includes("admin")`.
  // The caller already computed the correct list for the signed-in role and threw it
  // away, so every accordion body collapsed to admin-only children -- a sales user
  // saw section headers whose contents never rendered, and `design_engineer` could
  // never see the one section that listed it. The caller's list is now used directly.
  const visibleChildren = prefiltered ?? [];

  const activeChildCount = visibleChildren.filter((c) => c.to && isItemActive(c.to, currentPath)).length;

  if (!hasChildren) {
    return (
      <LeafItem
        item={section}
        isMini={isMini}
        isActive={isItemActive(section.to, currentPath)}
        onClick={() => onNavigate(section)}
        isFavorite={favorites.some((f) => f.id === section.id)}
        onToggleFavorite={(e) => onToggleFavorite(e, section.id, section.label)}
      />
    );
  }

  return (
    <div className="space-y-0.5">
      {/* Section Header */}
      <button
        onClick={onToggle}
        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-all duration-200 group ${isMini ? "justify-center" : ""}`}
        title={isMini ? section.label : undefined}
      >
        <span className="shrink-0 text-sky-600 group-hover:text-sky-700 transition-colors">
          <LucideIcon name={section.icon} className="w-4 h-4" />
        </span>
        {isFull && (
          <>
            <span className="text-xs font-bold tracking-tight flex-1 text-left text-slate-800 group-hover:text-slate-900">{section.label}</span>
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </motion.div>
          </>
        )}
        {isMini && activeChildCount > 0 && (
          <span className="absolute right-1 top-1 w-1.5 h-1.5 rounded-full bg-sky-600" />
        )}
      </button>

      {/* Accordion Sub-items */}
      <AnimatePresence initial={false}>
        {isExpanded && isFull && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden pl-3 pr-1 py-1 space-y-0.5 bg-slate-50/80 rounded-xl my-1 border-l-2 border-sky-400/40"
          >
            {visibleChildren.map((child) => (
              <LeafItem
                key={child.id}
                item={child}
                isMini={isMini}
                isActive={isItemActive(child.to, currentPath)}
                onClick={() => onNavigate(child)}
                isFavorite={favorites.some((f) => f.id === child.id)}
                onToggleFavorite={(e) => onToggleFavorite(e, child.id, child.label)}
                parentLabel={section.label}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function LeafItem({ item, isMini, isActive, onClick, isFavorite, onToggleFavorite, parentLabel }) {
  const isFull = !isMini;
  const Icon = ICON_MAP[item.icon] || ICON_MAP["LayoutDashboard"];

  return (
    <div className="relative group/item">
      {item.to ? (
        <NavLink
          to={item.to}
          end={item.to === "/"}
          onClick={onClick}
          className={({ isActive: navActive }) => {
            const active = navActive || isActive;
            return [
              "flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-200 relative",
              active
                ? "bg-sky-50 text-sky-700 border-l-[3px] border-sky-600 shadow-xs font-bold"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100",
              isMini ? "justify-center" : "",
            ].join(" ");
          }}
          title={isMini ? item.label : undefined}
        >
          {({ isActive: navActive }) => {
            const active = navActive || isActive;
            return (
              <>
                <span className="shrink-0 relative">
                  <Icon className={`w-4 h-4 ${active ? "text-sky-600" : "text-slate-400 group-hover/item:text-slate-700"}`} />
                  {item.badge && !isMini && (
                    <span className="absolute -top-1 -right-1 px-1 py-0.5 rounded text-[8px] font-black uppercase tracking-wider bg-sky-600 text-white">
                      {item.badge}
                    </span>
                  )}
                </span>
                {isFull && (
                  <span className="truncate flex-1 text-left">{item.label}</span>
                )}
              </>
            );
          }}
        </NavLink>
      ) : (
        <button
          onClick={onClick}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${isMini ? "justify-center" : ""} text-slate-600 hover:text-slate-900 hover:bg-slate-100`}
          title={isMini ? item.label : undefined}
        >
          <span className="shrink-0 relative">
            <Icon className="w-4 h-4 text-slate-400 group-hover/item:text-slate-700" />
          </span>
          {isFull && <span className="truncate">{item.label}</span>}
        </button>
      )}

      {/* Favorite button */}
      {isFull && (
        <button
          onClick={onToggleFavorite}
          className={`absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover/item:opacity-100 transition-all ${isFavorite ? "text-amber-500 opacity-100" : "text-slate-400 hover:text-amber-500"}`}
          title={isFavorite ? "Remove from favorites" : "Add to favorites"}
        >
          <Star className={`w-3.5 h-3.5 ${isFavorite ? "fill-amber-500" : ""}`} />
        </button>
      )}

      {/* Mini Mode Tooltip */}
      {isMini && (
        <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-3 py-1.5 bg-slate-900 text-white border border-slate-800 rounded-xl text-xs whitespace-nowrap opacity-0 group-hover/item:opacity-100 transition-opacity duration-200 pointer-events-none z-50 shadow-xl">
          <div className="font-bold">{item.label}</div>
          {parentLabel && <div className="text-[10px] text-slate-400 font-medium">{parentLabel}</div>}
        </div>
      )}
    </div>
  );
}

function FavoritesSection({ favorites, onNavigate, onToggleFavorite, currentPath }) {
  return (
    <div className="space-y-0.5 mb-2">
      <div className="label-eyebrow px-3 mb-1 text-slate-400 flex items-center gap-1.5 text-[10px]">
        <Star className="w-3 h-3 fill-amber-500 text-amber-500" />
        Favorites
      </div>
      {favorites.map((fav) => (
        <LeafItem
          key={fav.id}
          item={{
            id: fav.id,
            label: fav.label,
            to: fav.path || null,
            icon: "LayoutDashboard",
            badge: null,
            isNew: false,
            isBeta: false,
            roles: ["admin", "sales"],
          }}
          isMini={false}
          isActive={currentPath === fav.path}
          onClick={() => onNavigate({ id: fav.id, label: fav.label, to: fav.path })}
          isFavorite={true}
          onToggleFavorite={(e) => onToggleFavorite(e, fav.id, fav.label)}
        />
      ))}
    </div>
  );
}

function RecentSection({ recent, onNavigate, currentPath }) {
  return (
    <div className="space-y-0.5 pt-2 border-t border-slate-200">
      <div className="label-eyebrow px-3 mb-1 text-slate-400 flex items-center gap-1.5 text-[10px]">
        <Clock className="w-3 h-3" />
        Recent Pages
      </div>
      {recent.slice(0, 5).map((r) => (
        <LeafItem
          key={r.path}
          item={{
            id: `recent-${r.path}`,
            label: r.label,
            to: r.path,
            icon: "Pin",
            badge: null,
            isNew: false,
            isBeta: false,
            roles: ["admin", "sales"],
          }}
          isMini={false}
          isActive={currentPath === r.path}
          onClick={() => onNavigate({ id: `recent-${r.path}`, label: r.label, to: r.path })}
          isFavorite={false}
          onToggleFavorite={() => {}}
        />
      ))}
    </div>
  );
}

function SearchResults({ results, onNavigate, search, isMini, favorites, onToggleFavorite }) {
  if (results.length === 0) {
    return (
      <div className="px-3 py-6 text-center text-xs text-slate-500">
        No results for "{search}"
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {results.map(({ item, section }) => (
        <LeafItem
          key={item.id}
          item={item}
          isMini={isMini}
          isActive={isItemActive(item.to, window.location.pathname)}
          onClick={() => onNavigate(item)}
          isFavorite={favorites.some((f) => f.id === item.id)}
          onToggleFavorite={(e) => onToggleFavorite(e, item.id, item.label)}
          parentLabel={section.label}
        />
      ))}
    </div>
  );
}
