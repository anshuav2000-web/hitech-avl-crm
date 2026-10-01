import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Download, Send, CheckCircle2, FileText, Eye, Pencil, Trash2, X } from "lucide-react";
import PdfPreviewModal from "@/components/PdfPreviewModal";

const TYPES = ["invoice", "estimate", "expense", "payment"];
const STATUSES = ["draft", "sent", "paid", "overdue", "cancelled"];

export default function Accounting() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "superadmin" || user?.role === "admin";

  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [msg, setMsg] = useState("");
  const [previewTarget, setPreviewTarget] = useState(null);
  const [form, setForm] = useState({ doc_no: "", type: "invoice", party: "", amount: "", status: "draft", date: "" });

  const load = () => {
    api.get("/accounting").then((r) => setItems(r.data || []));
  };

  useEffect(() => { load(); }, []);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const startEdit = (doc) => {
    setEditingId(doc.id);
    setForm({
      doc_no: doc.doc_no || "",
      type: doc.type || "invoice",
      party: doc.party || "",
      amount: doc.amount || "",
      status: doc.status || "draft",
      date: doc.date || ""
    });
    setShowForm(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.patch(`/accounting/${editingId}`, {
          ...form,
          amount: Number(form.amount || 0)
        });
        setMsg(`Invoice record ${form.doc_no} updated successfully!`);
      } else {
        const r = await api.post("/accounting", {
          ...form,
          amount: Number(form.amount || 0)
        });
        setMsg(`Invoice record ${r.data.doc_no} created successfully!`);
      }
      setShowForm(false);
      setEditingId(null);
      setForm({ doc_no: "", type: "invoice", party: "", amount: "", status: "draft", date: "" });
      load();
    } catch (err) {
      alert("Error saving record: " + err.message);
    }
  };

  const deleteInvoice = async (id, docNo) => {
    if (!window.confirm(`SUPER ADMIN: Are you sure you want to permanently delete document ${docNo}?`)) return;
    try {
      await api.delete(`/accounting/${id}`);
      setMsg(`Document ${docNo} deleted successfully.`);
      load();
    } catch (err) {
      alert("Delete error: " + err.message);
    }
  };

  const downloadInvoicePdf = async (id, docNo) => {
    try {
      const r = await api.get(`/accounting/${id}/pdf`, { responseType: "blob" });
      const url = window.URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${docNo || "Invoice"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Error generating Invoice PDF: " + e.message);
    }
  };

  const sendInvoiceWebhook = async (id, docNo) => {
    try {
      const res = await api.post(`/accounting/${id}/send-webhook`);
      setMsg(res.data?.message || `Invoice PDF ${docNo} sent to connected webhook!`);
    } catch (e) {
      alert("Webhook dispatch error: " + e.message);
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="accounting-page">
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Finance & Billing</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <FileText className="w-8 h-8 text-sky-600" /> Accounting & Invoices
          </h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} accounting records in your financial ledger</p>
        </div>
        <button
          onClick={() => { setEditingId(null); setForm({ doc_no: "", type: "invoice", party: "", amount: "", status: "draft", date: "" }); setShowForm(true); }}
          data-testid="accounting-add-btn"
          className="inline-flex items-center gap-2 bg-sky-600 text-white px-5 py-2.5 rounded-xl text-xs font-bold hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Create Document
        </button>
      </header>

      {msg && (
        <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-800 text-xs flex items-center justify-between font-bold">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{msg}</span>
          </div>
          <button onClick={() => setMsg("")} className="hover:text-slate-900 text-slate-500">Dismiss</button>
        </div>
      )}

      {showForm && (
        <form onSubmit={submit} className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <h3 className="font-display text-base font-bold text-slate-900">{editingId ? "Super Admin: Edit Invoice Record" : "Create New Document"}</h3>
            <button type="button" onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Doc No *" value={form.doc_no} onChange={(v) => update("doc_no", v)} testid="af-doc" />
            <Select label="Type" value={form.type} onChange={(v) => update("type", v)} options={TYPES} testid="af-type" />
            <Field label="Party / Client" value={form.party} onChange={(v) => update("party", v)} testid="af-party" />
            <Field label="Amount (INR)" type="number" value={form.amount} onChange={(v) => update("amount", v)} testid="af-amount" />
            <Select label="Status" value={form.status} onChange={(v) => update("status", v)} options={STATUSES} testid="af-status" />
            <Field label="Date" type="date" value={form.date} onChange={(v) => update("date", v)} testid="af-date" />
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
            <button type="submit" data-testid="af-submit" className="inline-flex items-center gap-2 bg-sky-600 text-white px-5 py-2 rounded-xl text-xs font-bold hover:bg-sky-500">
              {editingId ? "Update Document" : "Save Record"}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-100/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 font-bold">
              <tr>
                <th className="px-6 py-4 font-bold">Doc No</th>
                <th className="px-6 py-4 font-bold">Type</th>
                <th className="px-6 py-4 font-bold">Client / Party</th>
                <th className="px-6 py-4 font-bold text-right">Amount (INR)</th>
                <th className="px-6 py-4 font-bold">Status</th>
                <th className="px-6 py-4 font-bold">Date</th>
                <th className="px-6 py-4 font-bold text-right">Preview, PDF & Super Admin Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.length === 0 && (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-500 font-medium">No financial documents logged yet.</td></tr>
              )}
              {items.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50 transition-colors group">
                  <td className="px-6 py-4 font-bold text-slate-900 font-mono">{a.doc_no}</td>
                  <td className="px-6 py-4 uppercase text-xs font-bold text-sky-700">{a.type}</td>
                  <td className="px-6 py-4 text-slate-800 font-bold">{a.party || "—"}</td>
                  <td className="px-6 py-4 text-right font-display font-extrabold text-slate-900">
                    {a.amount ? `₹${Number(a.amount).toLocaleString("en-IN")}` : "—"}
                  </td>
                  <td className="px-6 py-4"><StatusBadge status={a.status} /></td>
                  <td className="px-6 py-4 text-slate-500 text-xs font-mono">{a.date ? new Date(a.date).toLocaleDateString() : "—"}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-1.5 flex-wrap justify-end">
                      <button
                        onClick={() => setPreviewTarget({
                          id: a.id,
                          quoteNo: a.doc_no,
                          title: `Tax Invoice — ${a.doc_no}`,
                          pdfEndpoint: `/accounting/${a.id}/pdf`,
                          webhookEndpoint: `/accounting/${a.id}/send-webhook`
                        })}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-sky-800 bg-sky-50 border border-sky-200 hover:bg-sky-100 px-2.5 py-1 rounded-lg transition-all cursor-pointer"
                        title="Preview PDF Document"
                      >
                        <Eye className="w-3.5 h-3.5 text-sky-600" /> Preview
                      </button>

                      <button
                        onClick={() => downloadInvoicePdf(a.id, a.doc_no)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-white bg-sky-600 hover:bg-sky-500 px-2.5 py-1 rounded-lg transition-all shadow-2xs cursor-pointer"
                        title="Download Executive PDF Invoice"
                      >
                        <Download className="w-3.5 h-3.5" /> PDF
                      </button>

                      <button
                        onClick={() => sendInvoiceWebhook(a.id, a.doc_no)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 px-2 py-1 rounded-lg transition-all cursor-pointer"
                        title="Send PDF Invoice to Connected Webhook"
                      >
                        <Send className="w-3.5 h-3.5 text-indigo-600" /> Webhook
                      </button>

                      {/* SUPER ADMIN EDIT & DELETE ACTIONS */}
                      <button
                        onClick={() => startEdit(a)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 border border-slate-300 hover:bg-slate-200 px-2 py-1 rounded-lg transition-all cursor-pointer"
                        title="Super Admin Edit Document"
                      >
                        <Pencil className="w-3 h-3 text-slate-700" /> Edit
                      </button>

                      {isAdmin && (
                        <button
                          onClick={() => deleteInvoice(a.id, a.doc_no)}
                          className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 px-2 py-1 rounded-lg transition-all cursor-pointer"
                          title="Super Admin Delete Document"
                        >
                          <Trash2 className="w-3 h-3 text-rose-600" /> Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* PDF Preview Modal */}
      {previewTarget && (
        <PdfPreviewModal
          title={previewTarget.title}
          quoteNo={previewTarget.quoteNo}
          pdfEndpoint={previewTarget.pdfEndpoint}
          webhookEndpoint={previewTarget.webhookEndpoint}
          onClose={() => setPreviewTarget(null)}
          onWebhookSent={(m) => setMsg(m)}
        />
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    draft: "bg-slate-100 text-slate-700 border-slate-200",
    sent: "bg-sky-50 text-sky-700 border-sky-200",
    paid: "bg-emerald-50 text-emerald-700 border-emerald-200",
    overdue: "bg-rose-50 text-rose-700 border-rose-200",
    cancelled: "bg-slate-200 text-slate-600 border-slate-300",
  };
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border capitalize ${map[status] || map.draft}`}>
      {status || "draft"}
    </span>
  );
}

function Field({ label, value, onChange, type = "text", testid }) {
  return (
    <div>
      <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">{label}</label>
      <input data-testid={testid} type={type} value={value} onChange={(e) => onChange(e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
    </div>
  );
}

function Select({ label, value, onChange, options, testid }) {
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <div>
      <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">{label}</label>
      <select data-testid={testid} value={value} onChange={(e) => onChange(e.target.value)} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium capitalize">
        {opts.map((o) => (
          <option key={o.value} value={o.value} className="capitalize">{o.label}</option>
        ))}
      </select>
    </div>
  );
}
