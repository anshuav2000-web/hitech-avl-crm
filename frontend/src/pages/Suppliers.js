import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Truck } from "lucide-react";

const CATEGORIES = ["electronics", "components", "raw_materials", "services", "logistics"];

export default function Suppliers() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", company: "", email: "", phone: "", city: "", category: "electronics", rating: "", lead_id: "" });

  useEffect(() => {
    api.get("/suppliers").then((r) => setItems(r.data));
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/suppliers", form);
      setItems((prev) => [...prev, r.data]);
      setShowForm(false);
      setForm({ name: "", company: "", email: "", phone: "", city: "", category: "electronics", rating: "", lead_id: "" });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="suppliers-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Procurement</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Suppliers</h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} suppliers in your workspace</p>
        </div>
        <button onClick={() => setShowForm(true)} data-testid="suppliers-add-btn" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
          <Plus className="w-4 h-4" /> Add New
        </button>
      </header>

      {showForm && (
        <form onSubmit={submit} className="glass-card bg-white border border-slate-200 p-6 mb-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Name *" value={form.name} onChange={(v) => update("name", v)} testid="sf-name" />
            <Field label="Company" value={form.company} onChange={(v) => update("company", v)} testid="sf-company" />
            <Field label="Email" type="email" value={form.email} onChange={(v) => update("email", v)} testid="sf-email" />
            <Field label="Phone" value={form.phone} onChange={(v) => update("phone", v)} testid="sf-phone" />
            <Field label="City" value={form.city} onChange={(v) => update("city", v)} testid="sf-city" />
            <Select label="Category" value={form.category} onChange={(v) => update("category", v)} options={CATEGORIES} testid="sf-category" />
            <Field label="Rating" type="number" value={form.rating} onChange={(v) => update("rating", v)} testid="sf-rating" />
            <Field label="Lead ID" value={form.lead_id} onChange={(v) => update("lead_id", v)} testid="sf-lead" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
            <button type="submit" data-testid="sf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800">Save</button>
          </div>
        </form>
      )}

      <div className="glass-card bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
              <th className="text-left px-6 py-3 font-medium">Name</th>
              <th className="text-left px-6 py-3 font-medium">Company</th>
              <th className="text-left px-6 py-3 font-medium">Email</th>
              <th className="text-left px-6 py-3 font-medium">Phone</th>
              <th className="text-left px-6 py-3 font-medium">City</th>
              <th className="text-left px-6 py-3 font-medium">Category</th>
              <th className="text-left px-6 py-3 font-medium">Rating</th>
              <th className="text-left px-6 py-3 font-medium">Lead ID</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={8} className="px-6 py-14 text-center text-slate-500">No suppliers yet.</td></tr>
            )}
            {items.map((s) => (
              <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-3.5"><Link to={`/suppliers/${s.id}`} className="font-medium text-slate-900 hover:underline" data-testid={`supplier-row-${s.id}`}>{s.name}</Link></td>
                <td className="px-6 py-3.5 text-slate-600">{s.company || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{s.email || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{s.phone || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{s.city || "—"}</td>
                <td className="px-6 py-3.5 capitalize text-slate-700">{s.category}</td>
                <td className="px-6 py-3.5 text-slate-700">{s.rating || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{s.lead_id || "—"}</td>
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
