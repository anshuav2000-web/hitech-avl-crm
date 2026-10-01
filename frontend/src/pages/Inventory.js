import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Package, Search } from "lucide-react";

const STATUS_COLORS = { in_stock: "#16A34A", in_transit: "#2563EB", reserved: "#D97706", sold: "#64748B" };

export default function Inventory() {
  const [summary, setSummary] = useState([]);
  const [units, setUnits] = useState([]);
  const [activeProduct, setActiveProduct] = useState(null);
  const [search, setSearch] = useState("");

  const load = () => api.get("/inventory/summary").then((r) => setSummary(r.data));
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (activeProduct) {
      api.get("/inventory", { params: { product_id: activeProduct.id } }).then((r) => setUnits(r.data));
    }
  }, [activeProduct]);

  const filtered = summary.filter((p) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return `${p.brand} ${p.name} ${p.model || ""}`.toLowerCase().includes(q);
  });

  const totals = summary.reduce((a, p) => ({
    in_stock: a.in_stock + p.in_stock,
    in_transit: a.in_transit + p.in_transit,
    reserved: a.reserved + p.reserved,
    sold: a.sold + p.sold,
  }), { in_stock: 0, in_transit: 0, reserved: 0, sold: 0 });

  return (
    <div className="p-8 max-w-[1500px] mx-auto" data-testid="inventory-page">
      <header className="mb-6">
        <div className="label-eyebrow mb-2">Operations</div>
        <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Inventory</h1>
        <p className="text-sm text-slate-600 mt-1">Live stock by product + serial number drilldown.</p>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <Card label="In Stock" value={totals.in_stock} color="#16A34A" testid="inv-instock" />
        <Card label="In Transit" value={totals.in_transit} color="#2563EB" testid="inv-intransit" />
        <Card label="Reserved" value={totals.reserved} color="#D97706" testid="inv-reserved" />
        <Card label="Sold" value={totals.sold} color="#64748B" testid="inv-sold" />
      </div>

      <div className="bg-white border border-slate-200 rounded-md p-4 mb-4 relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-7 top-1/2 -translate-y-1/2" />
        <input
          data-testid="inv-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by brand, name, model…"
          className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-slate-500 bg-slate-50/50 border-b border-slate-200">
                <th className="text-left px-5 py-3 font-medium">Product</th>
                <th className="text-right px-3 py-3 font-medium">Stock</th>
                <th className="text-right px-3 py-3 font-medium">Transit</th>
                <th className="text-right px-3 py-3 font-medium">Reserved</th>
                <th className="text-right px-3 py-3 font-medium">Sold</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && <tr><td colSpan={5} className="px-6 py-14 text-center text-slate-500">No products with stock yet.</td></tr>}
              {filtered.map((p) => (
                <tr key={p.id} onClick={() => setActiveProduct(p)} className={`border-b border-slate-100 cursor-pointer transition-colors ${activeProduct?.id === p.id ? "bg-red-50/40" : "hover:bg-slate-50/50"}`} data-testid={`inv-row-${p.id}`}>
                  <td className="px-5 py-3">
                    <div className="text-sm font-semibold text-slate-900">{p.name}</div>
                    <div className="text-xs text-slate-500">{p.brand} · {p.model || "—"}</div>
                  </td>
                  <td className="px-3 py-3 text-right font-semibold" style={{ color: p.in_stock > 0 ? "#16A34A" : "#94A3B8" }}>{p.in_stock}</td>
                  <td className="px-3 py-3 text-right text-slate-700">{p.in_transit}</td>
                  <td className="px-3 py-3 text-right text-slate-700">{p.reserved}</td>
                  <td className="px-3 py-3 text-right text-slate-700">{p.sold}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-white border border-slate-200 rounded-md p-5 self-start lg:sticky lg:top-4">
          <div className="flex items-center gap-2 mb-3">
            <Package className="w-4 h-4 text-slate-500" />
            <div>
              <div className="label-eyebrow">Serial Numbers</div>
              <div className="font-display text-base font-bold text-slate-900 truncate">{activeProduct?.name || "Pick a product"}</div>
            </div>
          </div>
          {!activeProduct && <div className="text-sm text-slate-500 py-8 text-center border-2 border-dashed border-slate-200 rounded-md">Click any product on the left to inspect serial numbers.</div>}
          {activeProduct && (
            <div className="max-h-[480px] overflow-y-auto space-y-1.5" data-testid="inv-serials">
              {units.length === 0 && <div className="text-sm text-slate-500 py-4 text-center">No units yet.</div>}
              {units.map((u) => (
                <div key={u.id} className="border border-slate-200 rounded-md p-2.5 flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-mono text-slate-900">{u.serial_no}</div>
                    <div className="text-[10px] text-slate-500 truncate">{u.location || "—"}</div>
                  </div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-sm border" style={{ color: STATUS_COLORS[u.status], borderColor: STATUS_COLORS[u.status] + "55", background: STATUS_COLORS[u.status] + "11" }}>
                    {u.status.replace("_", " ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Card({ label, value, color, testid }) {
  return (
    <div className="bg-white border border-slate-200 rounded-md p-4 hover:border-slate-300 transition-all" data-testid={testid}>
      <div className="flex items-start justify-between mb-2">
        <div className="label-eyebrow">{label}</div>
        <div className="w-2 h-2 rounded-full" style={{ background: color }} />
      </div>
      <div className="font-display text-3xl font-black tracking-tighter text-slate-900">{value}</div>
    </div>
  );
}
