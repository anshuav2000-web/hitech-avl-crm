import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";

const tooltipStyle = {
  backgroundColor: "#ffffff",
  borderRadius: 12,
  border: "1px solid #cbd5e1",
  fontSize: 12,
  color: "#0f172a",
};

export default function LeadsInflowWidget({ stats }) {
  const trend = (stats.leads_by_day || []).map((d) => ({
    day: new Date(d.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
    count: d.count,
  }));

  return (
    <div data-testid="widget-leads-inflow">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-1">Acoustic Signal Trend</div>
          <div className="font-display text-xl font-bold text-slate-900">Lead Inflow (Last 14 Days)</div>
        </div>
        <Link
          to="/leads"
          className="text-xs text-sky-600 hover:text-sky-700 flex items-center gap-1 font-bold transition-colors"
        >
          View All Leads <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>
      <ResponsiveContainer width="100%" height={230}>
        <AreaChart data={trend} margin={{ left: -20, top: 10 }}>
          <defs>
            <linearGradient id="leadGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0284c7" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#0284c7" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey="day"
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
            interval={Math.max(0, Math.floor(trend.length / 7) - 1)}
          />
          <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Area type="monotone" dataKey="count" stroke="#0284c7" strokeWidth={3} fill="url(#leadGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
