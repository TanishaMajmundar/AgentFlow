import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

export default function Logo({ size = 20, to = "/" }) {
  return (
    <Link to={to} className="group flex items-center gap-2 rounded-md" aria-label="AgentFlow home">
      <span
        className="flex items-center justify-center rounded-md border border-brand/30 bg-brand/10 transition duration-300 group-hover:border-brand/60 group-hover:bg-brand/20"
        style={{ width: size + 12, height: size + 12 }}
      >
        <Sparkles size={size - 4} className="text-brand transition-transform duration-500 group-hover:rotate-[180deg] group-hover:scale-110" />
      </span>
      <span className="font-display font-semibold tracking-tight" style={{ fontSize: size - 2 }}>
        AgentFlow
      </span>
    </Link>
  );
}
