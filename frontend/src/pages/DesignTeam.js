import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { 
  Wrench, ClipboardList, Layers, User, Sparkles, CheckCircle2, FileText, Plus, X, UploadCloud, AlertCircle
} from "lucide-react";
import { toast } from "sonner";

export default function DesignTeam() {
  const [designTasks, setDesignTasks] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const [form, setForm] = useState({
    lead_id: "",
    title: "",
    description: "",
    assigned_to: "admin",
    drawing_type: "floor_plan",
    status: "pending",
    priority: "medium",
    due_date: new Date().toISOString().split("T")[0],
    revision: 1,
    auto_notify_sales: true
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tasks, lds] = await Promise.all([
        api.get("/design-tasks"),
        api.get("/leads")
      ]);
      setDesignTasks(tasks.data);
      setLeads(lds.data);
      if (lds.data.length > 0) {
        setForm((prev) => ({ ...prev, lead_id: lds.data[0].id }));
      }
    } catch (err) {
      toast.error("Failed to load design assignments.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.post("/design-tasks", form);
      toast.success("Design CAD Task assigned successfully!");
      setShowModal(false);
      fetchData();
    } catch (err) {
      toast.error("Failed to assign task.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateStatus = async (id, status) => {
    try {
      await api.patch(`/design-tasks/${id}`, { status });
      toast.success("Drawing coordinator status updated.");
      fetchData();
    } catch (err) {
      toast.error("Failed to update status.");
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "approved":
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Approved</span>;
      case "review":
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">In Review</span>;
      case "in_progress":
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">In Progress</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-50 text-slate-700 border border-slate-200">Pending</span>;
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-8 bg-white text-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-sky-700 font-bold uppercase tracking-wider mb-2">
            <span>Enterprise Design & Projects</span>
            <span>/</span>
            <span className="text-slate-900">CAD Team Coordinator</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Layers className="w-8 h-8 text-sky-600" />
            Design CAD & Acoustic Layout Coordinator
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Coordinate layout diagrams, 3D audio renders, wiring systems, and signal elevations. System automatically notifies the sales team on drawing revisions and sign-offs.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" /> Create Design CAD Task
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-slate-500 text-sm font-medium">Loading CAD coordinator...</div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
            <h3 className="font-display text-sm font-bold text-slate-900 uppercase tracking-wider">Active CAD drawings & acoustic plans</h3>
            <span className="text-xs font-semibold text-slate-500 font-mono">{designTasks.length} active assignments</span>
          </div>

          {designTasks.length === 0 ? (
            <div className="p-16 text-center space-y-3">
              <Layers className="w-10 h-10 text-sky-600 mx-auto opacity-70 animate-pulse" />
              <h3 className="font-display text-lg font-bold text-slate-900">No active CAD drawings</h3>
              <p className="text-sm text-slate-500 max-w-sm mx-auto">Create a drawing task for floor plans, custom sound layouts, or venue elevations.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {designTasks.map((task) => (
                <div key={task.id} className="p-6 hover:bg-slate-50 transition-all flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3 flex-wrap">
                      {getStatusBadge(task.status)}
                      <span className="text-xs font-bold text-sky-600 uppercase bg-sky-50 px-2.5 py-0.5 rounded-md border border-sky-100 capitalize">{task.drawing_type?.replace("_", " ")}</span>
                      <span className="text-xs font-mono font-bold bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-0.5 rounded-md">Revision v{task.revision}</span>
                      <span className="text-xs text-slate-500 font-mono font-semibold">Due: {task.due_date}</span>
                    </div>
                    <h4 className="font-display text-lg font-bold text-slate-900">{task.title}</h4>
                    <p className="text-sm text-slate-600 font-medium">{task.description}</p>
                    <div className="flex items-center gap-4 text-xs font-semibold text-slate-500">
                      <span className="flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> Assigned: {task.assigned_to}</span>
                      {task.auto_notify_sales && <span className="text-emerald-600 font-bold flex items-center gap-1">• Sales automated notifications active</span>}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap shrink-0">
                    {task.status !== "approved" && (
                      <>
                        <button
                          onClick={() => handleUpdateStatus(task.id, "in_progress")}
                          className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 border border-slate-200 cursor-pointer"
                        >
                          Work on it
                        </button>
                        <button
                          onClick={() => handleUpdateStatus(task.id, "review")}
                          className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 cursor-pointer"
                        >
                          Submit for Approval
                        </button>
                        <button
                          onClick={() => handleUpdateStatus(task.id, "approved")}
                          className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 cursor-pointer"
                        >
                          Sign-off & Approve
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Assignment Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-scale-in text-slate-900">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sky-600" /> Assign CAD Drawing Task
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
            </div>
            
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Select Lead / Installation</label>
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

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Drawing Title *</label>
                <input
                  required
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g., Main Hall Line Array Layout"
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                />
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Acoustic Elevation / Drawing Guidelines</label>
                <textarea
                  rows={3}
                  required
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Include angle coordinates, acoustic delays or layout specifications..."
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Drawing Category</label>
                  <select
                    value={form.drawing_type}
                    onChange={(e) => setForm({ ...form, drawing_type: e.target.value })}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  >
                    <option value="floor_plan">Acoustic Floor Plan</option>
                    <option value="elevation">Speaker Elevation</option>
                    <option value="wiring_diagram">System Wiring Diagram</option>
                    <option value="3d_render">3D acoustic venue rendering</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Target Due Date</label>
                  <input
                    type="date"
                    required
                    value={form.due_date}
                    onChange={(e) => setForm({ ...form, due_date: e.target.value })}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-medium"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 cursor-pointer disabled:opacity-50"
                >
                  Assign & Start Track
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}