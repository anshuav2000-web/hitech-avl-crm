import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { 
  Receipt, Plus, Trash2, Sparkles, CheckCircle2, History, AlertCircle, FileText, ChevronRight
} from "lucide-react";
import { toast } from "sonner";

export default function BoqGenerator() {
  const [boqs, setBoqs] = useState([]);
  const [leads, setLeads] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [selectedLeadId, setSelectedLeadId] = useState("");
  const [items, setItems] = useState([
    { product_name: "", sku: "", brand: "", qty: 1, unit_price: 0, discount_pct: 0, fixed_discount: 0, tax_pct: 18 }
  ]);
  const [terms, setTerms] = useState("Standard payment terms: 50% advance, 50% before dispatch.");
  const [notes, setNotes] = useState("Price valid for 30 days from date of generation.");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [boqList, lds, prods] = await Promise.all([
        api.get("/boqs"),
        api.get("/leads"),
        api.get("/products")
      ]);
      setBoqs(boqList.data);
      setLeads(lds.data);
      setProducts(prods.data);
      if (lds.data.length > 0) {
        setSelectedLeadId(lds.data[0].id);
      }
    } catch (err) {
      toast.error("Failed to load BOQ workspace.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddItem = () => {
    setItems([...items, { product_name: "", sku: "", brand: "", qty: 1, unit_price: 0, discount_pct: 0, fixed_discount: 0, tax_pct: 18 }]);
  };

  const handleRemoveItem = (index) => {
    const list = [...items];
    list.splice(index, 1);
    setItems(list);
  };

  const handleProductSelect = (index, prodName) => {
    const matched = products.find((p) => p.name === prodName);
    const list = [...items];
    if (matched) {
      list[index] = {
        ...list[index],
        product_name: matched.name,
        sku: matched.sku || "",
        brand: matched.brand || "",
        unit_price: matched.unit_price || matched.msrp || 0
      };
    } else {
      list[index].product_name = prodName;
    }
    setItems(list);
  };

  const handleItemChange = (index, field, value) => {
    const list = [...items];
    list[index][field] = value;
    setItems(list);
  };

  const calculateTotals = () => {
    let subtotal = 0;
    let tax = 0;
    items.forEach((item) => {
      const base = (item.qty || 1) * (item.unit_price || 0);
      const discount = (base * ((item.discount_pct || 0) / 100)) + (item.fixed_discount || 0);
      const lineTotal = Math.max(0, base - discount);
      subtotal += lineTotal;
      tax += lineTotal * ((item.tax_pct || 18) / 100);
    });
    return { subtotal, tax, total: subtotal + tax };
  };

  const handleSaveBOQ = async (e) => {
    e.preventDefault();
    if (!selectedLeadId) {
      toast.error("Please select a lead first.");
      return;
    }
    try {
      setSubmitting(true);
      const { subtotal, tax, total } = calculateTotals();
      const payload = {
        lead_id: selectedLeadId,
        items,
        subtotal,
        tax,
        total,
        terms,
        notes,
        status: "approved",
        version: 1
      };
      await api.post("/boqs", payload);
      toast.success("BOQ layout compiled and approved!");
      setItems([{ product_name: "", sku: "", brand: "", qty: 1, unit_price: 0, discount_pct: 0, fixed_discount: 0, tax_pct: 18 }]);
      fetchData();
    } catch (err) {
      toast.error("Failed to compile BOQ layout.");
    } finally {
      setSubmitting(false);
    }
  };

  const { subtotal, tax, total } = calculateTotals();

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-8 bg-white text-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-sky-700 font-bold uppercase tracking-wider mb-2">
            <span>Enterprise Proposals</span>
            <span>/</span>
            <span className="text-slate-900">Commercial Workflow</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Receipt className="w-8 h-8 text-sky-600" />
            BOQ Generator & Version Controller
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Design itemized commercial bills, configure products, custom margins, dynamic tax calculations, and manage revision history.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-slate-500 text-sm font-medium">Loading BOQ layout workspace...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Generator Form */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-6">
              <h3 className="font-display text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">
                <Sparkles className="w-5 h-5 text-sky-600" /> Create Bill of Quantities (BOQ)
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Select Lead / Account</label>
                  <select
                    value={selectedLeadId}
                    onChange={(e) => setSelectedLeadId(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  >
                    {leads.map((l) => (
                      <option key={l.id} value={l.id}>{l.name} • {l.company || "Direct"}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Items Table */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-display text-sm font-bold text-slate-800 uppercase tracking-wide">Itemized Products & Quantities</h4>
                  <button
                    type="button"
                    onClick={handleAddItem}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Row
                  </button>
                </div>

                <div className="space-y-3.5 max-h-96 overflow-y-auto pr-1">
                  {items.map((item, idx) => (
                    <div key={idx} className="bg-white border border-slate-200 rounded-xl p-4 space-y-3 relative group">
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(idx)}
                        className="absolute right-4 top-4 text-slate-400 hover:text-rose-600 cursor-pointer transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pr-6">
                        {/* Select Catalog Product or Custom text */}
                        <div className="md:col-span-2">
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Select Product Model *</label>
                          <select
                            value={item.product_name}
                            onChange={(e) => handleProductSelect(idx, e.target.value)}
                            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                          >
                            <option value="">-- Choose from Catalog --</option>
                            {products.map((p) => (
                              <option key={p.id} value={p.name}>{p.brand} • {p.name}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Brand Name</label>
                          <input
                            type="text"
                            value={item.brand}
                            onChange={(e) => handleItemChange(idx, "brand", e.target.value)}
                            placeholder="Brand"
                            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Qty</label>
                          <input
                            type="number"
                            required
                            min="1"
                            value={item.qty}
                            onChange={(e) => handleItemChange(idx, "qty", parseInt(e.target.value) || 1)}
                            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-bold"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Unit Rate (INR)</label>
                          <input
                            type="number"
                            required
                            min="0"
                            value={item.unit_price}
                            onChange={(e) => handleItemChange(idx, "unit_price", parseFloat(e.target.value) || 0)}
                            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-bold"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Disc (%)</label>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={item.discount_pct}
                            onChange={(e) => handleItemChange(idx, "discount_pct", parseFloat(e.target.value) || 0)}
                            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Fixed Disc</label>
                          <input
                            type="number"
                            min="0"
                            value={item.fixed_discount}
                            onChange={(e) => handleItemChange(idx, "fixed_discount", parseFloat(e.target.value) || 0)}
                            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">GST Tax (%)</label>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={item.tax_pct}
                            onChange={(e) => handleItemChange(idx, "tax_pct", parseFloat(e.target.value) || 18)}
                            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Commercial / Delivery Terms</label>
                <textarea
                  rows={2}
                  value={terms}
                  onChange={(e) => setTerms(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                />
              </div>

              <div className="flex justify-end pt-3">
                <button
                  onClick={handleSaveBOQ}
                  disabled={submitting}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" /> {submitting ? "Compiling Layout..." : "Compile & Sign-off BOQ"}
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Totals & History */}
          <div className="space-y-6">
            <div className="bg-slate-900 text-white rounded-2xl p-6 space-y-6 shadow-xl border border-slate-800">
              <h3 className="font-display text-sm font-bold text-sky-400 uppercase tracking-wider">BOQ Invoice Calculations</h3>
              
              <div className="space-y-4">
                <div className="flex justify-between items-center text-sm font-medium text-slate-400">
                  <span>Gross Subtotal:</span>
                  <span className="font-mono text-white text-base">₹{subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between items-center text-sm font-medium text-slate-400">
                  <span>SGST + CGST (GST):</span>
                  <span className="font-mono text-white text-base">₹{tax.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
                <div className="border-t border-slate-800 pt-4 flex justify-between items-center text-base font-extrabold text-sky-400">
                  <span>Grand Total:</span>
                  <span className="font-mono text-xl text-sky-400">₹{total.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              </div>
            </div>

            {/* Version Revision History */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
              <h3 className="font-display text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <History className="w-4 h-4 text-sky-600" /> Compiled BOQ Versions
              </h3>
              <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto pr-1">
                {boqs.map((boq) => (
                  <div key={boq.id} className="py-3.5 space-y-1.5 text-xs font-semibold">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-900 font-bold">BOQ Version v{boq.version}</span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 capitalize">{boq.status}</span>
                    </div>
                    <div className="flex justify-between text-slate-500 font-mono">
                      <span>Total Value: ₹{boq.total?.toLocaleString("en-IN")}</span>
                      <span>{new Date(boq.created_at).toLocaleDateString("en-IN")}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>
      )}
    </div>
  );
}