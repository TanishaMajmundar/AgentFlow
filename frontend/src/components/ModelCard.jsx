import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, ShieldAlert } from "lucide-react";
import { downloadModel, getModelInfo } from "../api/projects";

const SNIPPET = `import sys, joblib, pandas as pd
sys.path.insert(0, "<path to AgentFlow>/data_agent")   # lets Python load AgentFlow's preprocessing
model = joblib.load("best_model.pkl")                  # only load files you trust
rows = pd.read_csv("new_rows.csv")                     # raw columns, same as your original dataset
print(model.predict(rows))`;

export default function ModelCard({ projectId, projectName }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { data: info } = useQuery({
    queryKey: ["model-info", projectId],
    queryFn: () => getModelInfo(projectId),
    retry: false,
  });
  const safe = (projectName || "model").replace(/\W+/g, "_").toLowerCase();

  async function onDownload() {
    setBusy(true); setError("");
    try {
      await downloadModel(projectId, `${safe}_best_model.pkl`);
    } catch (e) {
      setError(e?.message || "Download failed.");
    } finally {
      setBusy(false);
    }
  }

  const v = info?.library_versions;
  return (
    <section className="card mt-6 p-6 print:hidden" aria-labelledby="mdl-h">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="mdl-h" className="font-display text-[15px] font-medium">Download trained model</h2>
          <p className="mt-1 max-w-xl text-sm text-muted">
            One file that takes raw rows in the shape of your dataset, applies the same preprocessing used in training,
            and returns predictions.
          </p>
        </div>
        <button onClick={onDownload} disabled={busy} className="btn-primary">
          <Download size={15} /> {busy ? "Preparing…" : "Download best_model.pkl"}
        </button>
      </div>
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}

      {info && (
        <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 font-mono text-xs md:grid-cols-4">
          <div><dt className="text-dim">MODEL</dt><dd className="mt-1 text-sm text-ink">{info.model_name}</dd></div>
          <div><dt className="text-dim">TARGET</dt><dd className="mt-1 text-sm text-ink">{info.target_column}</dd></div>
          <div><dt className="text-dim">INPUT COLUMNS</dt><dd className="mt-1 text-sm text-ink">{info.required_input_columns?.length ?? 0}</dd></div>
          <div><dt className="text-dim">SCIKIT-LEARN</dt><dd className="mt-1 text-sm text-ink">{v?.["scikit-learn"]}</dd></div>
        </dl>
      )}

      {info?.required_input_columns?.length > 0 && (
        <details className="mt-4 text-xs text-muted">
          <summary className="cursor-pointer">Columns the model expects</summary>
          <p className="mt-2 font-mono leading-relaxed">{info.required_input_columns.join(", ")}</p>
        </details>
      )}

      <details className="mt-3 text-xs text-muted">
        <summary className="cursor-pointer">How to use it</summary>
        <pre className="mt-2 overflow-x-auto rounded-lg border border-line bg-panel2 p-3 font-mono text-[11px] leading-relaxed text-ink">{SNIPPET}</pre>
      </details>

      <p className="mt-4 flex items-start gap-2 text-xs text-muted">
        <ShieldAlert size={14} className="mt-0.5 shrink-0 text-training" />
        <span>
          Pickle files can run code when loaded: only load models you created or trust. Use the same scikit-learn
          version{v?.["scikit-learn"] ? ` (${v["scikit-learn"]})` : ""} and keep AgentFlow's data_agent folder importable.
        </span>
      </p>
    </section>
  );
}