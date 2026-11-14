// Lightweight client-side CSV helpers.
// NOTE: handles quoted fields and escaped quotes, but not newlines inside quoted cells.

export function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuotes) {
      if (c === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; }
        else inQuotes = false;
      } else cur += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { out.push(cur); cur = ""; }
    else cur += c;
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

const splitLines = (text) => text.split(/\r?\n/).filter((l) => l.trim() !== "");

/**
 * Reads only the first 64 KB of the file — enough for the header and a small preview,
 * so even very large CSVs don't freeze the browser.
 */
export async function readCsvPreview(file, previewRows = 5) {
  const text = await file.slice(0, 64 * 1024).text();
  const lines = splitLines(text);
  if (lines.length === 0) throw new Error("This file looks empty.");
  const columns = parseCsvLine(lines[0]).map((c) => c.replace(/^\uFEFF/, ""));
  if (columns.length < 2) {
    throw new Error("Couldn't find at least 2 comma-separated columns. Is this a CSV file?");
  }
  const rows = lines.slice(1, 1 + previewRows).map(parseCsvLine);
  return { columns, rows };
}

const isNumeric = (v) => v !== "" && Number.isFinite(Number(v));

/** Full analysis of CSV text. Used by the mock backend to produce real dataset stats. */
export function analyzeCsv(text, targetColumn) {
  const lines = splitLines(text);
  const columns = parseCsvLine(lines[0]).map((c) => c.replace(/^\uFEFF/, ""));
  const body = lines.slice(1);
  const rows = body.length;

  let missing = 0;
  const seen = new Set();
  let duplicates = 0;
  const sample = body.slice(0, 500).map(parseCsvLine);

  for (const line of body) {
    if (seen.has(line)) duplicates++;
    else seen.add(line);
  }
  for (const r of sample) for (const cell of r) if (cell === "") missing++;
  // scale the sampled missing count up to the whole file
  if (sample.length > 0 && rows > sample.length) missing = Math.round((missing / sample.length) * rows);

  let numerical = 0;
  let categorical = 0;
  columns.forEach((col, ci) => {
    if (col === targetColumn) return;
    const vals = sample.map((r) => r[ci] ?? "").filter((v) => v !== "");
    const numericShare = vals.length ? vals.filter(isNumeric).length / vals.length : 0;
    if (numericShare >= 0.9) numerical++;
    else categorical++;
  });

  const tIdx = columns.indexOf(targetColumn);
  const targetVals = tIdx >= 0 ? sample.map((r) => r[tIdx] ?? "").filter((v) => v !== "") : [];
  const targetUnique = new Set(targetVals).size;
  const targetNumeric = targetVals.length > 0 && targetVals.every(isNumeric);

  return {
    rows,
    columns: columns.length,
    missing_values: missing,
    duplicates,
    numerical_features: numerical,
    categorical_features: categorical,
    targetUnique,
    targetNumeric,
  };
}
