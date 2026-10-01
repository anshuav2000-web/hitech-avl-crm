import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  Plus, Share2, Calendar, Eye, Heart, MessageSquare, Clock, CheckCircle2,
  X, Filter, Search, Sparkles, Image, Globe, Send, Trash2, Facebook, Instagram, RefreshCw, Unplug
} from "lucide-react";

const PLATFORMS = ["linkedin", "instagram", "facebook", "twitter", "youtube"];
const SOCIAL_STATUSES = ["draft", "scheduled", "published"];

export default function SocialMedia() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [platformFilter, setPlatformFilter] = useState("all");

  const [metaStatus, setMetaStatus] = useState({ connected: false });
  const [metaLoading, setMetaLoading] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    platform: "facebook",
    title: "",
    content: "",
    status: "draft",
    scheduled_at: "",
    media_url: "",
    views: 0,
    engagement: 0
  });

  const load = async () => {
    setLoading(true);
    try {
      const [socialRes, metaRes] = await Promise.all([
        api.get("/social"),
        api.get("/meta/status").catch(() => ({ data: { connected: false } }))
      ]);
      setItems(socialRes.data || []);
      setMetaStatus(metaRes.data || { connected: false });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const connectMeta = async () => {
    setMetaLoading(true);
    try {
      const res = await api.post("/meta/connect", {
        account_name: "Hitech Audio & Lighting Official",
        account_id: "act_10482938102938"
      });
      setMetaStatus(res.data);
      await load();
      alert("Meta Facebook & Instagram Business Suite Connected Successfully!");
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
      const r = await api.post("/social", {
        ...form,
        views: Number(form.views || 0),
        engagement: Number(form.engagement || 0)
      });
      setItems((prev) => [r.data, ...prev]);
      setShowForm(false);
      setForm({
        platform: "facebook",
        title: "",
        content: "",
        status: "draft",
        scheduled_at: "",
        media_url: "",
        views: 0,
        engagement: 0
      });
    } catch (err) {
      alert(formatApiError(err));
    }
  };

  const deletePost = async (id) => {
    if (!window.confirm("Are you sure you want to delete this social post?")) return;
    try {
      await api.delete(`/social/${id}`);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      alert(formatApiError(err));
    }
  };

  const filteredItems = useMemo(() => {
    let list = items;
    if (platformFilter !== "all") {
      list = list.filter((i) => (i.platform || "").toLowerCase() === platformFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((i) =>
        `${i.title} ${i.content || ""} ${i.platform}`.toLowerCase().includes(q)
      );
    }
    return list;
  }, [items, platformFilter, search]);

  const totalViews = items.reduce((s, i) => s + Number(i.views || 0), 0);
  const scheduledCount = items.filter((i) => i.status === "scheduled").length;
  const publishedCount = items.filter((i) => i.status === "published").length;

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="social-media-page">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Digital Marketing & PR</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Share2 className="w-8 h-8 text-sky-600" /> Social Media Command Center
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Manage concert launches, manufacturer brand announcements, and Meta Facebook & Instagram campaigns.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowForm(true)}
            data-testid="social-media-add-btn"
            className="inline-flex items-center gap-2 bg-sky-600 text-white px-5 py-2.5 rounded-xl text-xs font-bold hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" /> Create Social Post
          </button>
        </div>
      </header>

      {/* Meta Facebook Connection Banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold shrink-0 shadow-md shadow-blue-500/20">
            <Facebook className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display text-base font-bold text-slate-900">Meta Business Suite & Facebook Dashboard</h3>
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
                ? `Active Account: ${metaStatus.account_name || "Hitech Audio Official"} (${metaStatus.connected_page})`
                : "Connect your Facebook Page & Instagram Business account to sync posts and live engagement metrics."}
            </p>
          </div>
        </div>

        <div>
          {metaStatus.connected ? (
            <button
              onClick={disconnectMeta}
              disabled={metaLoading}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 transition-all cursor-pointer"
            >
              <Unplug className="w-3.5 h-3.5" /> Disconnect Meta
            </button>
          ) : (
            <button
              onClick={connectMeta}
              disabled={metaLoading}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 shadow-md shadow-blue-600/20 transition-all cursor-pointer"
            >
              <Facebook className="w-4 h-4" />
              {metaLoading ? "Connecting Meta..." : "Connect Meta Facebook Suite"}
            </button>
          )}
        </div>
      </div>

      {/* Analytics KPI Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Total Posts</span>
            <Share2 className="w-4 h-4 text-sky-600" />
          </div>
          <div className="font-display text-3xl font-black text-slate-900">{items.length}</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Scheduled</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="font-display text-3xl font-black text-amber-600">{scheduledCount}</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Published</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="font-display text-3xl font-black text-emerald-600">{publishedCount}</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            <span>Total Impressions</span>
            <Eye className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="font-display text-3xl font-black text-sky-700">{totalViews.toLocaleString()}</div>
        </div>
      </div>

      {/* Platform Filter Tabs & Search */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex gap-2 overflow-x-auto no-scrollbar w-full md:w-auto">
          <button
            onClick={() => setPlatformFilter("all")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all border ${
              platformFilter === "all"
                ? "bg-slate-900 text-white border-slate-900 shadow-xs"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
            }`}
          >
            All Channels
          </button>
          {PLATFORMS.map((p) => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all border capitalize ${
                platformFilter === p
                  ? "bg-sky-600 text-white border-sky-600 shadow-xs"
                  : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search social posts..."
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-900 font-medium placeholder:text-slate-400 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>

      {/* Create Post Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-xl p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sky-600" /> Compose Social Campaign Post
              </h3>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
            </div>

            <form onSubmit={submit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Target Platform</label>
                  <select
                    value={form.platform}
                    onChange={(e) => update("platform", e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 capitalize focus:outline-none focus:border-sky-500"
                  >
                    {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Status</label>
                  <select
                    value={form.status}
                    onChange={(e) => update("status", e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 capitalize focus:outline-none focus:border-sky-500"
                  >
                    {SOCIAL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Campaign Headline / Title *</label>
                <input
                  required
                  type="text"
                  value={form.title}
                  onChange={(e) => update("title", e.target.value)}
                  placeholder="e.g. L-Acoustics K2 Touring System Product Launch"
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Post Content & Copy</label>
                <textarea
                  rows={3}
                  value={form.content}
                  onChange={(e) => update("content", e.target.value)}
                  placeholder="Write post copy, hashtags (#hitechavl #soundvision)..."
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Scheduled Date & Time</label>
                  <input
                    type="datetime-local"
                    value={form.scheduled_at}
                    onChange={(e) => update("scheduled_at", e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-900 font-medium focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Media Banner URL</label>
                  <input
                    type="url"
                    value={form.media_url}
                    onChange={(e) => update("media_url", e.target.value)}
                    placeholder="https://..."
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-900 font-medium focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500">Save Post</button>
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
                <th className="px-6 py-4 font-bold">Headline / Campaign Title</th>
                <th className="px-6 py-4 font-bold">Channel</th>
                <th className="px-6 py-4 font-bold">Status</th>
                <th className="px-6 py-4 font-bold">Scheduled / Launch Time</th>
                <th className="px-6 py-4 font-bold text-right">Views / Reach</th>
                <th className="px-6 py-4 font-bold text-right">Engagement</th>
                <th className="px-6 py-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-500 text-sm font-medium">Loading social campaign data...</td></tr>
              ) : filteredItems.length === 0 ? (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-500 text-sm font-medium">No social media posts found. Click "Create Social Post" to start a campaign.</td></tr>
              ) : (
                filteredItems.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-bold text-slate-900">{s.title}</div>
                      {s.content && <div className="text-xs text-slate-500 truncate max-w-md mt-0.5">{s.content}</div>}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase bg-sky-50 text-sky-700 border border-sky-200">
                        {s.platform || "LinkedIn"}
                      </span>
                    </td>
                    <td className="px-6 py-4"><StatusBadge status={s.status} /></td>
                    <td className="px-6 py-4 text-xs font-mono text-slate-600">
                      {s.scheduled_at ? new Date(s.scheduled_at).toLocaleString() : "Immediate"}
                    </td>
                    <td className="px-6 py-4 text-right font-display font-bold text-slate-900">
                      {Number(s.views || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right font-display font-bold text-slate-900">
                      {Number(s.engagement || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {isAdmin && (
                        <button
                          onClick={() => deletePost(s.id)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                          title="Delete post"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
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
    scheduled: "bg-amber-50 text-amber-700 border-amber-200",
    published: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border capitalize ${map[status] || map.draft}`}>
      {status || "draft"}
    </span>
  );
}
