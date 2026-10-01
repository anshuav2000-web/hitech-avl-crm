import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { 
  ShieldCheck, Calculator, AlertCircle, ArrowUpRight, Flame, Thermometer, Snowflake, BadgePercent, Sparkles
} from "lucide-react";
import { toast } from "sonner";

export default function Qualification() {
  const [leads, setLeads] = useState([]);
  const [selectedLeadId, setSelectedLeadId] = useState("");
  const [loading, setLoading] = useState(true);
  const [qualifications, setQualifications] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  
  const [bant, setBant] = useState({
    budget: "medium",
    authority: "influencer",
    need: "high",
    timeline: "3_months",
    product_fit: "good",
    decision_maker: true,
    business_size: "mid_market",
    urgency: "medium"
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await api.get("/leads");
      setLeads(res.data);
      if (res.data.length > 0) {
        setSelectedLeadId(res.data[0].id);
        fetchLeadQualification(res.data[0].id);
      }
    } catch (err) {
      toast.error("Failed to load leads list.");
    } finally {
      setLoading(false);
    }
  };

  const fetchLeadQualification = async (leadId) => {
    try {
      const res = await api.get(`/leads/${leadId}/qualification`);
      setQualifications(res.data);
    } catch (err) {
      setQualifications([]);
    }
  };

  const handleLeadChange = (e) => {
    const leadId = e.target.value;
    setSelectedLeadId(leadId);
    fetchLeadQualification(leadId);
  };

  const handleQualifySubmit = async (e) => {
    e.preventDefault();
    if (!selectedLeadId) {
      toast.error("Please select a lead first.");
      return;
    }
    try {
      setSubmitting(true);
      await api.post(`/leads/${selectedLeadId}/qualify`, bant);
      toast.success("Lead qualification calculated successfully!");
      fetchLeadQualification(selectedLeadId);
    } catch (err) {
      toast.error("Failed to save lead qualification.");
    } finally {
      setSubmitting(false);
    }
  };

  const getClassificationBadge = (cls) => {
    switch (cls) {
      case "hot":
        return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200"><Flame className="w-3.5 h-3.5 fill-rose-500 animate-pulse" /> Hot Lead</span>;
      case "warm":
        return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200"><Thermometer className="w-3.5 h-3.5" /> Warm Lead</span>;
      case "cold":
        return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-sky-50 text-sky-700 border border-sky-200"><Snowflake className="w-3.5 h-3.5" /> Cold Lead</span>;
      case "qualified":
        return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200"><ShieldCheck className="w-3.5 h-3.5" /> Qualified</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-slate-50 text-slate-700 border border-slate-200"><AlertCircle className="w-3.5 h-3.5" /> Unqualified</span>;
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-8 bg-white text-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-sky-700 font-bold uppercase tracking-wider mb-2">
            <span>Enterprise Sales Automation</span>
            <span>/</span>
            <span className="text-slate-900">Lead Qualification</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-sky-600" />
            BANT Qualification Scorecard
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Automatically calculate qualification scoring based on Budget, Authority, Need, and Timeline parameters to classify leads as Hot, Warm, or Cold.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-slate-500 text-sm font-medium">Loading qualification parameters...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Form Selector */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-6">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-2">Select Active Lead for Evaluation</label>
                <select
                  value={selectedLeadId}
                  onChange={handleLeadChange}
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-semibold"
                >
                  {leads.map((l) => (
                    <option key={l.id} value={l.id}>{l.name} • {l.company || "Direct Enquiry"}</option>
                  ))}
                </select>
              </div>

              <form onSubmit={handleQualifySubmit} className="space-y-6 border-t border-slate-200 pt-6">
                <h3 className="font-display text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-sky-600" /> Calculate BANT Matrix
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Budget */}
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Budget Allocation</label>
                    <select
                      value={bant.budget}
                      onChange={(e) => setBant({ ...bant, budget: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                    >
                      <option value="high">High Allocation (Premium L-Acoustics/DiGiCo level)</option>
                      <option value="medium">Medium Allocation (RCF level)</option>
                      <option value="low">Low Allocation (Budget / Local audio brand)</option>
                      <option value="none">No current allocation defined</option>
                    </select>
                  </div>

                  {/* Authority */}
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Decision Authority</label>
                    <select
                      value={bant.authority}
                      onChange={(e) => setBant({ ...bant, authority: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                    >
                      <option value="decision_maker">Direct Decision Maker (Owner/Director/Purchasing Head)</option>
                      <option value="influencer">Technical Consultant / Sound Engineer (Highly influential)</option>
                      <option value="end_user">End User / Operator</option>
                      <option value="gatekeeper">Gatekeeper (Administrative / Secretary)</option>
                    </select>
                  </div>

                  {/* Need */}
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Need Analysis</label>
                    <select
                      value={bant.need}
                      onChange={(e) => setBant({ ...bant, need: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                    >
                      <option value="urgent">Critical/Urgent (Major upcoming concert/arena launch)</option>
                      <option value="high">High (Club/Theatre installation upgrade)</option>
                      <option value="medium">Medium (Standard rental expansion)</option>
                      <option value="low">Low (General exploration/interest)</option>
                      <option value="none">Undefined requirements</option>
                    </select>
                  </div>

                  {/* Timeline */}
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Project Timeline</label>
                    <select
                      value={bant.timeline}
                      onChange={(e) => setBant({ ...bant, timeline: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                    >
                      <option value="immediate">Immediate (Within 2 weeks)</option>
                      <option value="1_month">Near Term (Within 1 Month)</option>
                      <option value="3_months">Medium Term (Within 3 Months)</option>
                      <option value="6_months">Long Term (Beyond 6 Months)</option>
                      <option value="none">No timeline committed</option>
                    </select>
                  </div>

                  {/* Product Fit */}
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Product Catalog Fit</label>
                    <select
                      value={bant.product_fit}
                      onChange={(e) => setBant({ ...bant, product_fit: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                    >
                      <option value="excellent">Excellent Fit (Demanding premium European gear)</option>
                      <option value="good">Good Fit (Standard AV installations)</option>
                      <option value="fair">Fair Fit (Requires customized bundles/OEM imports)</option>
                      <option value="poor">Poor Fit (Budget constraints mismatch)</option>
                    </select>
                  </div>

                  {/* Business Size */}
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-1">Business Scale</label>
                    <select
                      value={bant.business_size}
                      onChange={(e) => setBant({ ...bant, business_size: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-sky-500 font-medium"
                    >
                      <option value="enterprise">National Touring / Large-scale Rental OEM</option>
                      <option value="mid_market">Mid-market Club / Premium Auditorium</option>
                      <option value="smb">Standard Church / Hall / Corporate AV</option>
                      <option value="startup">New AV Rental Startup</option>
                      <option value="individual">Individual Consultant / Freelance Sound Engineer</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-4 bg-white border border-slate-200 rounded-xl p-4">
                  <input
                    type="checkbox"
                    id="decision_maker"
                    checked={bant.decision_maker}
                    onChange={(e) => setBant({ ...bant, decision_maker: e.target.checked })}
                    className="w-4 h-4 text-sky-600 focus:ring-sky-500 border-slate-300 rounded"
                  />
                  <label htmlFor="decision_maker" className="text-sm font-semibold text-slate-700 cursor-pointer">
                    Confirm directly communicating with a verified budget owner / decision authority
                  </label>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <Sparkles className="w-4 h-4 animate-spin-slow" /> {submitting ? "Calculating..." : "Compute score & classify"}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Right Column: Calculations & History */}
          <div className="space-y-6">
            <div className="bg-slate-900 text-white rounded-2xl p-6 space-y-6 shadow-xl border border-slate-800">
              <h3 className="font-display text-lg font-bold flex items-center gap-2 text-sky-400">
                <ShieldCheck className="w-5 h-5 text-sky-400" /> Lead Qualification Status
              </h3>

              {qualifications.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-sm">
                  No evaluations computed yet for this lead. Complete the form to run BANT analysis.
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Score circle */}
                  <div className="flex flex-col items-center justify-center p-4 border border-slate-800 rounded-2xl bg-slate-950">
                    <span className="text-xs uppercase tracking-wider text-slate-400 font-bold">Qualification Score</span>
                    <span className="text-5xl font-extrabold text-white mt-2 font-mono">{qualifications[0].score}<span className="text-sm text-sky-400">/100</span></span>
                    <div className="mt-4">{getClassificationBadge(qualifications[0].classification)}</div>
                  </div>

                  <div className="space-y-3.5 border-t border-slate-800 pt-4 text-sm font-medium">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Budget Match:</span>
                      <span className="text-white capitalize">{qualifications[0].budget}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Decision Authority:</span>
                      <span className="text-white capitalize">{qualifications[0].authority?.replace("_", " ")}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Urgency Level:</span>
                      <span className="text-white capitalize">{qualifications[0].need}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Timeline Commitment:</span>
                      <span className="text-white capitalize">{qualifications[0].timeline?.replace("_", " ")}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Historical Log */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
              <h3 className="font-display text-sm font-bold text-slate-900 uppercase tracking-wider">Evaluation History</h3>
              <div className="divide-y divide-slate-100 max-h-60 overflow-y-auto pr-2">
                {qualifications.map((q, idx) => (
                  <div key={idx} className="py-3 flex justify-between items-center text-xs font-medium">
                    <div>
                      <div className="text-slate-900 font-bold capitalize">{q.classification} classification</div>
                      <div className="text-slate-500 mt-0.5">{new Date(q.created_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}</div>
                    </div>
                    <div className="font-mono text-slate-900 font-extrabold text-sm">{q.score} pts</div>
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