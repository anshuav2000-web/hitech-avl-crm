import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Settings2 } from "lucide-react";

export default function SystemSettings() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [form, setForm] = useState({
    app_name: "",
    logo_url: "",
    theme: "light",
    language: "en",
    email_provider: "smtp",
    sms_provider: "twilio",
    backup_frequency: "daily",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get("/settings/system").then((r) => {
      if (!cancelled && r.data?.data) setForm((f) => ({ ...f, ...r.data.data }));
    });
    return () => { cancelled = true; };
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch("/settings/system", form);
      alert("Settings saved successfully");
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto" data-testid="system-settings-page">
      <header className="mb-6">
        <div>
          <div className="label-eyebrow mb-2">Administration</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">System Settings</h1>
          <p className="text-sm text-slate-600 mt-1">Configure application-wide preferences and integrations</p>
        </div>
      </header>

      <form onSubmit={submit} className="glass-card bg-white border border-slate-200 rounded-md p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Field label="App Name" value={form.app_name} onChange={(v) => update("app_name", v)} testid="ssf-app" />
          <Field label="Logo URL" value={form.logo_url} onChange={(v) => update("logo_url", v)} testid="ssf-logo" />
          <Select label="Theme" value={form.theme} onChange={(v) => update("theme", v)} options={["light", "dark", "auto"]} testid="ssf-theme" />
          <Select label="Language" value={form.language} onChange={(v) => update("language", v)} options={["en", "hi", "ta", "te", "kn", "mr"]} testid="ssf-language" />
          <Select label="Email Provider" value={form.email_provider} onChange={(v) => update("email_provider", v)} options={["smtp", "sendgrid", "aws_ses"]} testid="ssf-email" />
          <Select label="SMS Provider" value={form.sms_provider} onChange={(v) => update("sms_provider", v)} options={["twilio", "msg91", "aws_sns"]} testid="ssf-sms" />
          <Select label="Backup Frequency" value={form.backup_frequency} onChange={(v) => update("backup_frequency", v)} options={["daily", "weekly", "monthly"]} testid="ssf-backup" />
        </div>
        <div className="flex justify-end">
          <button type="submit" disabled={saving} data-testid="ssf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800 disabled:opacity-60">
            <Settings2 className="w-4 h-4" /> {saving ? "Saving…" : "Save Settings"}
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
