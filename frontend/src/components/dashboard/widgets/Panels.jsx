import { Link } from "react-router-dom";
import { Crown, Tag, Calendar, Ship, Warehouse, ShieldCheck, ArrowUpRight } from "lucide-react";
import { SourceBadge, StageBadge } from "@/components/badges";

const fmtINRShort = (n) => {
  const v = Number(n || 0);
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(2)}Cr`;
  if (v >= 100000) return `₹${(v / 100000).toFixed(2)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${v}`;
};

export function TopRepsWidget({ stats }) {
  const reps = stats.top_reps || [];
  return (
    <div data-testid="top-reps">
      <div className="flex items-center gap-2.5 mb-4">
        <Crown className="w-4 h-4 text-amber-500" />
        <div>
          <div className="label-eyebrow">Performance</div>
          <div className="font-display text-lg font-bold text-slate-900">Top Sales Reps</div>
        </div>
      </div>
      {reps.length === 0 ? (
        <div className="text-sm text-slate-500 py-6 text-center">No sales reps logged.</div>
      ) : (
        <div className="space-y-3">
          {reps.map((r, i) => (
            <div
              key={r.id}
              className="flex items-center gap-3 p-2 rounded-xl hover:bg-slate-50 transition-colors"
              data-testid={`rep-${r.id}`}
            >
              <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-display font-black text-white shrink-0 bg-slate-900">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-bold text-slate-900 truncate">{r.name}</div>
                <div className="text-xs text-slate-500 font-medium">{r.won} won · {r.open} open</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-display font-bold text-sky-700">{fmtINRShort(r.won_value)}</div>
                <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Won</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function BrandInterestWidget({ stats }) {
  const rows = stats.brand_interest || [];
  const max = Math.max(...rows.map((x) => x.count), 1);
  return (
    <div data-testid="brand-interest">
      <div className="flex items-center gap-2.5 mb-4">
        <Tag className="w-4 h-4 text-sky-600" />
        <div>
          <div className="label-eyebrow">Brand Demand</div>
          <div className="font-display text-lg font-bold text-slate-900">Manufacturer Mentions</div>
        </div>
      </div>
      {rows.every((b) => b.count === 0) ? (
        <div className="text-sm text-slate-500 py-6 text-center">No brand mentions logged in leads.</div>
      ) : (
        <div className="space-y-3">
          {rows.map((b) => (
            <div key={b.brand}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-bold text-slate-900">{b.brand}</span>
                <span className="text-slate-500 font-semibold">
                  {b.count} lead{b.count === 1 ? "" : "s"}
                </span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                <div className="h-full rounded-full bg-sky-500" style={{ width: `${(b.count / max) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function FollowUpsWidget({ stats }) {
  const rows = stats.upcoming_follow_ups || [];
  return (
    <div data-testid="upcoming-follow-ups">
      <div className="flex items-center gap-2.5 mb-4">
        <Calendar className="w-4 h-4 text-sky-600" />
        <div>
          <div className="label-eyebrow">Next 7 Days</div>
          <div className="font-display text-lg font-bold text-slate-900">Follow-up Schedule</div>
        </div>
      </div>
      {rows.length === 0 ? (
        <div className="text-sm text-slate-500 py-6 text-center">No follow-ups scheduled.</div>
      ) : (
        <div className="space-y-2 max-h-56 overflow-y-auto no-scrollbar">
          {rows.slice(0, 6).map((a) => (
            <Link
              key={a.id}
              to={`/leads/${a.lead_id}`}
              className="block hover:bg-slate-50 p-2.5 rounded-xl border border-slate-100 transition-colors"
            >
              <div className="text-[10px] uppercase font-bold text-sky-600">
                {new Date(a.follow_up_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}{" "}
                · {a.type?.replace("_", " ")}
              </div>
              <div className="text-xs font-bold text-slate-900 truncate mt-0.5">{a.content}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function OperationsWidget({ stats }) {
  const ops = stats.ops;
  if (!ops) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="widget-operations">
      <div data-testid="ops-shipments">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 font-bold">
              <Ship className="w-4 h-4" />
            </div>
            <div>
              <div className="label-eyebrow">Import Shipments</div>
              <div className="font-display text-lg font-bold text-slate-900">In Transit · {ops.shipments_in_transit}</div>
            </div>
          </div>
          <Link
            to="/shipments"
            className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 font-semibold transition-colors"
          >
            Open <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        {ops.shipments_arriving_soon.length === 0 ? (
          <div className="text-sm text-slate-500 py-6 text-center">No shipments arriving soon.</div>
        ) : (
          <div className="space-y-2.5">
            {ops.shipments_arriving_soon.slice(0, 5).map((s) => (
              <div key={s.id} className="flex items-center justify-between border-b border-slate-100 pb-2 last:border-0">
                <div className="text-xs">
                  <div className="font-bold text-slate-900">{s.po_no} · {s.oem}</div>
                  <div className="text-slate-500 capitalize">{s.status.replace("_", " ")}</div>
                </div>
                <div className="text-xs font-bold text-sky-600">{s.eta || "—"}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div data-testid="ops-stock">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 font-bold">
              <Warehouse className="w-4 h-4" />
            </div>
            <div>
              <div className="label-eyebrow">Warehouse Hardware</div>
              <div className="font-display text-lg font-bold text-slate-900">Stock Summary</div>
            </div>
          </div>
          <Link
            to="/inventory"
            className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 font-semibold transition-colors"
          >
            Open <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="border border-slate-200 rounded-xl p-3 bg-slate-50">
            <div className="label-eyebrow">In Stock</div>
            <div className="font-display text-3xl font-black text-emerald-600 mt-1">{ops.stock_in_stock_units}</div>
            <div className="text-[10px] uppercase text-slate-500 font-bold mt-1">units available</div>
          </div>
          <div className="border border-slate-200 rounded-xl p-3 bg-slate-50">
            <div className="label-eyebrow">In Transit</div>
            <div className="font-display text-3xl font-black text-sky-600 mt-1">{ops.stock_in_transit_units}</div>
            <div className="text-[10px] uppercase text-slate-500 font-bold mt-1">units en route</div>
          </div>
        </div>
      </div>

      <div data-testid="ops-amcs">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 font-bold">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="label-eyebrow">Service Contracts</div>
              <div className="font-display text-lg font-bold text-slate-900">{ops.amcs_active} Active AMC</div>
            </div>
          </div>
          <Link
            to="/amcs"
            className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 font-semibold transition-colors"
          >
            Open <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        {ops.amcs_expiring_soon.length === 0 ? (
          <div className="text-sm text-slate-500 py-6 text-center">No contracts expiring in 60 days.</div>
        ) : (
          <div className="space-y-2 max-h-44 overflow-y-auto no-scrollbar">
            {ops.amcs_expiring_soon.slice(0, 5).map((a) => (
              <div key={a.id} className="flex items-center justify-between border-b border-slate-100 pb-2 last:border-0">
                <div className="text-xs min-w-0">
                  <div className="font-bold text-slate-900 truncate">{a.customer_name}</div>
                  <div className="text-slate-500 font-semibold">₹{Number(a.value).toLocaleString("en-IN")}</div>
                </div>
                <div className="text-xs font-bold text-amber-600 shrink-0 ml-2">{a.end_date}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function RecentLeadsWidget({ stats }) {
  return (
    <div data-testid="widget-recent-leads">
      <div className="flex items-center justify-between px-6 py-5 border-b border-slate-200 bg-slate-50/50">
        <div>
          <div className="label-eyebrow mb-1">Inbound Activity</div>
          <div className="font-display text-xl font-bold text-slate-900">Latest Lead Enquiries</div>
        </div>
        <Link
          to="/leads"
          className="text-xs text-sky-600 hover:text-sky-700 font-bold flex items-center gap-1 transition-colors"
          data-testid="link-all-leads"
        >
          View All Leads <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left text-slate-700" data-testid="recent-leads-table">
          <thead className="text-xs uppercase tracking-wider text-slate-500 bg-slate-100/70 border-b border-slate-200 font-bold">
            <tr>
              <th className="px-6 py-4 font-bold">Client Name</th>
              <th className="px-6 py-4 font-bold">Organization / Venue</th>
              <th className="px-6 py-4 font-bold">Source</th>
              <th className="px-6 py-4 font-bold">Stage</th>
              <th className="px-6 py-4 font-bold text-right">Created Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(stats.recent || []).length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                  No leads recorded yet.
                </td>
              </tr>
            )}
            {(stats.recent || []).map((l) => (
              <tr key={l.id} className="hover:bg-slate-50 transition-colors group">
                <td className="px-6 py-4 font-bold text-slate-900">
                  <Link
                    to={`/leads/${l.id}`}
                    className="hover:text-sky-600 transition-colors"
                    data-testid={`recent-lead-${l.id}`}
                  >
                    {l.name}
                  </Link>
                </td>
                <td className="px-6 py-4 text-slate-600 font-medium">{l.company || "—"}</td>
                <td className="px-6 py-4">
                  <SourceBadge source={l.source} />
                </td>
                <td className="px-6 py-4">
                  <StageBadge stage={l.stage} />
                </td>
                <td className="px-6 py-4 text-right text-slate-500 text-xs font-mono">
                  {new Date(l.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
