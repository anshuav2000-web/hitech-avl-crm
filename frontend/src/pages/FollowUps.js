import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { 
  Calendar, Clock, Bell, PhoneCall, AlertCircle, Sparkles, CheckCircle2, User, ChevronRight, Play, VolumeX, Mail
} from "lucide-react";
import { toast } from "sonner";

export default function FollowUps() {
  const [followUps, setFollowUps] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    lead_id: "",
    follow_up_date: new Date().toISOString().split("T")[0],
    follow_up_time: "11:00",
    type: "call",
    status: "pending",
    notes: "",
    reminder_enabled: true,
    reminder_minutes_before: 15,
    recurring: false,
    recurring_interval: "daily",
    recurring_end_date: "",
    escalation_enabled: true,
    escalation_after_minutes: 60
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [fups, lds] = await Promise.all([
        api.get("/follow-ups"),
        api.get("/leads")
      ]);
      setFollowUps(fups.data);
      setLeads(lds.data);
      if (lds.data.length > 0) {
        setForm((prev) => ({ ...prev, lead_id: lds.data[0].id }));
      }
    } catch (err) {
      toast.error("Failed to load follow-up schedules.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFollowUp = async (e) => {
    e.preventDefault();
    if (!form.lead_id) {
      toast.error("Please select a lead first.");
      return;
    }
    try {
      setSubmitting(true);
      await api.post("/follow-ups", form);
      toast.success("Follow-up scheduled and alerts configured!");
      fetchData();
    } catch (err) {
      toast.error("Failed to schedule follow-up.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleMarkCompleted = async (id) => {
    try {
      await api.patch(`/follow-ups/${id}`, { status: "completed" });
      toast.success("Follow-up marked as completed.");
      fetchData();
    } catch (err) {
      toast.error("Failed to update status.");
    }
  };

  const getFupBadge = (status) => {
    switch (status) {
      case "completed":
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Completed</span>;
      case "missed":
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">Missed Fup</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">Pending</span>;
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-8 bg-white text-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-sky-700 font-bold uppercase tracking-wider mb-2">
            <span>Enterprise ERP</span>
            <span>/</span>
            <span className="text-slate-900">CRM Engine</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Calendar className="w-8 h-8 text-sky-600" />
            Follow-Up Scheduler & Alerts
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Schedule next calls, customer discussion events, or system-integrated automated reminders. Enable automatic escalation for overdue items.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-slate-500 text-sm font-medium">Loading schedules...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Form */}
          <div className="lg:col-span-1">
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-5">
              <h3 className="font-display text-lg font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sky-600" /> Schedule Action
              </h3>

              <form onSubmit={handleCreateFollowUp} className="space-y-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Select Lead / Company</label>
                  <select
                    value={form.lead_id}
                    onChange={(e) => setForm({ ...form, lead_id: e.target.value })}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  >
                    {leads.map((l) => (
                      <option key={l.id} value={l.id}>{l.name} • {l.company || "Direct"}</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Date</label>
                    <input
                      type="date"
                      required
                      value={form.follow_up_date}
                      onChange={(e) => setForm({ ...form, follow_up_date: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Time</label>
                    <input
                      type="time"
                      required
                      value={form.follow_up_time}
                      onChange={(e) => setForm({ ...form, follow_up_time: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-medium"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Communication Channel</label>
                  <select
                    value={form.type}
                    onChange={(e) => setForm({ ...form, type: e.target.value })}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  >
                    <option value="call">Phone Call (Direct Outbound)</option>
                    <option value="whatsapp">Business WhatsApp Sync</option>
                    <option value="email">Zoho Pro Mail Integration</option>
                    <option value="sms">SMS Text Alert</option>
                    <option value="meeting">Physical Meeting</option>
                    <option value="video_call">Live Zoom/Video Call</option>
                    <option value="reminder">Internal Dashboard Task Only</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Action & Discussion Agenda</label>
                  <textarea
                    rows={3}
                    required
                    value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                    placeholder="Enter discussion agenda or checklist..."
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  />
                </div>

                {/* Alarm toggles */}
                <div className="space-y-3 pt-3 border-t border-slate-200 text-sm font-semibold">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-700 flex items-center gap-1.5"><Bell className="w-4 h-4 text-sky-600" /> Notifications</span>
                    <input
                      type="checkbox"
                      checked={form.reminder_enabled}
                      onChange={(e) => setForm({ ...form, reminder_enabled: e.target.checked })}
                      className="w-4 h-4 text-sky-600 focus:ring-sky-500 border-slate-300 rounded"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-700 flex items-center gap-1.5"><AlertCircle className="w-4 h-4 text-amber-600" /> Overdue Escalation</span>
                    <input
                      type="checkbox"
                      checked={form.escalation_enabled}
                      onChange={(e) => setForm({ ...form, escalation_enabled: e.target.checked })}
                      className="w-4 h-4 text-sky-600 focus:ring-sky-500 border-slate-300 rounded"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  Schedule Next Follow-Up
                </button>
              </form>
            </div>
          </div>

          {/* Right Column: Scheduled List */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
              <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
                <h3 className="font-display text-sm font-bold text-slate-900 uppercase tracking-wider">Scheduled Activities & Follow-ups</h3>
                <span className="text-xs font-semibold text-slate-500 font-mono">{followUps.length} entries scheduled</span>
              </div>

              {followUps.length === 0 ? (
                <div className="p-16 text-center space-y-3">
                  <Clock className="w-10 h-10 text-sky-600 mx-auto opacity-70" />
                  <h3 className="font-display text-lg font-bold text-slate-900">All follow-ups complete</h3>
                  <p className="text-sm text-slate-500 max-w-sm mx-auto">Nice job! There are no pending customer follow-ups currently scheduled.</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {followUps.map((item) => (
                    <div key={item.id} className="p-6 hover:bg-slate-50 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-3">
                          {getFupBadge(item.status)}
                          <span className="text-xs font-bold text-sky-600 uppercase bg-sky-50 px-2.5 py-0.5 rounded-md border border-sky-100">{item.type}</span>
                          <span className="text-xs text-slate-500 font-semibold font-mono flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-400" /> {item.follow_up_date} • {item.follow_up_time}
                          </span>
                        </div>
                        <h4 className="font-display text-base font-bold text-slate-900">Agenda: {item.notes}</h4>
                        <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                          <User className="w-3.5 h-3.5" />
                          <span>Owner Account: {item.created_by || "Admin"}</span>
                          {item.reminder_enabled && <span className="text-emerald-600 flex items-center gap-1">• <Bell className="w-3 h-3" /> SMS + Mail alert active</span>}
                          {item.escalation_enabled && <span className="text-rose-600 flex items-center gap-1">• <AlertCircle className="w-3 h-3" /> Auto-escalated</span>}
                        </div>
                      </div>

                      {item.status === "pending" && (
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => handleMarkCompleted(item.id)}
                            className="inline-flex items-center gap-1.5 px-4.5 py-2 rounded-xl text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 transition-all cursor-pointer"
                          >
                            <CheckCircle2 className="w-4 h-4" /> Mark Complete
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}