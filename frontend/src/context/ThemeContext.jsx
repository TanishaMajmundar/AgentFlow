import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { flushSync } from "react-dom";

const KEY = "af_theme";
const ThemeContext = createContext(null);

// Real hex values for places that can't use CSS variables (Recharts SVG props).
const CHART = {
  light: {
    brand: "#6B4226", grid: "#E5DCCB", tick: "#7A6A5A", label: "#685849",
    idleBar: "#D3C4AB", tooltipBg: "#FBF7EF", tooltipBorder: "#DED3C0", ink: "#2B1E16", cursor: "rgba(43,30,22,0.05)",
  },
  dark: {
    brand: "#D9A56E", grid: "#2E231B", tick: "#8A7968", label: "#B3A18D",
    idleBar: "#4A392D", tooltipBg: "#291F18", tooltipBorder: "#3E3026", ink: "#F1E8DA", cursor: "rgba(255,255,255,0.05)",
  },
};

const readTheme = () => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#17110D" : "#F5EFE4");
  try { localStorage.setItem(KEY, theme); } catch { /* storage unavailable — theme just won't persist */ }
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readTheme);

  const setTheme = useCallback((next, origin) => {
    const commit = () => { applyTheme(next); flushSync(() => setThemeState(next)); };
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (document.startViewTransition && !reduceMotion && origin) {
      // Circular reveal that grows out of the toggle button
      const { x, y } = origin;
      const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
      const transition = document.startViewTransition(commit);
      transition.ready
        .then(() =>
          document.documentElement.animate(
            { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
            { duration: 650, easing: "cubic-bezier(.4,0,.2,1)", pseudoElement: "::view-transition-new(root)" }
          )
        )
        .catch(() => {});
    } else {
      const root = document.documentElement;
      root.classList.add("theme-fade");
      commit();
      setTimeout(() => root.classList.remove("theme-fade"), 450);
    }
  }, []);

  const toggle = useCallback((origin) => setTheme(theme === "dark" ? "light" : "dark", origin), [theme, setTheme]);

  const value = useMemo(() => ({ theme, setTheme, toggle }), [theme, setTheme, toggle]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}

export const useChartColors = () => CHART[useTheme().theme];
