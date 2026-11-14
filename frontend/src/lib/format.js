export const formatNumber = (n) =>
  typeof n === "number" ? n.toLocaleString("en-US") : n ?? "—";

export const formatScore = (n) => (typeof n === "number" ? n.toFixed(2) : "—");

export function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return (
    d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
    " · " +
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  );
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * Turns an agent's structured `output` into short human-readable lines.
 * Defensive on purpose: the backend may omit fields while agents are still evolving.
 */
export function summarizeAgentOutput(key, output) {
  if (!output) return [];
  const lines = [];
  if (key === "data") {
    if (output.rows != null)
      lines.push(`${formatNumber(output.rows)} rows · ${formatNumber(output.columns)} columns`);
    if (output.missing_values != null)
      lines.push(
        `${formatNumber(output.missing_values)} missing values · ${formatNumber(output.duplicates ?? 0)} duplicate rows`
      );
    if (output.preprocessing?.length) lines.push(output.preprocessing.join(" · "));
  }
  if (key === "strategy") {
    if (output.problem_type) lines.push(`Problem type: ${output.problem_type}`);
    if (output.models?.length) lines.push(`Candidates: ${output.models.join(", ")}`);
    if (output.primary_metric) lines.push(`Primary metric: ${output.primary_metric}`);
  }
  if (key === "training") {
    (output.results ?? []).forEach((r) => lines.push(`${r.name} → ${formatScore(r.score)}`));
  }
  return lines;
}
