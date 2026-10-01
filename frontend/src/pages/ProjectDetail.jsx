import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, Users, FileText, CheckSquare, Paperclip, Plug, Activity,
  Plus, Trash2, Loader2, AlertCircle, Receipt, Contact,
} from "lucide-react";
import { api } from "@/lib/api";
import { useConfig } from "@/context/ConfigContext";

const money = (n) =>
  "\u20b9" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

const TABS = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "tasks", label: "Tasks", icon: CheckSquare },
  { id: "quotations", label: "Quotations", icon: Receipt },
  { id: "purchase_orders", label: "POs", icon: FileText },
  { id: "contacts", label: "Contacts", icon: Contact },
  { id: "documents", label: "Documents", icon: Paperclip },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "activity", label: "Activity", icon: Activity },
];

const card = "bg-white rounded-xl border border-slate-200 p-4";
const input = "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none";

function Empty({ children }) {
  return <p className="text-sm text-slate-400 py-6 text-center">{children}</p>;
}

export default function ProjectDetail() {
  const { id } = useParams();
const { config } = useConfig();
  const [tab, setTab] = useState("overview");
  const [project, setProject] = useState(null);
  const [related, setRelated] = useState(null);
  const [integrations, setIntegrations] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [detail, rel, acts] = await Promise.all([
        api.get(`/projects/${id}`),
        api.get(`/projects/${id}/related`),
        api.get(`/projects/${id}/activity`),
      ]);
      setProject(detail.data);
      setRelated(rel.data);
      setActivity(acts.data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Could not load this project");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { setLoading(true); load(); }, [load]);

  const loadIntegrations = useCallback(async () => {
    try {
      const { data } = await api.get(`/projects/${id}/integrations`);
      setIntegrations(data);
    } catch { setIntegrations(null); }
  }, [id]);

  useEffect(() => { if (tab === "integrations") loadIntegrations(); }, [tab, loadIntegrations]);

  const act = async (fn) => {
    setBusy(true);
    try { await fn(); await load(); } finally { setBusy(false); }
  };

  // useConfig() exposes the raw config map keyed by set name (no .get()). Project
  // stages live in the `project_stages` set; tolerate both the wrapped {items:[...]}
  // shape and a bare array so a config outage degrades to "no dropdown" rather than
  // a crash.
  const rawStages = config?.project_stages;
  const stageOptions = (Array.isArray(rawStages) ? rawStages : rawStages?.items || [])
    .filter((s) => s && s.id && s.is_active !== false)
    .map((s) => ({ id: s.id, label: s.label || s.id }));

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50" data-testid="project-loading">
        <Loader2 className="w-6 h-6 animate-spin text-sky-600" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6" data-testid="project-error">
        <div className="text-center">
          <AlertCircle className="w-10 h-10 mx-auto text-rose-400 mb-3" />
          <p className="text-slate-600">{error}</p>
          <Link to="/projects" className="inline-block mt-4 text-sm font-bold text-sky-600">Back to projects</Link>
        </div>
      </div>
    );
  }

  const counts = project.counts || {};

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen"
      data-testid="project-detail">

      <Link to="/projects" className="inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-sky-600">
        <ArrowLeft className="w-3.5 h-3.5" /> All projects
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="font-mono text-xs font-bold text-slate-400">{project.project_no}</div>
          <h1 className="text-2xl font-bold text-slate-900" data-testid="project-name">{project.name}</h1>
          <p className="text-sm text-slate-500">
            {project.client || "No client"} &middot; Budget {money(project.budget)}
          </p>
        </div>
        {stageOptions.length ? (
          <select
            className={input + " w-auto"}
            value={project.stage_id || ""}
            disabled={busy}
            onChange={(e) => act(() => api.patch(`/projects/${id}/stage`, { stage_id: e.target.value }))}
            data-testid="project-stage-select"
          >
            <option value="">No stage</option>
            {stageOptions.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        ) : null}
      </header>

      <nav className="flex flex-wrap gap-1 border-b border-slate-200" role="tablist">
        {TABS.map(({ id: tid, label, icon: Icon }) => (
          <button
            key={tid}
            role="tab"
            aria-selected={tab === tid}
            onClick={() => setTab(tid)}
            className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-2 border-b-2 -mb-px transition-colors ${
              tab === tid ? "border-sky-600 text-sky-700" : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
            data-testid={`project-tab-${tid}`}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
            {tid !== "overview" && tid !== "activity" && counts[tid] != null ? (
              <span className="ml-0.5 rounded-full bg-slate-100 px-1.5 text-[10px]">{counts[tid]}</span>
            ) : null}
          </button>
        ))}
      </nav>

      {tab === "overview" ? <Overview project={project} related={related} /> : null}
      {tab === "tasks" ? <Tasks projectId={id} tasks={related?.tasks || []} onChange={load} /> : null}
      {tab === "quotations" ? <Quotes rows={related?.quotations || []} /> : null}
      {tab === "purchase_orders" ? <POs rows={related?.purchase_orders || []} /> : null}
      {tab === "contacts" ? <Contacts projectId={id} rows={related?.contacts || []} onChange={load} /> : null}
      {tab === "documents" ? <Documents projectId={id} rows={related?.documents || []} onChange={load} /> : null}
      {tab === "integrations" ? <Integrations data={integrations} projectId={id} onChange={loadIntegrations} /> : null}
      {tab === "activity" ? <Timeline rows={activity} /> : null}
    </div>
  );
}

function Overview({ project, related }) {
  const history = project.stage_history || [];
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className={card}>
        <h2 className="text-sm font-bold text-slate-700 mb-3">Details</h2>
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-slate-500">Status</dt><dd className="font-semibold">{project.status || "\u2014"}</dd>
          <dt className="text-slate-500">Start</dt><dd>{project.start_date || "\u2014"}</dd>
          <dt className="text-slate-500">Target</dt><dd>{project.target_date || project.end_date || "\u2014"}</dd>
          <dt className="text-slate-500">Created</dt>
          <dd>{project.created_at ? new Date(project.created_at).toLocaleDateString("en-IN") : "\u2014"}</dd>
        </dl>
      </div>
      <div className={card}>
        <h2 className="text-sm font-bold text-slate-700 mb-3">Stage history</h2>
        {history.length === 0 ? <Empty>No stage changes yet.</Empty> : (
          <ol className="space-y-2">
            {history.map((h, i) => (
              <li key={i} className="text-sm border-l-2 border-sky-200 pl-3">
                <div className="font-semibold text-slate-800">{h.from_stage || "new"} &rarr; {h.to_stage}</div>
                <div className="text-xs text-slate-500">
                  {h.changed_by_name || h.changed_by} &middot;{" "}
                  {h.changed_at ? new Date(h.changed_at).toLocaleString("en-IN") : ""}
                </div>
                {h.note ? <div className="text-xs text-slate-600 italic">{h.note}</div> : null}
              </li>
            ))}
          </ol>
        )}
      </div>
      <div className={card}>
        <h2 className="text-sm font-bold text-slate-700 mb-2">Client</h2>
        {related?.lead ? (
          <Link to={`/leads/${related.lead.id}`} className="text-sm font-semibold text-sky-700 hover:underline">
            {related.lead.name} {related.lead.company ? `(${related.lead.company})` : ""}
          </Link>
        ) : <Empty>No linked lead.</Empty>}
      </div>
    </div>
  );
}

function Tasks({ projectId, tasks, onChange }) {
  const [title, setTitle] = useState("");
  const add = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    await api.post("/tasks", { title: title.trim(), project_id: projectId, status: "pending" });
    setTitle("");
    onChange();
  };
  return (
    <div className="space-y-3">
      <form onSubmit={add} className="flex gap-2">
        <input className={input} value={title} onChange={(e) => setTitle(e.target.value)}
          placeholder="Add a task" data-testid="project-task-input" />
        <button className="inline-flex items-center gap-1 rounded-lg bg-sky-600 px-3 py-2 text-sm font-bold text-white hover:bg-sky-500"
          data-testid="project-task-add">
          <Plus className="w-4 h-4" /> Add
        </button>
      </form>
      {tasks.length === 0 ? <Empty>No tasks on this project yet.</Empty> : (
        <ul className="space-y-2" data-testid="project-task-list">
          {tasks.map((t) => (
            <li key={t.id} className={`${card} flex items-center justify-between gap-3 py-3`}>
              <div>
                <div className="text-sm font-semibold text-slate-800">{t.title}</div>
                <div className="text-xs text-slate-500">
                  {t.priority} &middot; {t.status}
                  {t.due_date ? ` \u00b7 due ${t.due_date}` : ""}
                </div>
              </div>
              <button onClick={() => api.delete(`/tasks/${t.id}`).then(onChange)}
                className="text-rose-600 hover:text-rose-700" aria-label={`Delete ${t.title}`}>
                <Trash2 className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Quotes({ rows }) {
  if (!rows.length) return <Empty>No quotations linked.</Empty>;
  return (
    <ul className="space-y-2">
      {rows.map((q) => (
        <li key={q.id} className={`${card} flex items-center justify-between`}>
          <div>
            <span className="font-mono text-sm font-bold">{q.quote_no}</span>
            <span className="ml-2 text-sm text-slate-500">{q.status}</span>
          </div>
          <span className="font-bold">{money(q.total)}</span>
        </li>
      ))}
    </ul>
  );
}

function POs({ rows }) {
  if (!rows.length) return <Empty>No purchase orders.</Empty>;
  return (
    <ul className="space-y-2">
      {rows.map((p) => (
        <li key={p.id} className={`${card} flex items-center justify-between`}>
          <div>
            <span className="font-mono text-sm font-bold">{p.po_no}</span>
            <span className="ml-2 text-xs uppercase text-slate-500">{p.direction}</span>
            <span className="ml-2 text-sm text-slate-500">{p.status}</span>
          </div>
          <span className="font-bold">{money(p.total)}</span>
        </li>
      ))}
    </ul>
  );
}

function Contacts({ projectId, rows, onChange }) {
  const [form, setForm] = useState({ name: "", contact_type: "", phone: "" });
  const add = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    await api.post(`/projects/${projectId}/contacts`, {
      name: form.name.trim(),
      contact_type: form.contact_type || undefined,
      phone: form.phone || undefined,
    });
    setForm({ name: "", contact_type: "", phone: "" });
    onChange();
  };
  return (
    <div className="space-y-3">
      <form onSubmit={add} className="grid gap-2 sm:grid-cols-3">
        <input className={input} placeholder="Name" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="project-contact-name" />
        <input className={input} placeholder="Role / type" value={form.contact_type}
          onChange={(e) => setForm({ ...form, contact_type: e.target.value })} />
        <input className={input} placeholder="Phone" value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <button className="inline-flex items-center justify-center gap-1 rounded-lg bg-sky-600 px-3 py-2 text-sm font-bold text-white hover:bg-sky-500 sm:col-span-3"
          data-testid="project-contact-add">
          <Users className="w-4 h-4" /> Add contact
        </button>
      </form>
      {rows.length === 0 ? <Empty>No contacts yet.</Empty> : (
        <ul className="space-y-2" data-testid="project-contact-list">
          {rows.map((c) => (
            <li key={c.id} className={`${card} flex items-center justify-between py-3`}>
              <div>
                <div className="text-sm font-semibold">{c.name}</div>
                <div className="text-xs text-slate-500">
                  {[c.contact_type, c.company, c.phone].filter(Boolean).join(" \u00b7 ")}
                </div>
              </div>
              <button onClick={() => api.delete(`/projects/${projectId}/contacts/${c.id}`).then(onChange)}
                className="text-rose-600" aria-label={`Delete ${c.name}`}>
                <Trash2 className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Documents({ projectId, rows, onChange }) {
  const [form, setForm] = useState({ name: "", url: "" });
  const add = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.url.trim()) return;
    await api.post(`/projects/${projectId}/documents`, { name: form.name.trim(), url: form.url.trim() });
    setForm({ name: "", url: "" });
    onChange();
  };
  return (
    <div className="space-y-3">
      <form onSubmit={add} className="grid gap-2 sm:grid-cols-3">
        <input className={input} placeholder="Document name" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="project-doc-name" />
        <input className={input} placeholder="URL" value={form.url}
          onChange={(e) => setForm({ ...form, url: e.target.value })} data-testid="project-doc-url" />
        <button className="inline-flex items-center justify-center gap-1 rounded-lg bg-sky-600 px-3 py-2 text-sm font-bold text-white hover:bg-sky-500"
          data-testid="project-doc-add">
          <Plus className="w-4 h-4" /> Add
        </button>
      </form>
      {rows.length === 0 ? <Empty>No documents.</Empty> : (
        <ul className="space-y-2" data-testid="project-doc-list">
          {rows.map((d) => (
            <li key={d.id} className={`${card} flex items-center justify-between py-3`}>
              <a href={d.url} target="_blank" rel="noreferrer"
                className="text-sm font-semibold text-sky-700 hover:underline">{d.name}</a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Integrations({ data, projectId, onChange }) {
  if (!data) return <Empty>Loading integrations...</Empty>;
  const grouped = data.available.reduce((acc, i) => {
    (acc[i.category] ||= []).push(i);
    return acc;
  }, {});
  return (
    <div className="space-y-4" data-testid="project-integrations">
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} className={card}>
          <h2 className="text-xs font-bold uppercase tracking-wide text-slate-400 mb-2">{category}</h2>
          <ul className="space-y-2">
            {items.map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-800">
                    {i.label}
                    {i.in_use ? <span className="ml-2 text-[10px] font-bold text-emerald-700">in use</span> : null}
                  </div>
                  <div className="text-xs text-slate-500">{i.description}</div>
                </div>
                <button
                  onClick={() => api.post(`/projects/${projectId}/integrations/${i.id}`).then(onChange)}
                  className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-bold ${
                    i.in_use ? "bg-emerald-600 text-white hover:bg-emerald-500"
                             : "bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200"
                  }`}
                  data-testid={`project-integration-${i.id}`}
                >
                  {i.in_use ? "Attached" : "Attach"}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function Timeline({ rows }) {
  if (!rows.length) return <Empty>No activity recorded.</Empty>;
  return (
    <ol className="space-y-2" data-testid="project-activity">
      {rows.map((a) => (
        <li key={a.id} className={`${card} py-3`}>
          <div className="text-sm text-slate-800">{a.content}</div>
          <div className="text-xs text-slate-500">
            {a.type} &middot; {a.created_at ? new Date(a.created_at).toLocaleString("en-IN") : ""}
          </div>
        </li>
      ))}
    </ol>
  );
}