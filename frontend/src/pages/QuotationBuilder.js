import { useEffect, useMemo, useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useBrands } from "@/context/BrandContext";
import {
  ArrowLeft, Plus, Trash2, Search, Save, FileEdit, Sparkles, CheckCircle2
} from "lucide-react";

const TEMPLATES = [
  "Corporate",
  "Government",
  "Education",
  "Hospitality",
  "Residential",
  "Rental",
  "System Integration"
];

const PRICING_TIERS = ["MSRP", "Dealer Price", "Distributor Price", "Project Pricing"];

export default function QuotationBuilder() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectLeadId = searchParams.get("lead");
  const preselectPackageId = searchParams.get("package");
  const fromQuoteId = searchParams.get("from");
  const editQuoteId = searchParams.get("edit");

  const [leads, setLeads] = useState([]);
  // Brand list is shared app-wide via BrandContext; this page does not refetch it.
  const { brands } = useBrands();
  const [products, setProducts] = useState([]);
  const [packages, setPackages] = useState([]);
  const [leadId, setLeadId] = useState(preselectLeadId || "");
  const [leadQuery, setLeadQuery] = useState("");
  const [showLeadList, setShowLeadList] = useState(false);

  const [activeBrand, setActiveBrand] = useState("");
  const [browseMode, setBrowseMode] = useState("products");
  const [pricingTier, setPricingTier] = useState("MSRP");
  const [templateType, setTemplateType] = useState("Corporate");
  const [search, setSearch] = useState("");

  const [items, setItems] = useState([]);
  const [shippingCharges, setShippingCharges] = useState(0);
  const [installationCharges, setInstallationCharges] = useState(0);
  const [amcCharges, setAmcCharges] = useState(0);
  const [terms, setTerms] = useState("Payment: 50% advance, 50% on delivery. Validity: 30 days.");
  const [execSummary, setExecSummary] = useState("");

  const [aiLoading, setAiLoading] = useState(false);
  const [aiRecommendations, setAiRecommendations] = useState([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/leads"),
      api.get("/products"),
      api.get("/packages")
    ]).then(([l, p, pk]) => {
      setLeads(l.data || []);
      setProducts(p.data || []);
      setPackages(pk.data || []);
    });
  }, []);

  // Default the brand picker to the first brand this rep is allowed to quote.
  useEffect(() => {
    if (!activeBrand && brands.length) {
      const firstUnlocked = brands.find((x) => !x.locked);
      setActiveBrand((firstUnlocked || brands[0]).name);
    }
  }, [brands, activeBrand]);

  // Preload from existing quotation
  useEffect(() => {
    const sourceId = fromQuoteId || editQuoteId;
    if (!sourceId) return;
    api.get(`/quotations/${sourceId}`).then((r) => {
      const q = r.data;
      setLeadId(q.lead_id);
      setTemplateType(q.template_type || "Corporate");
      setTerms(q.terms || "Payment: 50% advance, 50% on delivery. Validity: 30 days.");
      setExecSummary(q.executive_summary || "");
      setShippingCharges(q.shipping_charges || 0);
      setInstallationCharges(q.installation_charges || 0);
      setAmcCharges(q.amc_charges || 0);
      setItems((q.items || []).map((it) => ({
        key: crypto.randomUUID(),
        product_id: it.product_id || null,
        product: it.product,
        brand: it.brand || "",
        qty: it.qty || 1,
        unit_price: it.unit_price || 0,
        pricing_tier: it.pricing_tier || "MSRP",
        discount_pct: it.discount_pct || 0,
        fixed_discount: it.fixed_discount || 0,
        tax_pct: it.tax_pct || 18,
        components: it.components || null,
      })));
    }).catch(() => {});
  }, [fromQuoteId, editQuoteId]);

  const selectedLead = leads.find((l) => l.id === leadId);

  const filteredLeads = useMemo(() => {
    const q = leadQuery.trim().toLowerCase();
    if (!q) return leads.slice(0, 20);
    return leads.filter((l) => `${l.name} ${l.company || ""} ${l.email || ""} ${l.phone || ""}`.toLowerCase().includes(q)).slice(0, 20);
  }, [leadQuery, leads]);

  const visibleProducts = useMemo(() => {
    const q = search.trim().toLowerCase();
    return products
      .filter((p) => p.brand === activeBrand)
      .filter((p) => !q || `${p.name} ${p.model || ""} ${p.category || ""}`.toLowerCase().includes(q));
  }, [products, activeBrand, search]);

  const visiblePackages = useMemo(() => {
    const q = search.trim().toLowerCase();
    return packages
      .filter((p) => p.brand === activeBrand)
      .filter((p) => !q || `${p.name} ${p.sku || ""}`.toLowerCase().includes(q));
  }, [packages, activeBrand, search]);

  const groupedProducts = useMemo(() => {
    const m = {};
    for (const p of visibleProducts) {
      const c = p.category || "General";
      if (!m[c]) m[c] = [];
      m[c].push(p);
    }
    return m;
  }, [visibleProducts]);

  const getPriceForTier = (p, tier) => {
    if (tier === "Dealer Price" && p.dealer_price) return p.dealer_price;
    if (tier === "Distributor Price" && p.distributor_price) return p.distributor_price;
    if (tier === "Project Pricing" && p.dealer_price) return p.dealer_price * 0.95;
    return p.unit_price || p.msrp || 0;
  };

  const addProduct = (p) => {
    const calculatedPrice = getPriceForTier(p, pricingTier);
    setItems((arr) => {
      const existing = arr.find((it) => it.product_id === p.id);
      if (existing) {
        return arr.map((it) => it.product_id === p.id ? { ...it, qty: it.qty + 1 } : it);
      }
      return [...arr, {
        key: crypto.randomUUID(),
        product_id: p.id,
        product: p.model ? `${p.name} (${p.model})` : p.name,
        brand: p.brand,
        qty: 1,
        unit_price: calculatedPrice,
        pricing_tier: pricingTier,
        discount_pct: 0,
        fixed_discount: 0,
        tax_pct: 18,
        components: null,
        stock: p.stock_quantity || 10
      }];
    });
  };

  const addPackage = (pkg) => {
    const price = Number(pkg.fixed_price_inr ?? pkg.display_price ?? pkg.estimated_total ?? 0);
    setItems((arr) => {
      const compList = (pkg.components || []).map((c) => `${c.qty}× ${c.description || c.model}`).join("; ");
      return [...arr, {
        key: crypto.randomUUID(),
        product_id: null,
        package_id: pkg.id,
        product: `${pkg.name} — Bundle${pkg.sku ? ` [${pkg.sku}]` : ""}`,
        brand: pkg.brand,
        qty: 1,
        unit_price: price,
        pricing_tier: "Bundle",
        discount_pct: 0,
        fixed_discount: 0,
        tax_pct: 18,
        components: compList || null,
        stock: 5
      }];
    });
  };

  const updateItem = (key, patch) => setItems((arr) => arr.map((it) => it.key === key ? { ...it, ...patch } : it));
  const removeItem = (key) => setItems((arr) => arr.filter((it) => it.key !== key));

  const calculatedLines = useMemo(() => {
    return items.map((i) => {
      const base = Number(i.unit_price || 0) * Number(i.qty || 1);
      const disc = (base * (Number(i.discount_pct || 0) / 100)) + Number(i.fixed_discount || 0);
      const lineSubtotal = Math.max(0, base - disc);
      const lineTax = lineSubtotal * (Number(i.tax_pct || 18) / 100);
      return {
        ...i,
        lineSubtotal,
        lineTax,
        lineTotal: lineSubtotal + lineTax
      };
    });
  }, [items]);

  const subtotal = calculatedLines.reduce((s, i) => s + i.lineSubtotal, 0);
  const tax = calculatedLines.reduce((s, i) => s + i.lineTax, 0);
  const grandTotal = subtotal + tax + Number(shippingCharges || 0) + Number(installationCharges || 0) + Number(amcCharges || 0);

  const runAiAssistance = async () => {
    if (!items.length) {
      alert("Add at least one product before running AI system recommendations.");
      return;
    }
    setAiLoading(true);
    try {
      const res = await api.post("/quotations/ai-recommend", { items });
      setAiRecommendations(res.data?.recommendations || []);
      if (res.data?.summary && !execSummary) {
        setExecSummary(res.data.summary);
      }
    } catch (e) {
      alert(formatApiError(e));
    } finally {
      setAiLoading(false);
    }
  };

  const addRecommendedAccessory = (rec) => {
    setItems((prev) => [
      ...prev,
      {
        key: crypto.randomUUID(),
        product_id: null,
        product: rec.name,
        brand: rec.brand,
        qty: rec.suggested_qty || 1,
        unit_price: rec.price || 150000,
        pricing_tier: "Recommended",
        discount_pct: 0,
        fixed_discount: 0,
        tax_pct: 18,
        components: rec.reason || null,
        stock: 10
      }
    ]);
  };

  const submit = async () => {
    setErr("");
    if (!leadId) { setErr("Please select a target Lead first."); return; }
    if (!items.length) { setErr("Add at least one product or package to the quote."); return; }
    setSaving(true);
    try {
      const payload = {
        lead_id: leadId,
        template_type: templateType,
        items: items.map((i) => ({
          product: i.product,
          brand: i.brand,
          qty: Number(i.qty),
          unit_price: Number(i.unit_price),
          pricing_tier: i.pricing_tier,
          discount_pct: Number(i.discount_pct || 0),
          fixed_discount: Number(i.fixed_discount || 0),
          tax_pct: Number(i.tax_pct || 18),
          components: i.components || null,
          product_id: i.product_id
        })),
        shipping_charges: Number(shippingCharges || 0),
        installation_charges: Number(installationCharges || 0),
        amc_charges: Number(amcCharges || 0),
        terms,
        executive_summary: execSummary
      };
      const r = await api.post("/quotations", payload);
      navigate(`/leads/${leadId}`, { state: { newQuote: r.data.quote_no } });
    } catch (e) {
      setErr(formatApiError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="quote-builder-page">
      <Link to="/quotations" className="inline-flex items-center gap-1.5 text-xs text-sky-700 hover:text-sky-800 font-bold transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Quotations Dashboard
      </Link>

      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Quotation Engine</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <FileEdit className="w-8 h-8 text-sky-600" /> Enterprise Quotation Builder
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Build branded commercial quotations with multi-tier pricing, stock verification, and AI accessory recommendations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={runAiAssistance}
            disabled={aiLoading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-sky-700 bg-sky-50 border border-sky-200 hover:bg-sky-100 transition-all cursor-pointer"
          >
            <Sparkles className={`w-4 h-4 ${aiLoading ? "animate-spin text-sky-600" : ""}`} />
            {aiLoading ? "Analyzing Rigging..." : "AI System Assistant"}
          </button>
          <button
            onClick={submit}
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" />
            {saving ? "Generating Quote..." : "Save & Generate Quote"}
          </button>
        </div>
      </header>

      {err && <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl font-bold">{err}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Catalog Browser */}
        <div className="lg:col-span-7 space-y-5">
          {/* Step 1: Target Client / Lead */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-xs">
            <div className="label-eyebrow">Step 1 · Client & Lead Selection</div>
            {selectedLead ? (
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200" data-testid="qb-selected-lead">
                <div>
                  <div className="font-bold text-slate-900 text-sm">{selectedLead.name}</div>
                  <div className="text-xs text-slate-500 font-medium">{selectedLead.company || "Individual"} · {selectedLead.email || selectedLead.phone || "No direct phone"}</div>
                </div>
                <button onClick={() => { setLeadId(""); setLeadQuery(""); }} className="text-xs font-bold text-sky-600 hover:underline">Change</button>
              </div>
            ) : (
              <div className="relative">
                <input
                  value={leadQuery}
                  onChange={(e) => { setLeadQuery(e.target.value); setShowLeadList(true); }}
                  onFocus={() => setShowLeadList(true)}
                  placeholder="Search lead by client name, company, email..."
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                />
                {showLeadList && filteredLeads.length > 0 && (
                  <div className="absolute z-30 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-2xl max-h-60 overflow-y-auto">
                    {filteredLeads.map((l) => (
                      <button
                        key={l.id}
                        type="button"
                        onClick={() => { setLeadId(l.id); setLeadQuery(""); setShowLeadList(false); }}
                        className="w-full text-left px-4 py-2.5 hover:bg-slate-50 border-b border-slate-100 last:border-0"
                      >
                        <div className="text-sm font-bold text-slate-900">{l.name}</div>
                        <div className="text-xs text-slate-500">{l.company || "—"} · {l.email || l.phone}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Step 2: Catalog Browser & Pricing Tier */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-xs">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div className="label-eyebrow">Step 2 · Select Equipment</div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-bold">Pricing Tier:</span>
                <select
                  value={pricingTier}
                  onChange={(e) => setPricingTier(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1 text-xs text-sky-700 font-bold focus:outline-none"
                >
                  {PRICING_TIERS.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Brand Filter Ribbons */}
            <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
              {brands.map((b) => (
                <button
                  key={b.id || b.name}
                  onClick={() => !b.locked && setActiveBrand(b.name)}
                  disabled={b.locked}
                  className={`whitespace-nowrap px-3.5 py-2 rounded-xl text-xs font-bold transition-all border ${
                    activeBrand === b.name
                      ? "bg-slate-900 text-white border-slate-900 shadow-xs"
                      : "bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200"
                  }`}
                >
                  {b.name}
                </button>
              ))}
            </div>

            {/* Product / Package Mode Switcher & Search */}
            <div className="flex items-center justify-between gap-3">
              <div className="inline-flex bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-bold">
                <button
                  onClick={() => setBrowseMode("products")}
                  className={`px-3 py-1.5 rounded-lg transition-all ${browseMode === "products" ? "bg-white text-slate-900 shadow-xs font-extrabold" : "text-slate-600 hover:text-slate-900"}`}
                >
                  Products ({products.filter((p) => p.brand === activeBrand).length})
                </button>
                <button
                  onClick={() => setBrowseMode("packages")}
                  className={`px-3 py-1.5 rounded-lg transition-all ${browseMode === "packages" ? "bg-white text-slate-900 shadow-xs font-extrabold" : "text-slate-600 hover:text-slate-900"}`}
                >
                  Packages ({packages.filter((p) => p.brand === activeBrand).length})
                </button>
              </div>

              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={`Filter ${activeBrand}...`}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-sky-500 font-medium"
                />
              </div>
            </div>

            {/* Catalog List View */}
            <div className="max-h-[450px] overflow-y-auto no-scrollbar space-y-3 pt-2">
              {browseMode === "products" ? (
                Object.entries(groupedProducts).map(([cat, prods]) => (
                  <div key={cat} className="space-y-2">
                    <div className="text-[10px] font-extrabold uppercase tracking-widest text-sky-700 border-b border-slate-100 pb-1">{cat}</div>
                    <div className="grid grid-cols-1 gap-2">
                      {prods.map((p) => (
                        <div
                          key={p.id}
                          onClick={() => addProduct(p)}
                          className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-400 transition-all cursor-pointer group"
                        >
                          <div className="space-y-0.5">
                            <div className="text-xs font-bold text-slate-900 group-hover:text-sky-700 transition-colors">{p.name}</div>
                            <div className="text-[10px] text-slate-500 font-mono">Model: {p.model || "N/A"} · Stock: {p.stock_quantity || 10} units</div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="text-right">
                              <span className="text-[9px] uppercase text-slate-400 block font-bold">{pricingTier}</span>
                              <span className="font-display text-xs font-extrabold text-slate-900">₹{Number(getPriceForTier(p, pricingTier)).toLocaleString("en-IN")}</span>
                            </div>
                            <div className="w-7 h-7 rounded-lg bg-sky-100 text-sky-700 group-hover:bg-sky-600 group-hover:text-white flex items-center justify-center transition-all">
                              <Plus className="w-4 h-4" />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="grid grid-cols-1 gap-2">
                  {visiblePackages.map((pkg) => (
                    <div
                      key={pkg.id}
                      onClick={() => addPackage(pkg)}
                      className="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-400 transition-all cursor-pointer group"
                    >
                      <div className="space-y-0.5">
                        <div className="text-xs font-bold text-slate-900 group-hover:text-sky-700">{pkg.name}</div>
                        <div className="text-[10px] text-slate-500">Bundle SKU: {pkg.sku || "N/A"}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-display text-xs font-extrabold text-slate-900">₹{Number(pkg.fixed_price_inr || pkg.estimated_total || 0).toLocaleString("en-IN")}</span>
                        <div className="w-7 h-7 rounded-lg bg-sky-100 text-sky-700 group-hover:bg-sky-600 group-hover:text-white flex items-center justify-center">
                          <Plus className="w-4 h-4" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Quotation Summary & Line Items */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <div className="label-eyebrow">Line Items & Commercials</div>
                <h3 className="font-display text-lg font-bold text-slate-900">Selected Equipment ({items.length})</h3>
              </div>
              <select
                value={templateType}
                onChange={(e) => setTemplateType(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-bold text-slate-900"
              >
                {TEMPLATES.map((t) => (
                  <option key={t} value={t}>{t} Template</option>
                ))}
              </select>
            </div>

            {/* AI Recommendations Banner */}
            {aiRecommendations.length > 0 && (
              <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 space-y-2">
                <div className="text-xs font-bold text-sky-800 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-sky-600" /> AI Recommended Accessories
                </div>
                <div className="space-y-1.5">
                  {aiRecommendations.map((rec, i) => (
                    <div key={i} className="flex items-center justify-between text-xs bg-white p-2 rounded-lg border border-sky-100 shadow-2xs">
                      <div>
                        <div className="font-bold text-slate-900">{rec.name}</div>
                        <div className="text-[10px] text-slate-500 font-medium">{rec.reason}</div>
                      </div>
                      <button
                        onClick={() => addRecommendedAccessory(rec)}
                        className="px-2.5 py-1 rounded-md bg-sky-600 text-white text-[10px] font-bold hover:bg-sky-500 transition-all shrink-0 ml-2"
                      >
                        + Add
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Itemized Lines */}
            <div className="space-y-3 max-h-[350px] overflow-y-auto no-scrollbar pr-1">
              {calculatedLines.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-xs border border-dashed border-slate-200 rounded-xl p-6 font-medium">
                  No products added yet. Click items from the catalog browser on the left.
                </div>
              ) : (
                calculatedLines.map((i) => (
                  <div key={i.key} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="text-xs font-bold text-slate-900">{i.product}</div>
                        <div className="text-[10px] text-slate-500 font-medium">{i.brand} · Tier: {i.pricing_tier}</div>
                      </div>
                      <button onClick={() => removeItem(i.key)} className="text-slate-400 hover:text-rose-600 p-1">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <label className="text-[9px] uppercase text-slate-500 font-bold block">Qty</label>
                        <input
                          type="number"
                          min="1"
                          value={i.qty}
                          onChange={(e) => updateItem(i.key, { qty: parseInt(e.target.value) || 1 })}
                          className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-900 text-xs font-bold text-center"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] uppercase text-slate-500 font-bold block">Unit Rate (₹)</label>
                        <input
                          type="number"
                          value={i.unit_price}
                          onChange={(e) => updateItem(i.key, { unit_price: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-900 text-xs font-bold text-center"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] uppercase text-slate-500 font-bold block">Discount (%)</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={i.discount_pct}
                          onChange={(e) => updateItem(i.key, { discount_pct: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-900 text-xs font-bold text-center"
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1 border-t border-slate-200 text-xs">
                      <span className="text-[10px] text-emerald-700 font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Stock Available
                      </span>
                      <span className="font-display font-extrabold text-slate-900">₹{i.lineTotal.toLocaleString("en-IN")}</span>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Additional Charges */}
            <div className="border-t border-slate-200 pt-3 space-y-2 text-xs">
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-[10px] uppercase text-slate-500 font-bold block mb-0.5">Shipping (₹)</label>
                  <input
                    type="number"
                    value={shippingCharges}
                    onChange={(e) => setShippingCharges(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-900 text-xs font-bold"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase text-slate-500 font-bold block mb-0.5">Installation (₹)</label>
                  <input
                    type="number"
                    value={installationCharges}
                    onChange={(e) => setInstallationCharges(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-900 text-xs font-bold"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase text-slate-500 font-bold block mb-0.5">AMC (₹)</label>
                  <input
                    type="number"
                    value={amcCharges}
                    onChange={(e) => setAmcCharges(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-900 text-xs font-bold"
                  />
                </div>
              </div>

              {/* Total Breakdown */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between text-slate-600 text-xs font-medium">
                  <span>Subtotal:</span>
                  <span className="font-bold text-slate-900">₹{subtotal.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between text-slate-600 text-xs font-medium">
                  <span>GST (18%):</span>
                  <span className="font-bold text-slate-900">₹{tax.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between text-slate-900 font-extrabold text-sm pt-1 border-t border-slate-200">
                  <span>Grand Total:</span>
                  <span className="font-display font-black text-base text-sky-700">₹{grandTotal.toLocaleString("en-IN")}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
