import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
  FALLBACK_LOST_KEY,
  FALLBACK_SOURCES,
  FALLBACK_STAGES,
  FALLBACK_WON_KEY,
  normaliseSources,
  normaliseStages,
} from "@/constants/leadStages";

const ConfigContext = createContext(null);

/**
 * Loads the admin-configurable CRM lists once and exposes them as the app-wide
 * source of truth.
 *
 * Every consumer falls back to the bundled constants so the UI still renders if
 * the request fails -- a config outage must not blank the dashboard or pipeline.
 */
export function ConfigProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/config");
      setConfig(data);
    } catch {
      // Keep the previous value (or the fallback) rather than tearing the UI down.
      setConfig(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(() => {
    const liveStages = normaliseStages(config?.lead_stages);
    const liveSources = normaliseSources(config?.lead_sources);
    const stages = liveStages || FALLBACK_STAGES;

    const won = stages.find((s) => s.isWon)?.key || FALLBACK_WON_KEY;
    const lost = stages.find((s) => s.isLost)?.key || FALLBACK_LOST_KEY;

    const byKey = Object.fromEntries(stages.map((s) => [s.key, s]));
    const labels = Object.fromEntries(stages.map((s) => [s.key, s.label]));

    return {
      loading,
      config,
      refresh,
      stages,
      sources: liveSources || FALLBACK_SOURCES,
      stageKeys: stages.map((s) => s.key),
      stageByKey: byKey,
      stageLabels: labels,
      wonKey: won,
      lostKey: lost,
      /** Stage ids that still count as "open" for pipeline/assignment maths. */
      openStageKeys: stages.filter((s) => s.isOpen !== false && s.key !== won && s.key !== lost).map((s) => s.key),
    };
  }, [config, loading, refresh]);

  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export function useConfig() {
  const ctx = useContext(ConfigContext);
  if (!ctx) throw new Error("useConfig must be used inside <ConfigProvider>");
  return ctx;
}
