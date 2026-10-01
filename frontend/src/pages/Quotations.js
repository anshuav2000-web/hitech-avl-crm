import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Plus, Copy, Download, FileCode, ShoppingBag, FolderKanban, Receipt, CheckCircle2, Send, Eye, Pencil, Trash2 } from "lucide-react";
import PdfPreviewModal from "@/components/PdfPreviewModal";
import QuotationActions from "@/components/quotations/QuotationActions";

const STATUS = ["draft", "under_review", "sent", "viewed", "accepted", "rejected", "expired"];
const statusStyle = {
  draft: "bg-slate-100 text-slate-700 border-slate-200",
  under_review: "bg-amber-50 text-amber-700 border-amber-200",
  sent: "bg-sky-50 text-sky-700 border-sky-200",
  viewed: "bg-indigo-50 text-indigo-700 border-indigo-200",
  accepted: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-rose-50 text-rose-700 border-rose-200",
  expired: "bg-slate-200 text-slate-600 border-slate-300",
};

export default function Quotations() {
  const { user } = useAuth();
  const isAdmin = user?.role === "superadmin" || user?.role === "admin";

  const [quotes, setQuotes] = useState([]);
  const [leads, setLeads] = useState([]);
  const [msg, setMsg] = useState("");
  const [previewTarget, setPreviewTarget] = useState(null);

  const load = () => Promise.all([
    api.get("/quotations"),
    api.get("/leads")
  ]).then(([q, l]) => {
    setQuotes(q.data || []);
    setLeads(l.data || []);
  });

  useEffect(() => { load(); }, []);

  const leadName = (id) => {
    const l = leads.find((x) => x.id === id);
    return l ? `${l.name} (${l.company || "Client"})` : "—";
  };

  const totalVal = quotes.reduce((s, q) => s + Number(q.total || 0), 0);

  const changeStatus = async (id, status) => {
    await api.patch(`/quotations/${id}`, { status });
    load();
  };

  const deleteQuote = async (id, quoteNo) => {
    if (!window.confirm(`SUPER ADMIN: Are you sure you want to permanently delete quotation ${quoteNo}?`)) return;
    try {
      await api.delete(`/quotations/${id}`);
      setMsg(`Quotation ${quoteNo} deleted successfully.`);
      load();
    } catch (e) {
      alert("Delete failed: " + e.message);
    }
  };

  const convertToSO = async (id, quoteNo) => {
    try {
      await api.post(`/quotations/${id}/convert-to-sales-order`);
      setMsg(`Quotation ${quoteNo} converted to Sales Order in Accounting!`);
      load();
    } catch (e) {
      alert("Conversion failed: " + e.message);
    }
  };

  const convertToProject = async (id, quoteNo) => {
    try {
      await api.post(`/quotations/${id}/convert-to-project`);
      setMsg(`Quotation ${quoteNo} converted to active Production Project!`);
      load();
    } catch (e) {
      alert("Conversion failed: " + e.message);
    }
  };

  const downloadPdf = async (id, quoteNo) => {
    const r = await api.get(`/quotations/${id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(r.data);
    const a = document.createElement("a");
    a.href = url; a.download = `${quoteNo}.pdf`;
    document.body.appendChild(a); a.click(); a.remove();
    window.URL.revokeObjectURL(url);
  };

  const sendQuoteWebhook = async (id, quoteNo) => {
    try {
      const res = await api.post(`/quotations/${id}/send-webhook`);
      setMsg(res.data?.message || `Quotation PDF ${quoteNo} sent to connected webhook!`);
    } catch (e) {
      alert("Webhook error: " + e.message);
    }
  };

  const downloadTally = async (id, quoteNo) => {
    const r = await api.get(`/quotations/${id}/tally-xml`, { responseType: "blob" });
    const url = window.URL.createObjectURL(r.data);
    const a = document.createElement("a");
    a.href = url; a.download = `${quoteNo}_tally.xml`;
    document.body.appendChild(a); a.click(); a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="quotations-page">
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Commercial Proposals</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Receipt className="w-8 h-8 text-sky-600" /> Commercial Quotations
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            {quotes.length} active quotes · Total Value: <span className="text-slate-900 font-extrabold font-display">₹{totalVal.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span>
          </p>
        </div>

        <Link
          to="/quotations/new"
          data-testid="quotations-new-btn"
          className="inline-flex items-center gap-2 text-white px-5 py-2.5 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Build Quotation
        </Link>
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

      {/* Main Quotations Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-100/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 font-bold">
              <tr>
                <th className="px-6 py-4 font-bold">Quote Ref #</th>
                <th className="px-6 py-4 font-bold">Client / Lead</th>
                <th className="px-6 py-4 font-bold">Template</th>
                <th className="px-6 py-4 font-bold">Items</th>
                <th className="px-6 py-4 font-bold text-right">Grand Total</th>
                <th className="px-6 py-4 font-bold">Status</th>
                <th className="px-6 py-4 font-bold text-right">Preview, PDF & Super Admin Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {quotes.length === 0 && (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-500 font-medium">No quotations generated yet. Click "Build Quotation" to create one.</td></tr>
              )}
              {quotes.map((q) => (
                <tr key={q.id} className="hover:bg-slate-50 transition-colors group" data-testid={`quote-row-${q.id}`}>
                  <td className="px-6 py-4 font-bold text-slate-900 font-mono">{q.quote_no}</td>
                  <td className="px-6 py-4">
                    <Link to={`/leads/${q.lead_id}`} className="text-slate-900 hover:text-sky-600 font-bold transition-colors">
                      {leadName(q.lead_id)}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-xs font-bold text-sky-700">
                    {q.template_type || "Corporate"}
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-600 font-mono">
                    {(q.items || []).length} lines
                  </td>
                  <td className="px-6 py-4 text-right font-display font-extrabold text-slate-900">
                    ₹{Number(q.total || 0).toLocaleString("en-IN")}
                  </td>
                  <td className="px-6 py-4">
                    <select
                      value={q.status}
                      onChange={(e) => changeStatus(q.id, e.target.value)}
                      data-testid={`quote-status-${q.id}`}
                      className={`text-xs font-bold border rounded-lg px-2.5 py-1 capitalize bg-white ${statusStyle[q.status] || statusStyle.draft}`}
                    >
                      {STATUS.map((s) => <option key={s} value={s} className="bg-white text-slate-900">{s.replace("_", " ")}</option>)}
                    </select>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-1.5 flex-wrap justify-end">
                      {/* PREVIEW BUTTON */}
                      <button
                        onClick={() => setPreviewTarget({
                          id: q.id,
                          quoteNo: q.quote_no,
                          title: `Quotation Proposal — ${q.quote_no}`,
                          pdfEndpoint: `/quotations/${q.id}/pdf`,
                          webhookEndpoint: `/quotations/${q.id}/send-webhook`
                        })}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-sky-800 bg-sky-50 border border-sky-200 hover:bg-sky-100 px-2.5 py-1 rounded-lg transition-all cursor-pointer"
                        title="Preview PDF Document"
                      >
                        <Eye className="w-3.5 h-3.5 text-sky-600" /> Preview
                      </button>

                      <button
                        onClick={() => downloadPdf(q.id, q.quote_no)}
                        data-testid={`quote-pdf-${q.id}`}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-white px-2.5 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 transition-all cursor-pointer"
                        title="Download Executive PDF Proposal"
                      >
                        <Download className="w-3 h-3" /> PDF
                      </button>

                      <button
                        onClick={() => sendQuoteWebhook(q.id, q.quote_no)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 px-2 py-1 rounded-lg transition-all cursor-pointer"
                        title="Send PDF Proposal to Connected Webhook"
                      >
                        <Send className="w-3 h-3 text-indigo-600" /> Webhook
                      </button>

                      <button
                        onClick={() => convertToSO(q.id, q.quote_no)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 px-2 py-1 rounded-lg transition-all cursor-pointer"
                        title="Convert to Sales Order"
                      >
                        <ShoppingBag className="w-3 h-3 text-emerald-600" /> Sales Order
                      </button>

                      <button
                        onClick={() => convertToProject(q.id, q.quote_no)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-800 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 px-2 py-1 rounded-lg transition-all cursor-pointer"
                        title="Convert to Production Project"
                      >
                        <FolderKanban className="w-3 h-3 text-indigo-600" /> Project
                      </button>

                      {/* SUPER ADMIN EDIT & DELETE ACTIONS */}
                      <Link
                        to={`/quotations/new?edit=${q.id}`}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 border border-slate-300 hover:bg-slate-200 px-2 py-1 rounded-lg transition-all"
                        title="Super Admin Edit Quotation"
                      >
                        <Pencil className="w-3 h-3 text-slate-700" /> Edit
                      </Link>

                      {isAdmin && (
                        <button
                          onClick={() => deleteQuote(q.id, q.quote_no)}
                          className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 px-2 py-1 rounded-lg transition-all cursor-pointer"
                          title="Super Admin Delete Quotation"
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

        {/* PHASE 5: Duplicate / Share / Approval ladder */}
        <div className="space-y-3">
          {quotes.map((q) => (
            <div key={q.id} className="bg-white rounded-xl border border-slate-200 p-3"
              data-testid={`quote-actionbar-${q.id}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-xs font-bold text-slate-700">{q.quote_no}</span>
                <span className="text-[11px] text-slate-500 truncate">Duplicate, share and approve this quotation</span>
              </div>
              <QuotationActions
                quote={q}
                onDone={(result) => {
                  if (result?.message) setMsg(result.message);
                  load();
                }}
              />
            </div>
          ))}
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
