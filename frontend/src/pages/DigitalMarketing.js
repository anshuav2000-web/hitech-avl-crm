import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  Plus, Megaphone, Facebook, RefreshCw, CheckCircle2, TrendingUp,
  Target, DollarSign, Users, Sparkles, X, Search, Unplug, Layers
} from "lucide-react";

const TYPES = ["email", "seo", "ads", "funnel"];
const STATUSES = ["draft", "active", "paused", "completed"];

export default function DigitalMarketing() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [metaStatus, setMetaStatus] = useState({ connected: false });
  const [metaLoading, setMetaLoading] = useState(false);
  const [search, setSearch] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    type: "ads",
    status: "active",
    budget: "",
    spent: "",
    leads: "",
    conversions: ""
  });

  const load = async () => {
    setLoading(true);
    try {
      const [mRes, statusRes] = await Promise.all([
        api.get("/marketing"),
        api.get("/meta/status").catch(() => ({ data: { connected: false } }))
      ]);
      setItems(mRes.data || []);
      setMetaStatus(statusRes.data || { connected: false });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const connectAndSyncMeta = async () => {
    setMetaLoading(true);
    try {
      const connRes = await api.post("/meta/connect", {
        account_name: "Hitech Audio & Lighting Official",
        account_id: "act_10482938102938"
      });
      setMetaStatus(connRes.data);
      await load();
      alert("Connected to Meta Ads Suite! Facebook & Instagram ad campaigns imported successfully.");
    } catch (err) {
      alert("Meta connection error: " + formatApiError(err));
    } finally {
      setMetaLoading(false);
    }
  };

  const disconnectMeta = async () => {
    if (!window.confirm("Disconnect Meta Facebook Account?")) return;
    setMetaLoading(true);
    try {
      await api.post("/meta/disconnect");
      setMetaStatus({ connected: false });
      await load();
    } catch (err) {
      alert(formatApiError(err));
    } finally {
      setMetaLoading(false);
    }
  };

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/marketing", {
        ...form,
        budget: Number(form.budget) || 0,
        spent: Number(form.spent) || 0,
        leads: Number(form.leads) || 0,
        conversions: Number(form.conversions) || 0
      });
      setItems((prev) => [r.data, ...prev]);
      setShowForm(false);
      setForm({ name: "", type: "ads", status: "active", budget: "", spent: "", leads: "", conversions: "" });
    } catch (err) {
      alert(formatApiError(err));
    }
  };

  const filteredItems = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter((i) =>
      `${i.name} ${i.type} ${i.status}`.toLowerCase().includes(q)
    );
  }, [items, search]);

  // Aggregate Metrics
  const totalBudget = items.reduce((s, i) => s + Number(i.budget || 0), 0);
  const totalSpent = items.reduce((s, i) => s + Number(i.spent || 0), 0);
  const totalLeads = items.reduce((s, i) => s + Number(i.leads || 0), 0);
  const totalConversions = items.reduce((s, i) => s + Number(i.conversions || 0), 0);

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="marketing-page">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Growth & Customer Acquisition</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Megaphone className="w-8 h-8 text-sky-600" /> Digital Marketing & Meta Ad Campaigns
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Track concert launch campaigns, SEO funnels, and Meta Facebook & Instagram lead ad performance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowForm(true)}
            data-testid="marketing-add-btn"
            className="inline-flex items-center gap-2 bg-sky-600 text-white px-5 py-2.5 rounded-xl text-xs font-bold hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" /> Create Campaign
          </button>
        </div>
      </header>

      {/* Meta Facebook Account Integration Banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold shrink-0 shadow-md shadow-blue-500/20">
            <Facebook className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display text-base font-bold text-slate-900">Meta Ads Manager Connection</h3>
              {metaStatus.connected ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-ping" /> Connected
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">
                  Not Connected
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 mt-0.5">
              {metaStatus.connected
                ? `Active Meta Ad Account: ${metaStatus.ad_account_name || "Hitech Pro Audio Ads Account"} (ID: ${metaStatus.account_id})`
                : "Connect your Facebook & Instagram Ad Account to auto-import live lead gen campaigns and ROAS metrics."}
            </p>
          </div>
        </div>

        <div>
          {metaStatus.connected ? (
            <div className="flex items-center gap-2">
              <button
                onClick={connectAndSyncMeta}
                disabled={metaLoading}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold text-sky-800 bg-sky-50 border border-sky-200 hover:bg-sky-100 transition-all cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${metaLoading ? "animate-spin" : ""}`} /> Sync Meta Ads
              </button>
              <button
                onClick={disconnectMeta}
                disabled={metaLoading}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 transition-all cursor-pointer"
              >
                <Unplug className="w-3.5 h-3.5" /> Disconnect
              </button>
            </div>
          ) : (
            <button
              onClick={connectAndSyncMeta}
              disabled={metaLoading}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 shadow-md shadow-blue-600/20 transition-all cursor-pointer"
            >
              <Facebook className="w-4 h-4" />
              {metaLoading ? "Linking Meta Account..." : "Login / Connect Meta Ads"}
            </button>
          )}
        </div>
      </div>

      {/* Campaign Performance KPI Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Total Ad Budget</span>
            <DollarSign className="w-4 h-4 text-sky-600" />
          </div>
          <div className="font-display text-2xl lg:text-3xl font-black text-slate-900">
            ₹{totalBudget.toLocaleString("en-IN")}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Amount Spent</span>
            <TrendingUp className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="font-display text-2xl lg:text-3xl font-black text-indigo-700">
            ₹{totalSpent.toLocaleString("en-IN")}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Inbound Leads</span>
            <Users className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="font-display text-2xl lg:text-3xl font-black text-emerald-600">
            {totalLeads.toLocaleString()}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Conversions</span>
            <Target className="w-4 h-4 text-amber-600" />
          </div>
          <div className="font-display text-2xl lg:text-3xl font-black text-amber-600">
            {totalConversions.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search campaigns..."
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-sky-500"
          />
        </div>
        <span className="text-xs text-slate-500 font-bold">Showing {filteredItems.length} active campaigns</span>
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sky-600" /> Launch Marketing Campaign
              </h3>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
            </div>

            <form onSubmit={submit} className="space-y-3">
              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Campaign Name *</label>
                <input required type="text" value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="e.g. Meta Ads: L-Acoustics K3 Touring Campaign" className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Type</label>
                  <select value={form.type} onChange={(e) => update("type", e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-sky-500">
                    {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Status</label>
                  <select value={form.status} onChange={(e) => update("status", e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-sky-500">
                    {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Budget (INR)</label>
                  <input type="number" value={form.budget} onChange={(e) => update("budget", e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Amount Spent (INR)</label>
                  <input type="number" value={form.spent} onChange={(e) => update("spent", e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Leads Generated</label>
                  <input type="number" value={form.leads} onChange={(e) => update("leads", e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Conversions</label>
                  <input type="number" value={form.conversions} onChange={(e) => update("conversions", e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500" />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500">Save Campaign</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Main Table */}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-100/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 font-bold">
              <tr>
                <th className="px-6 py-4 font-bold">Campaign Name</th>
                <th className="px-6 py-4 font-bold">Type</th>
                <th className="px-6 py-4 font-bold">Status</th>
                <th className="px-6 py-4 font-bold text-right">Budget (₹)</th>
                <th className="px-6 py-4 font-bold text-right">Spent (₹)</th>
                <th className="px-6 py-4 font-bold text-right">Leads</th>
                <th className="px-6 py-4 font-bold text-right">Conversions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-500 text-sm font-medium">Loading campaign data...</td></tr>
              ) : filteredItems.length === 0 ? (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-500 text-sm font-medium">No marketing campaigns found. Click "Create Campaign" or "Connect Meta Ads" to import.</td></tr>
              ) : (
                filteredItems.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-6 py-4 font-bold text-slate-900">{m.name}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold uppercase bg-sky-50 text-sky-700 border border-sky-200">
                        {m.type || "ads"}
                      </span>
                    </td>
                    <td className="px-6 py-4"><StatusBadge status={m.status} /></td>
                    <td className="px-6 py-4 text-right font-display font-extrabold text-slate-900">
                      {m.budget ? `₹${Number(m.budget).toLocaleString("en-IN")}` : "—"}
                    </td>
                    <td className="px-6 py-4 text-right font-display font-bold text-indigo-700">
                      {m.spent ? `₹${Number(m.spent).toLocaleString("en-IN")}` : "—"}
                    </td>
                    <td className="px-6 py-4 text-right font-bold text-emerald-600">
                      {m.leads || 0}
                    </td>
                    <td className="px-6 py-4 text-right font-bold text-slate-900">
                      {m.conversions || 0}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    draft: "bg-slate-100 text-slate-700 border-slate-200",
    active: "bg-emerald-50 text-emerald-700 border-emerald-200",
    paused: "bg-amber-50 text-amber-700 border-amber-200",
    completed: "bg-sky-50 text-sky-700 border-sky-200",
  };
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border capitalize ${map[status] || map.draft}`}>
      {status || "draft"}
    </span>
  );
}
