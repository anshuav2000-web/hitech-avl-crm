import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { KanbanSquare, History } from "lucide-react";
import { toast } from "sonner";
import { useConfig } from "@/context/ConfigContext";
import { groupsOf } from "@/constants/leadStages";
import StageTimeline from "@/components/pipeline/StageTimeline";

// The 24 stages used to be hard-coded here as well as in Leads.js, LeadDetail.js
// and Dashboard.js (four copies that had already drifted). They now come from the
// lead_stages config set via useConfig, so an admin renaming or regrouping a
// stage in Settings changes the board with no code edit.
export default function Pipeline() {
  const { stages, stageLabels } = useConfig();
  const [leads, setLeads] = useState([]);
  const [draggingId, setDraggingId] = useState(null);
  const [activeGroup, setActiveGroup] = useState(null);
  const [timelineFor, setTimelineFor] = useState(null);

  const load = () => api.get("/leads").then((r) => setLeads(r.data || []));
  useEffect(() => {
    load();
  }, []);

  const groups = useMemo(() => groupsOf(stages), [stages]);

  // Follow the config: if an admin adds or renames a group, land on a valid one
  // instead of rendering an empty board.
  useEffect(() => {
    if (!groups.length) return;
    if (!activeGroup || !groups.includes(activeGroup)) setActiveGroup(groups[0]);
  }, [groups, activeGroup]);

  const filteredStages = stages.filter((s) => s.group === activeGroup);

  const moveLead = async (leadId, stage) => {
    const lead = leads.find((l) => l.id === leadId);
    if (!lead || lead.stage === stage) return;

    const previous = lead.stage;
    setLeads((ls) => ls.map((l) => (l.id === leadId ? { ...l, stage } : l)));
    try {
      await api.patch(`/leads/${leadId}`, { stage });
      toast.success(`Moved to ${stageLabels[stage] || stage}`);
    } catch (e) {
      // Roll back to the server's truth rather than leaving a lie on the board.
      setLeads((ls) => ls.map((l) => (l.id === leadId ? { ...l, stage: previous } : l)));
      toast.error(e?.response?.data?.detail || "Could not move that lead");
      load();
    }
  };

  const onDrop = async (stage) => {
    if (!draggingId) return;
    const id = draggingId;
    setDraggingId(null);
    await moveLead(id, stage);
  };

  /** Keyboard equivalent of the drag gesture, so the board is not mouse-only. */
  const moveWithKeyboard = (lead, dir) => {
    const i = filteredStages.findIndex((s) => s.key === lead.stage);
    const target = filteredStages[i + dir];
    if (!target) {
      toast.error(`${lead.name} is at the edge of this group`);
      return;
    }
    moveLead(lead.id, target.key);
  };

  return (
    <div
      className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-8 bg-white min-h-screen text-slate-900"
      data-testid="pipeline-page"
    >
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-sky-700 font-bold uppercase tracking-wider mb-2">
            <span>Sales Workspace</span>
            <span>/</span>
            <span className="text-slate-900">Lead Progression</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <KanbanSquare className="w-8 h-8 text-sky-600" />
            Enterprise Pipeline Board
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Drag and drop leads to advance them across the {stages.length} stages of the HiTech AVL Sales
            Workflow. Stages, labels and groups come from Settings → CRM Lists.
          </p>
        </div>
      </header>

      <div className="flex gap-2.5 overflow-x-auto pb-2 border-b border-slate-100" data-testid="pipeline-groups">
        {groups.map((g) => (
          <button
            key={g}
            onClick={() => setActiveGroup(g)}
            data-testid={`pipeline-group-${g.replace(/\s+/g, "-").toLowerCase()}`}
            className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
              activeGroup === g
                ? "bg-sky-600 text-white shadow-md shadow-sky-600/20"
                : "bg-slate-50 border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            {g} Pipeline
          </button>
        ))}
      </div>

      <div className="flex gap-6 overflow-x-auto pb-6 no-scrollbar">
        {filteredStages.map((s) => {
          const stageLeads = leads.filter((l) => l.stage === s.key);
          return (
            <div
              key={s.key}
              data-testid={`pipeline-column-${s.key}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(s.key)}
              className="w-80 flex-shrink-0 bg-slate-50/60 border border-slate-200 rounded-2xl flex flex-col max-h-[calc(100vh-220px)] shadow-xs"
            >
              <div className="px-4.5 py-4.5 flex items-center justify-between border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${s.accent} shadow-sm`} />
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-900">{s.label}</span>
                </div>
                <span className="text-[10px] font-bold text-slate-500 bg-white px-2 py-0.5 rounded-full border border-slate-200 font-mono">
                  {stageLeads.length}
                </span>
              </div>

              <div className="p-3 overflow-y-auto space-y-3 flex-1 min-h-[400px]">
                {stageLeads.map((l) => (
                  <div
                    key={l.id}
                    draggable
                    onDragStart={() => setDraggingId(l.id)}
                    data-testid={`kanban-card-${l.id}`}
                    className="bg-white border border-slate-200 rounded-xl p-4 hover:border-sky-500 hover:shadow-md cursor-grab active:cursor-grabbing transition-all space-y-2.5"
                  >
                    <Link to={`/leads/${l.id}`} className="block" data-testid={`kanban-link-${l.id}`}>
                      <div>
                        <h4 className="font-display font-extrabold text-sm text-slate-900">{l.name}</h4>
                        {l.company && <p className="text-xs text-slate-500 font-semibold">{l.company}</p>}
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider border-t border-slate-100 pt-2.5 text-slate-400">
                        <span className="capitalize">{l.source?.replace(/_/g, " ")}</span>
                        {l.budget && (
                          <span className="font-mono text-slate-900 font-extrabold">
                            ₹{Number(l.budget).toLocaleString("en-IN")}
                          </span>
                        )}
                      </div>
                    </Link>

                    <div className="flex items-center justify-between gap-1 pt-1">
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => moveWithKeyboard(l, -1)}
                          aria-label={`Move ${l.name} to previous stage`}
                          className="text-[10px] font-bold px-2 py-0.5 rounded-md border border-slate-200 text-slate-500 hover:border-sky-400 hover:text-sky-700"
                        >
                          ◀
                        </button>
                        <button
                          type="button"
                          onClick={() => moveWithKeyboard(l, 1)}
                          aria-label={`Move ${l.name} to next stage`}
                          className="text-[10px] font-bold px-2 py-0.5 rounded-md border border-slate-200 text-slate-500 hover:border-sky-400 hover:text-sky-700"
                        >
                          ▶
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => setTimelineFor(l)}
                        aria-label={`Show stage history for ${l.name}`}
                        className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-400 hover:text-sky-600"
                      >
                        <History className="w-3 h-3" /> History
                      </button>
                    </div>
                  </div>
                ))}
                {stageLeads.length === 0 && (
                  <div className="text-xs text-slate-400 text-center py-12 font-medium">Drop leads here</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {timelineFor ? (
        <StageTimeline
          leadId={timelineFor.id}
          leadName={timelineFor.name}
          stageLabels={stageLabels}
          onClose={() => setTimelineFor(null)}
        />
      ) : null}
    </div>
  );
}
