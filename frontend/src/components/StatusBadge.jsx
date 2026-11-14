import { rgb } from "../lib/theme";

const MAP = {
  queued: { label: "QUEUED", token: "muted" },
  running: { label: "RUNNING", token: "training" },
  completed: { label: "COMPLETED", token: "data" },
  failed: { label: "FAILED", token: "danger" },
};

export default function StatusBadge({ status }) {
  const s = MAP[status] || MAP.queued;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[10px] transition-colors duration-500"
      style={{ color: rgb(s.token), borderColor: rgb(s.token, 0.33), background: rgb(s.token, 0.08) }}
    >
      <span className="relative flex h-1.5 w-1.5">
        {status === "running" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-70" style={{ background: rgb(s.token) }} />
        )}
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ background: rgb(s.token) }} />
      </span>
      {s.label}
    </span>
  );
}
