import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, UserCircle2 } from "lucide-react";

export default function CustomerPortal() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_name: "", email: "", last_login: "", invoices_count: "", tickets_count: "" });

  useEffect(() => {
    api.get("/customer-portal").then((r) => setItems(r.data));
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/customer-portal", form);
      setItems((prev) => [...prev, r.data]);
      setShowForm(false);
      setForm({ customer_name: "", email: "", last_login: "", invoices_count: "", tickets_count: "" });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="customer-portal-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Self Service</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Customer Portal</h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} portal access records</p>
        </div>
        <button onClick={() => setShowForm(true)} data-testid="customer-portal-add-btn" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
          <Plus className="w-4 h-4" /> Add New
        </button>
      </header>

      {showForm && (
        <form onSubmit={submit} className="glass-card bg-white border border-slate-200 p-6 mb-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Customer Name *" value={form.customer_name} onChange={(v) => update("customer_name", v)} testid="cpf-name" />
            <Field label="Email" type="email" value={form.email} onChange={(v) => update("email", v)} testid="cpf-email" />
            <Field label="Last Login" type="datetime-local" value={form.last_login} onChange={(v) => update("last_login", v)} testid="cpf-login" />
            <Field label="Invoices Count" type="number" value={form.invoices_count} onChange={(v) => update("invoices_count", v)} testid="cpf-invoices" />
            <Field label="Tickets Count" type="number" value={form.tickets_count} onChange={(v) => update("tickets_count", v)} testid="cpf-tickets" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
            <button type="submit" data-testid="cpf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800">Save</button>
          </div>
        </form>
      )}

      <div className="glass-card bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
              <th className="text-left px-6 py-3 font-medium">Customer Name</th>
              <th className="text-left px-6 py-3 font-medium">Email</th>
              <th className="text-left px-6 py-3 font-medium">Last Login</th>
              <th className="text-left px-6 py-3 font-medium">Invoices Count</th>
              <th className="text-left px-6 py-3 font-medium">Tickets Count</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={5} className="px-6 py-14 text-center text-slate-500">No portal access records yet.</td></tr>
            )}
            {items.map((p) => (
              <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-3.5"><Link to={`/customer-portal/${p.id}`} className="font-medium text-slate-900 hover:underline" data-testid={`portal-row-${p.id}`}>{p.customer_name}</Link></td>
                <td className="px-6 py-3.5 text-slate-600">{p.email || "—"}</td>
                <td className="px-6 py-3.5 text-slate-700">{p.last_login ? new Date(p.last_login).toLocaleString() : "—"}</td>
                <td className="px-6 py-3.5 text-slate-700">{p.invoices_count || "—"}</td>
                <td className="px-6 py-3.5 text-slate-700">{p.tickets_count || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
