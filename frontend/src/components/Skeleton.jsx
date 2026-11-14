export function Skeleton({ className = "" }) {
  return <div className={`skeleton rounded-lg ${className}`} aria-hidden="true" />;
}

export function PageSpinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-24 text-sm text-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line2 border-t-brand" />
      {label}
    </div>
  );
}
