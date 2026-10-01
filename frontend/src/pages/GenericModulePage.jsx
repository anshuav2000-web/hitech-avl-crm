import { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, FolderKanban, Search, CheckCircle2, AlertCircle, Sparkles, X } from "lucide-react";

export default function GenericModulePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", status: "active", priority: "medium" });

  const pathSegments = location.pathname.split("/").filter(Boolean);
  const moduleKey = pathSegments[0] || "dashboard";
  const moduleName = moduleKey.charAt(0).toUpperCase() + moduleKey.slice(1).replace(/-/g, " ");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const endpoint = `/${moduleKey}`;
    api.get(endpoint)
      .then((r) => {
        if (!cancelled) {
          setItems(Array.isArray(r.data) ? r.data : r.data?.items || []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems([
            { id: "1", title: `Sample ${moduleName} Record Alpha`, status: "Active", priority: "High", date: "2026-07-25", value: "₹2,50,000" },
            { id: "2", title: `Sample ${moduleName} Record Beta`, status: "Pending", priority: "Medium", date: "2026-07-28", value: "₹1,20,000" },
            { id: "3", title: `Sample ${moduleName} Record Gamma`, status: "Completed", priority: "Low", date: "2026-08-02", value: "₹4,80,000" },
          ]);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [moduleKey, moduleName]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const newItem = { id: Date.now().toString(), title: form.title || `New ${moduleName}`, status: form.status, priority: form.priority, date: new Date().toISOString().split("T")[0], value: "₹1,00,000" };
      setItems((prev) => [newItem, ...prev]);
      setShowModal(false);
      setForm({ title: "", description: "", status: "active", priority: "medium" });
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = search.trim()
    ? items.filter((i) => (i.title || i.name || "").toLowerCase().includes(search.toLowerCase()))
    : items;

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid={`${moduleKey}-page`}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-sky-700 font-bold uppercase tracking-wider mb-2">
            <span>Enterprise ERP</span>
            <span>/</span>
            <span className="text-slate-900">{moduleName}</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <FolderKanban className="w-8 h-8 text-sky-600" />
            {moduleName} Management
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Manage records, track status lifecycles, and review detailed operational data.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" /> Add {moduleName.slice(0, -1) || moduleName}
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4 p-4">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search ${moduleName.toLowerCase()}...`}
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-sky-500 transition-all font-medium"
          />
        </div>
        <span className="text-xs text-slate-500 font-semibold">Showing {filtered.length} records</span>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sky-600" /> Create New {moduleName.slice(0, -1) || moduleName}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Title / Name *</label>
                <input
                  required
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="Enter title..."
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Description</label>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Add notes or details..."
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Status</label>
                  <select
                    value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  >
                    <option value="active">Active</option>
                    <option value="pending">Pending</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Priority</label>
                  <select
                    value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: e.target.value })}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500"
                >
                  Save Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Main Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        {loading ? (
          <div className="p-12 text-center text-slate-500 text-sm font-medium">Loading records...</div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center space-y-3">
            <AlertCircle className="w-10 h-10 text-sky-600 mx-auto opacity-70" />
            <h3 className="font-display text-lg font-bold text-slate-900">No records found</h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto">Get started by creating your first record.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 font-bold">
                <tr>
                  <th className="px-6 py-4 font-bold">Title / Name</th>
                  <th className="px-6 py-4 font-bold">Status</th>
                  <th className="px-6 py-4 font-bold">Priority</th>
                  <th className="px-6 py-4 font-bold">Date</th>
                  <th className="px-6 py-4 font-bold text-right">Value / Metric</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((item, idx) => (
                  <tr key={item.id || idx} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-6 py-4 font-bold text-slate-900 flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-700 font-bold text-xs shrink-0">
                        {(item.title || item.name || "R")[0].toUpperCase()}
                      </div>
                      <span className="group-hover:text-sky-600 transition-colors">{item.title || item.name || "Untitled Record"}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3" /> {item.status || "Active"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                        {item.priority || "Medium"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 text-xs font-mono">
                      {item.date || new Date().toISOString().split("T")[0]}
                    </td>
                    <td className="px-6 py-4 text-right font-bold text-slate-900">
                      {item.value || "₹1,50,000"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
