import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import { sourceColors, statusColors } from "@/components/badges";

const tooltipStyle = {
  backgroundColor: "#ffffff",
  borderRadius: 12,
  border: "1px solid #cbd5e1",
  fontSize: 12,
  color: "#0f172a",
};

/** Shared donut + legend body used by both the sources and quotation-status widgets. */
function Donut({ rows, colors, emptyText, testid }) {
  if (!rows.length) {
    return <div className="text-sm text-slate-500 py-12 text-center">{emptyText}</div>;
  }
  return (
    <div data-testid={testid}>
      <ResponsiveContainer width="100%" height={170}>
        <PieChart>
          <Pie data={rows} dataKey="value" innerRadius={48} outerRadius={76} paddingAngle={3}>
            {rows.map((d, i) => (
              <Cell key={i} fill={colors[d.name] || "#0284c7"} stroke="#ffffff" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-2 mt-3">
        {rows.map((s) => (
          <div key={s.name} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: colors[s.name] || "#0284c7" }} />
              <span className="capitalize text-slate-700 font-semibold">{s.name}</span>
            </div>
            <span className="font-bold text-slate-900">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LeadSourcesWidget({ stats }) {
  const rows = Object.entries(stats.by_source || {})
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: k, value: v }));

  return (
    <div>
      <div className="label-eyebrow mb-1">Inbound Channels</div>
      <div className="font-display text-xl font-bold text-slate-900 mb-4">Lead Sources</div>
      <Donut rows={rows} colors={sourceColors} emptyText="No lead sources logged yet." testid="lead-source-chart" />
    </div>
  );
}

export function QuotationStatusWidget({ stats }) {
  const rows = Object.entries(stats.quote_stats?.by_status || {})
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: k, value: v }));

  return (
    <div>
      <div className="label-eyebrow mb-1">Financial Quotes</div>
      <div className="font-display text-xl font-bold text-slate-900 mb-4">Quotation Status</div>
      <Donut rows={rows} colors={statusColors} emptyText="No quotations generated yet." testid="quote-status-chart" />
    </div>
  );
}
