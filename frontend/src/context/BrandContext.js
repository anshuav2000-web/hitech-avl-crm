import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

const BrandContext = createContext(null);

/**
 * The single canonical source of brands and product categories for the whole app.
 *
 * Every dropdown, filter, search facet and brand-scoped picker reads from here, so
 * there is exactly one place the brand list comes from: `GET /api/brands`. No
 * component keeps its own copy, so adding, renaming or archiving a brand in the
 * catalogue updates every screen at once and no screen can drift out of step with
 * another.
 *
 * On failure the provider resolves to an empty list rather than throwing: a
 * catalogue outage should leave the rest of the CRM usable, and every consumer
 * already renders safely with no brands.
 */
export function BrandProvider({ children }) {
  const [brands, setBrands] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [b, c] = await Promise.all([
        api.get("/brands"),
        api.get("/categories").catch(() => ({ data: [] })),
      ]);
      setBrands(Array.isArray(b.data) ? b.data : []);
      setCategories(Array.isArray(c.data) ? c.data : []);
    } catch (e) {
      setError(e);
      setBrands([]);
      setCategories([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(() => {
    const byName = Object.fromEntries(brands.map((b) => [b.name, b]));
    // Brand categories present in the data, rather than a list maintained by hand
    // in a component that would silently go stale.
    const brandCategories = ["All Categories", ...new Set(
      brands.map((b) => b.brand_category).filter(Boolean)
    )];

    return {
      loading,
      error,
      refresh,
      brands,
      categories,
      brandCategories,
      brandByName: byName,
      /** Brand names, for callers that only need the option list. */
      brandNames: brands.map((b) => b.name),
      /** Brands the signed-in rep is not permitted to quote, excluded. */
      unlockedBrands: brands.filter((b) => !b.locked),
      /** Products are not part of this provider: they are large and page-specific. */
    };
  }, [brands, categories, loading, error, refresh]);

  return <BrandContext.Provider value={value}>{children}</BrandContext.Provider>;
}

export function useBrands() {
  const ctx = useContext(BrandContext);
  if (!ctx) throw new Error("useBrands must be used inside <BrandProvider>");
  return ctx;
}
