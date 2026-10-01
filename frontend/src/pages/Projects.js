import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, FolderKanban, Pencil, Trash2, X, CheckCircle2 } from "lucide-react";

const STATUSES = ["active", "completed", "on_hold"];

export default function Projects() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "superadmin" || user?.role === "admin";

  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({ name: "", client: "", status: "active", start_date: "", end_date: "", budget: "" });

  const load = () => {
    api.get("/projects").then((r) => setItems(r.data || []));
  };

  useEffect(() => { load(); }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const startEdit = (p) => {
    setEditingId(p.id);
    setForm({
      name: p.name || "",
      client: p.client || "",
      status: p.status || "active",
      start_date: p.start_date || "",
      end_date: p.end_date || "",
      budget: p.budget || ""
    });
    setShowForm(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.patch(`/projects/${editingId}`, {
          ...form,
          budget: Number(form.budget || 0)
        });
        setMsg(`Project '${form.name}' updated successfully!`);
      } else {
        const r = await api.post("/projects", {
          ...form,
          budget: Number(form.budget || 0)
        });
        setMsg(`Project '${r.data.name}' created successfully!`);
      }
      setShowForm(false);
      setEditingId(null);
      setForm({ name: "", client: "", status: "active", start_date: "", end_date: "", budget: "" });
      load();
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const deleteProject = async (id, name) => {
    if (!window.confirm(`SUPER ADMIN: Permanently delete project '${name}'?`)) return;
    try {
      await api.delete(`/projects/${id}`);
      setMsg(`Project '${name}' deleted successfully.`);
      load();
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="projects-page">
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Stage Production Operations</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <FolderKanban className="w-8 h-8 text-sky-600" /> Production Projects
          </h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} active projects in your workspace</p>
        </div>
        <button
          onClick={() => { setEditingId(null); setForm({ name: "", client: "", status: "active", start_date: "", end_date: "", budget: "" }); setShowForm(true); }}
          data-testid="projects-add-btn"
          className="inline-flex items-center gap-2 bg-sky-600 text-white px-5 py-2.5 rounded-xl text-xs font-bold hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Create Project
        </button>
      </header>

      {msg && (
        <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-800 text-xs flex items-center justify-between font-bold">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{msg}</span>
          </div>
          <button onClick={() => setMsg("")} className="hover:text-slate-900 text-slate-500">Dismiss</button>
        </div>
      )}

      {showForm && (
        <form onSubmit={submit} className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <h3 className="font-display text-base font-bold text-slate-900">{editingId ? "Super Admin: Edit Production Project" : "Create New Project"}</h3>
            <button type="button" onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Project Name *" value={form.name} onChange={(v) => update("name", v)} testid="pf-name" />
            <Field label="Client Name / Organization" value={form.client} onChange={(v) => update("client", v)} testid="pf-client" />
            <Select label="Status" value={form.status} onChange={(v) => update("status", v)} options={STATUSES} testid="pf-status" />
            <Field label="Budget (INR)" type="number" value={form.budget} onChange={(v) => update("budget", v)} testid="pf-budget" />
            <Field label="Start Date" type="date" value={form.start_date} onChange={(v) => update("start_date", v)} testid="pf-start" />
            <Field label="End Date" type="date" value={form.end_date} onChange={(v) => update("end_date", v)} testid="pf-end" />
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
            <button type="submit" data-testid="pf-submit" className="inline-flex items-center gap-2 bg-sky-600 text-white px-5 py-2 rounded-xl text-xs font-bold hover:bg-sky-500">
              {editingId ? "Update Project" : "Save Project"}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-100/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 font-bold">
              <tr>
                <th className="px-6 py-4 font-bold">Project Name</th>
                <th className="px-6 py-4 font-bold">Client</th>
                <th className="px-6 py-4 font-bold">Status</th>
                <th className="px-6 py-4 font-bold">Timeline</th>
                <th className="px-6 py-4 font-bold text-right">Budget (₹)</th>
                <th className="px-6 py-4 font-bold text-right">Super Admin Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.length === 0 && (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-slate-500 font-medium">No projects logged yet.</td></tr>
              )}
              {items.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50 transition-colors group">
                  <td className="px-6 py-4 font-bold text-slate-900">{p.name}</td>
                  <td className="px-6 py-4 text-slate-700 font-semibold">{p.client || "—"}</td>
                  <td className="px-6 py-4"><StatusBadge status={p.status} /></td>
                  <td className="px-6 py-4 text-slate-500 text-xs font-mono">
                    {p.start_date || "—"} → {p.end_date || "—"}
                  </td>
                  <td className="px-6 py-4 text-right font-display font-extrabold text-slate-900">
                    {p.budget ? `₹${Number(p.budget).toLocaleString("en-IN")}` : "—"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-1.5 justify-end">
                      <button
                        onClick={() => startEdit(p)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 border border-slate-300 hover:bg-slate-200 px-2.5 py-1 rounded-lg transition-all cursor-pointer"
                        title="Edit Project"
                      >
                        <Pencil className="w-3 h-3 text-slate-700" /> Edit
                      </button>

                      {isAdmin && (
                        <button
                          onClick={() => deleteProject(p.id, p.name)}
                          className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 px-2.5 py-1 rounded-lg transition-all cursor-pointer"
                          title="Super Admin Delete Project"
                        >
                          <Trash2 className="w-3 h-3 text-rose-600" /> Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    active: "bg-emerald-50 text-emerald-700 border-emerald-200",
    completed: "bg-sky-50 text-sky-700 border-sky-200",
    on_hold: "bg-amber-50 text-amber-700 border-amber-200",
  };
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border capitalize ${map[status] || map.active}`}>
      {status?.replace("_", " ") || "active"}
    </span>
  );
}

function Field({ label, value, onChange, type = "text", testid }) {
  return (
    <div>
      <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">{label}</label>
      <input data-testid={testid} type={type} value={value} onChange={(e) => onChange(e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
    </div>
  );
}

function Select({ label, value, onChange, options, testid }) {
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <div>
      <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">{label}</label>
      <select data-testid={testid} value={value} onChange={(e) => onChange(e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium capitalize">
        {opts.map((o) => (
          <option key={o.value} value={o.value} className="capitalize">{o.label}</option>
        ))}
      </select>
    </div>
  );
}
