import { useEffect, useState, useMemo } from "react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useBrands } from "@/context/BrandContext";
import {
  Plus, Trash2, Package, RefreshCw, ExternalLink, Globe, FileText,
  Download, CheckCircle2, ChevronRight, X, Search
} from "lucide-react";

export default function Catalog() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  // Brands and brand categories come from the shared provider, which reads
  // GET /api/brands once for the whole app. This page no longer keeps its own copy
  // or its own hard-coded category list.
  const { brands, brandCategories, categories: productCategories, refresh: refreshBrands } = useBrands();

  const [products, setProducts] = useState([]);
  const [myRequests, setMyRequests] = useState([]);
  
  const [categoryFilter, setCategoryFilter] = useState("All Categories");
  const [activeBrand, setActiveBrand] = useState("");
  const [search, setSearch] = useState("");
  const [selectedProduct, setSelectedProduct] = useState(null);

  const [syncing, setSyncing] = useState(false);
  const [syncLogs, setSyncLogs] = useState([]);
  const [showBrandModal, setShowBrandModal] = useState(false);
  const [showProdModal, setShowProdModal] = useState(false);

  const [pf, setPf] = useState({
    brand: "", name: "", model: "", sku: "", category: "", sub_category: "",
    unit_price: "", msrp: "", short_description: "", warranty: "3 Years Warranty"
  });
  const [bf, setBf] = useState({ name: "", country: "", description: "", official_website: "", brand_category: "Professional Audio" });
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      const [p, r] = await Promise.all([
        api.get("/products"),
        api.get("/brand-access-requests").catch(() => ({ data: [] })),
      ]);
      setProducts(p.data || []);
      setMyRequests(r.data || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Land on the first brand once the shared list arrives, so the detail pane is
  // never blank on first paint.
  useEffect(() => {
    if (!activeBrand && brands.length) setActiveBrand(brands[0].name);
  }, [brands, activeBrand]);

  const triggerCatalogSync = async () => {
    setSyncing(true);
    try {
      const res = await api.post("/sync/catalog/trigger");
      setSyncLogs(res.data?.logs || []);
      await load();
    } catch (e) {
      alert(formatApiError(e));
    } finally {
      setSyncing(false);
    }
  };

  const filteredBrands = useMemo(() => {
    if (categoryFilter === "All Categories") return brands;
    return brands.filter((b) => b.brand_category === categoryFilter);
  }, [brands, categoryFilter]);

  const activeBrandObj = useMemo(() => {
    return brands.find((b) => b.name === activeBrand) || null;
  }, [brands, activeBrand]);

  const displayedProducts = useMemo(() => {
    let list = activeBrand ? products.filter((p) => p.brand === activeBrand) : products;
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((p) =>
        `${p.name} ${p.model || ""} ${p.category || ""} ${p.short_description || ""}`.toLowerCase().includes(q)
      );
    }
    return list;
  }, [products, activeBrand, search]);

  const submitProduct = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/products", {
        ...pf,
        brand: pf.brand || activeBrand,
        unit_price: parseFloat(pf.unit_price || 0),
        msrp: pf.msrp ? parseFloat(pf.msrp) : undefined,
      });
      setPf({ brand: "", name: "", model: "", sku: "", category: "", sub_category: "", unit_price: "", msrp: "", short_description: "", warranty: "3 Years Warranty" });
      setShowProdModal(false);
      load();
    } catch (e2) { setErr(formatApiError(e2)); }
  };

  // A brand is created through the same API the provider reads, so the shared list
  // is refreshed rather than patched locally.
  const submitBrand = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/brands", bf);
      setBf({ name: "", country: "", description: "", official_website: "", brand_category: "Professional Audio" });
      setShowBrandModal(false);
      await refreshBrands();
      load();
    } catch (e2) { setErr(formatApiError(e2)); }
  };

  const removeProduct = async (id) => {
    if (!window.confirm("Remove this product from the catalogue? It will be archived, not deleted.")) return;
    await api.delete(`/products/${id}`);
    load();
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="catalog-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Product Information Management</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Package className="w-8 h-8 text-sky-600" /> Brands & Products Catalog
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Official manufacturer product catalog, downloads, datasheets, and technical specifications for audio, lighting & control gear.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isAdmin && (
            <>
              <button
                onClick={triggerCatalogSync}
                disabled={syncing}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-sky-700 bg-sky-50 border border-sky-200 hover:bg-sky-100 transition-all cursor-pointer"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Syncing Catalog..." : "Sync Official Data"}
              </button>
              <button
                onClick={() => setShowBrandModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-slate-800 bg-slate-100 border border-slate-300 hover:bg-slate-200 transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Add Brand
              </button>
              <button
                onClick={() => { setPf({ ...pf, brand: activeBrand }); setShowProdModal(true); }}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Add Product
              </button>
            </>
          )}
        </div>
      </div>

      {/* Sync Log Indicator */}
      {syncLogs.length > 0 && (
        <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50 text-xs text-emerald-800 flex items-center justify-between font-medium">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Catalog Synchronization Complete: {syncLogs.length} data streams updated.</span>
          </div>
          <button onClick={() => setSyncLogs([])} className="text-slate-500 hover:text-slate-900"><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* Category Filter Pills */}
      <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
        {brandCategories.map((cat) => (
          <button
            key={cat}
            onClick={() => {
              setCategoryFilter(cat);
              const available = cat === "All Categories" ? brands : brands.filter((b) => b.brand_category === cat);
              if (available.length) setActiveBrand(available[0].name);
            }}
            className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all border ${
              categoryFilter === cat
                ? "bg-sky-600 text-white border-sky-600 shadow-xs"
                : "bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Brand Selector Ribbon */}
      <div className="flex gap-2 overflow-x-auto no-scrollbar py-2 border-y border-slate-200">
        {filteredBrands.map((b) => {
          const isSelected = activeBrand === b.name;
          const count = products.filter((p) => p.brand === b.name).length;
          return (
            <button
              key={b.id || b.name}
              onClick={() => setActiveBrand(b.name)}
              className={`whitespace-nowrap px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border ${
                isSelected
                  ? "bg-slate-900 text-white border-slate-900 shadow-md"
                  : "bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              {b.logo_url && (
                <img src={b.logo_url} alt={b.name} className={`h-4 w-auto object-contain ${isSelected ? "brightness-0 invert" : ""}`} />
              )}
              <span>{b.name}</span>
              <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-extrabold ${isSelected ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600"}`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active Brand Information Banner */}
      {activeBrandObj && (
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 relative overflow-hidden">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h2 className="font-display text-2xl font-black text-slate-900">{activeBrandObj.name}</h2>
                {activeBrandObj.country && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-200 text-slate-800 border border-slate-300">
                    {activeBrandObj.country}
                  </span>
                )}
                {activeBrandObj.brand_category && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-sky-100 text-sky-800 border border-sky-200">
                    {activeBrandObj.brand_category}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600 max-w-3xl font-medium">{activeBrandObj.description}</p>
            </div>

            {activeBrandObj.official_website && (
              <a
                href={activeBrandObj.official_website}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-sky-700 bg-white border border-sky-200 hover:bg-sky-50 transition-all shrink-0 shadow-xs"
              >
                <Globe className="w-3.5 h-3.5" /> Official Website <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
      )}

      {/* Product Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search ${activeBrand} catalog...`}
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-sky-500 font-medium"
          />
        </div>
        <div className="text-xs text-slate-600 font-semibold">
          Showing <span className="text-slate-900 font-extrabold">{displayedProducts.length}</span> products for {activeBrand}
        </div>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {displayedProducts.length === 0 ? (
          <div className="col-span-full bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-sm font-medium">
            No products match the search query for {activeBrand}.
          </div>
        ) : (
          displayedProducts.map((p) => (
            <div
              key={p.id}
              onClick={() => setSelectedProduct(p)}
              className="bg-white border border-slate-200 rounded-xl p-5 hover:border-sky-400 hover:shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between group"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] font-extrabold uppercase tracking-widest text-sky-700 block mb-0.5">
                      {p.category || "Audio/Lighting"}
                    </span>
                    <h3 className="font-display text-lg font-bold text-slate-900 group-hover:text-sky-700 transition-colors">
                      {p.name}
                    </h3>
                    {p.model && <p className="text-xs text-slate-500 font-mono">Model: {p.model}</p>}
                  </div>
                  {isAdmin && (
                    <button
                      onClick={(e) => { e.stopPropagation(); removeProduct(p.id); }}
                      className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                      title="Delete product"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <p className="text-xs text-slate-600 line-clamp-2 font-medium">
                  {p.short_description || p.long_description || p.description || "Official manufacturer specifications."}
                </p>

                {p.features && p.features.length > 0 && (
                  <div className="space-y-1 pt-1">
                    {p.features.slice(0, 2).map((f, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-[11px] text-slate-600 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-sky-600" />
                        <span className="truncate">{f}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-100 mt-4 flex items-center justify-between">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">List Price (INR)</div>
                  <div className="font-display text-base font-extrabold text-slate-900">
                    ₹{Number(p.unit_price || p.msrp || 0).toLocaleString("en-IN")}
                  </div>
                </div>
                <span className="inline-flex items-center gap-1 text-xs font-bold text-sky-700 group-hover:translate-x-1 transition-transform">
                  Specs & Downloads <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Product Detail Modal */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-3xl p-6 space-y-6 shadow-2xl animate-scale-in max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-widest text-sky-700">{selectedProduct.brand} · {selectedProduct.category}</span>
                <h2 className="font-display text-2xl font-black text-slate-900">{selectedProduct.name}</h2>
                <p className="text-xs text-slate-500 font-mono">SKU: {selectedProduct.sku || "N/A"} | Model: {selectedProduct.model || "N/A"}</p>
              </div>
              <button onClick={() => setSelectedProduct(null)} className="p-2 rounded-xl text-slate-400 hover:text-slate-800 hover:bg-slate-100"><X className="w-5 h-5" /></button>
            </div>

            <div className="space-y-4 text-sm text-slate-700 font-medium">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Description</h4>
                <p className="text-xs text-slate-600 leading-relaxed">{selectedProduct.long_description || selectedProduct.short_description || selectedProduct.description}</p>
              </div>

              {selectedProduct.technical_specifications && Object.keys(selectedProduct.technical_specifications).length > 0 && (
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-sky-700 mb-2">Technical Specifications</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                    {Object.entries(selectedProduct.technical_specifications).map(([k, v]) => (
                      <div key={k} className="border-b border-slate-200 pb-1.5 last:border-0">
                        <span className="text-slate-500 font-bold block">{k}:</span>
                        <span className="text-slate-900 font-bold">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedProduct.downloads && selectedProduct.downloads.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-sky-700 mb-2">Official Downloads & Documentation</h4>
                  <div className="space-y-2">
                    {selectedProduct.downloads.map((d, i) => (
                      <a
                        key={i}
                        href={d.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-300 transition-all text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-sky-600" />
                          <span className="font-bold text-slate-900">{d.title}</span>
                          <span className="uppercase text-[9px] px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-bold">{d.type}</span>
                        </div>
                        <span className="text-sky-700 font-bold flex items-center gap-1">Download <Download className="w-3.5 h-3.5" /></span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <div>
                <span className="text-[10px] uppercase text-slate-500 font-bold block">List Price (INR)</span>
                <span className="font-display text-2xl font-black text-slate-900">₹{Number(selectedProduct.unit_price || 0).toLocaleString("en-IN")}</span>
              </div>
              <button onClick={() => setSelectedProduct(null)} className="px-5 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Brand Modal */}
      {showBrandModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-scale-in">
            <h3 className="font-display text-xl font-bold text-slate-900">Add New Manufacturer Brand</h3>
            {err && <div className="p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded-xl">{err}</div>}
            <form onSubmit={submitBrand} className="space-y-3">
              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Brand Name *</label>
                <input required type="text" value={bf.name} onChange={(e) => setBf({ ...bf, name: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Country</label>
                  <input type="text" value={bf.country} onChange={(e) => setBf({ ...bf, country: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Category</label>
                  <select value={bf.brand_category} onChange={(e) => setBf({ ...bf, brand_category: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium">
                    {brandCategories.filter((c) => c !== "All Categories").map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Official Website</label>
                <input type="url" value={bf.official_website} onChange={(e) => setBf({ ...bf, official_website: e.target.value })} placeholder="https://..." className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Description</label>
                <textarea rows={2} value={bf.description} onChange={(e) => setBf({ ...bf, description: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowBrandModal(false)} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500">Save Brand</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Product Modal */}
      {showProdModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-scale-in">
            <h3 className="font-display text-xl font-bold text-slate-900">Add Product to {activeBrand}</h3>
            {err && <div className="p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded-xl">{err}</div>}
            <form onSubmit={submitProduct} className="space-y-3">
              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Product Name *</label>
                <input required type="text" value={pf.name} onChange={(e) => setPf({ ...pf, name: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Model</label>
                  <input type="text" value={pf.model} onChange={(e) => setPf({ ...pf, model: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">SKU</label>
                  <input type="text" value={pf.sku} onChange={(e) => setPf({ ...pf, sku: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Category</label>
                  <input type="text" value={pf.category} onChange={(e) => setPf({ ...pf, category: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Unit Price (INR) *</label>
                  <input required type="number" value={pf.unit_price} onChange={(e) => setPf({ ...pf, unit_price: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
                </div>
              </div>
              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Short Description</label>
                <textarea rows={2} value={pf.short_description} onChange={(e) => setPf({ ...pf, short_description: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowProdModal(false)} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500">Save Product</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
