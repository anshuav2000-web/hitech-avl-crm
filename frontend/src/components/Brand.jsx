import { memo } from "react";

const LOGO_URL = "/logo.png";
const GOOGLE_DRIVE_DIRECT = "https://lh3.googleusercontent.com/d/1Ldp6Kc-5Ztio4Yv_LlXUo0QvSfVVH0Ek";

const HitechLogo = ({ className = "h-8", showText = true }) => {
  return (
    <div className="flex items-center gap-2 select-none">
      <img
        src={LOGO_URL}
        onError={(e) => {
          e.currentTarget.onerror = null;
          e.currentTarget.src = GOOGLE_DRIVE_DIRECT;
        }}
        alt="Hitech Audio & Image Logo"
        className={`${className} w-auto object-contain max-h-10`}
      />
    </div>
  );
};

export const HitechLogo = memo(HitechLogo);
