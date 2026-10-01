import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Calendar as CalendarIcon } from "lucide-react";

const TYPES = ["meeting", "call", "follow_up", "holiday"];

export default function Calendar() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", type: "meeting", start_time: "", end_time: "", location: "", lead_id: "" });

  useEffect(() => {
    api.get("/calendar").then((r) => setItems(r.data));
  }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/calendar", form);
      setItems((prev) => [...prev, r.data]);
      setShowForm(false);
      setForm({ title: "", type: "meeting", start_time: "", end_time: "", location: "", lead_id: "" });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="calendar-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Schedule</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Calendar</h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} events in your workspace</p>
        </div>
        <button onClick={() => setShowForm(true)} data-testid="calendar-add-btn" className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
          <Plus className="w-4 h-4" /> Add New
        </button>
      </header>

      {showForm && (
        <form onSubmit={submit} className="glass-card bg-white border border-slate-200 p-6 mb-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Title *" value={form.title} onChange={(v) => update("title", v)} testid="cf-title" />
            <Select label="Type" value={form.type} onChange={(v) => update("type", v)} options={TYPES} testid="cf-type" />
            <Field label="Start Time" type="datetime-local" value={form.start_time} onChange={(v) => update("start_time", v)} testid="cf-start" />
            <Field label="End Time" type="datetime-local" value={form.end_time} onChange={(v) => update("end_time", v)} testid="cf-end" />
            <Field label="Location" value={form.location} onChange={(v) => update("location", v)} testid="cf-location" />
            <Field label="Lead ID" value={form.lead_id} onChange={(v) => update("lead_id", v)} testid="cf-lead" />
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
              <th className="text-left px-6 py-3 font-medium">Title</th>
              <th className="text-left px-6 py-3 font-medium">Type</th>
              <th className="text-left px-6 py-3 font-medium">Start Time</th>
              <th className="text-left px-6 py-3 font-medium">End Time</th>
              <th className="text-left px-6 py-3 font-medium">Location</th>
              <th className="text-left px-6 py-3 font-medium">Lead ID</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={6} className="px-6 py-14 text-center text-slate-500">No events yet.</td></tr>
            )}
            {items.map((ev) => (
              <tr key={ev.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-3.5"><Link to={`/calendar/${ev.id}`} className="font-medium text-slate-900 hover:underline" data-testid={`calendar-row-${ev.id}`}>{ev.title}</Link></td>
                <td className="px-6 py-3.5 capitalize text-slate-700">{ev.type}</td>
                <td className="px-6 py-3.5 text-slate-700">{ev.start_time ? new Date(ev.start_time).toLocaleString() : "—"}</td>
                <td className="px-6 py-3.5 text-slate-700">{ev.end_time ? new Date(ev.end_time).toLocaleString() : "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{ev.location || "—"}</td>
                <td className="px-6 py-3.5 text-slate-600">{ev.lead_id || "—"}</td>
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
