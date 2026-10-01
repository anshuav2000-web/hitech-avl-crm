import { useState, useEffect } from "react";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { HitechLogo } from "@/components/Brand";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PublicLeadForm() {
  const [form, setForm] = useState({ name: "", email: "", phone: "", company: "", interested_in: "", notes: "" });
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [brands, setBrands] = useState([]);

  useEffect(() => {
    // brand logos are loaded from the authenticated catalog page only;
    // the public capture form intentionally does NOT fetch any catalog data
    // to keep the pricelist & brand portfolio strictly internal.
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setSaving(true);
    try {
      const payload = { ...form, source: "website" };
      if (!payload.email) delete payload.email;
      await axios.post(`${API}/public/leads`, payload);
      setSent(true);
    } catch (e2) {
      setErr("Could not submit. Try again.");
    } finally { setSaving(false); }
  };

  return (
    <div className="min-h-screen bg-white grid-bg flex items-center justify-center p-6">
      <div className="max-w-xl w-full">
        <div className="flex items-center gap-2.5 mb-8 justify-center">
          <HitechLogo className="h-10" />
        </div>

        <div className="bg-white border border-slate-200 rounded-md p-8 shadow-sm">
          {sent ? (
            <div className="text-center py-6" data-testid="public-success">
              <CheckCircle2 className="w-12 h-12 text-green-600 mx-auto mb-3" />
              <h2 className="font-display text-2xl font-bold text-slate-900 mb-2">Thanks, we'll be in touch.</h2>
              <p className="text-sm text-slate-600">Our sales team typically responds within 24 hours.</p>
              <button onClick={() => { setSent(false); setForm({ name: "", email: "", phone: "", company: "", interested_in: "", notes: "" }); }} className="mt-6 text-sm text-slate-900 underline" data-testid="public-another">Submit another enquiry</button>
            </div>
          ) : (
            <>
              <div className="label-eyebrow mb-2">Enquiry form</div>
              <h1 className="font-display text-3xl font-bold tracking-tighter text-slate-900 mb-2">Tell us what you're looking for</h1>
              <p className="text-sm text-slate-600 mb-6">Pro audio, broadcast, imaging equipment — we import directly from leading OEMs.</p>

              <form onSubmit={submit} className="space-y-4" data-testid="public-form">
                <PF label="Name *" v={form.name} onV={(v) => setForm({ ...form, name: v })} required testid="pub-name" />
                <div className="grid grid-cols-2 gap-4">
                  <PF label="Email" type="email" v={form.email} onV={(v) => setForm({ ...form, email: v })} testid="pub-email" />
                  <PF label="Phone / WhatsApp" v={form.phone} onV={(v) => setForm({ ...form, phone: v })} testid="pub-phone" />
                </div>
                <PF label="Company" v={form.company} onV={(v) => setForm({ ...form, company: v })} testid="pub-company" />
                <PF label="What are you looking for?" v={form.interested_in} onV={(v) => setForm({ ...form, interested_in: v })} testid="pub-interest" />
                <div>
                  <label className="label-eyebrow block mb-1.5">Additional details</label>
                  <textarea rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none" data-testid="pub-notes" />
                </div>
                {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">{err}</div>}
                <button type="submit" disabled={saving} data-testid="pub-submit" className="w-full text-white px-4 py-3 rounded-md text-sm font-medium hover:opacity-90 transition-all disabled:opacity-60" style={{ background: "#DC2626" }}>
                  {saving ? "Submitting…" : "Submit enquiry"}
                </button>
              </form>
            </>
          )}
        </div>

        <div className="text-center mt-6 text-xs text-slate-500">© {new Date().getFullYear()} Hi-Tech Audio and Image LLP</div>

        {brands.length > 0 && (
          <div className="mt-6 pt-6 border-t border-slate-200">
            <div className="text-center label-eyebrow mb-3">Premium brands we distribute</div>
            <div className="flex items-center justify-center gap-6 flex-wrap">
              {brands.map((b) => b.logo_url && (
                <img key={b.id} src={b.logo_url} alt={b.name} title={b.name} className="h-8 w-auto object-contain opacity-60 hover:opacity-100 transition-opacity grayscale hover:grayscale-0" />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PF({ label, v, onV, type = "text", required, testid }) {
  return (
    <div>
      <label className="label-eyebrow block mb-1.5">{label}</label>
      <input data-testid={testid} required={required} type={type} value={v} onChange={(e) => onV(e.target.value)} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2.5 focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none" />
    </div>
  );
}
