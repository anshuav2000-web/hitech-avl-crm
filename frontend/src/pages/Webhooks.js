import { useState, useEffect } from "react";
import { Send, Webhook, CheckCircle2, XCircle, Loader2, RefreshCw } from "lucide-react";
import { api, formatApiError } from "@/lib/api";

export default function Webhooks() {
  const [settings, setSettings] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState("");

  const loadSettings = async () => {
    try {
      const r = await api.get("/webhooks/settings");
      setSettings(r.data);
    } catch (e) {
      setError(formatApiError(e));
    }
  };

  const loadLogs = async () => {
    try {
      const r = await api.get("/webhooks/logs?limit=50");
      setLogs(r.data);
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
      const r = await api.post("/webhooks/settings", {
        n8n_webhook_url: settings.n8n_webhook_url,
        enabled: settings.enabled,
        admin_phone: settings.admin_phone,
        events: settings.events,
      });
      setSettings(r.data);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    setError("");
    try {
      const r = await api.post("/webhooks/test");
      setTestResult(r.data);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setTesting(false);
    }
  };

  const toggleEvent = (key) => {
    setSettings((s) => ({
      ...s,
      events: { ...s.events, [key]: !s.events[key] },
    }));
  };

  if (loading) {
    return (
      <div className="p-8 max-w-[1200px] mx-auto">
        <div className="text-sm text-slate-500">Loading webhook settings…</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[1200px] mx-auto" data-testid="webhooks-page">
      <header className="mb-8">
        <div className="label-eyebrow mb-2">Automation</div>
        <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">n8n Webhooks</h1>
        <p className="text-sm text-slate-600 mt-2 max-w-2xl">
          Pipe lead and quotation events into n8n so you can send WhatsApp notifications to admins, update external systems, or trigger any workflow.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Panel */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={save} className="bg-white border border-slate-200 rounded-md p-6">
            <div className="flex items-center gap-2 mb-5">
              <Webhook className="w-5 h-5 text-slate-500" />
              <h2 className="font-display text-xl font-bold text-slate-900">n8n Configuration</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">n8n Webhook URL</label>
                <input
                  type="url"
                  required
                  value={settings?.n8n_webhook_url || ""}
                  onChange={(e) => setSettings({ ...settings, n8n_webhook_url: e.target.value })}
                  placeholder="https://your-n8n-instance.com/webhook/..."
                  className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">Admin WhatsApp Number</label>
                <input
                  type="text"
                  value={settings?.admin_phone || ""}
                  onChange={(e) => setSettings({ ...settings, admin_phone: e.target.value })}
                  placeholder="+91 9999999999"
                  className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />
                <p className="text-xs text-slate-500 mt-1">Included in every webhook payload so n8n can target the right WhatsApp thread.</p>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enabled"
                  checked={settings?.enabled || false}
                  onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
                  className="w-4 h-4 text-red-600 border-slate-300 rounded focus:ring-red-500"
                />
                <label htmlFor="enabled" className="text-sm font-medium text-slate-700">Enable webhook delivery</label>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-slate-100">
              <h3 className="text-xs font-semibold text-slate-700 mb-3 uppercase tracking-wide">Trigger Events</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  ["lead_created", "New lead captured"],
                  ["quotation_created", "Quotation generated"],
                  ["lead_updated", "Lead stage changed"],
                ].map(([key, label]) => (
                  <div key={key} className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-md px-3 py-2.5">
                    <input
                      type="checkbox"
                      id={`evt-${key}`}
                      checked={settings?.events?.[key] || false}
                      onChange={() => toggleEvent(key)}
                      className="w-4 h-4 text-red-600 border-slate-300 rounded focus:ring-red-500"
                    />
                    <label htmlFor={`evt-${key}`} className="text-sm text-slate-700">{label}</label>
                  </div>
                ))}
              </div>
            </div>

            {error && (
              <div className="mt-4 bg-red-50 border border-red-200 text-red-800 rounded-md px-4 py-3 text-sm">{error}</div>
            )}

            <div className="mt-6 flex items-center gap-3">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                {saving ? "Saving…" : "Save Settings"}
              </button>
              <button
                type="button"
                onClick={test}
                disabled={testing || !settings?.n8n_webhook_url}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-white text-sm font-semibold rounded-md hover:bg-slate-800 disabled:opacity-50"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {testing ? "Testing…" : "Test Connection"}
              </button>
            </div>

            {testResult && (
              <div className={`mt-4 rounded-md px-4 py-3 text-sm ${testResult.ok ? "bg-green-50 border border-green-200 text-green-800" : "bg-red-50 border border-red-200 text-red-800"}`}>
                {testResult.ok ? (
                  <span className="font-semibold">Success</span>
                ) : (
                  <span className="font-semibold">Failed</span>
                )}{" "}
                — status {testResult.status_code || "N/A"}{testResult.error ? `: ${testResult.error}` : ""}
                {testResult.response && <pre className="mt-2 text-xs bg-white/50 p-2 rounded overflow-x-auto">{testResult.response}</pre>}
              </div>
            )}
          </form>
        </div>

        {/* Info + Logs */}
        <div className="space-y-6">
          <div className="bg-slate-900 text-white rounded-md p-6">
            <div className="label-eyebrow !text-white/70 mb-2">How it works</div>
            <p className="text-sm text-white/90 leading-relaxed">
              When a lead or quotation is created, the CRM POSTs a JSON payload to your n8n webhook URL. In n8n, use a <span className="font-mono text-xs bg-white/10 px-1.5 py-0.5 rounded">Webhook</span> node as the trigger, then add a <span className="font-mono text-xs bg-white/10 px-1.5 py-0.5 rounded">WhatsApp</span> node (Meta Cloud API / Twilio) to notify the admin.
            </p>
            <div className="mt-4 p-3 bg-white/10 rounded-md">
              <div className="text-xs font-semibold text-white/70 mb-1">Sample payload</div>
              <pre className="text-xs text-white/90 overflow-x-auto">{`{
  "event": "lead_created",
  "timestamp": "2026-07-21T08:30:00Z",
  "admin_phone": "+919999999999",
  "data": {
    "id": "lead-uuid",
    "name": "Acme Corp",
    "phone": "+91 98765 43210",
    "email": "buyer@acme.in",
    "source": "website",
    "stage": "new"
  }
}`}</pre>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-slate-500" />
                <h3 className="font-display text-lg font-bold text-slate-900">Delivery Log</h3>
              </div>
              <button
                onClick={loadLogs}
                className="text-xs text-slate-600 hover:text-slate-900 font-medium"
              >
                Refresh
              </button>
            </div>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {logs.length === 0 && (
                <div className="text-xs text-slate-500">No deliveries yet.</div>
              )}
              {logs.map((log) => (
                <div key={log.id} className="border border-slate-200 rounded-md p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono font-semibold text-slate-700">{log.event}</span>
                    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${log.status === "success" ? "text-green-700" : "text-red-700"}`}>
                      {log.status === "success" ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      {log.status_code || log.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500">{new Date(log.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
