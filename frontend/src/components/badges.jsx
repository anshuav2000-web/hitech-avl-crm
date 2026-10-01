import { useConfig } from "@/context/ConfigContext";

// Extracted from pages/Dashboard.js because Leads.js and LeadDetail.js both
// imported StageBadge/SourceBadge from a page module -- editing the dashboard
// could silently break list rendering elsewhere.
//
// Bug B5 lived here too: the colour map was keyed on the legacy
// new/contacted/qualified/quoted/won/lost set. None of those are real stage ids
// ("quoted", "won" and "lost" never existed), so every badge fell through to
// grey. Colour now comes from the live lead_stages config, which carries a real
// `color` per stage.

export const sourceColors = {
  facebook: "#1877f2",
  instagram: "#e1306c",
  linkedin: "#0a66c2",
  website_contact_form: "#0284c7",
  direct_enquiry: "#0f172a",
  cold_call: "#64748b",
  business_whatsapp: "#25d366",
  email: "#ea4335",
  channel_partner: "#9333ea",
  internal_employee_referral: "#ec4899",
  existing_customer: "#059669",
  walk_in_customer: "#d97706",
  // Fallbacks for older data
  website: "#0284c7",
  whatsapp: "#25d366",
  manual: "#0f172a",
  referral: "#9333ea",
  exhibition: "#d97706",
};

export const statusColors = {
  draft: "#64748b",
  sent: "#0284c7",
  accepted: "#059669",
  rejected: "#e11d48",
};

const TINTS = {
  slate: "bg-slate-100 text-slate-700 border-slate-200",
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
  pink: "bg-pink-50 text-pink-700 border-pink-200",
};

export const tintForColor = (color) => TINTS[color] || TINTS.slate;

export function StageBadge({ stage }) {
  const { stageByKey, stageLabels } = useConfig();
  const meta = stageByKey[stage];
  const tint = tintForColor(meta?.color);

  // Terminal stages read as outcomes, so they get a solid semantic colour even
  // if an admin picked an arbitrary palette colour for them.
  const semantic = meta?.isWon
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : meta?.isLost
      ? "bg-rose-50 text-rose-700 border-rose-200"
      : tint;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${semantic}`}
      data-testid="stage-badge"
      data-stage={stage}
    >
      {stageLabels[stage] || stage}
    </span>
  );
}

export function SourceBadge({ source }) {
  const hex = sourceColors[source] || "#0284c7";
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border capitalize"
      style={{ borderColor: `${hex}55`, color: hex, backgroundColor: `${hex}10` }}
    >
      {source}
    </span>
  );
}
