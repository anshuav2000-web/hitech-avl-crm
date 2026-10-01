import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

/**
 * Load / save / reset the per-user dashboard layout.
 *
 * Saves are optimistic and debounced so dragging a widget does not fire a request
 * per pixel. A failed save reverts to the last server-confirmed layout and
 * surfaces an error rather than leaving the UI lying about what was stored.
 */
export function useDashboardLayout() {
  const [layout, setLayout] = useState([]);
  const [registry, setRegistry] = useState({ widgets: [], default_layout: [] });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const timer = useRef(null);
  const confirmed = useRef([]);

  const load = useCallback(async () => {
    try {
      const [layoutRes, widgetRes] = await Promise.all([
        api.get("/dashboard/layout"),
        api.get("/dashboard/widgets"),
      ]);
      confirmed.current = layoutRes.data.layout || [];
      setLayout(confirmed.current);
      setRegistry(widgetRes.data);
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const persist = useCallback(async (next) => {
    setSaving(true);
    try {
      const { data } = await api.put("/dashboard/layout", { layout: next });
      confirmed.current = data.layout || [];
      setError(null);
    } catch (e) {
      // Roll back to whatever the server last confirmed.
      setLayout(confirmed.current);
      setError(e);
    } finally {
      setSaving(false);
    }
  }, []);

  /** Replace the layout; schedules a debounced save. */
  const update = useCallback(
    (next) => {
      setLayout(next);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => persist(next), 600);
    },
    [persist]
  );

  const move = useCallback(
    (id, delta) => {
      setLayout((cur) => {
        const i = cur.findIndex((c) => c.id === id);
        const j = i + delta;
        if (i < 0 || j < 0 || j >= cur.length) return cur;
        const next = cur.slice();
        [next[i], next[j]] = [next[j], next[i]];
        update(next);
        return next;
      });
    },
    [update]
  );

  const resize = useCallback(
    (id, patch) => {
      setLayout((cur) => {
        const next = cur.map((c) => (c.id === id ? { ...c, ...patch } : c));
        update(next);
        return next;
      });
    },
    [update]
  );

  const hide = useCallback(
    (id) => {
      setLayout((cur) => {
        const next = cur.filter((c) => c.id !== id);
        update(next);
        return next;
      });
    },
    [update]
  );

  const add = useCallback(
    (id) => {
      setLayout((cur) => {
        if (cur.some((c) => c.id === id)) return cur;
        const meta = registry.widgets.find((w) => w.id === id);
        const next = [...cur, { id, w: meta?.min_w || 3, h: meta?.min_h || 2 }];
        update(next);
        return next;
      });
    },
    [registry, update]
  );

  const reset = useCallback(async () => {
    clearTimeout(timer.current);
    setSaving(true);
    try {
      const { data } = await api.post("/dashboard/layout/reset");
      confirmed.current = data.layout || [];
      setLayout(confirmed.current);
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setSaving(false);
    }
  }, []);

  const hidden = registry.widgets.filter((w) => !layout.some((c) => c.id === w.id));

  return { layout, registry, loading, saving, error, move, resize, hide, add, reset, hidden, reload: load };
}
