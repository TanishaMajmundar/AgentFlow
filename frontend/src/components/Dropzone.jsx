import { useRef, useState } from "react";
import { FileText, Upload, X } from "lucide-react";
import { formatBytes } from "../lib/format";

export default function Dropzone({ file, onFile, onClear, error, disabled }) {
  const inputRef = useRef(null);
  const [over, setOver] = useState(false);

  const pick = (f) => { if (f) onFile(f); };

  return (
    <div>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload CSV dataset"
        aria-disabled={disabled}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => { if (!disabled && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); inputRef.current?.click(); } }}
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); if (!disabled) pick(e.dataTransfer.files?.[0]); }}
        className={`flex cursor-pointer flex-col transition-all duration-200 items-center justify-center gap-2 rounded-lg border-[1.5px] border-dashed px-4 py-7 text-center transition
          ${over ? "scale-[1.015] border-brand bg-brand/5 shadow-lg" : error ? "border-danger/60 bg-panel2" : "border-dash bg-panel2 hover:border-brand"}
          ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
      >
        {file ? (
          <>
            <FileText size={22} className="animate-pop text-data" />
            <span className="font-mono text-[12.5px] text-ink">{file.name}</span>
            <span className="text-xs text-dim">{formatBytes(file.size)} · click to replace</span>
          </>
        ) : (
          <>
            <Upload size={22} className={`text-dim ${over ? "-translate-y-1 text-brand" : "animate-float"}`} />
            <span className="text-sm text-muted">Drop a CSV here, or click to browse</span>
            <span className="text-xs text-dim">Comma-separated, first row = column names</span>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }}
        />
      </div>
      {file && !disabled && (
        <button type="button" onClick={onClear} className="mt-2 inline-flex items-center gap-1 text-xs text-dim transition hover:text-ink">
          <X size={12} /> Remove file
        </button>
      )}
      {error && <p role="alert" className="mt-1.5 text-xs text-danger">{error}</p>}
    </div>
  );
}
