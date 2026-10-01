import { useState } from "react";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import WidgetShell, { ResetButton, ReorderButtons } from "@/components/dashboard/WidgetShell";
import WidgetPicker from "@/components/dashboard/WidgetPicker";
import { WIDGETS, WidgetBody, spanClass } from "@/config/widgetRegistry";

export default function DashboardGrid({ layout, hidden, saving, error, stats, summary, move, resize, hide, add, reset }) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [expanded, setExpanded] = useState({});

  return (
    <div className="space-y-6" data-testid="dashboard-grid">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-xs text-slate-500">
          {saving ? "Saving layout…" : "Drag-free reordering keeps the board keyboard accessible."}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPickerOpen(true)}
            data-testid="add-widget"
            className="inline-flex items-center gap-2 text-white px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all"
          >
            <Plus className="w-3.5 h-3.5" /> Add Widget
          </button>
          <ResetButton onClick={reset} />
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 text-rose-700 text-xs font-semibold px-4 py-3">
          Could not save your layout — it has been restored to the last saved version.
        </div>
      ) : null}

      {layout.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-sm text-slate-500">
          Your dashboard is empty. Use “Add Widget” to build it.
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-6">
          {layout.map((cell, index) => {
            const entry = WIDGETS[cell.id];
            if (!entry) return null;
            const Component = entry.component;
            const isLarge = expanded[cell.id] === true;

            const body = <Component stats={stats} data={summary?.[SUMMARY_FOR[cell.id]]} />;

            return (
              <div key={cell.id} className={spanClass(isLarge ? 12 : cell.w)} data-testid={`widget-slot-${cell.id}`}>
                {entry.bare ? (
                  body
                ) : (
                  <WidgetShell
                    title={entry.label}
                    icon={entry.icon}
                    large={isLarge}
                    onHide={() => hide(cell.id)}
                    onResize={() => {
                      setExpanded((e) => ({ ...e, [cell.id]: !e[cell.id] }));
                      resize(cell.id, { h: isLarge ? 2 : 3 });
                    }}
                    actions={
                      <ReorderButtons
                        label={entry.label}
                        onMoveUp={index > 0 ? () => move(cell.id, -1) : null}
                        onMoveDown={index < layout.length - 1 ? () => move(cell.id, 1) : null}
                      />
                    }
                  >
                    {body}
                  </WidgetShell>
                )}
              </div>
            );
          })}
        </div>
      )}

      {pickerOpen ? (
        <WidgetPicker hidden={hidden} onAdd={add} onClose={() => setPickerOpen(false)} />
      ) : null}
    </div>
  );
}

/** Mirrors SUMMARY_KEYS in the registry; kept local so the grid needs no import cycle. */
const SUMMARY_FOR = {
  projects: "projects",
  tasks: "tasks",
  purchase_orders: "purchase_orders",
  notifications: "notifications",
}
