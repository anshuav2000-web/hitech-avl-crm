import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useBrands } from "@/context/BrandContext";
import { Plus, Trash2, Package as PackageIcon, X, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function Packages() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  // Brands come from the shared provider (one GET /api/brands for the whole app)
  // rather than a second copy fetched by this page.
  const { brands } = useBrands();
  const [packages, setPackages] = useState([]);
  const [products, setProducts] = useState([]);
  const [activeBrand, setActiveBrand] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [pf, setPf] = useState({ brand: "", name: "", description: "", items: [{ product_id: "", qty: 1 }] });
  const [err, setErr] = useState("");

  const load = async () => {
    const [pkg, p] = await Promise.all([api.get("/packages"), api.get("/products")]);
    setPackages(pkg.data);
    setProducts(p.data);
  };

  // Default the brand picker to the first brand this rep is allowed to quote.
  useEffect(() => {
    if (!activeBrand && brands.length) {
      setActiveBrand(brands.find((x) => !x.locked)?.name || brands[0].name);
    }
  }, [brands, activeBrand]);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const filtered = activeBrand ? packages.filter((p) => p.brand === activeBrand) : packages;
  const brandProducts = pf.brand ? products.filter((p) => p.brand === pf.brand) : [];

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      const payload = {
        brand: pf.brand,
        name: pf.name,
        description: pf.description,
        items: pf.items.filter((i) => i.product_id).map((i) => ({ product_id: i.product_id, qty: parseInt(i.qty) || 1 })),
      };
      if (!payload.items.length) { setErr("Add at least one item."); return; }
      await api.post("/packages", payload);
      setPf({ brand: "", name: "", description: "", items: [{ product_id: "", qty: 1 }] });
      setShowForm(false);
      load();
    } catch (e2) { setErr(formatApiError(e2)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this package?")) return;
    await api.delete(`/packages/${id}`);
    load();
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="packages-page">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="label-eyebrow mb-2">Catalog</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Package templates</h1>
          <p className="text-sm text-slate-600 mt-1">Pre-built system bundles. Apply any package to a quotation in one click.</p>
        </div>
        {isAdmin && (
          <button onClick={() => { setPf({ ...pf, brand: activeBrand }); setShowForm(true); }} data-testid="pkg-add-btn" className="inline-flex items-center gap-2 text-white px-4 py-2.5 rounded-md text-sm font-medium hover:opacity-90" style={{ background: "#DC2626" }}>
            <Plus className="w-4 h-4" /> New package
          </button>
        )}
      </header>

      <div className="flex gap-2 mb-5 overflow-x-auto no-scrollbar">
        {brands.map((b) => (
          <button
            key={b.id}
            onClick={() => !b.locked && setActiveBrand(b.name)}
            disabled={b.locked}
            data-testid={`pkg-brand-${b.name}`}
            className={`whitespace-nowrap px-4 py-2.5 rounded-md text-sm font-semibold transition-colors border flex items-center gap-2 ${
              activeBrand === b.name ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
            } ${b.locked ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            {b.locked && <span className="text-xs">🔒</span>}
            {b.logo_url && !b.locked && <img src={b.logo_url} alt={b.name} className={`h-5 w-auto object-contain ${activeBrand === b.name ? "brightness-0 invert" : ""}`} />}
            {b.name}
            {!b.locked && <span className="text-xs opacity-70">{packages.filter((p) => p.brand === b.name).length}</span>}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.length === 0 && (
          <div className="md:col-span-2 lg:col-span-3 bg-white border border-slate-200 rounded-md p-10 text-center text-slate-500" data-testid="pkg-empty">
            No packages yet for {activeBrand}. {isAdmin && "Click 'New package' to build one."}
          </div>
        )}
        {filtered.map((p) => (
          <div key={p.id} className="bg-white border border-slate-200 rounded-md p-5 flex flex-col" data-testid={`pkg-card-${p.id}`}>
            <div className="flex items-start gap-2 mb-2">
              <PackageIcon className="w-4 h-4 text-slate-500 mt-1 shrink-0" />
              <div className="flex-1">
                <div className="font-display font-bold text-slate-900">{p.name}</div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500">{p.brand} · {(p.items.length + (p.components?.length || 0))} item{(p.items.length + (p.components?.length || 0)) === 1 ? "" : "s"}{p.fixed_price_inr ? " · Fixed bundle" : ""}</div>
              </div>
              {isAdmin && (
                <button onClick={() => remove(p.id)} className="text-slate-300 hover:text-red-600" data-testid={`pkg-delete-${p.id}`}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            {p.description && <p className="text-xs text-slate-600 leading-relaxed mb-3">{p.description}</p>}
            <div className="space-y-1 mb-3 text-xs flex-1">
              {/* Catalog-linked items */}
              {p.items.slice(0, 6).map((it, idx) => (
                <div key={`it-${idx}`} className="flex items-center justify-between border-b border-slate-100 pb-1 last:border-0">
                  <span className="text-slate-700 truncate">{it.product?.name || "—"}</span>
                  <span className="font-semibold text-slate-900 shrink-0 ml-2">×{it.qty}</span>
                </div>
              ))}
              {p.items.length > 6 && <div className="text-slate-400">+ {p.items.length - 6} more catalog items…</div>}
              {/* Free-form components (imported bundles) */}
              {(p.components || []).slice(0, 8).map((c, idx) => (
                <div key={`co-${idx}`} className="flex items-center justify-between border-b border-slate-100 pb-1 last:border-0">
                  <span className="text-slate-700 truncate">{c.description || c.model}</span>
                  <span className="font-semibold text-slate-900 shrink-0 ml-2">×{c.qty}</span>
                </div>
              ))}
              {(p.components?.length || 0) > 8 && <div className="text-slate-400">+ {p.components.length - 8} more components…</div>}
            </div>
            <div className="border-t border-slate-100 pt-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500">
                  {p.fixed_price_inr ? "Bundle price" : "Est. total"}
                </div>
                <div className="font-display font-bold text-slate-900" data-testid={`pkg-price-${p.id}`}>
                  ₹{Number(p.display_price ?? p.estimated_total ?? 0).toLocaleString("en-IN")}
                </div>
              </div>
              <Link
                to={`/quotations/new?package=${p.id}`}
                data-testid={`pkg-use-${p.id}`}
                className="inline-flex items-center gap-1 text-xs font-semibold text-white px-3 py-1.5 rounded-md hover:opacity-90"
                style={{ background: "#DC2626" }}
              >
                Use in quote <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="pkg-form-modal">
          <div className="bg-white rounded-md border border-slate-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
              <div className="font-display text-lg font-bold text-slate-900">New package template</div>
              <button onClick={() => setShowForm(false)} className="text-slate-500 hover:text-slate-900"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={submit} className="p-5 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label-eyebrow block mb-1.5">Brand *</label>
                  <select value={pf.brand} onChange={(e) => setPf({ ...pf, brand: e.target.value, items: [{ product_id: "", qty: 1 }] })} required className="w-full border border-slate-200 rounded-md text-sm px-3 py-2 bg-white">
                    <option value="">Select…</option>
                    {brands.filter((b) => !b.locked).map((b) => <option key={b.id} value={b.name}>{b.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label-eyebrow block mb-1.5">Package name *</label>
                  <input data-testid="pkg-name" value={pf.name} onChange={(e) => setPf({ ...pf, name: e.target.value })} required className="w-full border border-slate-200 rounded-md text-sm px-3 py-2" />
                </div>
              </div>
              <div>
                <label className="label-eyebrow block mb-1.5">Description</label>
                <textarea rows={2} value={pf.description} onChange={(e) => setPf({ ...pf, description: e.target.value })} className="w-full border border-slate-200 rounded-md text-sm px-3 py-2" />
              </div>
              <div>
                <label className="label-eyebrow block mb-2">Items *</label>
                <div className="space-y-2">
                  {pf.items.map((it, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <select
                        value={it.product_id}
                        onChange={(e) => setPf({ ...pf, items: pf.items.map((x, idx) => idx === i ? { ...x, product_id: e.target.value } : x) })}
                        className="flex-1 border border-slate-200 rounded-md text-sm px-2 py-1.5"
                      >
                        <option value="">— Product —</option>
                        {brandProducts.map((p) => {
                          const label = `${p.name}${p.model ? ` (${p.model})` : ""}`;
                          return <option key={p.id} value={p.id}>{label}</option>;
                        })}
                      </select>
                      <input type="number" min={1} value={it.qty} onChange={(e) => setPf({ ...pf, items: pf.items.map((x, idx) => idx === i ? { ...x, qty: e.target.value } : x) })} className="w-20 border border-slate-200 rounded-md text-sm px-2 py-1.5 text-center" />
                      <button type="button" onClick={() => setPf({ ...pf, items: pf.items.filter((_, idx) => idx !== i) })} className="text-slate-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  ))}
                </div>
                <button type="button" onClick={() => setPf({ ...pf, items: [...pf.items, { product_id: "", qty: 1 }] })} className="mt-2 text-xs text-slate-700 hover:text-slate-900 inline-flex items-center gap-1">
                  <Plus className="w-3 h-3" /> Add item
                </button>
              </div>
              {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">{err}</div>}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md">Cancel</button>
                <button type="submit" data-testid="pkg-submit" className="text-white px-4 py-2 rounded-md text-sm hover:opacity-90" style={{ background: "#DC2626" }}>Create package</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
