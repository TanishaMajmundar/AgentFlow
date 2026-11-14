import { Upload, CheckCircle2, Check, Loader2, AlertTriangle } from "lucide-react";
import { AGENTS, BRAND_TOKEN, DONE_TOKEN, ERROR_TOKEN } from "../lib/constants";
import { rgb } from "../lib/theme";

const NODES = [
  { key: "input", label: "Input", token: "muted", icon: Upload },
  ...AGENTS,
  { key: "result", label: "Result", token: BRAND_TOKEN, icon: CheckCircle2 },
];

/**
 * Horizontal pipeline: Input → Data → Strategy → Training → Result.
 *  - Without `states`: ambient/decorative mode with the travelling signal dot (marketing).
 *  - With `states` ({ input, data, strategy, training, result } = idle|running|done|error):
 *    live mode that fills the connector as the workflow advances.
 */
export default function PipelineFlow({ states, compact = false }) {
  const ambient = !states;
  const size = compact ? 30 : 38;
  const iconSize = compact ? 14 : 17;

  let lastReached = -1;
  if (!ambient) {
    for (let i = 0; i < NODES.length; i++) {
      const s = states[NODES[i].key];
      if (s === "done" || s === "running" || s === "error") lastReached = i;
      else break;
    }
  }
  const fillPct = ambient ? 0 : Math.max(0, (lastReached / (NODES.length - 1)) * 100);

  return (
    <div className={`relative w-full ${compact ? "py-2" : "py-[18px]"}`} role="img"
      aria-label={ambient ? "AgentFlow pipeline: input, data agent, strategy agent, training agent, result" : "Workflow progress"}>
      <div className="relative flex items-start justify-between">
        {/* connector track */}
        <div className="absolute left-[30px] right-[30px] h-px bg-line" style={{ top: size / 2 }}>
          {!ambient && (
            <div
              className="absolute left-0 top-0 h-px transition-all duration-1000 ease-out"
              style={{ width: `${fillPct}%`, background: rgb(DONE_TOKEN), boxShadow: `0 0 8px ${rgb(DONE_TOKEN, 0.6)}` }}
            />
          )}
          {ambient && (
            <span
              className="absolute -mt-1 h-2 w-2 animate-travel rounded-full"
              style={{ top: 0, background: rgb("brand"), boxShadow: `0 0 14px 3px ${rgb("brand", 0.8)}` }}
            />
          )}
        </div>

        {NODES.map((n) => {
          const state = ambient ? "ambient" : states[n.key] || "idle";
          const Icon = n.icon;
          let token = n.token;
          if (state === "idle") token = "idle";
          if (state === "done") token = DONE_TOKEN;
          if (state === "error") token = ERROR_TOKEN;

          let glyph = <Icon size={iconSize} />;
          if (state === "running") glyph = <Loader2 size={iconSize} className="animate-spin" />;
          if (state === "done" && n.key !== "result" && n.key !== "input") glyph = <Check size={iconSize} />;
          if (state === "error") glyph = <AlertTriangle size={iconSize} />;

          const animated = state === "running" || state === "ambient";
          return (
            <div key={n.key} className="relative z-10 flex w-[60px] flex-col items-center">
              <div
                className={`flex items-center justify-center rounded-full bg-panel transition-colors duration-500 ${
                  animated ? "animate-pulse-ring" : state === "done" || state === "error" ? "animate-pop" : ""
                }`}
                style={{ width: size, height: size, border: `1.5px solid ${rgb(token)}`, color: rgb(token) }}
              >
                {glyph}
              </div>
              {!compact && (
                <span className="mt-2 text-center font-mono text-[10px] leading-tight text-muted">{n.label}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Vertical decorative version used on the login / signup side panel. */
export function PipelineVertical() {
  return (
    <div className="relative flex h-full min-h-[420px] items-center justify-center" aria-hidden="true">
      <div className="relative flex h-full flex-col items-start justify-between py-2">
        <div className="absolute bottom-0 left-[19px] top-0 w-px bg-line">
          <span
            className="absolute -ml-[3.5px] h-2 w-2 animate-travel-v rounded-full"
            style={{ left: 0, background: rgb("brand"), boxShadow: `0 0 14px 3px ${rgb("brand", 0.8)}` }}
          />
        </div>
        {NODES.map((n, i) => {
          const Icon = n.icon;
          return (
            <div key={n.key} className="reveal relative z-10 my-6 flex items-center gap-3" style={{ "--i": i + 2 }}>
              <div
                className="flex h-10 w-10 animate-pulse-ring items-center justify-center rounded-full bg-deep"
                style={{ border: `1.5px solid ${rgb(n.token)}`, color: rgb(n.token) }}
              >
                <Icon size={18} />
              </div>
              <span className="font-mono text-[11px] text-muted">{n.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
