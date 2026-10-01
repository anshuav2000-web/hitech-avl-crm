import { GripVertical, X, Maximize2, Minimize2, RotateCcw } from "lucide-react";

/**
 * Card chrome shared by every widget: title bar, drag handle, size toggle, hide.
 *
 * Widgets stay presentational -- the grid owns ordering and the layout hook owns
 * persistence. Keeping reordering as explicit "move left/right" buttons (rather
 * than free-form drag) is what makes the board keyboard-operable, which the
 * accessibility pass requires.
 */
export default function WidgetShell({
  title,
  subtitle,
  icon: Icon,
  onHide,
  onResize,
  large,
  canHide = true,
  canResize = true,
  actions,
  children,
}) {
  return (
    <section
      className="bg-white border border-slate-200 rounded-xl shadow-xs flex flex-col h-full overflow-hidden"
      aria-label={title}
    >
      <header className="flex items-center gap-2 px-5 py-3 border-b border-slate-100">
        {Icon ? (
          <span className="w-7 h-7 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shrink-0">
            <Icon className="w-3.5 h-3.5" />
          </span>
        ) : null}
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-sm font-bold text-slate-900 truncate">{title}</h2>
          {subtitle ? <p className="text-[11px] text-slate-500 truncate">{subtitle}</p> : null}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {actions}
          {canResize && onResize ? (
            <button
              type="button"
              onClick={() => onResize(!large)}
              title={large ? "Collapse height" : "Expand height"}
              aria-label={large ? `Collapse ${title}` : `Expand ${title}`}
              className="w-6 h-6 rounded-md text-slate-400 hover:text-sky-600 hover:bg-sky-50 flex items-center justify-center transition-colors"
            >
              {large ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
          ) : null}
          {canHide && onHide ? (
            <button
              type="button"
              onClick={onHide}
              title="Hide widget"
              aria-label={`Hide ${title}`}
              className="w-6 h-6 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : null}
        </div>
      </header>

      <div className="flex-1 min-h-0 overflow-auto p-5">{children}</div>
    </section>
  );
}

/** Ordered-list controls used inside the shell header. */
export function ReorderButtons({ onMoveUp, onMoveDown, label }) {
  return (
    <span className="flex items-center text-slate-300">
      <GripVertical className="w-3.5 h-3.5" aria-hidden="true" />
      <button
        type="button"
        onClick={onMoveUp}
        aria-label={`Move ${label} up`}
        className="w-5 h-5 text-[10px] font-bold hover:text-sky-600 disabled:opacity-30"
        disabled={!onMoveUp}
      >
        ▲
      </button>
      <button
        type="button"
        onClick={onMoveDown}
        aria-label={`Move ${label} down`}
        className="w-5 h-5 text-[10px] font-bold hover:text-sky-600 disabled:opacity-30"
        disabled={!onMoveDown}
      >
        ▼
      </button>
    </span>
  );
}

export function ResetButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-600 bg-slate-100 border border-slate-300 hover:bg-slate-200 px-2.5 py-1 rounded-lg transition-all"
    >
      <RotateCcw className="w-3 h-3" /> Reset layout
    </button>
  );
}
