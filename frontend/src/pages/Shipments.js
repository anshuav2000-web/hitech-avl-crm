import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useBrands } from "@/context/BrandContext";
import { Plus, Ship, Package, Trash2, X } from "lucide-react";

const STATUS_FLOW = ["planned", "in_transit", "customs", "cleared", "received"];
const STATUS_LABELS = {
  planned: "Planned", in_transit: "In Transit", customs: "At Customs",
  cleared: "Cleared", received: "Received",
};
const STATUS_STYLES = {
  planned: "bg-slate-100 text-slate-700 border-slate-200",
  in_transit: "bg-blue-50 text-blue-700 border-blue-200",
  customs: "bg-amber-50 text-amber-700 border-amber-200",
  cleared: "bg-purple-50 text-purple-700 border-purple-200",
  received: "bg-green-50 text-green-700 border-green-200",
};

export default function Shipments() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  // Brands are shared app-wide; this page only fetches its own shipments and products.
  const { brands } = useBrands();
  const [list, setList] = useState([]);
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ po_no: "", oem: "", currency: "EUR", bl_awb: "", eta: "", notes: "", items: [{ product_id: "", qty: 1, fob_unit: 0 }] });
  const [err, setErr] = useState("");

  const load = () => Promise.all([api.get("/shipments"), api.get("/products")]).then(([s, p]) => {
    setList(s.data); setProducts(p.data);
  });
  useEffect(() => { load(); }, []);

  const updateStatus = async (sid, status) => {
    await api.patch(`/shipments/${sid}`, { status });
    load();
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/shipments", {
        ...form,
        items: form.items.filter((i) => i.product_id).map((i) => ({ ...i, qty: parseInt(i.qty), fob_unit: parseFloat(i.fob_unit) })),
      });
      setForm({ po_no: "", oem: "", currency: "EUR", bl_awb: "", eta: "", notes: "", items: [{ product_id: "", qty: 1, fob_unit: 0 }] });
      setShowForm(false);
      load();
    } catch (e2) { setErr(formatApiError(e2)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this shipment?")) return;
    await api.delete(`/shipments/${id}`);
    load();
  };

  const oemProducts = form.oem ? products.filter((p) => p.brand === form.oem) : [];

  return (
    <div className="p-8 max-w-[1500px] mx-auto" data-testid="shipments-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Operations</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Shipments</h1>
          <p className="text-sm text-slate-600 mt-1">{list.length} purchase orders · {list.filter((s) => ["planned", "in_transit", "customs"].includes(s.status)).length} in transit</p>
        </div>
        {isAdmin && (
          <button onClick={() => setShowForm(true)} data-testid="shipment-add-btn" className="inline-flex items-center gap-2 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:opacity-90" style={{ background: "#DC2626" }}>
            <Plus className="w-4 h-4" /> New PO
          </button>
        )}
      </header>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
              <th className="text-left px-6 py-3 font-medium">PO #</th>
              <th className="text-left px-6 py-3 font-medium">OEM</th>
              <th className="text-left px-6 py-3 font-medium">Items</th>
              <th className="text-left px-6 py-3 font-medium">BL/AWB</th>
              <th className="text-left px-6 py-3 font-medium">ETA</th>
              <th className="text-left px-6 py-3 font-medium">Status</th>
              <th className="text-right px-6 py-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {list.length === 0 && <tr><td colSpan={7} className="px-6 py-14 text-center text-slate-500">No shipments yet.</td></tr>}
            {list.map((s) => {
              const totalUnits = s.items.reduce((a, i) => a + Number(i.qty || 0), 0);
              return (
                <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors" data-testid={`shipment-row-${s.id}`}>
                  <td className="px-6 py-3.5 font-semibold text-slate-900">{s.po_no}</td>
                  <td className="px-6 py-3.5 text-slate-700">{s.oem} <span className="text-xs text-slate-500">({s.currency})</span></td>
                  <td className="px-6 py-3.5 text-slate-600">{s.items.length} skus · {totalUnits} units</td>
                  <td className="px-6 py-3.5 text-slate-600 font-mono text-xs">{s.bl_awb || "—"}</td>
                  <td className="px-6 py-3.5 text-slate-600 text-xs">{s.eta || "—"}</td>
                  <td className="px-6 py-3.5">
                    <select value={s.status} onChange={(e) => updateStatus(s.id, e.target.value)} data-testid={`shipment-status-${s.id}`} disabled={!isAdmin} className={`text-xs font-medium border rounded-sm px-2 py-1 capitalize ${STATUS_STYLES[s.status]}`}>
                      {STATUS_FLOW.map((st) => <option key={st} value={st}>{STATUS_LABELS[st]}</option>)}
                    </select>
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    {isAdmin && <button onClick={() => remove(s.id)} className="text-slate-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="shipment-form-modal">
          <div className="bg-white rounded-md border border-slate-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
              <div className="font-display text-lg font-bold text-slate-900 flex items-center gap-2"><Ship className="w-4 h-4" /> New purchase order</div>
              <button onClick={() => setShowForm(false)} className="text-slate-500 hover:text-slate-900"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={submit} className="p-5 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="PO Number *" v={form.po_no} onV={(v) => setForm({ ...form, po_no: v })} required testid="sh-po" />
                <div>
                  <label className="label-eyebrow block mb-1.5">OEM *</label>
                  <select value={form.oem} onChange={(e) => setForm({ ...form, oem: e.target.value, items: [{ product_id: "", qty: 1, fob_unit: 0 }] })} required className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 bg-white" data-testid="sh-oem">
                    <option value="">Select…</option>
                    {brands.filter((b) => !b.locked).map((b) => <option key={b.id} value={b.name}>{b.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label-eyebrow block mb-1.5">Currency</label>
                  <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 bg-white">
                    <option>EUR</option><option>USD</option><option>GBP</option>
                  </select>
                </div>
                <Field label="BL / AWB" v={form.bl_awb} onV={(v) => setForm({ ...form, bl_awb: v })} testid="sh-bl" />
                <Field label="ETA" type="date" v={form.eta} onV={(v) => setForm({ ...form, eta: v })} testid="sh-eta" />
              </div>
              <div>
                <label className="label-eyebrow block mb-2">Items *</label>
                <div className="space-y-2">
                  {form.items.map((it, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <select value={it.product_id} onChange={(e) => setForm({ ...form, items: form.items.map((x, idx) => idx === i ? { ...x, product_id: e.target.value } : x) })} className="flex-1 border border-slate-200 rounded-md text-sm px-2 py-1.5">
                        <option value="">— Product —</option>
                        {oemProducts.map((p) => { const lbl = `${p.name}${p.model ? ` (${p.model})` : ""}`; return <option key={p.id} value={p.id}>{lbl}</option>; })}
                      </select>
                      <input type="number" min={1} value={it.qty} onChange={(e) => setForm({ ...form, items: form.items.map((x, idx) => idx === i ? { ...x, qty: e.target.value } : x) })} className="w-20 border border-slate-200 rounded-md text-sm px-2 py-1.5" placeholder="Qty" />
                      <input type="number" value={it.fob_unit} onChange={(e) => setForm({ ...form, items: form.items.map((x, idx) => idx === i ? { ...x, fob_unit: e.target.value } : x) })} className="w-28 border border-slate-200 rounded-md text-sm px-2 py-1.5" placeholder={`FOB ${form.currency}`} />
                      <button type="button" onClick={() => setForm({ ...form, items: form.items.filter((_, idx) => idx !== i) })} className="text-slate-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  ))}
                </div>
                <button type="button" onClick={() => setForm({ ...form, items: [...form.items, { product_id: "", qty: 1, fob_unit: 0 }] })} className="mt-2 text-xs text-slate-700 hover:text-slate-900 inline-flex items-center gap-1">
                  <Plus className="w-3 h-3" /> Add item
                </button>
              </div>
              <div>
                <label className="label-eyebrow block mb-1.5">Notes</label>
                <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2" />
              </div>
              {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">{err}</div>}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
                <button type="submit" data-testid="sh-submit" className="text-white px-4 py-2 rounded-md text-sm hover:opacity-90" style={{ background: "#DC2626" }}>Create PO</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, v, onV, type = "text", required, testid }) {
  return (
    <div>
      <label className="label-eyebrow block mb-1.5">{label}</label>
      <input data-testid={testid} type={type} required={required} value={v} onChange={(e) => onV(e.target.value)} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none" />
    </div>
  );
}
