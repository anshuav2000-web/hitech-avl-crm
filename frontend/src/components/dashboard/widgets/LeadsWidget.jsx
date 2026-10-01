import { TrendingUp, Users, Trophy, Target } from "lucide-react";
import { useConfig } from "@/context/ConfigContext";

function Kpi({ label, value, icon: Icon, accent = "text-slate-900", testid }) {
  return (
    <div
      className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between"
      data-testid={testid}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="label-eyebrow">{label}</div>
        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className={`font-display text-3xl lg:text-4xl font-black tracking-tight ${accent}`}>{value}</div>
    </div>
  );
}

/**
 * Lead KPI tiles.
 *
 * "In Pipeline" used to read `stats.by_stage.won` / `.lost`, which are undefined
 * because no stage is named won or lost -- so the tile rendered NaN. The won and
 * lost keys now come from the config set via useConfig.
 */
export default function LeadsWidget({ stats }) {
  const { wonKey, lostKey } = useConfig();
  const byStage = stats.by_stage || {};
  const won = byStage[wonKey] ?? 0;
  const lost = byStage[lostKey] ?? 0;
  const inPipeline = Math.max(0, (stats.total ?? 0) - won - lost);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="kpi-grid">
      <Kpi label="Total Leads" value={stats.total ?? 0} icon={Users} accent="text-sky-700" testid="kpi-total" />
      <Kpi label="In Pipeline" value={inPipeline} icon={Target} accent="text-indigo-700" testid="kpi-pipeline" />
      <Kpi label="Won Deals" value={won} icon={Trophy} accent="text-emerald-700" testid="kpi-won" />
      <Kpi label="Conversion" value={`${stats.conversion_rate ?? 0}%`} icon={TrendingUp} accent="text-amber-700" testid="kpi-conversion" />
    </div>
  );
}
