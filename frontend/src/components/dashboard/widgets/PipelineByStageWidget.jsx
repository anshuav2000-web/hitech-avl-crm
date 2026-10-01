import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { useConfig } from "@/context/ConfigContext";

const tooltipStyle = {
  backgroundColor: "#ffffff",
  borderRadius: 12,
  border: "1px solid #cbd5e1",
  fontSize: 12,
  color: "#0f172a",
};

export default function PipelineByStageWidget({ stats }) {
  const { stageLabels } = useConfig();
  const data = Object.entries(stats.by_stage || {}).map(([k, v]) => ({
    stage: stageLabels[k] || k,
    count: v,
  }));

  return (
    <div data-testid="widget-pipeline-by-stage">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-1">Pipeline Overview</div>
          <div className="font-display text-xl font-bold text-slate-900">Leads By Stage</div>
        </div>
        <Link
          to="/pipeline"
          className="text-xs text-sky-600 hover:text-sky-700 font-bold flex items-center gap-1 transition-colors"
          data-testid="link-pipeline"
        >
          Open Board <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>
      <ResponsiveContainer width="100%" height={230}>
        <BarChart data={data}>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="stage" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill="#0284c7" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
