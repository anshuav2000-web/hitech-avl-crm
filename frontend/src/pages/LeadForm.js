import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { ArrowLeft, Save } from "lucide-react";
import { Link } from "react-router-dom";

const SOURCES = [
  "direct_enquiry", "facebook", "instagram", "linkedin", "website_contact_form",
  "cold_call", "business_whatsapp", "email", "channel_partner", "internal_employee_referral",
  "existing_customer", "walk_in_customer"
];

export default function LeadForm() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    company: "",
    source: "direct_enquiry",
    interested_in: "",
    budget: "",
    city: "",
    state: "",
    country: "India",
    product_interest: "",
    business_type: "",
    industry: "",
    requirements: "",
    priority: "medium",
    lead_score: 10,
    assigned_to: "",
    notes: ""
  });

  useEffect(() => {
    api.get("/users/roster").then((r) => setUsers(r.data || []));
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const payload = { ...form };
      if (!payload.email) delete payload.email;
      if (!payload.assigned_to) delete payload.assigned_to;
      if (payload.budget) payload.budget = parseFloat(payload.budget); else delete payload.budget;
      if (payload.lead_score) payload.lead_score = parseInt(payload.lead_score); else delete payload.lead_score;
      const r = await api.post("/leads", payload);
      navigate(`/leads/${r.data.id}`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="lead-form-page">
      <Link to="/leads" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to leads
      </Link>
      <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900 mb-1">New lead</h1>
      <p className="text-sm text-slate-600 mb-8">Capture a prospect manually. Every field integrates automatically with our Enterprise ERP pipeline.</p>

      <form onSubmit={submit} className="bg-white border border-slate-200 rounded-md p-6 space-y-5">
        <h2 className="font-display text-lg font-bold border-b border-slate-100 pb-2">Client Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Field label="Name *" name="name" value={form.name} onChange={(v) => update("name", v)} required testid="lf-name" />
          <Field label="Company / Venue Name" name="company" value={form.company} onChange={(v) => update("company", v)} testid="lf-company" />
          <Field label="Email" type="email" name="email" value={form.email} onChange={(v) => update("email", v)} testid="lf-email" />
          <Field label="Phone / WhatsApp" name="phone" value={form.phone} onChange={(v) => update("phone", v)} testid="lf-phone" />
        </div>

        <h2 className="font-display text-lg font-bold border-b border-slate-100 pb-2 pt-4">Location & Source</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <Field label="City" name="city" value={form.city} onChange={(v) => update("city", v)} />
          <Field label="State" name="state" value={form.state} onChange={(v) => update("state", v)} />
          <Field label="Country" name="country" value={form.country} onChange={(v) => update("country", v)} />
          <Select label="Lead Source" value={form.source} onChange={(v) => update("source", v)} options={SOURCES} testid="lf-source" />
          <Select label="Priority" value={form.priority} onChange={(v) => update("priority", v)} options={["low", "medium", "high", "urgent"]} />
          <Field label="Lead Score (Initial)" type="number" name="lead_score" value={form.lead_score} onChange={(v) => update("lead_score", v)} />
        </div>

        <h2 className="font-display text-lg font-bold border-b border-slate-100 pb-2 pt-4">Business Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Field label="Product Category Interest" name="product_interest" value={form.product_interest} onChange={(v) => update("product_interest", v)} />
          <Field label="Brand Focus" name="interested_in" value={form.interested_in} onChange={(v) => update("interested_in", v)} testid="lf-interest" />
          <Field label="Business Type" name="business_type" value={form.business_type} onChange={(v) => update("business_type", v)} placeholder="e.g. System Integrator, Dealer, Live Rental" />
          <Field label="Industry Sector" name="industry" value={form.industry} onChange={(v) => update("industry", v)} placeholder="e.g. Hospitality, Entertainment, Education" />
          <Field label="Estimated Budget (₹)" type="number" name="budget" value={form.budget} onChange={(v) => update("budget", v)} testid="lf-budget" />
          <Select label="Assign to Sales Representative" value={form.assigned_to} onChange={(v) => update("assigned_to", v)} options={[{ value: "", label: "— Auto assign —" }, ...users.map((u) => ({ value: u.id, label: u.name }))]} testid="lf-assign" />
        </div>

        <div>
          <label className="label-eyebrow block mb-2">Requirements Brief</label>
          <textarea
            value={form.requirements}
            onChange={(e) => update("requirements", e.target.value)}
            rows={3}
            placeholder="Describe technical requirements, quantities, site location specifics..."
            className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none"
          />
        </div>

        <div>
          <label className="label-eyebrow block mb-2">Internal General Notes</label>
          <textarea
            data-testid="lf-notes"
            value={form.notes}
            onChange={(e) => update("notes", e.target.value)}
            rows={3}
            placeholder="Add general notes..."
            className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none"
          />
        </div>

        {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">{error}</div>}
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Link to="/leads" className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</Link>
          <button type="submit" disabled={saving} data-testid="lf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800 disabled:opacity-60">
            <Save className="w-4 h-4" /> {saving ? "Saving…" : "Create lead"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required, testid }) {
  return (
    <div>
      <label className="label-eyebrow block mb-2">{label}</label>
      <input
        data-testid={testid}
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none"
      />
    </div>
  );
}

function Select({ label, value, onChange, options, testid }) {
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <div>
      <label className="label-eyebrow block mb-2">{label}</label>
      <select
        data-testid={testid}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm bg-white focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none capitalize"
      >
        {opts.map((o) => (
          <option key={o.value} value={o.value} className="capitalize">{o.label}</option>
        ))}
      </select>
    </div>
  );
}
