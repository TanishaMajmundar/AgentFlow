import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { getDataReport } from "../api/projects";
import { formatNumber } from "../lib/format";

function Bar({ label, value, max = 100, tone = "bg-brand", text }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="flex justify-between font-mono text-[11px] text-muted">
        <span className="truncate pr-2">{label}</span>
        <span>{text ?? value}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-line">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const Title = ({ children }) => <h3 className="label-mono mb-3">{children}</h3>;

export default function DataReport({ projectId }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["data-report", projectId],
    queryFn: () => getDataReport(projectId),
    retry: false,
  });
  if (isLoading || isError || !data) return null;   // mock mode / older projects: just hide

  const { health, target, correlations, outliers, preprocessing: pp, leakage } = data;
  const classes = target.class_distribution ? Object.entries(target.class_distribution) : [];
  const classMax = Math.max(1, ...classes.map(([, n]) => n));

  return (
      <section className="card break-auto mt-6 p-6" aria-labelledby="dr-h">
      <div className="mb-5 flex items-center justify-between">
        <h2 id="dr-h" className="font-display text-[15px] font-medium">Data analysis report</h2>
        <span className="flex items-center gap-1.5 rounded-full border border-data/40 bg-data/10 px-2.5 py-0.5 font-mono text-[11px] text-data">
          <ShieldCheck size={12} /> HEALTH {health.grade} · {health.score}/100
        </span>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <div>
          <Title>Data quality</Title>
          <div className="flex flex-col gap-3">
            {Object.entries(health.components).map(([k, v]) => (
              <Bar key={k} label={k} value={Math.round(v)} tone="bg-data" />
            ))}
          </div>
          {health.remediations.length > 0 && (
            <ul className="mt-4 flex flex-col gap-1.5">
              {health.remediations.map((r, i) => (
                <li key={i} className="text-xs text-muted">· {r}</li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <Title>Target: {target.column}</Title>
          {classes.length > 0 ? (
            <div className="flex flex-col gap-3">
              {classes.map(([label, n]) => (
                <Bar key={label} label={label} value={n} max={classMax} tone="bg-brand" text={formatNumber(n)} />
              ))}
              <p className="font-mono text-[11px] text-dim">
                {target.is_imbalanced ? `Imbalanced (${target.imbalance_ratio}:1) — handled in training` : `Balanced (${target.imbalance_ratio}:1)`}
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted">
              Continuous target{target.skewness != null ? ` · skewness ${target.skewness}` : ""}.
            </p>
          )}
        </div>

        {correlations.length > 0 && (
          <div>
            <Title>Strongest relationships</Title>
            <div className="flex flex-col gap-3">
              {correlations.map((c, i) => (
                <Bar key={i} label={`${c.a} ↔ ${c.b}`} value={c.value} max={1} tone="bg-strategy" text={c.value.toFixed(2)} />
              ))}
            </div>
          </div>
        )}

        {outliers.length > 0 && (
          <div>
            <Title>Outlier share by column</Title>
            <div className="flex flex-col gap-3">
              {outliers.map((o) => (
                <Bar key={o.column} label={o.column} value={o.pct} max={Math.max(10, ...outliers.map((x) => x.pct))}
                  tone="bg-training" text={`${o.pct}%`} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 grid gap-8 border-t border-line pt-6 md:grid-cols-2">
        <div>
          <Title>Feature pipeline</Title>
          <dl className="grid grid-cols-3 gap-3 font-mono text-xs">
            <div><dt className="text-dim">BEFORE</dt><dd className="mt-1 text-sm text-ink">{pp.features_before}</dd></div>
            <div><dt className="text-dim">EXPANDED</dt><dd className="mt-1 text-sm text-ink">{pp.features_expanded}</dd></div>
            <div><dt className="text-dim">FINAL</dt><dd className="mt-1 text-sm text-ink">{pp.features_final}</dd></div>
          </dl>
          <p className="mt-3 text-xs text-muted">
            Scaling: {pp.scaling} · {pp.encoded_columns} categorical columns encoded
            {pp.engineered_features.length > 0 && ` · engineered: ${pp.engineered_features.join(", ")}`}
            {pp.smote_applied && ` · SMOTE added ${pp.smote_rows} training rows`}
          </p>
        </div>

        <div>
          <Title>Leakage protection</Title>
          <ul className="flex flex-col gap-1.5 text-xs text-muted">
            <li>· Split before fitting: {leakage.train_rows} train / {leakage.test_rows} test{leakage.stratified ? " (stratified)" : ""}</li>
            <li>· Preprocessing learned from training rows only</li>
            {leakage.leaky_removed.length > 0 && (
              <li className="flex items-start gap-1.5 text-training">
                <AlertTriangle size={12} className="mt-0.5 shrink-0" /> Removed target-like features: {leakage.leaky_removed.join(", ")}
              </li>
            )}
            {leakage.collinear_removed.length > 0 && <li>· Removed redundant features: {leakage.collinear_removed.join(", ")}</li>}
          </ul>
        </div>
      </div>
    </section>
  );
}