import { memo } from "react";

/**
 * The Hi-Tech Audio & Image logo.
 *
 * Primary source is the Google Drive file the business supplied. The bundled
 * ``public/logo.png`` is the fallback: Drive rate-limits and serves an HTML error
 * page under load, and an HTML body decoded as an image renders as a broken image
 * in every header, sidebar and login screen at once. Having a local copy means the
 * worst case is a slightly older logo, not a blank brand mark.
 *
 * The id is the image's public URL, so nothing about the CRM's data is exposed by
 * loading it -- the same reasoning that makes ``/api/media/{id}`` public.
 */
export const HITECH_LOGO =
  "https://drive.google.com/uc?export=view&id=1680IgbZrG_C1HodFQumzwTt1F6d9qcSv";

const HITECH_LOGO_FALLBACK = "/logo.png";

/**
 * @param className Height of the mark; width follows the image aspect ratio.
 * @param invert   Rendered on a dark background (login split panel, coloured hero).
 *   The logo is dropped behind a light pill rather than recoloured, because
 *   inverting a raster logo destroys the colours that identify the brand.
 */
const HitechLogo = ({ className = "h-9", invert = false }) => (
  <div className="flex items-center select-none">
    <img
      src={HITECH_LOGO}
      // Cleared before reassignment: without it a failing fallback re-enters
      // onError and the browser loops the request forever.
      onError={(e) => {
        e.currentTarget.onerror = null;
        e.currentTarget.src = HITECH_LOGO_FALLBACK;
      }}
      alt="Hi-Tech Audio & Image LLP"
      className={`${className} w-auto object-contain ${invert ? "rounded-md bg-white px-1.5 py-1" : ""}`}
    />
  </div>
);

export { HitechLogo };
export default memo(HitechLogo);