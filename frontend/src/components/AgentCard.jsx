import { CheckCircle2, Loader2, AlertTriangle } from "lucide-react";
import { summarizeAgentOutput } from "../lib/format";
import { DONE_TOKEN, ERROR_TOKEN } from "../lib/constants";
import { rgb } from "../lib/theme";

const STATUS_LABEL = { waiting: "WAITING", running: "RUNNING", done: "DONE", error: "FAILED" };

export default function AgentCard({ meta, agent }) {
  const status = agent?.status || "waiting";
  const Icon = meta.icon;
  const lines = status === "done" ? summarizeAgentOutput(meta.key, agent?.output) : [];

  const token = status === "done" ? DONE_TOKEN : status === "error" ? ERROR_TOKEN : meta.token;
  const idle = status === "waiting";

  return (
    <article
      className={`card relative overflow-hidden p-5 transition-all duration-500 ${idle ? "opacity-70" : ""}`}
      style={
        status === "running"
          ? { borderColor: rgb(meta.token, 0.4), boxShadow: `0 0 0 1px ${rgb(meta.token, 0.12)}, 0 10px 30px -14px ${rgb(meta.token, 0.45)}` }
          : status === "error"
          ? { borderColor: rgb(ERROR_TOKEN, 0.45) }
          : undefined
      }
      aria-label={`${meta.label}: ${STATUS_LABEL[status]}`}
    >
      <div className="flex items-center gap-3">
        <span
          key={status}
          className={`flex h-[34px] w-[34px] items-center justify-center rounded-lg border transition-colors duration-500 ${
            status === "done" || status === "error" ? "animate-pop" : ""
          }`}
          style={{
            color: idle ? rgb("dim") : rgb(token),
            borderColor: idle ? rgb("line") : rgb(token, 0.27),
            background: idle ? rgb("panel2") : rgb(token, 0.08),
          }}
        >
          {status === "running" ? <Loader2 size={16} className="animate-spin" />
            : status === "done" ? <CheckCircle2 size={16} />
            : status === "error" ? <AlertTriangle size={16} />
            : <Icon size={16} />}
        </span>
        <span className={`font-mono text-xs font-medium ${idle ? "text-dim" : "text-ink"}`}>{meta.tag}</span>
        <span className="ml-auto font-mono text-[10px]" style={{ color: idle ? rgb("dim") : rgb(token) }}>
          {STATUS_LABEL[status]}
        </span>
      </div>

      {status === "running" && (
        <p className="mt-3 pl-[46px] text-sm text-muted">{agent?.message || meta.running}</p>
      )}
      {status === "error" && (
        <p className="mt-3 pl-[46px] text-sm" style={{ color: rgb(ERROR_TOKEN) }}>{agent?.message || "This agent failed."}</p>
      )}
      {lines.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1 pl-[46px]">
          {lines.map((l, i) => (
            <li key={i} className="reveal font-mono text-xs text-muted" style={{ "--i": i + 1 }}>· {l}</li>
          ))}
        </ul>
      )}

      {/* indeterminate activity bar while the agent is working */}
      {status === "running" && (
        <span className="absolute inset-x-0 bottom-0 h-[2px] overflow-hidden" aria-hidden="true">
          <span className="absolute h-full w-1/3 animate-sweep" style={{ background: `linear-gradient(90deg, transparent, ${rgb(meta.token)}, transparent)` }} />
        </span>
      )}
    </article>
  );
}
