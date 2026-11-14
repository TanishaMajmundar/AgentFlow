export default function StatCard({ label, value, sub, color }) {
  return (
    <div className="card flex-1 p-5 transition duration-300 hover:-translate-y-0.5 hover:border-line2">
      <span className="font-mono text-[10.5px] uppercase text-dim">{label}</span>
      <div className="mt-1.5 font-display text-[22px] font-semibold leading-tight" style={color ? { color } : undefined}>
        {value}
      </div>
      {sub && <span className="text-xs text-muted">{sub}</span>}
    </div>
  );
}
