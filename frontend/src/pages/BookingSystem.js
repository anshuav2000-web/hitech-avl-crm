import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, CalendarCheck } from "lucide-react";

const BOOKING_STATUSES = ["confirmed", "pending", "cancelled"];

export default function BookingSystem() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ service: "", date: "", time: "", resource: "", customer_name: "", status: "pending" });

  useEffect(() => {
    api.get("/bookings").then((r) => setItems(r.data));
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/bookings", form);
      setItems((prev) => [...prev, r.data]);
      setShowForm(false);
      setForm({ service: "", date: "", time: "", resource: "", customer_name: "", status: "pending" });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="booking-system-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Reservations</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Booking System</h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} bookings in your workspace</p>
        </div>
        <button onClick={() => setShowForm(true)} data-testid="booking-system-add-btn" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
          <Plus className="w-4 h-4" /> Add New
        </button>
      </header>

      {showForm && (
        <form onSubmit={submit} className="glass-card bg-white border border-slate-200 p-6 mb-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Service *" value={form.service} onChange={(v) => update("service", v)} testid="bf-service" />
            <Field label="Customer Name" value={form.customer_name} onChange={(v) => update("customer_name", v)} testid="bf-customer" />
            <Field label="Date" type="date" value={form.date} onChange={(v) => update("date", v)} testid="bf-date" />
            <Field label="Time" type="time" value={form.time} onChange={(v) => update("time", v)} testid="bf-time" />
            <Field label="Resource" value={form.resource} onChange={(v) => update("resource", v)} testid="bf-resource" />
            <Select label="Status" value={form.status} onChange={(v) => update("status", v)} options={BOOKING_STATUSES} testid="bf-status" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
            <button type="submit" data-testid="bf-submit" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800">Save</button>
          </div>
        </form>
      )}

      <div className="glass-card bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
              <th className="text-left px-6 py-3 font-medium">Service</th>
              <th className="text-left px-6 py-3 font-medium">Customer Name</th>
              <th className="text-left px-6 py-3 font-medium">Date</th>
              <th className="text-left px-6 py-3 font-medium">Time</th>
              <th className="text-left px-6 py-3 font-medium">Resource</th>
              <th className="text-left px-6 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={6} className="px-6 py-14 text-center text-slate-500">No bookings yet.</td></tr>
            )}
            {items.map((b) => (
              <tr key={b.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-3.5"><Link to={`/bookings/${b.id}`} className="font-medium text-slate-900 hover:underline" data-testid={`booking-row-${b.id}`}>{b.service}</Link></td>
                <td className="px-6 py-3.5 text-slate-600">{b.customer_name || "—"}</td>
                <td className="px-6 py-3.5 text-slate-700">{b.date ? new Date(b.date).toLocaleDateString() : "—"}</td>
                <td className="px-6 py-3.5 text-slate-700">{b.time || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{b.resource || "—"}</td>
                <td className="px-6 py-3.5"><StatusBadge status={b.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    confirmed: "bg-green-50 text-green-700 border-green-200",
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    cancelled: "bg-red-50 text-red-700 border-red-200",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-sm text-xs font-medium border capitalize ${map[status] || ""}`}>{status || "—"}</span>
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
