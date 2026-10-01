import { useState, useEffect } from "react";
import { Mail, Send, CheckCircle2, XCircle, Loader2, RefreshCw, Eye, X, Server, Zap } from "lucide-react";
import { api, formatApiError } from "@/lib/api";

const ZOHO_PRESETS = [
  { label: "Zoho Pro India (smtppro.zoho.in : 587)", host: "smtppro.zoho.in", port: 587 },
  { label: "Zoho Pro Global (smtppro.zoho.com : 587)", host: "smtppro.zoho.com", port: 587 },
  { label: "Zoho Mail SSL (smtp.zoho.in : 465)", host: "smtp.zoho.in", port: 465 },
  { label: "Gmail TLS (smtp.gmail.com : 587)", host: "smtp.gmail.com", port: 587 },
];

export default function ResendSettings() {
  const [settings, setSettings] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [selectedMail, setSelectedMail] = useState(null);
  const [error, setError] = useState("");
  // Credentials are write-only. The API masks them on read, so they are held in
  // separate fields rather than in `settings`, which would send the mask back.
  const [smtpPassword, setSmtpPassword] = useState("");
  const [resendApiKey, setResendApiKey] = useState("");

  const loadSettings = async () => {
    try {
      const r = await api.get("/resend/settings");
      setSettings(r.data);
    } catch (e) {
      setError(formatApiError(e));
    }
  };

  const loadLogs = async () => {
    try {
      const r = await api.get("/resend/logs?limit=50");
      setLogs(r.data || []);
    } catch (e) {
      // non-critical
    }
  };

  useEffect(() => {
    const init = async () => {
      await loadSettings();
      await loadLogs();
      setLoading(false);
    };
    init();
  }, []);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setTestResult(null);
    try {
      const payload = {
        enabled: settings.enabled,
        smtp_host: settings.smtp_host,
        smtp_port: Number(settings.smtp_port || 587),
        smtp_user: settings.smtp_user,
        sender_email: settings.sender_email,
        sender_name: settings.sender_name,
        reply_to: settings.reply_to,
        events: settings.events,
        quotation_subject: settings.quotation_subject,
        quotation_body: settings.quotation_body,
        lead_update_subject: settings.lead_update_subject,
        lead_update_body: settings.lead_update_body,
      };
      // Only send a credential when one was actually typed. The backend keeps the
      // stored value otherwise, so a blank field is never a request to erase it.
      if (resendApiKey) payload.resend_api_key = resendApiKey;
      if (smtpPassword) payload.smtp_password = smtpPassword;

      const r = await api.post("/resend/settings", payload);
      setSettings(r.data);
      setSmtpPassword("");
      setResendApiKey("");
      alert("Zoho SMTP & Email Configuration Saved Successfully!");
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setSaving(false);
    }
  };

  const applyPreset = (preset) => {
    setSettings((prev) => ({
      ...prev,
      smtp_host: preset.host,
      smtp_port: preset.port
    }));
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    setError("");
    try {
      const r = await api.post("/resend/test");
      setTestResult(r.data);
      await loadLogs();
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-[1200px] mx-auto text-slate-500 font-bold text-sm">
        Loading Zoho SMTP settings…
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="resend-settings-page">
      <header className="border-b border-slate-200 pb-6">
        <div className="label-eyebrow mb-2">System Email & Zoho SMTP Engine</div>
        <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
          <Mail className="w-8 h-8 text-sky-600" /> Zoho SMTP & Email Integration
        </h1>
        <p className="text-sm text-slate-600 mt-1 max-w-2xl">
          Configure your official Zoho Mail SMTP server (`smtppro.zoho.in` / `smtp.zoho.in`) to send onboarding emails, commercial quotes, and invoices directly to clients.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Config Form */}
        <div className="lg:col-span-7 space-y-6">
          <form onSubmit={save} className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-5 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-sky-600" />
                <h2 className="font-display text-xl font-bold text-slate-900">Zoho Mail SMTP Credentials</h2>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-100 text-sky-800 border border-sky-200 flex items-center gap-1">
                <Zap className="w-3 h-3 text-sky-600" /> Zoho Preset Ready
              </span>
            </div>

            {/* Quick Presets */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">1-Click Quick Presets:</label>
              <div className="flex flex-wrap gap-2">
                {ZOHO_PRESETS.map((p, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => applyPreset(p)}
                    className="px-3 py-1 rounded-lg text-xs font-bold bg-white border border-slate-200 hover:border-sky-400 hover:bg-sky-50 text-slate-800 transition-all cursor-pointer shadow-2xs"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Free SMTP Configuration Block */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3 shadow-2xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="sm:col-span-2">
                  <label className="block text-[10px] font-bold text-slate-700 mb-1 uppercase">Zoho SMTP Host *</label>
                  <input
                    type="text"
                    required
                    value={settings?.smtp_host || ""}
                    onChange={(e) => setSettings({ ...settings, smtp_host: e.target.value })}
                    placeholder="smtppro.zoho.in"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono font-bold text-slate-900 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-700 mb-1 uppercase">Port *</label>
                  <input
                    type="number"
                    required
                    value={settings?.smtp_port || 587}
                    onChange={(e) => setSettings({ ...settings, smtp_port: e.target.value })}
                    placeholder="587"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold text-slate-700 mb-1 uppercase">Zoho User Email *</label>
                  <input
                    type="email"
                    required
                    value={settings?.smtp_user || ""}
                    onChange={(e) => setSettings({ ...settings, smtp_user: e.target.value })}
                    placeholder="info@hitechavl.com"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-700 mb-1 uppercase">Zoho Password / App Key *</label>
                  {/* Not `required`: the API returns a mask for an already-stored
                      password, and this field starts empty on purpose. Leaving it
                      blank keeps the stored password; typing a value replaces it. */}
                  <input
                    type="password"
                    value={smtpPassword}
                    onChange={(e) => setSmtpPassword(e.target.value)}
                    placeholder={settings?.smtp_password_set ? "Saved — type to replace" : "Enter the Zoho app password"}
                    autoComplete="new-password"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500"
                  />
                  {settings?.smtp_password_set && !smtpPassword && (
                    <p className="mt-1 text-[10px] text-slate-500">
                      A password is saved. Leave blank to keep it.
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wide">Sender Email Address</label>
                <input
                  type="email"
                  required
                  value={settings?.sender_email || ""}
                  onChange={(e) => setSettings({ ...settings, sender_email: e.target.value })}
                  placeholder="info@hitechavl.com"
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wide">Sender Name</label>
                <input
                  type="text"
                  required
                  value={settings?.sender_name || ""}
                  onChange={(e) => setSettings({ ...settings, sender_name: e.target.value })}
                  placeholder="Hi-Tech Audio & Image LLP"
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            {error && (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-3 text-xs font-bold">{error}</div>
            )}

            <div className="flex items-center gap-3 pt-2 border-t border-slate-200">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-sky-600 text-white text-xs font-bold rounded-xl hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                {saving ? "Saving Zoho SMTP..." : "Save Zoho SMTP Settings"}
              </button>
            </div>
          </form>
        </div>

        {/* Right Column: Outbox Logs */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-sky-600" />
                <h3 className="font-display text-lg font-bold text-slate-900">System Outbox Logs ({logs.length})</h3>
              </div>
              <button onClick={loadLogs} className="text-xs text-sky-700 font-bold hover:underline">
                Refresh
              </button>
            </div>

            <div className="space-y-2.5 max-h-[550px] overflow-y-auto no-scrollbar">
              {logs.length === 0 ? (
                <div className="text-xs text-slate-500 py-10 text-center font-medium">No emails logged in outbox yet.</div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="border border-slate-200 rounded-xl p-3 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-slate-900 truncate flex-1 mr-2">{log.subject}</span>
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full shrink-0">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Sent
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500">
                      <span>To: <code className="font-mono text-slate-700 font-bold">{log.to_email}</code></span>
                      {log.html && (
                        <button
                          onClick={() => setSelectedMail(log)}
                          className="text-sky-700 hover:text-sky-800 font-bold flex items-center gap-1"
                        >
                          <Eye className="w-3 h-3" /> Preview
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* HTML Email Preview Modal */}
      {selectedMail && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-2xl p-6 space-y-4 shadow-2xl animate-scale-in max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-sky-700">Outbox Email Preview</span>
                <h3 className="font-display text-lg font-bold text-slate-900">{selectedMail.subject}</h3>
                <p className="text-xs text-slate-500">To: {selectedMail.to_email} | Sent: {new Date(selectedMail.created_at).toLocaleString()}</p>
              </div>
              <button onClick={() => setSelectedMail(null)} className="p-2 rounded-xl text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
            </div>

            <div className="flex-1 bg-slate-100 p-4 rounded-xl overflow-y-auto border border-slate-200">
              {selectedMail.html ? (
                <div dangerouslySetInnerHTML={{ __html: selectedMail.html }} />
              ) : (
                <pre className="text-xs text-slate-800 font-mono whitespace-pre-wrap">{selectedMail.body}</pre>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-200">
              <button onClick={() => setSelectedMail(null)} className="px-5 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800">Close Preview</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
