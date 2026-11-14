import { useEffect, useState } from "react";

/** Animates a number from 0 to `value` (ease-out). Non-numeric values render as-is. */
export default function CountUp({ value, decimals = 0, duration = 1100 }) {
  const numeric = typeof value === "number" && Number.isFinite(value);
  const [n, setN] = useState(0);

  useEffect(() => {
    if (!numeric) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setN(value); return; }
    let raf;
    let start = null;
    const tick = (t) => {
      if (start === null) start = t;
      const p = Math.min(1, (t - start) / duration);
      setN(value * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration, numeric]);

  if (!numeric) return <>{value ?? "—"}</>;
  return <>{decimals ? n.toFixed(decimals) : Math.round(n).toLocaleString("en-US")}</>;
}
