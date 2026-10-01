// Single source of truth for the pipeline vocabulary.
//
// Before this module the 24 stages were duplicated in four places (Pipeline.js as
// objects, Leads.js and LeadDetail.js as bare strings, Dashboard.js as a label
// map) and had already drifted apart -- bug B5 exists because StageBadge still
// keyed its colours on the legacy new/contacted/qualified/quoted/won/lost set,
// none of which are real stage ids any more.
//
// The values below are only a fallback for the first paint. Once ConfigContext
// resolves /api/config/lead_stages the live config wins, so an admin renaming a
// stage in Settings propagates everywhere without a code change.

export const FALLBACK_STAGES = [
  // Initiation
  { key: "new", label: "New Lead", accent: "bg-blue-500", group: "Initiation" },
  { key: "assigned", label: "Assigned", accent: "bg-indigo-500", group: "Initiation" },
  { key: "contact_attempted", label: "Contact Attempted", accent: "bg-sky-500", group: "Initiation" },
  { key: "contacted", label: "Contacted", accent: "bg-emerald-500", group: "Initiation" },
  { key: "not_contacted", label: "Not Contacted", accent: "bg-slate-400", group: "Initiation" },
  { key: "call_back_later", label: "Call Back Later", accent: "bg-amber-400", group: "Initiation" },
  // Qualification
  { key: "detailed_requirement_discussion", label: "Detailed Requirement Discussion", accent: "bg-purple-500", group: "Qualification" },
  { key: "interested", label: "Interested", accent: "bg-teal-500", group: "Qualification" },
  { key: "qualified", label: "Qualified", accent: "bg-emerald-600", group: "Qualification" },
  { key: "need_analysis", label: "Need Analysis", accent: "bg-orange-500", group: "Qualification" },
  { key: "forward_to_design", label: "Forward to Design", accent: "bg-rose-500", group: "Qualification" },
  { key: "drawing", label: "CAD Drawing", accent: "bg-rose-600", group: "Qualification" },
  // Quotation Flow
  { key: "boq_creation", label: "BOQ Creation", accent: "bg-sky-600", group: "Quotation Flow" },
  { key: "send_boq_design", label: "Send BOQ & Design", accent: "bg-blue-600", group: "Quotation Flow" },
  { key: "boq_finalized", label: "BOQ Finalized", accent: "bg-indigo-600", group: "Quotation Flow" },
  { key: "convert_to_quotation", label: "Convert to Quotation", accent: "bg-purple-600", group: "Quotation Flow" },
  { key: "send_quotation", label: "Send Quotation", accent: "bg-pink-600", group: "Quotation Flow" },
  { key: "quotation_negotiation", label: "Quotation Negotiation", accent: "bg-amber-600", group: "Quotation Flow" },
  // Closing
  { key: "quotation_rejected", label: "Quotation Rejected", accent: "bg-rose-700", group: "Closing" },
  { key: "quotation_confirmed", label: "Quotation Confirmed", accent: "bg-emerald-700", group: "Closing" },
  { key: "po_received", label: "PO Received", accent: "bg-teal-700", group: "Closing" },
  { key: "invoice_raised", label: "Invoice Raised", accent: "bg-blue-700", group: "Closing" },
  { key: "completed", label: "Completed", accent: "bg-emerald-800", group: "Closing" },
  { key: "lost_lead", label: "Lost Lead", accent: "bg-red-600", group: "Closing" },
];

export const FALLBACK_SOURCES = [
  "facebook", "instagram", "linkedin", "website_contact_form",
  "direct_enquiry", "cold_call", "business_whatsapp", "email",
  "channel_partner", "internal_employee_referral", "existing_customer", "walk_in_customer",
];

// The won/lost markers are flags on the config items, not hard-coded ids. These
// match the backend's TERMINAL_STAGE_FALLBACK and are used only until the config
// resolves. Never invent "won"/"lost" as stage ids again -- bug B4.
export const FALLBACK_WON_KEY = "quotation_confirmed";
export const FALLBACK_LOST_KEY = "lost_lead";

/** Tailwind classes need to exist statically, so accents are looked up, not built. */
const ACCENT_BY_COLOR = {
  slate: "bg-slate-400", blue: "bg-blue-500", sky: "bg-sky-500", emerald: "bg-emerald-500",
  teal: "bg-teal-500", amber: "bg-amber-400", orange: "bg-orange-500", rose: "bg-rose-500",
  purple: "bg-purple-500", indigo: "bg-indigo-500", red: "bg-red-600",
};

/** Pill tint pairs used by badges across the app. */
const TINT_BY_COLOR = {
  slate: "bg-slate-50 text-slate-700 border-slate-200",
  sky: "bg-sky-50 text-sky-700 border-sky-200",
  blue: "bg-blue-50 text-blue-700 border-blue-200",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
  teal: "bg-teal-50 text-teal-700 border-teal-200",
  amber: "bg-amber-50 text-amber-700 border-amber-200",
  orange: "bg-orange-50 text-orange-700 border-orange-200",
  rose: "bg-rose-50 text-rose-700 border-rose-200",
  red: "bg-rose-50 text-rose-700 border-rose-200",
  purple: "bg-purple-50 text-purple-700 border-purple-200",
  indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
};

export const accentFor = (color) => ACCENT_BY_COLOR[color] || "bg-slate-400";
export const tintFor = (color) => TINT_BY_COLOR[color] || TINT_BY_COLOR.slate;

/** Turn a crm_config_sets `lead_stages` document into the shape pages consume. */
export function normaliseStages(doc) {
  const items = doc?.items || [];
  if (!items.length) return null;
  return items
    .filter((it) => it.is_active !== false)
    .slice()
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((it) => ({
      key: it.id,
      label: it.label || it.id,
      accent: accentFor(it.color),
      group: it.group || "Pipeline",
      isWon: !!it.is_won,
      isLost: !!it.is_lost,
      isOpen: it.is_open,
      color: it.color,
    }));
}

export function normaliseSources(doc) {
  const items = doc?.items || [];
  if (!items.length) return null;
  return items.filter((it) => it.is_active !== false).map((it) => it.id);
}

/** Ordered, de-duplicated group list for the pipeline tab bar. */
export function groupsOf(stages) {
  const seen = [];
  for (const s of stages) if (!seen.includes(s.group)) seen.push(s.group);
  return seen;
}
