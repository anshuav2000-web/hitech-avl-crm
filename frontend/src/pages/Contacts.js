import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Mail, Phone } from "lucide-react";

export default function Contacts() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", company: "", role: "", customer_id: "" });
  // Reports the address the API derived when the field was left blank.
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    api.get("/contacts").then((r) => setItems(r.data));
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/contacts", form);
      setItems((prev) => [...prev, r.data]);
      setShowForm(false);
      setForm({ name: "", email: "", phone: "", company: "", role: "", customer_id: "" });
      setNotice(r.data?.email_generated
        ? `No email was entered, so one was generated: ${r.data.email}`
        : null);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="contacts-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">People</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Contacts</h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} contacts in your workspace</p>
        </div>
        <button onClick={() => setShowForm(true)} data-testid="contacts-add-btn" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
          <Plus className="w-4 h-4" /> Add New
        </button>
      </header>

      {notice && (
        <div
          data-testid="contacts-generated-email"
          className="mb-4 rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900"
        >
          {notice}
        </div>
      )}

      {showForm && (
        <form onSubmit={submit} className="glass-card bg-white border border-slate-200 p-6 mb-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Name *" value={form.name} onChange={(v) => update("name", v)} testid="cf-name" />
            <Field label="Company" value={form.company} onChange={(v) => update("company", v)} testid="cf-company" />
            {/* Optional on purpose: a blank field makes the API derive a valid,
                unique address from the contact's name. */}
            <Field
              label="Email (optional — generated from the name if left blank)"
              value={form.email}
              onChange={(v) => update("email", v)}
              testid="cf-email"
            />
            <Field label="Phone" value={form.phone} onChange={(v) => update("phone", v)} testid="cf-phone" />
            <Field label="Role" value={form.role} onChange={(v) => update("role", v)} testid="cf-role" />
            <Field label="Customer ID" value={form.customer_id} onChange={(v) => update("customer_id", v)} testid="cf-customer" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
            <button type="submit" data-testid="cf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800">Save</button>
          </div>
        </form>
      )}

      <div className="glass-card bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
              <th className="text-left px-6 py-3 font-medium">Name</th>
              <th className="text-left px-6 py-3 font-medium">Email</th>
              <th className="text-left px-6 py-3 font-medium">Phone</th>
              <th className="text-left px-6 py-3 font-medium">Company</th>
              <th className="text-left px-6 py-3 font-medium">Role</th>
              <th className="text-left px-6 py-3 font-medium">Customer ID</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={6} className="px-6 py-14 text-center text-slate-500">No contacts yet.</td></tr>
            )}
            {items.map((c) => (
              <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-3.5"><Link to={`/contacts/${c.id}`} className="font-medium text-slate-900 hover:underline" data-testid={`contact-row-${c.id}`}>{c.name}</Link></td>
                <td className="px-6 py-3.5 text-slate-600">{c.email || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{c.phone || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{c.company || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{c.role || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{c.customer_id || "—"}</td>
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
