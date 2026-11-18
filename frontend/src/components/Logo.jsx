import { Link } from "react-router-dom";

/** Two overlapping rings = agents collaborating. Wordmark is set in the display serif. */
export function LogoMark({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <circle cx="10.5" cy="14" r="8" stroke="rgb(var(--c-brand))" strokeWidth="1.6" />
      <circle cx="17.5" cy="14" r="8" stroke="rgb(var(--c-ink))" strokeWidth="1.6" />
    </svg>
  );
}

export default function Logo({ size = 20, to = "/" }) {
  return (
    <Link to={to} className="group inline-flex items-center gap-2.5 rounded-md" aria-label="AgentFlow home">
      <span>
        <LogoMark size={size + 6} />
      </span>
      <span className="font-display tracking-tight" style={{ fontSize: size, fontWeight: 480 }}>
        Agent<span className="italic text-brand">flow</span>
      </span>
    </Link>
  );
}
