import { useState } from "react";
import { Outlet } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import AppSidebar from "@/components/layout/Sidebar";
import AppHeader from "@/components/layout/Header";
import { useTheme } from "@/components/ThemeProvider";
import { EventProductionBackground } from "@/components/EventProductionBackground";

export default function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { resolvedTheme } = useTheme();

  return (
    <div className="min-h-screen flex bg-background text-foreground relative selection:bg-sky-500/20 selection:text-sky-300 grain">
      <EventProductionBackground />

      <div className="hidden lg:block sticky top-0 h-screen z-20">
        <AppSidebar />
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="lg:hidden fixed inset-0 z-40 bg-black/70 backdrop-blur-lg"
            onClick={() => setMobileOpen(false)}
          >
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="w-[280px] h-full"
              onClick={(e) => e.stopPropagation()}
            >
              <AppSidebar onMobileClose={() => setMobileOpen(false)} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 flex flex-col min-h-screen overflow-hidden relative z-10">
        <AppHeader onToggleSidebar={() => setMobileOpen((s) => !s)} sidebarOpen={mobileOpen} />
        <motion.main
          key={resolvedTheme}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex-1 overflow-y-auto relative"
        >
          <div className="diagonal-accent">
            <div className="brand-bg min-h-full">
              <div className="max-w-[1600px] mx-auto px-4 lg:px-8">
                <Outlet />
              </div>
            </div>
          </div>
        </motion.main>
      </div>
    </div>
  );
}
