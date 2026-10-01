import { useState } from "react";
import { Copy, Share2, CheckCircle2, XCircle, Send, Printer, Link2, MessageCircle, Mail, ShoppingCart } from "lucide-react";
import { api } from "@/lib/api";

const btn = "inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-lg transition-all";
const primary = `${btn} text-white bg-sky-600 hover:bg-sky-500 shadow-sm`;
const ghost = `${btn} text-slate-700 bg-slate-100 border border-slate-300 hover:bg-slate-200`;
const danger = `${btn} text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100`;

/**
 * Phase 5 quotation actions: duplicate, share (WhatsApp/email/link/print) and the
 * approval ladder.
 *
 * Approval goes through POST /approval rather than a bare status PATCH so the
 * server records who approved, when, and why -- and so accepting a quotation also
 * advances the lead to the real won stage.
 */
export default function QuotationActions({ quote, onDone, canEdit = true }) {
  const [busy, setBusy] = useState(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState(null);
  const [shareResult, setShareResult] = useState(null);

  const run = async (key, fn) => {
    setBusy(key);
    setError(null);
    try {
      await fn();
      onDone?.();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Action failed");
    } finally {
      setBusy(null);
    }
  };

  const duplicate = () =>
    run("duplicate", async () => {
      const { data } = await api.post(`/quotations/${quote.id}/duplicate`);
      onDone?.({ message: `Duplicated as ${data.quote_no}` });
    });

  const approve = () =>
    run("approve", () =>
      api.post(`/quotations/${quote.id}/approval`, { action: "approve", note: note || undefined })
    );

  const reject = () =>
    run("reject", () =>
      api.post(`/quotations/${quote.id}/approval`, { action: "reject", note: note || undefined })
    );

  const submit = () => run("submit", () => api.post(`/quotations/${quote.id}/approval`, { action: "submit" }));
  const reopen = () => run("reopen", () => api.post(`/quotations/${quote.id}/approval`, { action: "reopen" }));

  // Phase 6: quotation -> customer PO. A quotation can only be converted once, so
  // once converted the button becomes a link to the PO it produced.
  const convertToPO = () =>
    run("convert", async () => {
      const { data } = await api.post(`/quotations/${quote.id}/convert-to-po`);
      onDone?.({ message: `Customer PO ${data.purchase_order.po_no} created`, poId: data.purchase_order.id });
    });

  const share = async (channel) => {
    await run(`share-${channel}`, async () => {
      const { data } = await api.post(`/quotations/${quote.id}/share`, {
        channel,
        recipient: recipient || undefined,
      });
      setShareResult({ channel, ...data });
      if (channel === "whatsapp" && data.url) window.open(data.url, "_blank", "noopener");
      if (channel === "email" && data.ok) {
        setShareResult(null);
        setRecipient("");
      }
    });
  };

  const printPdf = () =>
    run("print", async () => {
      // Ask the server to mint the share token first so a printed copy and the
      // emailed link are traceable to the same share event.
      const r = await api.get(`/quotations/${quote.id}/pdf`, { responseType: "blob" });
      const url = window.URL.createObjectURL(r.data);
      const frame = document.createElement("iframe");
      frame.style.display = "none";
      frame.src = url;
      document.body.appendChild(frame);
      frame.onload = () => {
        frame.contentWindow?.print();
        setTimeout(() => {
          frame.remove();
          window.URL.revokeObjectURL(url);
        }, 1000);
      };
    });

  const copyLink = () => {
    if (shareResult?.public_url) navigator.clipboard?.writeText(shareResult.public_url);
  };

  const terminal = ["accepted", "rejected", "expired"].includes(quote.status);

  return (
    <div className="flex flex-col gap-2" data-testid={`quote-actions-${quote.id}`}>
      <div className="flex flex-wrap items-center gap-1.5">
        <button type="button" className={ghost} onClick={duplicate} disabled={busy === "duplicate" || !canEdit}
          data-testid={`quote-duplicate-${quote.id}`}>
          <Copy className="w-3 h-3" /> Duplicate
        </button>

        <button type="button" className={ghost} onClick={() => setShareOpen((v) => !v)}
          data-testid={`quote-share-${quote.id}`}>
          <Share2 className="w-3 h-3" /> Share
        </button>

        {!terminal ? (
          <>
            {quote.status === "draft" && (
              <button type="button" className={primary} onClick={submit} disabled={busy === "submit"}
                data-testid={`quote-submit-${quote.id}`}>
                <Send className="w-3 h-3" /> Submit for approval
              </button>
            )}
            <button type="button" className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 px-2.5 py-1 rounded-lg transition-all"
              onClick={approve} disabled={busy === "approve" || !canEdit}
              data-testid={`quote-approve-${quote.id}`}>
              <CheckCircle2 className="w-3 h-3" /> Approve
            </button>
            <button type="button" className={danger} onClick={reject} disabled={busy === "reject" || !canEdit}
              data-testid={`quote-reject-${quote.id}`}>
              <XCircle className="w-3 h-3" /> Reject
            </button>
          </>
        ) : (
          <button type="button" className={ghost} onClick={reopen} disabled={busy === "reopen"}
            data-testid={`quote-reopen-${quote.id}`}>
            Reopen
          </button>
        )}

        {quote.converted_to_po ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg"
            data-testid={`quote-po-converted-${quote.id}`}>
            PO {quote.converted_po_no || "created"}
          </span>
        ) : (
          <button type="button" className={ghost} onClick={convertToPO}
            disabled={busy === "convert" || !canEdit}
            data-testid={`quote-convert-po-${quote.id}`}>
            <ShoppingCart className="w-3 h-3" /> Convert to PO
          </button>
        )}
      </div>

      {shareOpen ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-2" data-testid="share-panel">
          <input
            type="text"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder="Email or WhatsApp number (optional)"
            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs"
            data-testid="share-recipient"
          />
          <div className="flex flex-wrap gap-1.5">
            <button type="button" className={primary} onClick={() => share("email")} data-testid="share-email">
              <Mail className="w-3 h-3" /> Email
            </button>
            <button type="button" className={primary} onClick={() => share("whatsapp")} data-testid="share-whatsapp">
              <MessageCircle className="w-3 h-3" /> WhatsApp
            </button>
            <button type="button" className={ghost} onClick={() => share("link")} data-testid="share-link">
              <Link2 className="w-3 h-3" /> Copy link
            </button>
            <button type="button" className={ghost} onClick={printPdf} data-testid="share-print">
              <Printer className="w-3 h-3" /> Print
            </button>
          </div>
          {shareResult?.public_url ? (
            <div className="flex items-center gap-2 text-[11px] text-slate-600" data-testid="share-result">
              <span className="truncate font-mono">{shareResult.public_url}</span>
              <button type="button" className="text-sky-600 font-bold shrink-0" onClick={copyLink}>
                copy
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {error ? <div className="text-[11px] font-bold text-rose-600">{error}</div> : null}
    </div>
  );
}
