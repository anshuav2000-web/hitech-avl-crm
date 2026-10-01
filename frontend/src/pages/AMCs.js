import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, ShieldCheck, AlertTriangle, Trash2, X } from "lucide-react";

const statusStyle = {
  active:    "bg-green-50 text-green-700 border-green-200",
  expired:   "bg-slate-100 text-slate-700 border-slate-200",
  renewed:   "bg-blue-50 text-blue-700 border-blue-200",
  cancelled: "bg-red-50 text-red-700 border-red-200",
};

const daysToEnd = (end) => Math.ceil((new Date(end) - new Date()) / (1000 * 60 * 60 * 24));

export default function AMCs() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [list, setList] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_name: "", customer_company: "", start_date: "", end_date: "", value: "", serial_numbers: "", notes: "" });
  const [err, setErr] = useState("");

  const load = () => api.get("/amcs").then((r) => setList(r.data));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/amcs", {
        ...form,
        value: parseFloat(form.value),
        serial_numbers: form.serial_numbers.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setForm({ customer_name: "", customer_company: "", start_date: "", end_date: "", value: "", serial_numbers: "", notes: "" });
      setShowForm(false);
      load();
    } catch (e2) { setErr(formatApiError(e2)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this AMC?")) return;
    await api.delete(`/amcs/${id}`);
    load();
  };

  const renew = async (a) => {
    const newEnd = new Date(a.end_date);
    newEnd.setFullYear(newEnd.getFullYear() + 1);
    await api.patch(`/amcs/${a.id}`, { status: "active", end_date: newEnd.toISOString().slice(0, 10) });
    load();
  };

  const expiring = list.filter((a) => a.status === "active" && daysToEnd(a.end_date) <= 60);
  const totalActive = list.filter((a) => a.status === "active").length;
  const totalValue = list.filter((a) => a.status === "active").reduce((s, a) => s + Number(a.value || 0), 0);

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="amcs-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Operations</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">AMC contracts</h1>
          <p className="text-sm text-slate-600 mt-1">{totalActive} active · ₹{totalValue.toLocaleString("en-IN", { maximumFractionDigits: 0 })} recurring value · {expiring.length} expiring in 60 days</p>
        </div>
        {isAdmin && (
          <button onClick={() => setShowForm(true)} data-testid="amc-add-btn" className="inline-flex items-center gap-2 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:opacity-90" style={{ background: "#DC2626" }}>
            <Plus className="w-4 h-4" /> New AMC
          </button>
        )}
      </header>

      {expiring.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-md p-4 mb-4 flex items-start gap-3" data-testid="amc-alert">
          <AlertTriangle className="w-4 h-4 text-amber-700 mt-0.5 shrink-0" />
          <div className="text-sm text-amber-900">
            <strong>{expiring.length} AMC{expiring.length === 1 ? "" : "s"}</strong> expiring within 60 days · total renewal value <strong>₹{expiring.reduce((s, a) => s + Number(a.value || 0), 0).toLocaleString("en-IN")}</strong>. Reach out to customers now to lock in the renewal.
          </div>
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
              <th className="text-left px-6 py-3 font-medium">Customer</th>
              <th className="text-left px-6 py-3 font-medium">Coverage</th>
              <th className="text-left px-6 py-3 font-medium">Period</th>
              <th className="text-right px-6 py-3 font-medium">Value</th>
              <th className="text-left px-6 py-3 font-medium">Status</th>
              <th className="text-right px-6 py-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {list.length === 0 && <tr><td colSpan={6} className="px-6 py-14 text-center text-slate-500">No AMCs yet.</td></tr>}
            {list.map((a) => {
              const days = daysToEnd(a.end_date);
              const isExpiringSoon = a.status === "active" && days <= 60;
              return (
                <tr key={a.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors" data-testid={`amc-row-${a.id}`}>
                  <td className="px-6 py-3.5">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-slate-400" />
                      <div>
                        <div className="font-semibold text-slate-900">{a.customer_name}</div>
                        <div className="text-xs text-slate-500">{a.customer_company || "—"}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-3.5 text-xs text-slate-600">{a.serial_numbers?.length || 0} serial{a.serial_numbers?.length === 1 ? "" : "s"}</td>
                  <td className="px-6 py-3.5 text-xs text-slate-600">
                    {a.start_date} → <strong className={isExpiringSoon ? "text-amber-700" : "text-slate-700"}>{a.end_date}</strong>
                    {a.status === "active" && (
                      <div className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: days < 0 ? "#DC2626" : days <= 60 ? "#D97706" : "#64748B" }}>
                        {days < 0 ? `expired ${Math.abs(days)}d ago` : `${days} days left`}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-3.5 text-right font-semibold text-slate-900">₹{Number(a.value).toLocaleString("en-IN")}</td>
                  <td className="px-6 py-3.5">
                    <span className={`inline-block px-2 py-0.5 rounded-sm text-xs font-medium border capitalize ${statusStyle[a.status] || ""}`}>{a.status}</span>
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    {isAdmin && (
                      <div className="inline-flex items-center gap-1.5">
                        {isExpiringSoon && (
                          <button onClick={() => renew(a)} data-testid={`amc-renew-${a.id}`} className="text-xs text-white bg-green-600 hover:bg-green-700 px-2 py-1 rounded-md">Renew +1y</button>
                        )}
                        <button onClick={() => remove(a.id)} className="text-slate-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="amc-form-modal">
          <div className="bg-white rounded-md border border-slate-200 max-w-xl w-full">
            <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
              <div className="font-display text-lg font-bold text-slate-900">New AMC</div>
              <button onClick={() => setShowForm(false)} className="text-slate-500 hover:text-slate-900"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={submit} className="p-5 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Customer name *" v={form.customer_name} onV={(v) => setForm({ ...form, customer_name: v })} required testid="amc-customer" />
                <Field label="Company / City" v={form.customer_company} onV={(v) => setForm({ ...form, customer_company: v })} testid="amc-company" />
                <Field label="Start date *" type="date" v={form.start_date} onV={(v) => setForm({ ...form, start_date: v })} required testid="amc-start" />
                <Field label="End date *" type="date" v={form.end_date} onV={(v) => setForm({ ...form, end_date: v })} required testid="amc-end" />
                <Field label="Value (₹) *" type="number" v={form.value} onV={(v) => setForm({ ...form, value: v })} required testid="amc-value" />
              </div>
              <Field label="Serial numbers covered (comma-separated)" v={form.serial_numbers} onV={(v) => setForm({ ...form, serial_numbers: v })} testid="amc-serials" />
              <div>
                <label className="label-eyebrow block mb-1.5">Notes</label>
                <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2" />
              </div>
              {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">{err}</div>}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
                <button type="submit" data-testid="amc-submit" className="text-white px-4 py-2 rounded-md text-sm hover:opacity-90" style={{ background: "#DC2626" }}>Create AMC</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, v, onV, type = "text", required, testid }) {
  return (
    <div>
      <label className="label-eyebrow block mb-1.5">{label}</label>
      <input data-testid={testid} type={type} required={required} value={v} onChange={(e) => onV(e.target.value)} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none" />
    </div>
  );
}
