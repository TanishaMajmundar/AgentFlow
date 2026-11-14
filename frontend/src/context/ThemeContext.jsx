import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { flushSync } from "react-dom";

const KEY = "af_theme";
const ThemeContext = createContext(null);

// Real hex values for places that can't use CSS variables (Recharts SVG props).
const CHART = {
  dark: {
    brand: "#6C7CFF", grid: "#1B212B", tick: "#5B6472", label: "#8992A3",
    idleBar: "#2B3341", tooltipBg: "#171C25", tooltipBorder: "#232A35", ink: "#E9EDF4", cursor: "rgba(255,255,255,0.05)",
  },
  light: {
    brand: "#4F5BE8", grid: "#E6E9F1", tick: "#70798C", label: "#5A6478",
    idleBar: "#CBD2E0", tooltipBg: "#FFFFFF", tooltipBorder: "#DDE2EC", ink: "#11151F", cursor: "rgba(15,23,42,0.05)",
  },
};

const readTheme = () => (document.documentElement.dataset.theme === "light" ? "light" : "dark");

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "light" ? "#F6F7FB" : "#0A0D12");
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
