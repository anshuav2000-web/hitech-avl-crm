import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import DashboardGrid from "@/components/dashboard/DashboardGrid";
import { useDashboardLayout } from "@/components/dashboard/hooks/useDashboardLayout";
import { Plus, Volume2 } from "lucide-react";

// StageBadge/SourceBadge/stageLabels used to be defined here and imported by
// Leads.js and LeadDetail.js -- a page module exporting shared UI. They now live
// in @/components/badges, which is also where bug B5 was fixed (the colour map
// was keyed on stage ids that do not exist).
export { StageBadge, SourceBadge } from "@/components/badges";

function greet() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const board = useDashboardLayout();

  useEffect(() => {
    // One call feeds every widget; it embeds /dashboard/stats plus the delivery
    // and inbox data, so the dashboard is a single round trip.
    api
      .get("/dashboard/summary")
      .then((r) => setSummary(r.data))
      .catch((e) => setLoadError(e));
  }, []);

  if (!summary) {
    // The old page spun forever on failure because the fetch had no catch.
    if (loadError) {
      return (
        <div className="p-12 text-center" data-testid="dashboard-error">
          <div className="text-sm font-bold text-slate-900 mb-2">Could not load your dashboard</div>
          <div className="text-xs text-slate-500 mb-4">
            The backend did not respond. Check that the API is running, then reload.
          </div>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 text-white px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500"
          >
            Retry
          </button>
        </div>
      );
    }
    return (
      <div
        className="p-12 text-slate-500 text-sm flex items-center justify-center gap-3"
        data-testid="dashboard-loading"
      >
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin" />
        <span>Loading Console Workspace…</span>
      </div>
    );
  }

  const stats = summary.stats;

  return (
    <div
      className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-8 bg-white min-h-screen text-slate-900"
      data-testid="dashboard-page"
    >
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-3 text-xs text-sky-700 font-bold uppercase tracking-widest mb-2">
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sky-50 border border-sky-200">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-600 animate-ping" />
              Live System Workspace
            </span>
            <span>·</span>
            <span>
              {new Date().toLocaleDateString("en-IN", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900">
            Good {greet()}, {user?.name?.split(" ")[0]}.
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-xl">
            Real-time pipeline volume, audio/lighting inventory, active quotes, and project performance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs">
            <Volume2 className="w-4 h-4 text-sky-600" />
            <span className="text-slate-600 font-semibold mr-1">VU Signal</span>
            <div className="flex items-end gap-0.5 h-4 w-12">
              <div className="w-1.5 h-[40%] bg-emerald-500 rounded-sm" />
              <div className="w-1.5 h-[65%] bg-emerald-500 rounded-sm" />
              <div className="w-1.5 h-[85%] bg-amber-500 rounded-sm" />
              <div className="w-1.5 h-[100%] bg-sky-600 rounded-sm" />
            </div>
          </div>

          <Link
            to="/leads/new"
            data-testid="dashboard-add-lead"
            className="inline-flex items-center gap-2 text-white px-5 py-2.5 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" /> New Lead
          </Link>
        </div>
      </header>

      <DashboardGrid
        layout={board.layout}
        hidden={board.hidden}
        saving={board.saving}
        error={board.error}
        stats={stats}
        summary={summary}
        move={board.move}
        resize={board.resize}
        hide={board.hide}
        add={board.add}
        reset={board.reset}
      />
    </div>
  );
}
