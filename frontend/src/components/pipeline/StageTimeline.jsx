import { useEffect, useState } from "react";
import { X, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";

function sinceLabel(iso) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

/**
 * Structured stage timeline for a single lead.
 *
 * Reads the dedicated /stage-history endpoint rather than parsing free-text
 * activity notes, which cannot be queried for stage duration.
 */
export default function StageTimeline({ leadId, leadName, stageLabels, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    api
      .get(`/leads/${leadId}/stage-history`)
      .then((r) => live && setData(r.data))
      .catch((e) => live && setError(e));
    return () => {
      live = false;
    };
  }, [leadId]);

  const history = data?.history || [];

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-start justify-center p-6 overflow-y-auto"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Stage history for ${leadName}`}
    >
      <div
        className="bg-white border border-slate-200 rounded-xl shadow-2xl w-full max-w-lg mt-16"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <div className="label-eyebrow mb-1">Timeline</div>
            <div className="font-display text-lg font-bold text-slate-900">{leadName}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 flex items-center justify-center"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 max-h-[55vh] overflow-y-auto">
          {error ? (
            <div className="text-sm text-rose-600 py-6 text-center">Could not load stage history.</div>
          ) : !data ? (
            <div className="text-sm text-slate-500 py-6 text-center">Loading…</div>
          ) : history.length === 0 ? (
            <div className="text-sm text-slate-500 py-6 text-center">No stage changes recorded yet.</div>
          ) : (
            <ol className="space-y-3" data-testid="stage-timeline">
              {history.map((h, i) => (
                <li key={i} className="flex items-start gap-3">
                  <div className="flex flex-col items-center shrink-0 pt-1">
                    <div className="w-2.5 h-2.5 rounded-full bg-sky-600" />
                    {i < history.length - 1 && <div className="w-px flex-1 min-h-[24px] bg-slate-200 mt-1" />}
                  </div>
                  <div className="flex-1 pb-1">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
                      {h.from_stage ? (
                        <>
                          <span className="text-slate-500">{stageLabels[h.from_stage] || h.from_stage}</span>
                          <ArrowRight className="w-3 h-3 text-slate-400" />
                        </>
                      ) : (
                        <span className="text-slate-500">Created in</span>
                      )}
                      <span>{stageLabels[h.to_stage] || h.to_stage}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {h.changed_by_name || "System"} · {sinceLabel(h.changed_at)}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}
