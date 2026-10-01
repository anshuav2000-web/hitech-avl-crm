import { Link } from "react-router-dom";
import { FolderKanban, CheckSquare, ShoppingCart, Bell, ArrowUpRight, FileText } from "lucide-react";

const card = "bg-white border border-slate-200 rounded-xl p-5 shadow-xs";
const empty = "text-sm text-slate-500 py-8 text-center";

function Row({ primary, secondary, to }) {
  const inner = (
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 py-2 last:border-0">
      <div className="min-w-0">
        <div className="text-xs font-bold text-slate-900 truncate">{primary}</div>
        {secondary ? <div className="text-[11px] text-slate-500 truncate">{secondary}</div> : null}
      </div>
      {to ? <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 shrink-0" /> : null}
    </div>
  );
  return to ? <Link to={to} className="block hover:bg-slate-50 rounded-lg px-1">{inner}</Link> : inner;
}

const projectName = (p) => p.project_name || p.name || p.customer_name || p.id;

export function ProjectsWidget({ data }) {
  if (!data) return null;
  return (
    <div className={card} data-testid="widget-projects">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600">
            <FolderKanban className="w-4 h-4" />
          </div>
          <div>
            <div className="label-eyebrow">Delivery</div>
            <div className="font-display text-lg font-bold text-slate-900">Projects ({data.count})</div>
          </div>
        </div>
        <Link to="/projects" className="text-xs text-slate-500 hover:text-slate-900 font-semibold">Open</Link>
      </div>
      {data.recent.length === 0 ? (
        <div className={empty}>No projects yet.</div>
      ) : (
        <div>
          {data.recent.map((p) => (
            <Row key={p.id} primary={projectName(p)} secondary={`${p.stage || "unassigned"} · ${p.project_no || "—"}`} to={`/projects/${p.id}`} />
          ))}
        </div>
      )}
    </div>
  );
}

export function TasksWidget({ data }) {
  if (!data) return null;
  return (
    <div className={card} data-testid="widget-tasks">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
            <CheckSquare className="w-4 h-4" />
          </div>
          <div>
            <div className="label-eyebrow">Workload</div>
            <div className="font-display text-lg font-bold text-slate-900">Tasks ({data.open} open)</div>
          </div>
        </div>
        <Link to="/tasks" className="text-xs text-slate-500 hover:text-slate-900 font-semibold">Open</Link>
      </div>
      {data.recent.length === 0 ? (
        <div className={empty}>No tasks yet.</div>
      ) : (
        <div>
          {data.recent.map((t) => (
            <Row key={t.id} primary={t.title || t.name || "Task"} secondary={`${t.status || "open"}${t.priority ? ` · ${t.priority}` : ""}`} />
          ))}
        </div>
      )}
    </div>
  );
}

export function PurchaseOrdersWidget({ data }) {
  if (!data) return null;
  return (
    <div className={card} data-testid="widget-purchase-orders">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
            <ShoppingCart className="w-4 h-4" />
          </div>
          <div>
            <div className="label-eyebrow">Procurement</div>
            <div className="font-display text-lg font-bold text-slate-900">Purchase Orders ({data.count})</div>
          </div>
        </div>
        <Link to="/purchase-orders" className="text-xs text-slate-500 hover:text-slate-900 font-semibold">Open</Link>
      </div>
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="border border-slate-200 rounded-xl p-3 bg-slate-50">
          <div className="label-eyebrow">Supplier</div>
          <div className="font-display text-xl font-black text-slate-900 mt-1">₹{Number(data.supplier_value || 0).toLocaleString("en-IN")}</div>
        </div>
        <div className="border border-slate-200 rounded-xl p-3 bg-slate-50">
          <div className="label-eyebrow">Customer</div>
          <div className="font-display text-xl font-black text-sky-700 mt-1">₹{Number(data.customer_value || 0).toLocaleString("en-IN")}</div>
        </div>
      </div>
      {data.recent.length === 0 ? (
        <div className={empty}>No purchase orders yet.</div>
      ) : (
        <div>
          {data.recent.map((p) => (
            <Row
              key={p.id}
              primary={p.po_no || p.id}
              secondary={`${p.direction === "customer" ? "Customer" : "Supplier"} · ${p.status || "draft"}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function NotificationsWidget({ data }) {
  if (!data) return null;
  return (
    <div className={card} data-testid="widget-notifications">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
            <Bell className="w-4 h-4" />
          </div>
          <div>
            <div className="label-eyebrow">Inbox</div>
            <div className="font-display text-lg font-bold text-slate-900">
              Notifications ({data.unread} unread)
            </div>
          </div>
        </div>
      </div>
      {data.recent.length === 0 ? (
        <div className={empty}>You're all caught up.</div>
      ) : (
        <div>
          {data.recent.map((n) => (
            <Row
              key={n.id}
              primary={n.title || n.type || "Notification"}
              secondary={`${n.message || ""}${n.read ? "" : " · new"}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function SalesSummaryWidget({ stats }) {
  const q = stats.quote_stats || {};
  return (
    <div className={card} data-testid="widget-sales-summary">
      <div className="flex items-center gap-2.5 mb-4">
        <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600">
          <FileText className="w-4 h-4" />
        </div>
        <div>
          <div className="label-eyebrow">Commercials</div>
          <div className="font-display text-lg font-bold text-slate-900">Sales Summary</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Tile label="Quotations" value={q.count ?? 0} />
        <Tile label="Pipeline Value" value={`₹${Number(q.pipeline_value || 0).toLocaleString("en-IN")}`} accent="text-sky-700" />
        <Tile label="Accepted" value={`₹${Number(q.accepted_value || 0).toLocaleString("en-IN")}`} accent="text-emerald-700" />
        <Tile label="Total Quoted" value={`₹${Number(q.total_value || 0).toLocaleString("en-IN")}`} />
      </div>
    </div>
  );
}

function Tile({ label, value, accent = "text-slate-900" }) {
  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-slate-50">
      <div className="label-eyebrow">{label}</div>
      <div className={`font-display text-lg font-black mt-1 truncate ${accent}`}>{value}</div>
    </div>
  );
}
