import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ConfigProvider } from "@/context/ConfigContext";
import { BrandProvider } from "@/context/BrandContext";
import "./index.css";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>
        {/* One canonical brand/category list for every screen. Mounted above the
            router so the login page and the public quotation view never have to
            refetch it separately. */}
        <BrandProvider>
          <ThemeProvider>
            <App />
          </ThemeProvider>
        </BrandProvider>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
