import { rgb } from "../lib/theme";

/** Slow-drifting blurred color blobs (one per agent colour) used as decorative background. */
export default function AmbientGlow({ className = "" }) {
  const blob = (token) => ({ background: rgb(token), opacity: "var(--glow-opacity)" });
  return (
    <div aria-hidden="true" className={`pointer-events-none absolute inset-0 z-0 overflow-hidden ${className}`}>
      <span className="absolute -left-24 top-0 h-80 w-80 animate-drift-a rounded-full blur-3xl" style={blob("data")} />
      <span className="absolute -right-24 top-10 h-96 w-96 animate-drift-b rounded-full blur-3xl" style={blob("strategy")} />
      <span className="absolute -bottom-24 left-1/3 h-72 w-72 animate-drift-c rounded-full blur-3xl" style={blob("training")} />
    </div>
  );
}
