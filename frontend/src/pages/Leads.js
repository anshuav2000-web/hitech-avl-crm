import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Search, Trash2, Pencil, Users, CheckCircle2 } from "lucide-react";
import { StageBadge, SourceBadge } from "@/components/badges";
import { useConfig } from "@/context/ConfigContext";

export default function Leads() {
  const { user } = useAuth();
  const { stageKeys, sources: SOURCES, stageLabels } = useConfig();
  const isAdmin = user?.role === "superadmin" || user?.role === "admin";

  const [leads, setLeads] = useState([]);
  const [search, setSearch] = useState("");
  const [stage, setStage] = useState("");
  const [source, setSource] = useState("");
  const [users, setUsers] = useState([]);
  const [msg, setMsg] = useState("");

  const load = () => {
    const params = {};
    if (search) params.search = search;
    if (stage) params.stage = stage;
    if (source) params.source = source;
    api.get("/leads", { params }).then((r) => setLeads(r.data || []));
  };

  useEffect(() => {
    api.get("/users/roster").then((r) => setUsers(r.data || []));
  }, []);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [search, stage, source]);

  const userName = (id) => users.find((u) => u.id === id)?.name || "—";

  const deleteLead = async (id, leadName) => {
    if (!window.confirm(`SUPER ADMIN: Are you sure you want to permanently delete lead '${leadName}'?`)) return;
    try {
      await api.delete(`/leads/${id}`);
      setMsg(`Lead '${leadName}' deleted successfully.`);
      load();
    } catch (e) {
      alert("Delete failed: " + e.message);
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="leads-page">
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Lead Acquisition & Sales Pipeline</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Users className="w-8 h-8 text-sky-600" /> All Client Leads
          </h1>
          <p className="text-sm text-slate-600 mt-1">{leads.length} active leads in your sales workspace</p>
        </div>
        <Link
          to="/leads/new"
          data-testid="leads-add-btn"
          className="inline-flex items-center gap-2 text-white px-5 py-2.5 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Create New Lead
        </Link>
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

      {/* Filters */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-wrap gap-3 items-center">
        <div className="flex-1 min-w-[240px] relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            data-testid="leads-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search lead by client name, email, company, phone…"
            className="w-full bg-white pl-9 pr-3 py-2 border border-slate-200 rounded-xl text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500"
          />
        </div>
        <select value={stage} onChange={(e) => setStage(e.target.value)} className="border border-slate-200 rounded-xl text-xs font-bold px-3 py-2 bg-white text-slate-900 capitalize" data-testid="filter-stage">
          <option value="">All Stages</option>
          {stageKeys.map((s) => <option key={s} value={s}>{stageLabels[s] || s}</option>)}
        </select>
        <select value={source} onChange={(e) => setSource(e.target.value)} className="border border-slate-200 rounded-xl text-xs font-bold px-3 py-2 bg-white text-slate-900 capitalize" data-testid="filter-source">
          <option value="">All Sources</option>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-100/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 font-bold">
              <tr>
                <th className="px-6 py-4 font-bold">Client Name</th>
                <th className="px-6 py-4 font-bold">Organization / Venue</th>
                <th className="px-6 py-4 font-bold">Contact Info</th>
                <th className="px-6 py-4 font-bold">Source</th>
                <th className="px-6 py-4 font-bold">Stage</th>
                <th className="px-6 py-4 font-bold">Assigned Sales Rep</th>
                <th className="px-6 py-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.length === 0 && (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-500 font-medium">No matching leads found.</td></tr>
              )}
              {leads.map((l) => (
                <tr key={l.id} className="hover:bg-slate-50 transition-colors group" data-testid={`lead-row-${l.id}`}>
                  <td className="px-6 py-4 font-bold text-slate-900">
                    <Link to={`/leads/${l.id}`} className="hover:text-sky-600 transition-colors" data-testid={`lead-link-${l.id}`}>
                      {l.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-slate-700 font-medium">{l.company || "—"}</td>
                  <td className="px-6 py-4 text-xs font-medium">
                    {l.email && <div className="text-slate-900 font-bold">{l.email}</div>}
                    {l.phone && <div className="text-slate-500">{l.phone}</div>}
                  </td>
                  <td className="px-6 py-4"><SourceBadge source={l.source} /></td>
                  <td className="px-6 py-4"><StageBadge stage={l.stage} /></td>
                  <td className="px-6 py-4 text-xs font-bold text-slate-800">{userName(l.assigned_to)}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-1.5 justify-end">
                      <Link
                        to={`/leads/${l.id}`}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 border border-slate-300 hover:bg-slate-200 px-2.5 py-1 rounded-lg transition-all"
                        title="View & Edit Lead Details"
                      >
                        <Pencil className="w-3 h-3 text-slate-700" /> View / Edit
                      </Link>

                      {isAdmin && (
                        <button
                          onClick={() => deleteLead(l.id, l.name)}
                          className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 px-2.5 py-1 rounded-lg transition-all cursor-pointer"
                          title="Super Admin Delete Lead"
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
