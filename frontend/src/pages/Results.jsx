import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Download, Plus, Printer, Star } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { getWorkflowResults } from "../api/projects";
import { getErrorMessage, getErrorStatus } from "../api/client";
import StatCard from "../components/StatCard";
import ErrorState from "../components/ErrorState";
import { Skeleton } from "../components/Skeleton";
import { formatNumber, formatScore } from "../lib/format";
import { rgb } from "../lib/theme";
import { useChartColors, useTheme } from "../context/ThemeContext";
import CountUp from "../components/CountUp";
import Reveal from "../components/Reveal";
import DataReport from "../components/DataReport";
import ModelCard from "../components/ModelCard";
import { useState } from "react";

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "—");

function exportJson(results) {
  const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${results.project_name.replace(/\W+/g, "_").toLowerCase()}_results.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Results() {
  const { projectId } = useParams();
  const chart = useChartColors();
  const { theme, setTheme } = useTheme();
  const [narrow] = useState(() => typeof window !== "undefined" && window.innerWidth < 640);
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["results", projectId],
    queryFn: () => getWorkflowResults(projectId),
    retry: (count, err) => ![404, 409].includes(getErrorStatus(err)) && count < 2,
  });

  const Back = (
    <Link to="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-ink print:hidden">
      <ArrowLeft size={14} /> Projects
    </Link>
  );

  if (isError) {
    const status = getErrorStatus(error);
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8 md:py-10">
        {Back}
        <div className="mt-8">
          <ErrorState
            title={status === 409 ? "Results aren't ready yet" : status === 404 ? "Project not found" : "Couldn't load results"}
            message={getErrorMessage(error)}
          >
            {status === 409 && <Link to={`/projects/${projectId}/workflow`} className="btn-primary">Watch the workflow</Link>}
            {status !== 409 && status !== 404 && (
              <button className="btn-primary" onClick={() => refetch()} disabled={isFetching}>
                {isFetching ? "Retrying…" : "Try again"}
              </button>
            )}
            <Link to="/projects" className="btn-ghost">Back to projects</Link>
          </ErrorState>
        </div>
      </main>
    );
  }

  if (isLoading || !data) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8 md:py-10" aria-busy="true">
        {Back}
        <Skeleton className="mt-6 h-8 w-64" />
        <div className="mt-6 flex gap-4"><Skeleton className="h-24 flex-1" /><Skeleton className="h-24 flex-1" /><Skeleton className="h-24 flex-1" /></div>
        <Skeleton className="mt-6 h-[300px]" />
      </main>
    );
  }

  const { dataset, strategy, models, final_model: best } = data;
  const sorted = [...models].sort((a, b) => b.score - a.score);
  const chartHeight = Math.max(180, models.length * 58 + 30);

  // Charts take their colours from JS, so switch to the light theme while printing.
  function downloadPdf() {
    const original = theme;
    const previousTitle = document.title;
    document.title = `${data.project_name} - AgentFlow report`;   // becomes the PDF file name
    window.addEventListener("afterprint", () => {
      document.title = previousTitle;
      if (original !== "light") setTheme(original);
    }, { once: true });
    if (original !== "light") setTheme("light");
    setTimeout(() => window.print(), 400);
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8 md:py-10">
      {Back}

      <div className="mt-5 flex flex-wrap items-start justify-between gap-4 animate-fade-in">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 font-mono text-[11px] text-data">
            <Check size={13} /> AGENTFLOW COMPLETE
          </div>
          <h1 className="mt-2 font-display text-2xl font-semibold">{data.project_name}</h1>
          <p className="mt-1 text-sm text-muted">{data.problem_statement}</p>
          <p className="mt-2 font-mono text-[11px] text-dim">
            target: <span className="text-muted">{data.target_column}</span> · dataset: <span className="text-muted">{dataset.filename}</span>
          </p>
          <p className="mt-1 hidden font-mono text-[11px] text-dim print:block">
            Report generated {new Date().toLocaleString()}
          </p>
        </div>
        <button onClick={downloadPdf} className="btn-primary print:hidden">
          <Printer size={15} /> Download report (PDF)
        </button>
      </div>

      <div className="stagger mt-7 flex flex-col gap-4 sm:flex-row">
        <StatCard label="PROBLEM TYPE" value={cap(strategy.problem_type)} />
        <StatCard label="FINAL MODEL" value={best.name} color={rgb("brand")} />
        <StatCard label={(best.metric || "SCORE").toUpperCase()} value={<CountUp value={best.score} decimals={2} />} color={rgb("data")} />
      </div>

      <Reveal><section className="card mt-6 p-6" aria-labelledby="cmp-h">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="cmp-h" className="font-display text-[15px] font-medium">Model comparison</h2>
          <span className="font-mono text-[10.5px] text-dim">{best.metric}</span>
        </div>
        <div style={{ height: chartHeight }} role="img" aria-label={`Bar chart comparing ${models.length} models by ${best.metric}`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={models} layout="vertical" margin={{ top: 0, right: narrow ? 34 : 40, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} horizontal={false} />
              <XAxis type="number" domain={[Math.min(0, ...models.map((m) => m.score)), 1]} tick={{ fill: chart.tick, fontSize: 10.5 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" width={narrow ? 104 : 170}
                tickFormatter={(v) => (v.length > (narrow ? 15 : 26) ? v.slice(0, narrow ? 14 : 25) + "…" : v)}
                tick={{ fill: chart.label, fontSize: 11.5 }} axisLine={false} tickLine={false} />
              <Tooltip
                cursor={{ fill: chart.cursor }}
                formatter={(v) => [formatScore(v), best.metric]}
                contentStyle={{ background: chart.tooltipBg, border: `1px solid ${chart.tooltipBorder}`, borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: chart.ink }} itemStyle={{ color: chart.label }}
              />
              <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={22} animationDuration={1100} animationEasing="ease-out">
                {models.map((m) => <Cell key={m.name} fill={m.name === best.name ? chart.brand : chart.idleBar} />)}
                <LabelList dataKey="score" position="right" formatter={formatScore} fill={chart.label} fontSize={11} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <table className="mt-5 w-full border-collapse text-sm">
          <caption className="sr-only">Models ranked by {best.metric}</caption>
          <thead>
            <tr className="border-b border-line text-left font-mono text-[10.5px] uppercase text-dim">
              <th className="py-2 font-normal">#</th><th className="py-2 font-normal">Model</th>
              <th className="py-2 text-right font-normal">{best.metric}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((m, i) => (
              <tr key={m.name} className="border-b border-line/60 last:border-0">
                <td className="py-2.5 font-mono text-xs text-dim">{i + 1}</td>
                <td className="py-2.5">
                  {m.name}
                  {m.name === best.name && <Star size={12} className="ml-2 inline fill-training text-training" aria-label="Selected model" />}
                </td>
                <td className="py-2.5 text-right font-mono">{formatScore(m.score)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section></Reveal>

      <Reveal className="mt-6"><div className="grid gap-6 md:grid-cols-2">
        <section className="card p-6" aria-labelledby="ds-h">
          <h2 id="ds-h" className="mb-4 font-display text-[15px] font-medium">Dataset summary</h2>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-4 font-mono text-xs">
            {[
              ["ROWS", dataset.rows], ["COLUMNS", dataset.columns],
              ["MISSING", dataset.missing_values], ["DUPLICATES", dataset.duplicates],
              ["NUMERICAL", dataset.numerical_features], ["CATEGORICAL", dataset.categorical_features],
            ].map(([k, v]) => (
              <div key={k}><dt className="text-dim">{k}</dt><dd className="mt-1 text-sm text-ink"><CountUp value={v} /></dd></div>
            ))}
          </dl>
        </section>

        <section className="card p-6" aria-labelledby="pp-h">
          <h2 id="pp-h" className="mb-4 font-display text-[15px] font-medium">Preprocessing performed</h2>
          {dataset.preprocessing?.length ? (
            <ul className="flex flex-col gap-2.5">
              {dataset.preprocessing.map((s) => (
                <li key={s} className="flex items-center gap-2.5 text-sm text-muted">
                  <Check size={14} className="shrink-0 text-data" /> {s}
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-dim">No preprocessing steps were reported.</p>}
        </section>
      </div></Reveal>
      {data.model_available && (
        <Reveal><ModelCard projectId={projectId} projectName={data.project_name} /></Reveal>
      )}      
      <Reveal><DataReport projectId={projectId} /></Reveal>
      <Reveal><div className="mt-8 flex flex-wrap gap-3 print:hidden">
        <Link to="/projects" className="btn-ghost"><ArrowLeft size={14} /> All projects</Link>
        <button onClick={() => exportJson(data)} className="btn-ghost"><Download size={14} /> Export JSON</button>
        <Link to="/projects/new" className="btn-primary ml-auto"><Plus size={15} /> New project</Link>
      </div></Reveal>
    </main>
  );
}
