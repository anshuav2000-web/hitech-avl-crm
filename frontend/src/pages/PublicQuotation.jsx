import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Printer, FileText, CheckCircle2, Clock } from "lucide-react";

const money = (n) =>
  "\u20b9" +
  Number(n || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/**
 * Unauthenticated customer-facing quotation view, reached through the share link
 * minted by POST /quotations/{id}/share. It deliberately renders only commercial
 * terms -- never lead contact details or internal CRM fields.
 */
export default function PublicQuotation() {
  const { token } = useParams();
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    fetch(`${process.env.REACT_APP_API_URL || "http://localhost:8000/api"}/public/quotation/${token}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(r.status === 404 ? "This quotation link is invalid or has been revoked." : "Unable to load this quotation.");
        return r.json();
      })
      .then((d) => alive && setQuote(d))
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [token]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading quotation...</div>;
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" data-testid="public-quote-error">
        <div className="text-center">
          <FileText className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <p className="text-slate-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4" data-testid="public-quotation">
      <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-8 py-6 border-b border-slate-200 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">{quote.company_name || "Quotation"}</h1>
            <p className="font-mono text-sm text-slate-500 mt-1" data-testid="public-quote-no">
              {quote.quote_no}
            </p>
          </div>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-sky-600 text-white hover:bg-sky-500"
            data-testid="public-quote-print"
          >
            <Printer className="w-3.5 h-3.5" /> Print / Save PDF
          </button>
        </div>

        <div className="px-8 py-5 grid grid-cols-2 gap-4 text-sm border-b border-slate-100">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Prepared For</div>
            <div className="font-semibold text-slate-800">{quote.client_name}</div>
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Date</div>
            <div className="text-slate-700">{new Date(quote.created_at || Date.now()).toLocaleDateString("en-IN")}</div>
          </div>
        </div>

        <div className="px-8 py-5">
          <table className="w-full text-sm" data-testid="public-quote-items">
            <thead>
              <tr className="border-b border-slate-200 text-left">
                <th className="py-2 font-bold text-slate-600">Item</th>
                <th className="py-2 font-bold text-slate-600 text-right">Qty</th>
                <th className="py-2 font-bold text-slate-600 text-right">Rate</th>
                <th className="py-2 font-bold text-slate-600 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {(quote.items || []).map((it, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="py-2.5">
                    <div className="font-semibold text-slate-800">{it.product}</div>
                    {it.brand ? <div className="text-xs text-slate-500">{it.brand}</div> : null}
                  </td>
                  <td className="py-2.5 text-right text-slate-700">{it.qty}</td>
                  <td className="py-2.5 text-right text-slate-700">{money(it.unit_price)}</td>
                  <td className="py-2.5 text-right font-semibold text-slate-900">{money(it.line_total ?? it.unit_price * it.qty)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-5 ml-auto w-64 space-y-1.5 text-sm">
            <Row label="Subtotal" value={money(quote.subtotal)} />
            {quote.discount ? <Row label="Discount" value={`- ${money(quote.discount)}`} /> : null}
            <Row label="GST" value={money(quote.tax)} />
            <div className="flex justify-between pt-2 border-t border-slate-200 text-base font-bold text-slate-900">
              <span>Total</span>
              <span data-testid="public-quote-total">{money(quote.total)}</span>
            </div>
          </div>

          <div className="mt-6 flex items-center gap-2 text-xs text-slate-500">
            {quote.status === "accepted" ? (
              <><CheckCircle2 className="w-4 h-4 text-emerald-500" /> This quotation has been accepted.</>
            ) : (
              <><Clock className="w-4 h-4 text-slate-400" /> Prices are valid as per the terms above.</>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold text-slate-800">{value}</span>
    </div>
  );
}