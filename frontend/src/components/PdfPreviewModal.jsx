import { useState, useEffect } from "react";
import { X, Download, Send, Eye, FileText, Printer } from "lucide-react";
import { api } from "@/lib/api";

export default function PdfPreviewModal({ title, quoteNo, pdfEndpoint, webhookEndpoint, onClose, onWebhookSent }) {
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingWebhook, setSendingWebhook] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    let activeUrl = null;
    api.get(pdfEndpoint, { responseType: "blob" })
      .then((res) => {
        const blob = new Blob([res.data], { type: "application/pdf" });
        activeUrl = URL.createObjectURL(blob);
        setPdfUrl(activeUrl);
      })
      .catch((err) => {
        console.error("PDF load error:", err);
      })
      .finally(() => setLoading(false));

    return () => {
      if (activeUrl) URL.revokeObjectURL(activeUrl);
    };
  }, [pdfEndpoint]);

  const handleDownload = () => {
    if (!pdfUrl) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `${quoteNo || "Document"}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const handleWebhook = async () => {
    if (!webhookEndpoint) return;
    setSendingWebhook(true);
    try {
      const res = await api.post(webhookEndpoint);
      setMsg(res.data?.message || "PDF successfully sent to connected webhook!");
      if (onWebhookSent) onWebhookSent(res.data?.message);
    } catch (err) {
      alert("Webhook error: " + err.message);
    } finally {
      setSendingWebhook(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-scale-in">
        {/* Header bar */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-100 border border-sky-200 flex items-center justify-center text-sky-700">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-sky-700">PDF Preview Mode</div>
              <h3 className="font-display text-lg font-black text-slate-900">{title || quoteNo || "Document Preview"}</h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {webhookEndpoint && (
              <button
                onClick={handleWebhook}
                disabled={sendingWebhook}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 transition-all cursor-pointer"
              >
                <Send className={`w-3.5 h-3.5 ${sendingWebhook ? "animate-pulse" : ""}`} />
                {sendingWebhook ? "Sending..." : "Send Webhook"}
              </button>
            )}

            <button
              onClick={handleDownload}
              disabled={!pdfUrl}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-sm transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" /> Download PDF
            </button>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-900 hover:bg-slate-200 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {msg && (
          <div className="px-6 py-2 bg-emerald-50 border-b border-emerald-200 text-xs font-bold text-emerald-800 flex justify-between items-center">
            <span>{msg}</span>
            <button onClick={() => setMsg("")} className="text-slate-400 hover:text-slate-800">Dismiss</button>
          </div>
        )}

        {/* PDF Viewer Body */}
        <div className="flex-1 bg-slate-100 p-4 overflow-hidden flex items-center justify-center relative">
          {loading ? (
            <div className="flex flex-col items-center gap-3 text-slate-600 font-bold text-sm">
              <div className="w-8 h-8 border-3 border-sky-600 border-t-transparent rounded-full animate-spin" />
              <span>Rendering Document Preview…</span>
            </div>
          ) : pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="w-full h-full rounded-xl border border-slate-200 bg-white shadow-md"
              title="PDF Preview"
            />
          ) : (
            <div className="text-slate-500 text-sm font-medium">Failed to load PDF preview.</div>
          )}
        </div>
      </div>
    </div>
  );
}
