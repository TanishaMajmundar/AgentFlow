import { Eye, EyeOff } from "lucide-react";

export default function PasswordToggle({ shown, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={shown ? "Hide password" : "Show password"}
      className="rounded p-1 text-dim transition hover:text-ink"
    >
      {shown ? <EyeOff size={16} /> : <Eye size={16} />}
    </button>
  );
}
