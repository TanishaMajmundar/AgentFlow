import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, ChevronDown } from "lucide-react";
import Dropzone from "../components/Dropzone";
import { createProject, startWorkflow, uploadDataset } from "../api/projects";
import { getErrorMessage } from "../api/client";
import { readCsvPreview } from "../lib/csv";
import { MAX_UPLOAD_MB } from "../lib/constants";

const STAGE_LABEL = {
  creating: "Creating project…",
  uploading: "Uploading dataset…",
  starting: "Starting AgentFlow…",
};

export default function CreateProject() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState("");
  const [problem, setProblem] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null); // { columns, rows }
  const [target, setTarget] = useState("");
  const [errors, setErrors] = useState({});
  const [stage, setStage] = useState(null); // null | creating | uploading | starting
  const [progress, setProgress] = useState(0);
  const [submitError, setSubmitError] = useState("");

  // If the project was created but a later step failed, reuse it on retry
  // instead of creating a duplicate.
  const createdId = useRef(null);
  const busy = stage !== null;

  const clearError = (k) => setErrors((e) => ({ ...e, [k]: undefined }));

  async function handleFile(f) {
    clearError("file");
    if (!/\.csv$/i.test(f.name)) return setErrors((e) => ({ ...e, file: "Only .csv files are supported." }));
    if (f.size > MAX_UPLOAD_MB * 1024 * 1024) return setErrors((e) => ({ ...e, file: `File is larger than ${MAX_UPLOAD_MB} MB.` }));
    try {
      const p = await readCsvPreview(f);
      setFile(f);
      setPreview(p);
      setTarget(p.columns[p.columns.length - 1]); // targets are most often the last column
      createdId.current = null;
      clearError("target");
    } catch (err) {
      setFile(null); setPreview(null); setTarget("");
      setErrors((e) => ({ ...e, file: err.message }));
    }
  }

  function clearFile() { setFile(null); setPreview(null); setTarget(""); createdId.current = null; }

  function validate() {
    const e = {};
    if (!name.trim()) e.name = "Give your project a name.";
    else if (name.length > 80) e.name = "Keep the name under 80 characters.";
    if (problem.trim().length < 10) e.problem = "Describe what you want to predict (at least 10 characters).";
    if (!file) e.file = "Upload a CSV dataset.";
    if (file && !target) e.target = "Choose the column to predict.";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function onSubmit(ev) {
    ev.preventDefault();
    if (!validate()) return;
    setSubmitError(""); setProgress(0);
    try {
      if (!createdId.current) {
        setStage("creating");
        const { project_id } = await createProject({
          name: name.trim(), problem_statement: problem.trim(), target_column: target,
        });
        createdId.current = project_id;
      }
      setStage("uploading");
      await uploadDataset(createdId.current, file, setProgress);
      setStage("starting");
      await startWorkflow(createdId.current);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${createdId.current}/workflow`);
    } catch (err) {
      setSubmitError(getErrorMessage(err));
      setStage(null);
    }
  }

  return (
    <main className="mx-auto max-w-[600px] px-6 py-10">
      <Link to="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-ink">
        <ArrowLeft size={14} /> Projects
      </Link>

      <form onSubmit={onSubmit} noValidate className="card mt-4 animate-fade-in rounded-2xl p-8">
        <h1 className="font-display text-[22px] font-semibold">Create new ML project</h1>
        <p className="mt-1.5 text-sm text-muted">
          Tell AgentFlow what you're trying to predict, and give it the data to work with.
        </p>

        <div className="stagger mt-7 flex flex-col gap-5">
          <div>
            <label htmlFor="name" className="label-mono mb-2 block">Project name</label>
            <input id="name" className={`input ${errors.name ? "input-error" : ""}`} value={name} disabled={busy}
              onChange={(e) => { setName(e.target.value); clearError("name"); createdId.current = null; }}
              placeholder="e.g. Heart Disease Prediction" />
            {errors.name && <p role="alert" className="mt-1.5 text-xs text-danger">{errors.name}</p>}
          </div>

          <div>
            <label htmlFor="problem" className="label-mono mb-2 block">Problem statement</label>
            <textarea id="problem" rows={3} className={`input resize-none ${errors.problem ? "input-error" : ""}`} value={problem} disabled={busy}
              onChange={(e) => { setProblem(e.target.value); clearError("problem"); createdId.current = null; }}
              placeholder="Predict whether a patient has heart disease based on medical attributes." />
            {errors.problem && <p role="alert" className="mt-1.5 text-xs text-danger">{errors.problem}</p>}
          </div>

          <div>
            <span className="label-mono mb-2 block">Dataset</span>
            <Dropzone file={file} onFile={handleFile} onClear={clearFile} error={errors.file} disabled={busy} />
          </div>

          {preview && (
            <div className="animate-fade-in">
              <label htmlFor="target" className="label-mono mb-2 block">Target column</label>
              <div className="relative">
                <select id="target" value={target} disabled={busy}
                  onChange={(e) => { setTarget(e.target.value); clearError("target"); createdId.current = null; }}
                  className={`input appearance-none pr-10 ${errors.target ? "input-error" : ""}`}>
                  <option value="">Select a column…</option>
                  {preview.columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <ChevronDown size={15} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-dim" />
              </div>
              {errors.target && <p role="alert" className="mt-1.5 text-xs text-danger">{errors.target}</p>}
              <p className="mt-1.5 text-xs text-dim">The column the model will learn to predict. Defaulted to the last column.</p>

              <div className="mt-4 overflow-x-auto rounded-lg border border-line">
                <table className="w-full border-collapse font-mono text-[11px]">
                  <thead>
                    <tr className="bg-panel2">
                      {preview.columns.map((c) => (
                        <th key={c} scope="col"
                          className={`whitespace-nowrap px-3 py-2 text-left font-medium ${c === target ? "text-brand" : "text-muted"}`}>
                          {c}{c === target && " ◎"}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r, i) => (
                      <tr key={i} className="border-t border-line">
                        {preview.columns.map((c, ci) => (
                          <td key={ci} className={`whitespace-nowrap px-3 py-1.5 ${c === target ? "text-ink" : "text-dim"}`}>{r[ci]}</td>
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

        {busy && (
          <div className="mt-6" role="status" aria-live="polite">
            <div className="mb-2 flex justify-between font-mono text-[11px] text-muted">
              <span>{STAGE_LABEL[stage]}</span>
              {stage === "uploading" && <span>{progress}%</span>}
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-line">
              <div className="h-full bg-brand transition-all duration-300"
                style={{ width: stage === "creating" ? "8%" : stage === "uploading" ? `${Math.max(progress, 8)}%` : "100%" }} />
            </div>
          </div>
        )}

        <button type="submit" disabled={busy} className="btn-primary mt-7 w-full !py-3">
          {busy ? STAGE_LABEL[stage] : <>Start AgentFlow <ArrowRight size={15} className="nudge" /></>}
        </button>
      </form>
    </main>
  );
}
