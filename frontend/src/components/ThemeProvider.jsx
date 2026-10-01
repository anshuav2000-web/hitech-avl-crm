import { createContext, useContext } from "react";

const ThemeCtx = createContext({
  theme: "light",
  setTheme: () => {},
  resolvedTheme: "light",
});

export function ThemeProvider({ children }) {
  // Always lock theme to clean white/light mode
  const theme = "light";
  const resolvedTheme = "light";

  return (
    <ThemeCtx.Provider value={{ theme, setTheme: () => {}, resolvedTheme }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export const useTheme = () => useContext(ThemeCtx);
