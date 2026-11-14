export default function Field({
  id, label, icon: Icon, error, right, className = "", ...inputProps
}) {
  return (
    <div className={className}>
      {label && <label htmlFor={id} className="label-mono mb-2 block">{label}</label>}
      <div className="relative">
        {Icon && (
          <Icon size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-dim" />
        )}
        <input
          id={id}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-err` : undefined}
          className={`input ${Icon ? "pl-10" : ""} ${right ? "pr-11" : ""} ${error ? "input-error" : ""}`}
          {...inputProps}
        />
        {right && <div className="absolute right-3 top-1/2 -translate-y-1/2">{right}</div>}
      </div>
      {error && <p id={`${id}-err`} role="alert" className="mt-1.5 text-xs text-danger">{error}</p>}
    </div>
  );
}
