import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, FileSpreadsheet, CheckCircle2, Sparkles, ArrowRight } from "lucide-react";

export default function Import() {
  const [tab, setTab] = useState("leads");
  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="import-page">
      <header className="mb-6">
        <div className="label-eyebrow mb-2">Admin · Migration</div>
        <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Bring your existing data in</h1>
        <p className="text-sm text-slate-600 mt-1">CSV/Excel for prospects · AI-powered PDF parsing for past quotations.</p>
      </header>

      <div className="flex gap-2 mb-5 border-b border-slate-200">
        {[
          { key: "leads", label: "Leads (CSV / Excel)", icon: FileSpreadsheet },
          { key: "pdf", label: "Quotations (PDF · AI)", icon: FileText },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            data-testid={`import-tab-${t.key}`}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              tab === t.key ? "border-red-600 text-slate-900" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {tab === "leads" ? <LeadsImport /> : <PdfImport />}
    </div>
  );
}

function LeadsImport() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setErr(""); setResult(null); setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/import/leads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(r.data);
    } catch (e2) { setErr(formatApiError(e2)); }
    finally { setBusy(false); }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-md p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="label-eyebrow mb-2">Step 1 · Upload your file</div>
          <h2 className="font-display text-lg font-bold text-slate-900 mb-1">Bulk-add prospects</h2>
          <p className="text-sm text-slate-600 mb-4">Common columns are auto-detected: <strong>Name</strong>, Email, Phone/WhatsApp, Company, Source, Stage, Interested In, Budget, Notes. Only <strong>Name</strong> is required.</p>

          <form onSubmit={submit} className="space-y-3">
            <label className="block border-2 border-dashed border-slate-300 rounded-md p-6 text-center hover:border-slate-400 cursor-pointer transition-colors">
              <input
                data-testid="import-leads-file"
                type="file"
                accept=".csv,.xlsx"
                onChange={(e) => setFile(e.target.files[0])}
                className="hidden"
              />
              <Upload className="w-6 h-6 text-slate-400 mx-auto mb-2" />
              <div className="text-sm font-semibold text-slate-700">{file ? file.name : "Click to select .csv or .xlsx"}</div>
              <div className="text-xs text-slate-500 mt-1">Max ~5,000 rows per upload</div>
            </label>
            {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">{err}</div>}
            <button
              type="submit"
              disabled={!file || busy}
              data-testid="import-leads-submit"
              className="w-full inline-flex items-center justify-center gap-2 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50"
              style={{ background: "#DC2626" }}
            >
              {busy ? "Importing…" : "Import leads"} <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>

        <div>
          <div className="label-eyebrow mb-2">Step 2 · Result</div>
          {!result ? (
            <div className="bg-slate-50 border border-slate-200 rounded-md p-6 text-center text-sm text-slate-500">Results will appear here after import.</div>
          ) : (
            <div className="bg-green-50 border border-green-200 rounded-md p-5" data-testid="import-leads-result">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-5 h-5 text-green-700" />
                <div className="font-display text-base font-bold text-green-900">Import complete</div>
              </div>
              <div className="text-sm text-green-800 leading-relaxed">
                <strong>{result.created}</strong> leads created · <strong>{result.skipped}</strong> skipped · <strong>{result.total}</strong> total rows.
              </div>
              {result.errors?.length > 0 && (
                <details className="mt-3 text-xs">
                  <summary className="cursor-pointer text-slate-700">View {result.errors.length} errors</summary>
                  <ul className="mt-2 space-y-1 list-disc pl-5">
                    {result.errors.map((e, i) => <li key={i} className="text-slate-600">{e}</li>)}
                  </ul>
                </details>
              )}
            </div>
          )}
          <div className="text-xs text-slate-500 mt-4">
            <strong>Tip:</strong> column headers don't need to be exact. We match common variants like "Contact Name", "Mobile No", "Org", "Lead Source", "Remarks".
          </div>
        </div>
      </div>
    </div>
  );
}

function PdfImport() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [parsed, setParsed] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const parseFile = async () => {
    if (!file) return;
    setBusy(true); setErr(""); setParsed(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/import/quotation-pdf/parse", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setParsed(r.data.parsed);
    } catch (e) { setErr(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const updateField = (path, value) => {
    setParsed((p) => ({ ...p, [path]: value }));
  };
  const updateItem = (i, key, value) => {
    setParsed((p) => ({ ...p, items: p.items.map((it, idx) => idx === i ? { ...it, [key]: value } : it) }));
  };

  const confirm = async () => {
    setBusy(true); setErr("");
    try {
      const r = await api.post("/import/quotation-pdf/confirm", parsed);
      navigate(`/leads/${r.data.lead_id}`);
    } catch (e) { setErr(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const subtotal = parsed?.items?.reduce((s, i) => s + Number(i.qty || 0) * Number(i.unit_price || 0), 0) || 0;
  const tax = parsed?.items?.reduce((s, i) => s + Number(i.qty || 0) * Number(i.unit_price || 0) * (Number(i.tax_pct || 0) / 100), 0) || 0;

  return (
    <div className="bg-white border border-slate-200 rounded-md p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="label-eyebrow mb-2">Step 1 · Drop your PDF</div>
          <h2 className="font-display text-lg font-bold text-slate-900 mb-1">Parse past quotations with AI</h2>
          <p className="text-sm text-slate-600 mb-4">Claude reads your PDF and extracts customer, line items, and totals. Review and confirm — we'll create the quotation (and auto-create the lead if needed).</p>

          <label className="block border-2 border-dashed border-slate-300 rounded-md p-6 text-center hover:border-slate-400 cursor-pointer transition-colors">
            <input
              data-testid="import-pdf-file"
              type="file"
              accept=".pdf"
              onChange={(e) => { setFile(e.target.files[0]); setParsed(null); }}
              className="hidden"
            />
            <Upload className="w-6 h-6 text-slate-400 mx-auto mb-2" />
            <div className="text-sm font-semibold text-slate-700">{file ? file.name : "Click to select .pdf"}</div>
            <div className="text-xs text-slate-500 mt-1">Text-based PDF (not scanned image)</div>
          </label>

          <button
            onClick={parseFile}
            disabled={!file || busy}
            data-testid="import-pdf-parse"
            className="w-full mt-3 inline-flex items-center justify-center gap-2 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50"
            style={{ background: "#0F172A" }}
          >
            <Sparkles className="w-4 h-4" />
            {busy && !parsed ? "AI parsing…" : "Parse with AI"}
          </button>
          {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md mt-3">{err}</div>}
        </div>

        <div>
          <div className="label-eyebrow mb-2">Step 2 · Review & save</div>
          {!parsed ? (
            <div className="bg-slate-50 border border-slate-200 rounded-md p-6 text-center text-sm text-slate-500">Upload a PDF on the left to see AI-extracted data here.</div>
          ) : (
            <div className="space-y-3" data-testid="import-pdf-review">
              <div className="grid grid-cols-2 gap-2">
                <input value={parsed.customer_name || ""} onChange={(e) => updateField("customer_name", e.target.value)} placeholder="Customer name *" className="border border-slate-200 rounded-md text-sm px-2 py-1.5" data-testid="pdf-customer-name" />
                <input value={parsed.customer_company || ""} onChange={(e) => updateField("customer_company", e.target.value)} placeholder="Company" className="border border-slate-200 rounded-md text-sm px-2 py-1.5" />
                <input value={parsed.customer_email || ""} onChange={(e) => updateField("customer_email", e.target.value)} placeholder="Email" className="border border-slate-200 rounded-md text-sm px-2 py-1.5" />
                <input value={parsed.customer_phone || ""} onChange={(e) => updateField("customer_phone", e.target.value)} placeholder="Phone" className="border border-slate-200 rounded-md text-sm px-2 py-1.5" />
              </div>
              <div>
                <div className="label-eyebrow mb-1">Items</div>
                <div className="border border-slate-200 rounded-md max-h-60 overflow-y-auto">
                  {(parsed.items || []).map((it, i) => (
                    <div key={i} className="border-b border-slate-100 last:border-0 p-2 grid grid-cols-12 gap-1 text-xs">
                      <input value={it.product || ""} onChange={(e) => updateItem(i, "product", e.target.value)} className="col-span-6 border border-slate-200 rounded-sm px-1.5 py-1" placeholder="Product" />
                      <input value={it.brand || ""} onChange={(e) => updateItem(i, "brand", e.target.value)} className="col-span-2 border border-slate-200 rounded-sm px-1.5 py-1" placeholder="Brand" />
                      <input type="number" value={it.qty || 1} onChange={(e) => updateItem(i, "qty", e.target.value)} className="col-span-1 border border-slate-200 rounded-sm px-1.5 py-1 text-center" />
                      <input type="number" value={it.unit_price || 0} onChange={(e) => updateItem(i, "unit_price", e.target.value)} className="col-span-2 border border-slate-200 rounded-sm px-1.5 py-1 text-right" placeholder="Unit ₹" />
                      <input type="number" value={it.tax_pct || 18} onChange={(e) => updateItem(i, "tax_pct", e.target.value)} className="col-span-1 border border-slate-200 rounded-sm px-1.5 py-1 text-center" placeholder="GST" />
                    </div>
                  ))}
                </div>
              </div>
              <div className="text-xs text-slate-700 border-t border-slate-200 pt-2 text-right">
                Subtotal ₹{subtotal.toLocaleString("en-IN", { maximumFractionDigits: 0 })} · GST ₹{tax.toLocaleString("en-IN", { maximumFractionDigits: 0 })} · <strong>Total ₹{(subtotal + tax).toLocaleString("en-IN", { maximumFractionDigits: 0 })}</strong>
              </div>
              <button
                onClick={confirm}
                disabled={busy || !parsed.customer_name}
                data-testid="import-pdf-confirm"
                className="w-full inline-flex items-center justify-center gap-2 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50"
                style={{ background: "#DC2626" }}
              >
                {busy ? "Saving…" : "Create lead + quotation"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
