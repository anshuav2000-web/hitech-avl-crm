import { useState } from "react";
import { X } from "lucide-react";
import { WIDGETS } from "@/config/widgetRegistry";

/**
 * Add-widget modal, grouped by category. Lists only widgets the caller does not
 * already have on their board; roles were already applied server-side by
 * /dashboard/widgets, so nothing here needs to re-check permissions.
 */
export default function WidgetPicker({ hidden, onAdd, onClose }) {
  const groups = hidden.reduce((acc, w) => {
    (acc[w.group] ||= []).push(w);
    return acc;
  }, {});

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-start justify-center p-6 overflow-y-auto"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Add widget"
    >
      <div
        className="bg-white border border-slate-200 rounded-xl shadow-2xl w-full max-w-2xl mt-16"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <div className="label-eyebrow mb-1">Customise</div>
            <div className="font-display text-lg font-bold text-slate-900">Add Widget</div>
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

        <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
          {hidden.length === 0 ? (
            <div className="text-sm text-slate-500 py-8 text-center">
              Every available widget is already on your board.
            </div>
          ) : (
            Object.entries(groups).map(([group, widgets]) => (
              <div key={group}>
                <div className="label-eyebrow mb-2">{group}</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {widgets.map((w) => {
                    const Icon = WIDGETS[w.id]?.icon;
                    return (
                      <button
                        key={w.id}
                        type="button"
                        onClick={() => {
                          onAdd(w.id);
                          onClose();
                        }}
                        className="flex items-center gap-3 text-left border border-slate-200 rounded-xl px-4 py-3 hover:border-sky-400 hover:bg-sky-50/40 transition-colors"
                      >
                        {Icon ? <Icon className="w-4 h-4 text-sky-600 shrink-0" /> : null}
                        <span className="text-sm font-bold text-slate-900">{w.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
