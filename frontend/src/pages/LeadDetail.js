import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { StageBadge, SourceBadge } from "@/components/badges";
import { useConfig } from "@/context/ConfigContext";
import {
  ArrowLeft,
  Mail,
  Phone,
  Building2,
  IndianRupee,
  Sparkles,
  Plus,
  Receipt,
  Trash2,
} from "lucide-react";

const ACT_TYPES = ["note", "call", "email", "whatsapp", "meeting", "follow_up", "sms", "video_call", "voice_note", "attachment"];

export default function LeadDetail() {
  const { id } = useParams();
  const { stageKeys: STAGES, stageLabels } = useConfig();
  const [lead, setLead] = useState(null);
  const [activities, setActivities] = useState([]);
  const [users, setUsers] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [newAct, setNewAct] = useState({ type: "note", content: "" });
  const [aiOutput, setAiOutput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [showQuote, setShowQuote] = useState(false);

  // BANT & Requirements Module States
  const [qualification, setQualification] = useState(null);
  const [requirements, setRequirements] = useState(null);
  const [qualForm, setQualForm] = useState({
    budget: "medium",
    authority: "influencer",
    need: "medium",
    timeline: "3_months",
    product_fit: "good",
    decision_maker: true,
    business_size: "mid_market",
    urgency: "medium"
  });
  const [reqForm, setReqForm] = useState({
    project_type: "",
    products_required: [],
    brands: [],
    quantities: "",
    site_location: "",
    special_requirements: "",
    budget: 0,
    competitors: "",
    timeline: "",
    technical_notes: ""
  });
  const [savingQual, setSavingQual] = useState(false);
  const [savingReq, setSavingReq] = useState(false);

  const load = async () => {
    const [l, a, u, q, qual, req] = await Promise.all([
      api.get(`/leads/${id}`),
      api.get(`/leads/${id}/activities`),
      api.get(`/users/roster`).catch(() => ({ data: [] })),
      api.get(`/quotations`, { params: { lead_id: id } }),
      api.get(`/leads/${id}/qualification`).catch(() => ({ data: [] })),
      api.get(`/leads/${id}/requirements`).catch(() => ({ data: [] }))
    ]);
    setLead(l.data);
    setActivities(a.data);
    setUsers(u.data);
    setQuotes(q.data);
    
    if (qual.data && qual.data.length > 0) {
      setQualification(qual.data[0]);
      setQualForm(qual.data[0]);
    }
    if (req.data && req.data.length > 0) {
      setRequirements(req.data[0]);
      setReqForm(req.data[0]);
    } else {
      // Set some initial blanks based on lead details
      setReqForm((prev) => ({
        ...prev,
        budget: l.data.budget || 0,
        site_location: l.data.city || ""
      }));
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, [id]);

  const updateField = async (patch) => {
    const r = await api.patch(`/leads/${id}`, patch);
    setLead(r.data);
    load();
  };

  const submitQual = async (e) => {
    e.preventDefault();
    setSavingQual(true);
    try {
      await api.post(`/leads/${id}/qualify`, qualForm);
      load();
    } catch (err) {
      alert("Qualify save failed: " + formatApiError(err));
    } finally {
      setSavingQual(false);
    }
  };

  const submitReq = async (e) => {
    e.preventDefault();
    setSavingReq(true);
    try {
      // make sure budget is float
      const payload = { ...reqForm };
      payload.budget = parseFloat(payload.budget) || 0;
      await api.post(`/leads/${id}/requirements`, payload);
      load();
    } catch (err) {
      alert("Requirements save failed: " + formatApiError(err));
    } finally {
      setSavingReq(false);
    }
  };

  const addActivity = async (e) => {
    e.preventDefault();
    if (!newAct.content.trim()) return;
    await api.post(`/leads/${id}/activities`, newAct);
    setNewAct({ type: "note", content: "" });
    load();
  };

  const runAi = async () => {
    setAiLoading(true);
    setAiOutput("");
    try {
      const r = await api.post(`/leads/${id}/ai-summary`);
      setAiOutput(r.data.summary);
    } catch (err) {
      setAiOutput("⚠ " + formatApiError(err));
    } finally {
      setAiLoading(false);
    }
  };

  if (!lead) return <div className="p-10 text-sm text-slate-500">Loading…</div>;

  const userName = (uid) => users.find((u) => u.id === uid)?.name || (uid ? uid.slice(0, 6) : "Unassigned");

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="lead-detail-page">
      <Link to="/leads" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to leads
      </Link>

      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-md p-6 mb-4">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="font-display text-3xl font-bold tracking-tighter text-slate-900" data-testid="lead-name">{lead.name}</h1>
              <StageBadge stage={lead.stage} />
              <SourceBadge source={lead.source} />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
              <InfoLine icon={Building2} label="Company" value={lead.company || "—"} />
              <InfoLine icon={Mail} label="Email" value={lead.email || "—"} />
              <InfoLine icon={Phone} label="Phone" value={lead.phone || "—"} />
              <InfoLine icon={IndianRupee} label="Budget" value={lead.budget ? `₹${Number(lead.budget).toLocaleString("en-IN")}` : "—"} />
            </div>
            {lead.interested_in && (
              <div className="mt-4 text-sm">
                <div className="label-eyebrow mb-1">Interested in</div>
                <div className="text-slate-800">{lead.interested_in}</div>
              </div>
            )}
            {lead.notes && (
              <div className="mt-4 text-sm">
                <div className="label-eyebrow mb-1">Notes</div>
                <div className="text-slate-700 whitespace-pre-line">{lead.notes}</div>
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="w-64 shrink-0 space-y-3">
            <div>
              <div className="label-eyebrow mb-1.5">Stage</div>
              <select
                data-testid="lead-stage-select"
                value={lead.stage}
                onChange={(e) => updateField({ stage: e.target.value })}
                className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 bg-white capitalize"
              >
                {STAGES.map((s) => <option key={s} value={s}>{stageLabels[s] || s}</option>)}
              </select>
            </div>
            <div>
              <div className="label-eyebrow mb-1.5">Assigned to</div>
              <select
                data-testid="lead-assign-select"
                value={lead.assigned_to || ""}
                onChange={(e) => updateField({ assigned_to: e.target.value || null })}
                className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 bg-white"
              >
                <option value="">Unassigned</option>
                {users.filter((u) => u.role !== "admin" || u.id === lead.assigned_to).map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </div>
            <button
              onClick={runAi}
              disabled={aiLoading}
              data-testid="ai-summary-btn"
              className="w-full inline-flex items-center justify-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors disabled:opacity-60"
            >
              <Sparkles className="w-4 h-4" /> {aiLoading ? "Thinking…" : "AI Next Action"}
            </button>
            <button
              onClick={() => setShowQuote(true)}
              data-testid="new-quote-btn"
              className="w-full inline-flex items-center justify-center gap-2 bg-white border border-slate-200 text-slate-900 px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-50"
            >
              <Receipt className="w-4 h-4" /> New Quotation
            </button>
          </div>
        </div>
      </div>

      {aiOutput && (
        <div className="bg-slate-900 text-white rounded-md p-5 mb-4 prose prose-invert prose-sm max-w-none" data-testid="ai-summary-output">
          <div className="flex items-center gap-2 label-eyebrow !text-white/70 mb-2">
            <Sparkles className="w-3.5 h-3.5" /> AI Coach
          </div>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-white/95">{aiOutput}</pre>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Activity */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-md p-6">
          <div className="label-eyebrow mb-1">Activity</div>
          <h2 className="font-display text-lg font-bold text-slate-900 mb-5">Timeline</h2>

          <form onSubmit={addActivity} className="flex gap-2 mb-5">
            <select value={newAct.type} onChange={(e) => setNewAct({ ...newAct, type: e.target.value })} className="border border-slate-200 rounded-md text-sm px-2 py-2 bg-white capitalize" data-testid="activity-type">
              {ACT_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
            </select>
            <input
              data-testid="activity-content"
              value={newAct.content}
              onChange={(e) => setNewAct({ ...newAct, content: e.target.value })}
              placeholder="What happened? (e.g., Called, asked for spec sheet)"
              className="flex-1 px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none"
            />
            <button type="submit" data-testid="activity-add-btn" className="bg-slate-900 text-white px-3 rounded-md text-sm hover:bg-slate-800 inline-flex items-center gap-1">
              <Plus className="w-4 h-4" /> Log
            </button>
          </form>

          <div className="relative border-l border-slate-200 ml-2.5">
            {activities.length === 0 && <div className="text-sm text-slate-500 ml-6 py-4">No activity yet.</div>}
            {activities.map((a) => (
              <div key={a.id} className="mb-5 ml-6 relative">
                <div className="absolute -left-[1.85rem] mt-1.5 h-2.5 w-2.5 rounded-full bg-slate-900 ring-4 ring-white" />
                <div className="flex items-baseline gap-2">
                  <span className="text-xs uppercase tracking-wider font-semibold text-slate-500">{a.type.replace("_", " ")}</span>
                  <span className="text-xs text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
                  <span className="text-xs text-slate-500">· {userName(a.user_id)}</span>
                </div>
                <div className="text-sm text-slate-800 mt-1">{a.content}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Lead Qualification & Requirement Discussion Module */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* BANT Qualification Scorecard */}
          <div className="bg-white border border-slate-200 rounded-md p-6 space-y-4">
            <div className="label-eyebrow">Enterprise Qualification</div>
            <h2 className="font-display text-lg font-bold text-slate-900">BANT Scoring & Classification</h2>
            
            <form onSubmit={submitQual} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="label-eyebrow block mb-1">Budget Allocation</label>
                  <select
                    value={qualForm.budget}
                    onChange={(e) => setQualForm({ ...qualForm, budget: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-2.5 py-1.5 bg-white font-medium"
                  >
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                    <option value="none">None</option>
                  </select>
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Decision Authority</label>
                  <select
                    value={qualForm.authority}
                    onChange={(e) => setQualForm({ ...qualForm, authority: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-2.5 py-1.5 bg-white font-medium"
                  >
                    <option value="decision_maker">Decision Maker</option>
                    <option value="influencer">Influencer</option>
                    <option value="end_user">End User</option>
                    <option value="gatekeeper">Gatekeeper</option>
                  </select>
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Need Urgency</label>
                  <select
                    value={qualForm.need}
                    onChange={(e) => setQualForm({ ...qualForm, need: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-2.5 py-1.5 bg-white font-medium"
                  >
                    <option value="urgent">Urgent</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                    <option value="none">None</option>
                  </select>
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Project Timeline</label>
                  <select
                    value={qualForm.timeline}
                    onChange={(e) => setQualForm({ ...qualForm, timeline: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-2.5 py-1.5 bg-white font-medium"
                  >
                    <option value="immediate">Immediate</option>
                    <option value="1_month">1 Month</option>
                    <option value="3_months">3 Months</option>
                    <option value="6_months">6 Months</option>
                    <option value="none">None</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="label-eyebrow block mb-1">Product Match</label>
                  <select
                    value={qualForm.product_fit}
                    onChange={(e) => setQualForm({ ...qualForm, product_fit: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-2.5 py-1.5 bg-white font-medium"
                  >
                    <option value="excellent">Excellent</option>
                    <option value="good">Good</option>
                    <option value="fair">Fair</option>
                    <option value="poor">Poor</option>
                  </select>
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Business Scale</label>
                  <select
                    value={qualForm.business_size}
                    onChange={(e) => setQualForm({ ...qualForm, business_size: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-2.5 py-1.5 bg-white font-medium"
                  >
                    <option value="enterprise">Enterprise</option>
                    <option value="mid_market">Mid Market</option>
                    <option value="smb">SMB</option>
                    <option value="startup">Startup</option>
                    <option value="individual">Individual</option>
                  </select>
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Urgency</label>
                  <select
                    value={qualForm.urgency}
                    onChange={(e) => setQualForm({ ...qualForm, urgency: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-2.5 py-1.5 bg-white font-medium"
                  >
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div className="flex items-end pb-1">
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700">
                    <input
                      type="checkbox"
                      checked={qualForm.decision_maker}
                      onChange={(e) => setQualForm({ ...qualForm, decision_maker: e.target.checked })}
                      className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                    />
                    Is Decision Maker
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-slate-100 pt-3">
                <div className="flex items-center gap-4 text-xs font-bold">
                  {qualification ? (
                    <>
                      <span className="text-slate-500">Qualification Score: <span className="text-slate-900 font-mono text-sm font-extrabold">{qualification.score}/100</span></span>
                      <span className="text-slate-500">Classification: <span className="text-sky-700 font-bold uppercase">{qualification.classification}</span></span>
                    </>
                  ) : (
                    <span className="text-slate-400">No score computed yet. Click evaluate.</span>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={savingQual}
                  className="bg-slate-900 text-white px-4 py-2 rounded-md text-xs font-bold hover:bg-slate-800 disabled:opacity-50"
                >
                  {savingQual ? "Evaluating..." : "Evaluate & Save"}
                </button>
              </div>
            </form>
          </div>

          {/* Requirement Discussion Module */}
          <div className="bg-white border border-slate-200 rounded-md p-6 space-y-4">
            <div className="label-eyebrow">Technical Planning</div>
            <h2 className="font-display text-lg font-bold text-slate-900">Requirement Discussions</h2>
            
            <form onSubmit={submitReq} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label-eyebrow block mb-1">Project Type</label>
                  <input
                    type="text"
                    value={reqForm.project_type || ""}
                    onChange={(e) => setReqForm({ ...reqForm, project_type: e.target.value })}
                    placeholder="e.g. Auditorium, Arena, Stadium, Hotel"
                    className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                  />
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Site / Installation Location</label>
                  <input
                    type="text"
                    value={reqForm.site_location || ""}
                    onChange={(e) => setReqForm({ ...reqForm, site_location: e.target.value })}
                    placeholder="e.g. Mumbai, Goa, Delhi"
                    className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label-eyebrow block mb-1">Custom Quantities & Spec Requests</label>
                  <input
                    type="text"
                    value={reqForm.quantities || ""}
                    onChange={(e) => setReqForm({ ...reqForm, quantities: e.target.value })}
                    placeholder="e.g. 12x Line Arrays, 4x Subwoofers"
                    className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                  />
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Estimated Budget Match (₹)</label>
                  <input
                    type="number"
                    value={reqForm.budget || ""}
                    onChange={(e) => setReqForm({ ...reqForm, budget: e.target.value })}
                    className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label-eyebrow block mb-1">Known Competitors</label>
                  <input
                    type="text"
                    value={reqForm.competitors || ""}
                    onChange={(e) => setReqForm({ ...reqForm, competitors: e.target.value })}
                    placeholder="e.g. SoundTech Pro"
                    className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                  />
                </div>
                <div>
                  <label className="label-eyebrow block mb-1">Target Timeline</label>
                  <input
                    type="text"
                    value={reqForm.timeline || ""}
                    onChange={(e) => setReqForm({ ...reqForm, timeline: e.target.value })}
                    placeholder="e.g. Immediate, Q3 Launch, Next month"
                    className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="label-eyebrow block mb-1">Special Requirements & Technical Brief</label>
                <textarea
                  rows={2}
                  value={reqForm.special_requirements || ""}
                  onChange={(e) => setReqForm({ ...reqForm, special_requirements: e.target.value })}
                  placeholder="e.g. Must support 148 dB SPL peak, outdoor waterproof arrays..."
                  className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                />
              </div>

              <div>
                <label className="label-eyebrow block mb-1">Acoustic / Technical Engineering Notes</label>
                <textarea
                  rows={2}
                  value={reqForm.technical_notes || ""}
                  onChange={(e) => setReqForm({ ...reqForm, technical_notes: e.target.value })}
                  placeholder="System notes for design engineers..."
                  className="w-full border border-slate-200 rounded-md text-xs px-3 py-2 focus:border-sky-500 outline-none"
                />
              </div>

              <div className="flex justify-end pt-2 border-t border-slate-100">
                <button
                  type="submit"
                  disabled={savingReq}
                  className="bg-slate-900 text-white px-4 py-2 rounded-md text-xs font-bold hover:bg-slate-800 disabled:opacity-50"
                >
                  {savingReq ? "Saving..." : "Save Discussions"}
                </button>
              </div>
            </form>
          </div>

        </div>

        {/* Quotations */}
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <div className="label-eyebrow mb-1">Deals</div>
          <h2 className="font-display text-lg font-bold text-slate-900 mb-4">Quotations</h2>
          {quotes.length === 0 && <div className="text-sm text-slate-500">No quotations yet.</div>}
          <div className="space-y-3">
            {quotes.map((q) => (
              <div key={q.id} className="border border-slate-200 rounded-md p-3 hover:border-slate-300" data-testid={`quote-${q.id}`}>
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-slate-900">{q.quote_no}</div>
                  <div className="text-xs uppercase tracking-wider text-slate-500">{q.status}</div>
                </div>
                <div className="font-display text-xl font-bold tracking-tight text-slate-900 mt-1">₹{Number(q.total).toLocaleString("en-IN")}</div>
                <div className="text-xs text-slate-500">{q.items.length} line items · {new Date(q.created_at).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showQuote && (
        <QuotationModal
          leadId={id}
          onClose={() => setShowQuote(false)}
          onSaved={() => {
            setShowQuote(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function InfoLine({ icon: Icon, label, value }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 label-eyebrow mb-1"><Icon className="w-3 h-3" />{label}</div>
      <div className="text-sm text-slate-800 truncate">{value}</div>
    </div>
  );
}

function QuotationModal({ leadId, onClose, onSaved }) {
  const [items, setItems] = useState([{ product: "", brand: "", qty: 1, unit_price: 0, tax_pct: 18 }]);
  const [terms, setTerms] = useState("Payment: 50% advance, 50% on delivery. Validity: 15 days.");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [products, setProducts] = useState([]);

  useEffect(() => {
    api.get("/products").then((r) => setProducts(r.data)).catch(() => {});
  }, []);

  const setItem = (i, k, v) =>
    setItems((arr) => arr.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));
  const pickProduct = (i, productId) => {
    const p = products.find((x) => x.id === productId);
    if (!p) return;
    setItems((arr) => arr.map((it, idx) => idx === i ? {
      ...it,
      product: p.model ? `${p.name} (${p.model})` : p.name,
      brand: p.brand,
      unit_price: p.unit_price,
    } : it));
  };
  const addLine = () => setItems((a) => [...a, { product: "", brand: "", qty: 1, unit_price: 0, tax_pct: 18 }]);
  const removeLine = (i) => setItems((a) => a.filter((_, idx) => idx !== i));

  const subtotal = items.reduce((s, i) => s + Number(i.qty || 0) * Number(i.unit_price || 0), 0);
  const tax = items.reduce((s, i) => s + Number(i.qty || 0) * Number(i.unit_price || 0) * (Number(i.tax_pct || 0) / 100), 0);
  const total = subtotal + tax;

  const submit = async () => {
    setErr("");
    setSaving(true);
    try {
      const payload = {
        lead_id: leadId,
        items: items.map((i) => ({
          product: i.product,
          brand: i.brand || null,
          qty: Number(i.qty),
          unit_price: Number(i.unit_price),
          tax_pct: Number(i.tax_pct),
        })),
        terms,
      };
      await api.post("/quotations", payload);
      onSaved();
    } catch (e) {
      setErr(formatApiError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="quote-modal">
      <div className="bg-white rounded-md border border-slate-200 max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="font-display text-xl font-bold text-slate-900">New Quotation</div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-900" data-testid="quote-close">✕</button>
        </div>
        <div className="p-6 space-y-3">
          {products.length > 0 && (
            <div className="text-xs text-slate-500 -mb-1">Tip: pick a catalog item to auto-fill product, brand & price.</div>
          )}
          {items.map((it, i) => (
            <div key={i} className="space-y-2 pb-2 border-b border-slate-100 last:border-0">
              {products.length > 0 && (
                <CatalogPicker
                  products={products}
                  onPick={(productId) => pickProduct(i, productId)}
                  testid={`q-catalog-${i}`}
                />
              )}
              <div className="grid grid-cols-12 gap-2 items-end">
              <div className="col-span-4">
                <label className="label-eyebrow block mb-1">Product</label>
                <input data-testid={`q-product-${i}`} className="w-full border border-slate-200 rounded-md text-sm px-2 py-1.5" value={it.product} onChange={(e) => setItem(i, "product", e.target.value)} />
              </div>
              <div className="col-span-2">
                <label className="label-eyebrow block mb-1">Brand</label>
                <input className="w-full border border-slate-200 rounded-md text-sm px-2 py-1.5" value={it.brand} onChange={(e) => setItem(i, "brand", e.target.value)} />
              </div>
              <div className="col-span-1">
                <label className="label-eyebrow block mb-1">Qty</label>
                <input type="number" className="w-full border border-slate-200 rounded-md text-sm px-2 py-1.5" value={it.qty} onChange={(e) => setItem(i, "qty", e.target.value)} />
              </div>
              <div className="col-span-2">
                <label className="label-eyebrow block mb-1">Unit ₹</label>
                <input data-testid={`q-price-${i}`} type="number" className="w-full border border-slate-200 rounded-md text-sm px-2 py-1.5" value={it.unit_price} onChange={(e) => setItem(i, "unit_price", e.target.value)} />
              </div>
              <div className="col-span-2">
                <label className="label-eyebrow block mb-1">GST %</label>
                <input type="number" className="w-full border border-slate-200 rounded-md text-sm px-2 py-1.5" value={it.tax_pct} onChange={(e) => setItem(i, "tax_pct", e.target.value)} />
              </div>
              <div className="col-span-1">
                <button onClick={() => removeLine(i)} className="text-slate-400 hover:text-red-600 p-1.5">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              </div>
            </div>
          ))}
          <button onClick={addLine} className="text-sm text-slate-700 hover:text-slate-900 inline-flex items-center gap-1" data-testid="q-add-line">
            <Plus className="w-4 h-4" /> Add line
          </button>

          <div>
            <label className="label-eyebrow block mb-1 mt-3">Terms</label>
            <textarea value={terms} onChange={(e) => setTerms(e.target.value)} rows={2} className="w-full border border-slate-200 rounded-md text-sm px-2 py-1.5" />
          </div>

          <div className="border-t border-slate-200 pt-4 flex justify-end gap-8 text-sm">
            <div className="space-y-1 text-slate-600">
              <div>Subtotal</div><div>GST</div><div className="font-bold text-slate-900 text-base">Total</div>
            </div>
            <div className="space-y-1 text-right">
              <div>₹{subtotal.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</div>
              <div>₹{tax.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</div>
              <div className="font-display font-bold text-slate-900 text-base">₹{total.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</div>
            </div>
          </div>

          {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">{err}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
            <button onClick={submit} disabled={saving} data-testid="q-submit" className="bg-slate-900 text-white px-4 py-2 rounded-md text-sm hover:bg-slate-800 disabled:opacity-60">
              {saving ? "Saving…" : "Create quotation"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


function CatalogPicker({ products, onPick, testid }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onDocClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const needle = q.trim().toLowerCase();
  const filtered = !needle
    ? products.slice(0, 50)
    : products.filter((p) => {
        const hay = `${p.brand} ${p.name} ${p.model || ""} ${p.category || ""}`.toLowerCase();
        return hay.includes(needle);
      }).slice(0, 50);

  return (
    <div className="relative" ref={ref}>
      <input
        data-testid={testid}
        value={q}
        onFocus={() => setOpen(true)}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        placeholder={`Search catalog (${products.length} products)…`}
        className="w-full border border-slate-200 rounded-md text-sm px-3 py-1.5 bg-slate-50 focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none"
      />
      {open && filtered.length > 0 && (
        <div className="absolute z-20 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-72 overflow-y-auto" data-testid={`${testid}-list`}>
          {filtered.map((p) => {
            const label = `${p.brand} · ${p.name}${p.model ? ` (${p.model})` : ""}`;
            return (
              <button
                key={p.id}
                type="button"
                data-testid={`${testid}-item-${p.id}`}
                onClick={() => {
                  onPick(p.id);
                  setQ("");
                  setOpen(false);
                }}
                className="w-full text-left px-3 py-2 hover:bg-slate-50 border-b border-slate-100 last:border-0 text-sm flex items-center justify-between gap-3"
              >
                <span className="truncate text-slate-800">{label}</span>
                <span className="shrink-0 font-semibold text-slate-900">₹{Number(p.unit_price).toLocaleString("en-IN")}</span>
              </button>
            );
          })}
          {q.trim() && products.length > 50 && filtered.length === 50 && (
            <div className="px-3 py-2 text-xs text-slate-500 bg-slate-50 border-t border-slate-100">Showing first 50 matches — refine your search…</div>
          )}
        </div>
      )}
      {open && filtered.length === 0 && (
        <div className="absolute z-20 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg px-3 py-3 text-sm text-slate-500">
          No matches for "{q}"
        </div>
      )}
    </div>
  );
}
