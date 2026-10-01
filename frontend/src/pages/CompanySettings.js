import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Building2 } from "lucide-react";

export default function CompanySettings() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [form, setForm] = useState({
    company_name: "",
    address: "",
    phone: "",
    email: "",
    website: "",
    currency: "INR",
    timezone: "Asia/Kolkata",
    fiscal_year: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get("/settings/company").then((r) => {
      if (!cancelled && r.data?.data) setForm((f) => ({ ...f, ...r.data.data }));
    });
    return () => { cancelled = true; };
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch("/settings/company", form);
      alert("Settings saved successfully");
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto" data-testid="company-settings-page">
      <header className="mb-6">
        <div>
          <div className="label-eyebrow mb-2">Administration</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Company Settings</h1>
          <p className="text-sm text-slate-600 mt-1">Manage your company profile and preferences</p>
        </div>
      </header>

      <form onSubmit={submit} className="glass-card bg-white border border-slate-200 rounded-md p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Field label="Company Name" value={form.company_name} onChange={(v) => update("company_name", v)} testid="csf-name" />
          <Field label="Email" type="email" value={form.email} onChange={(v) => update("email", v)} testid="csf-email" />
          <Field label="Phone" value={form.phone} onChange={(v) => update("phone", v)} testid="csf-phone" />
          <Field label="Website" value={form.website} onChange={(v) => update("website", v)} testid="csf-website" />
          <Field label="Currency" value={form.currency} onChange={(v) => update("currency", v)} testid="csf-currency" />
          <Field label="Timezone" value={form.timezone} onChange={(v) => update("timezone", v)} testid="csf-timezone" />
          <Field label="Fiscal Year" value={form.fiscal_year} onChange={(v) => update("fiscal_year", v)} testid="csf-fiscal" />
        </div>
        <div>
          <label className="label-eyebrow block mb-2">Address</label>
          <textarea
            data-testid="csf-address"
            value={form.address}
            onChange={(e) => update("address", e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none"
          />
        </div>
        <div className="flex justify-end">
          <button type="submit" disabled={saving} data-testid="csf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800 disabled:opacity-60">
            <Building2 className="w-4 h-4" /> {saving ? "Saving…" : "Save Settings"}
          </button>
        </div>
      </form>
    </div>
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
