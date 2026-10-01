import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, CheckSquare } from "lucide-react";

const PRIORITIES = ["low", "medium", "high", "urgent"];
const TASK_STATUSES = ["pending", "in_progress", "completed"];

export default function Tasks() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", priority: "medium", status: "pending", due_date: "", assigned_to: "", lead_id: "" });

  useEffect(() => {
    api.get("/tasks").then((r) => setItems(r.data));
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/tasks", form);
      setItems((prev) => [...prev, r.data]);
      setShowForm(false);
      setForm({ title: "", priority: "medium", status: "pending", due_date: "", assigned_to: "", lead_id: "" });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="tasks-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Work</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Tasks</h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} tasks in your workspace</p>
        </div>
        <button onClick={() => setShowForm(true)} data-testid="tasks-add-btn" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
          <Plus className="w-4 h-4" /> Add New
        </button>
      </header>

      {showForm && (
        <form onSubmit={submit} className="glass-card bg-white border border-slate-200 p-6 mb-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Title *" value={form.title} onChange={(v) => update("title", v)} testid="tf-title" />
            <Select label="Priority" value={form.priority} onChange={(v) => update("priority", v)} options={PRIORITIES} testid="tf-priority" />
            <Select label="Status" value={form.status} onChange={(v) => update("status", v)} options={TASK_STATUSES} testid="tf-status" />
            <Field label="Due Date" type="date" value={form.due_date} onChange={(v) => update("due_date", v)} testid="tf-due" />
            <Field label="Assigned To" value={form.assigned_to} onChange={(v) => update("assigned_to", v)} testid="tf-assign" />
            <Field label="Lead ID" value={form.lead_id} onChange={(v) => update("lead_id", v)} testid="tf-lead" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
            <button type="submit" data-testid="tf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800">Save</button>
          </div>
        </form>
      )}

      <div className="glass-card bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
              <th className="text-left px-6 py-3 font-medium">Title</th>
              <th className="text-left px-6 py-3 font-medium">Priority</th>
              <th className="text-left px-6 py-3 font-medium">Status</th>
              <th className="text-left px-6 py-3 font-medium">Due Date</th>
              <th className="text-left px-6 py-3 font-medium">Assigned To</th>
              <th className="text-left px-6 py-3 font-medium">Lead ID</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={6} className="px-6 py-14 text-center text-slate-500">No tasks yet.</td></tr>
            )}
            {items.map((t) => (
              <tr key={t.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-3.5"><Link to={`/tasks/${t.id}`} className="font-medium text-slate-900 hover:underline" data-testid={`task-row-${t.id}`}>{t.title}</Link></td>
                <td className="px-6 py-3.5"><PriorityBadge priority={t.priority} /></td>
                <td className="px-6 py-3.5"><StatusBadge status={t.status} /></td>
                <td className="px-6 py-3.5 text-slate-700">{t.due_date ? new Date(t.due_date).toLocaleDateString() : "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{t.assigned_to || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{t.lead_id || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PriorityBadge({ priority }) {
  const map = {
    low: "bg-slate-100 text-slate-700 border-slate-200",
    medium: "bg-blue-50 text-blue-700 border-blue-200",
    high: "bg-amber-50 text-amber-700 border-amber-200",
    urgent: "bg-red-50 text-red-700 border-red-200",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-sm text-xs font-medium border capitalize ${map[priority] || ""}`}>{priority || "—"}</span>
  );
}

function StatusBadge({ status }) {
  const map = {
    pending: "bg-slate-100 text-slate-700 border-slate-200",
    in_progress: "bg-blue-50 text-blue-700 border-blue-200",
    completed: "bg-green-50 text-green-700 border-green-200",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-sm text-xs font-medium border capitalize ${map[status] || ""}`}>{status?.replace("_", " ") || "—"}</span>
  );
}

function Field({ label, value, onChange, type = "text", testid }) {
  return (
    <div>
      <label className="label-eyebrow block mb-2">{label}</label>
      <input data-testid={testid} type={type} value={value} onChange={(e) => onChange(e.target.value)} className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none" />
    </div>
  );
}

function Select({ label, value, onChange, options, testid }) {
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <div>
      <label className="label-eyebrow block mb-2">{label}</label>
      <select data-testid={testid} value={value} onChange={(e) => onChange(e.target.value)} className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm bg-white focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none capitalize">
        {opts.map((o) => (
          <option key={o.value} value={o.value} className="capitalize">{o.label}</option>
        ))}
      </select>
    </div>
  );
}
