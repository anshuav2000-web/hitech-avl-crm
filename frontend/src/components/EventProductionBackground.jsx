import { memo } from "react";

export const EventProductionBackground = memo(function EventProductionBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none bg-white">
      {/* 1. Technical Grid Lines on Clean White */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(15, 23, 42, 0.2) 1px, transparent 1px),
            linear-gradient(90deg, rgba(15, 23, 42, 0.2) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
        }}
      />

      {/* 2. Soft Ambient Vignette */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          background: `
            radial-gradient(ellipse 80% 50% at 20% -10%, rgba(2, 132, 199, 0.08) 0%, transparent 70%),
            radial-gradient(ellipse 60% 45% at 85% 105%, rgba(99, 102, 241, 0.06) 0%, transparent 65%)
          `,
        }}
      />

      {/* 3. Subtle Stage Truss Lineart */}
      <svg
        className="absolute -top-10 left-1/2 -translate-x-1/2 w-full h-[300px] opacity-[0.04]"
        viewBox="0 0 1200 300"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <line x1="100" y1="30" x2="1100" y2="30" stroke="#0f172a" strokeWidth="2" strokeDasharray="6 6" />
        <line x1="100" y1="50" x2="1100" y2="50" stroke="#0f172a" strokeWidth="2" strokeDasharray="6 6" />
        <rect x="220" y="50" width="28" height="16" rx="3" fill="#0f172a" />
        <rect x="580" y="50" width="28" height="16" rx="3" fill="#0f172a" />
        <rect x="940" y="50" width="28" height="16" rx="3" fill="#0f172a" />
      </svg>
    </div>
  );
});
