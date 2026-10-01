// Brand assets pulled from www.hitechavl.com CMS
export const HITECH_LOGO = "https://customer-assets.emergentagent.com/job_db40f655-6e53-4589-a605-467da9dcc230/artifacts/hitech-logo.png";
// We try the real site logo first; if it fails, fallback to a wordmark
export const HITECH_LOGO_FALLBACKS = [
  "https://www.hitechavl.com/img/logo.png",
  "https://www.hitechavl.com/img/logo.svg",
  "https://cms.hitechavl.com/files/images/logo.png",
];

export function HitechLogo({ className = "h-9", invert = false }) {
  return (
    <div className={`flex items-center gap-2.5`}>
      <div className={`relative ${className} aspect-square rounded-md flex items-center justify-center font-display font-black text-white`}
           style={{ background: invert ? "#fff" : "#DC2626", color: invert ? "#DC2626" : "#fff" }}>
        <span className="text-[11px] tracking-tighter">Hi-T</span>
      </div>
      <div className="leading-tight">
        <div className={`font-display font-bold text-[15px] ${invert ? "text-white" : "text-slate-900"}`}>Hi-Tech</div>
        <div className={`text-[10px] tracking-[0.18em] font-medium uppercase ${invert ? "text-white/70" : "text-slate-500"}`}>Audio & Image LLP</div>
      </div>
    </div>
  );
}
