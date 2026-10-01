import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { 
  Wallet, Plus, Trash2, Sparkles, CheckCircle2, History, AlertCircle, FileText, UserCircle
} from "lucide-react";
import { toast } from "sonner";

export default function PurchaseOrders() {
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [poNo, setPoNo] = useState("");
  const [items, setItems] = useState([
    { product_name: "", sku: "", qty: 1, unit_price: 0, tax_pct: 18 }
  ]);
  const [paymentTerms, setPaymentTerms] = useState("Net 30 Days from delivery confirmation.");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    fetchData();
    // Auto generate a mock PO number
    setPoNo(`HAI-PO-${Math.floor(100000 + Math.random() * 900000)}`);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [pos, sups, prods] = await Promise.all([
        api.get("/purchase-orders"),
        api.get("/suppliers"),
        api.get("/products")
      ]);
      setPurchaseOrders(pos.data);
      setSuppliers(sups.data);
      setProducts(prods.data);
      if (sups.data.length > 0) {
        setSelectedSupplierId(sups.data[0].id);
      }
    } catch (err) {
      toast.error("Failed to load PO workspace.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddItem = () => {
    setItems([...items, { product_name: "", sku: "", qty: 1, unit_price: 0, tax_pct: 18 }]);
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
        unit_price: matched.dealer_price || matched.msrp || 0
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
      const lineBase = (item.qty || 1) * (item.unit_price || 0);
      subtotal += lineBase;
      tax += lineBase * ((item.tax_pct || 18) / 100);
    });
    return { subtotal, tax, total: subtotal + tax };
  };

  const handleSavePO = async (e) => {
    e.preventDefault();
    if (!selectedSupplierId) {
      toast.error("Please select a supplier first.");
      return;
    }
    const sup = suppliers.find((s) => s.id === selectedSupplierId);
    try {
      setSubmitting(true);
      const { subtotal, tax, total } = calculateTotals();
      const payload = {
        po_no: poNo,
        supplier_id: selectedSupplierId,
        supplier_name: sup ? (sup.company || sup.name) : "Supplier",
        items,
        subtotal,
        tax,
        total,
        payment_terms: paymentTerms,
        notes,
        status: "approved"
      };
      await api.post("/purchase-orders", payload);
      toast.success("Purchase Order issued and approved!");
      setItems([{ product_name: "", sku: "", qty: 1, unit_price: 0, tax_pct: 18 }]);
      setPoNo(`HAI-PO-${Math.floor(100000 + Math.random() * 900000)}`);
      fetchData();
    } catch (err) {
      toast.error("Failed to submit Purchase Order.");
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
            <span>Enterprise Procurement</span>
            <span>/</span>
            <span className="text-slate-900">Supply Chain</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Wallet className="w-8 h-8 text-sky-600" />
            Supplier Purchase Orders (PO)
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Compile authorized supplier purchase orders, select regional distributors, set delivery schedules, and manage manager-level sign-offs.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-slate-500 text-sm font-medium">Loading PO dashboard...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Form Builder */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-6">
              <h3 className="font-display text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">
                <Sparkles className="w-5 h-5 text-sky-600" /> Issue Supplier PO
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Purchase Order No *</label>
                  <input
                    type="text"
                    required
                    value={poNo}
                    onChange={(e) => setPoNo(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Select Supplier / Manufacturer</label>
                  <select
                    value={selectedSupplierId}
                    onChange={(e) => setSelectedSupplierId(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-semibold"
                  >
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>{s.company || s.name} • {s.city}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Items */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-display text-sm font-bold text-slate-800 uppercase tracking-wide">Itemized Supply Order</h4>
                  <button
                    type="button"
                    onClick={handleAddItem}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Row
                  </button>
                </div>

                <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                  {items.map((item, idx) => (
                    <div key={idx} className="bg-white border border-slate-200 rounded-xl p-4 space-y-3 relative group">
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(idx)}
                        className="absolute right-4 top-4 text-slate-400 hover:text-rose-600 cursor-pointer transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pr-6">
                        <div>
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
                        <div className="grid grid-cols-3 gap-2">
                          <div className="col-span-1">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Qty</label>
                            <input
                              type="number"
                              required
                              min="1"
                              value={item.qty}
                              onChange={(e) => handleItemChange(idx, "qty", parseInt(e.target.value) || 1)}
                              className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-bold"
                            />
                          </div>
                          <div className="col-span-2">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Rate (INR)</label>
                            <input
                              type="number"
                              required
                              min="0"
                              value={item.unit_price}
                              onChange={(e) => handleItemChange(idx, "unit_price", parseFloat(e.target.value) || 0)}
                              className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-mono font-bold"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Payment Schedule & Terms</label>
                  <input
                    type="text"
                    value={paymentTerms}
                    onChange={(e) => setPaymentTerms(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Additional Procurement Notes</label>
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="e.g., Shipping logistics instructions..."
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-3">
                <button
                  onClick={handleSavePO}
                  disabled={submitting}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" /> {submitting ? "Submitting..." : "Approve & Dispatch PO"}
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Values & History */}
          <div className="space-y-6">
            <div className="bg-slate-900 text-white rounded-2xl p-6 space-y-6 shadow-xl border border-slate-800">
              <h3 className="font-display text-sm font-bold text-sky-400 uppercase tracking-wider">Purchase Order Totals</h3>
              
              <div className="space-y-4">
                <div className="flex justify-between items-center text-sm font-medium text-slate-400">
                  <span>Pre-tax Amount:</span>
                  <span className="font-mono text-white text-base">₹{subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between items-center text-sm font-medium text-slate-400">
                  <span>Customs / Standard GST (18%):</span>
                  <span className="font-mono text-white text-base">₹{tax.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="border-t border-slate-800 pt-4 flex justify-between items-center text-base font-extrabold text-sky-400">
                  <span>PO Total:</span>
                  <span className="font-mono text-xl text-sky-400">₹{total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                </div>
              </div>
            </div>

            {/* Issued History */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
              <h3 className="font-display text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-600" /> Issued Purchase Orders (POs)
              </h3>
              <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto pr-1">
                {purchaseOrders.map((po) => (
                  <div key={po.id} className="py-3.5 space-y-1.5 text-xs font-semibold">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-900 font-bold">{po.po_no}</span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 capitalize">{po.status}</span>
                    </div>
                    <div className="flex justify-between text-slate-500 font-mono">
                      <span>{po.supplier_name}</span>
                      <span>₹{po.total?.toLocaleString("en-IN")}</span>
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