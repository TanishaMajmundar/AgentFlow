import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, ArrowRight, ChevronDown, Sparkles } from "lucide-react";
import Dropzone from "../components/Dropzone";
import {
  analyzeProject, createProject, setProjectTarget, startWorkflow, uploadDataset,
} from "../api/projects";
import { getErrorMessage } from "../api/client";
import { readCsvPreview } from "../lib/csv";
import { MAX_UPLOAD_MB } from "../lib/constants";

const STAGE_LABEL = {
  creating: "Creating project…",
  uploading: "Uploading dataset…",
  analyzing: "Finding the best target column…",
  starting: "Starting AgentFlow…",
};

function ProgressBar({ stage, progress }) {
  const width =
    stage === "creating" ? "8%"
    : stage === "uploading" ? `${Math.max(progress, 8)}%`
    : stage === "analyzing" ? "92%"
    : "100%";
  return (
    <div className="mt-6" role="status" aria-live="polite">
      <div className="mb-2 flex justify-between font-mono text-[11px] text-muted">
        <span>{STAGE_LABEL[stage]}</span>
        {stage === "uploading" && <span>{progress}%</span>}
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-line">
        <div className="h-full bg-brand transition-all duration-300" style={{ width }} />
      </div>
    </div>
  );
}

export default function CreateProject() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [phase, setPhase] = useState("form"); // "form" | "confirm"
  const [name, setName] = useState("");
  const [problem, setProblem] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null); // { columns, rows }
  const [analysis, setAnalysis] = useState(null);
  const [target, setTarget] = useState("");
  const [errors, setErrors] = useState({});
  const [stage, setStage] = useState(null); // null | creating | uploading | analyzing | starting
  const [progress, setProgress] = useState(0);
  const [submitError, setSubmitError] = useState("");

  // If the project was created but a later step failed, reuse it on retry.
  const createdId = useRef(null);
  const busy = stage !== null;

  const clearError = (k) => setErrors((e) => ({ ...e, [k]: undefined }));
  const resetProject = () => { createdId.current = null; setAnalysis(null); };

  async function handleFile(f) {
    clearError("file");
    if (!/\.csv$/i.test(f.name)) return setErrors((e) => ({ ...e, file: "Only .csv files are supported." }));
    if (f.size > MAX_UPLOAD_MB * 1024 * 1024) return setErrors((e) => ({ ...e, file: `File is larger than ${MAX_UPLOAD_MB} MB.` }));
    try {
      const p = await readCsvPreview(f);
      setFile(f);
      setPreview(p);
      resetProject();
    } catch (err) {
      setFile(null); setPreview(null);
      setErrors((e) => ({ ...e, file: err.message }));
    }
  }

  function clearFile() { setFile(null); setPreview(null); resetProject(); }

  function validate() {
    const e = {};
    if (!name.trim()) e.name = "Give your project a name.";
    else if (name.length > 80) e.name = "Keep the name under 80 characters.";
    if (problem.trim().length < 10) e.problem = "Describe what you want to predict (at least 10 characters).";
    if (!file) e.file = "Upload a CSV dataset.";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  // Phase 1: create the project, upload the file, ask the backend for a target recommendation.
  async function onAnalyze(ev) {
    ev.preventDefault();
    if (!validate()) return;
    setSubmitError(""); setProgress(0);
    try {
      if (!createdId.current) {
        setStage("creating");
        const { project_id } = await createProject({
          name: name.trim(),
          problem_statement: problem.trim(),
          target_column: preview.columns[preview.columns.length - 1], // only used by the mock
        });
        createdId.current = project_id;
      }
      setStage("uploading");
      await uploadDataset(createdId.current, file, setProgress);
      setStage("analyzing");
      const result = await analyzeProject(createdId.current, preview.columns);
      setAnalysis(result);
      setTarget(result.recommended || "");
      setPhase("confirm");
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    } finally {
      setStage(null);
    }
  }

  // Phase 2: save the confirmed target, then start the agents.
  async function onConfirm() {
    if (!target) return setErrors((e) => ({ ...e, target: "Choose the column to predict." }));
    setSubmitError("");
    try {
      setStage("starting");
      await setProjectTarget(createdId.current, target);
      await startWorkflow(createdId.current);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${createdId.current}/workflow`);
    } catch (err) {
      setSubmitError(getErrorMessage(err));
      setStage(null);
    }
  }

  /* ------------------------------ confirm screen ------------------------------ */
  if (phase === "confirm" && analysis) {
    const rec = analysis.recommended;
    const conf = Math.round((analysis.confidence ?? 0) * 100);
    const columns = analysis.columns?.length
      ? analysis.columns
      : (preview?.columns ?? []).map((n) => ({ name: n, usable: true, note: "" }));
    const showWarnings = Boolean(analysis.validation?.warnings?.length) && target === rec;

    return (
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-8 md:py-12">
        <button type="button" disabled={busy} onClick={() => setPhase("form")}
          className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-ink">
          <ArrowLeft size={14} /> Back
        </button>

        <div className="card mt-4 animate-fade-in p-5 sm:p-8">
          <h1 className="font-display text-[22px] font-semibold">Confirm the target column</h1>
          <p className="mt-1.5 text-sm text-muted">
            AgentFlow read your problem statement and dataset and suggests what to predict. Change it if it's wrong.
          </p>

          <div className="mt-7 grid gap-8 lg:grid-cols-2">
            <div className="flex flex-col gap-4">
              <div className="rounded-xl border border-brand/30 bg-brand/5 p-5">
                <div className="label-mono flex items-center gap-2 !text-brand">
                  <Sparkles size={13} /> Recommended target
                </div>
                <div className="mt-2 break-words font-display text-xl font-semibold">{rec ?? "No clear recommendation"}</div>
                <div className="mt-1 flex flex-wrap gap-x-4 font-mono text-[11px] text-dim">
                  {analysis.problem_type && <span>{analysis.problem_type.replace(/_/g, " ")}</span>}
                  {rec && <span>confidence {conf}%</span>}
                </div>
                <p className="mt-3 text-sm leading-relaxed text-muted">{analysis.reason}</p>
                {analysis.llm && !analysis.llm.error && (
                  <p className="mt-2 font-mono text-[11px] text-dim">
                    Checked by {analysis.llm.model} ·{" "}
                    {analysis.llm.agrees_with_rules ? "agrees with rule-based scoring" : "differs from rule-based scoring"}
                  </p>
                )}
              </div>

              {analysis.ambiguous && (
                <div role="status" className="flex items-start gap-2 rounded-lg border border-training/40 bg-training/10 px-3.5 py-2.5 text-sm text-training">
                  <AlertTriangle size={15} className="mt-0.5 shrink-0" />
                  <span>AgentFlow isn't fully sure about this one. Please check the column on the right.</span>
                </div>
              )}

              {showWarnings && (
                <ul className="flex flex-col gap-1.5">
                  {analysis.validation.warnings.map((w, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted">
                      <AlertTriangle size={13} className="mt-0.5 shrink-0 text-training" /> {w}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <label htmlFor="target" className="label-mono mb-2 block">Target column</label>
              <div className="relative">
                <select id="target" value={target} disabled={busy}
                  onChange={(e) => { setTarget(e.target.value); clearError("target"); }}
                  className={`input appearance-none pr-10 ${errors.target ? "input-error" : ""}`}>
                  <option value="">Select a column…</option>
                  {columns.map((c) => (
                    <option key={c.name} value={c.name} disabled={!c.usable}>
                      {c.name}{c.name === rec ? "  ★ recommended" : ""}{!c.usable ? `  (${c.note})` : ""}
                    </option>
                  ))}
                </select>
                <ChevronDown size={15} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-dim" />
              </div>
              {errors.target && <p role="alert" className="mt-1.5 text-xs text-danger">{errors.target}</p>}

              {analysis.alternatives?.length > 0 && (
                <div className="mt-5">
                  <span className="label-mono mb-2 block">Other candidates</span>
                  <div className="flex flex-wrap gap-2">
                    {analysis.alternatives.map((a) => (
                      <button key={a.column} type="button" disabled={busy}
                        onClick={() => { setTarget(a.column); clearError("target"); }}
                        className={`rounded-full border px-3 py-1 font-mono text-[11px] transition ${
                          target === a.column
                            ? "border-brand bg-brand/10 text-brand"
                            : "border-line text-muted hover:border-line2 hover:text-ink"
                        }`}>
                        {a.column}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {submitError && (
            <p role="alert" className="mt-6 rounded-lg border border-danger/40 bg-danger/10 px-3.5 py-2.5 text-sm text-danger">
              {submitError}
            </p>
          )}

          {busy && <ProgressBar stage={stage} progress={progress} />}

          <div className="mt-8 flex justify-end">
            <button type="button" onClick={onConfirm} disabled={busy}
              className="btn-primary w-full !py-3 sm:w-auto sm:min-w-[300px]">
              {busy ? STAGE_LABEL[stage] : <>Confirm &amp; start AgentFlow <ArrowRight size={15} className="nudge" /></>}
            </button>
          </div>
        </div>
      </main>
    );
  }

  /* -------------------------------- form screen ------------------------------- */
  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-8 md:py-12">
      <Link to="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-ink">
        <ArrowLeft size={14} /> Projects
      </Link>

      <form onSubmit={onAnalyze} noValidate className="card mt-4 animate-fade-in p-5 sm:p-8">
        <h1 className="font-display text-[22px] font-semibold">Create new ML project</h1>
        <p className="mt-1.5 text-sm text-muted">
          Tell AgentFlow what you're trying to predict, and give it the data to work with.
        </p>

        <div className="stagger mt-7 grid gap-x-8 gap-y-5 lg:grid-cols-2">
          <div className="flex flex-col gap-5">
            <div>
              <label htmlFor="name" className="label-mono mb-2 block">Project name</label>
              <input id="name" className={`input ${errors.name ? "input-error" : ""}`} value={name} disabled={busy}
                onChange={(e) => { setName(e.target.value); clearError("name"); resetProject(); }}
                placeholder="e.g. Customer Churn Prediction" />
              {errors.name && <p role="alert" className="mt-1.5 text-xs text-danger">{errors.name}</p>}
            </div>

            <div>
              <label htmlFor="problem" className="label-mono mb-2 block">Problem statement</label>
              <textarea id="problem" rows={4} className={`input resize-none ${errors.problem ? "input-error" : ""}`} value={problem} disabled={busy}
                onChange={(e) => { setProblem(e.target.value); clearError("problem"); resetProject(); }}
                placeholder="Predict whether a customer will leave the company based on their account information and usage patterns." />
              {errors.problem && <p role="alert" className="mt-1.5 text-xs text-danger">{errors.problem}</p>}
            </div>
          </div>

          <div>
            <span className="label-mono mb-2 block">Dataset</span>
            <Dropzone file={file} onFile={handleFile} onClear={clearFile} error={errors.file} disabled={busy} />
          </div>

          {preview && (
            <div className="animate-fade-in lg:col-span-2">
              <div className="overflow-x-auto rounded-lg border border-line">
                <table className="w-full border-collapse font-mono text-[11px]">
                  <thead>
                    <tr className="bg-panel2">
                      {preview.columns.map((c) => (
                        <th key={c} scope="col" className="whitespace-nowrap px-3 py-2 text-left font-medium text-muted">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r, i) => (
                      <tr key={i} className="border-t border-line">
                        {preview.columns.map((c, ci) => (
                          <td key={ci} className="whitespace-nowrap px-3 py-1.5 text-dim">{r[ci]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-1.5 text-xs text-dim">{preview.columns.length} columns detected · showing first {preview.rows.length} rows</p>
            </div>
          )}
        </div>

        {submitError && (
          <p role="alert" className="mt-6 rounded-lg border border-danger/40 bg-danger/10 px-3.5 py-2.5 text-sm text-danger">
            {submitError}
          </p>
        )}

        {busy && <ProgressBar stage={stage} progress={progress} />}

        <div className="mt-8 flex justify-end">
          <button type="submit" disabled={busy} className="btn-primary w-full !py-3 sm:w-auto sm:min-w-[260px]">
            {busy ? STAGE_LABEL[stage] : <>Analyze dataset <ArrowRight size={15} className="nudge" /></>}
          </button>
        </div>
      </form>
    </main>
  );
}