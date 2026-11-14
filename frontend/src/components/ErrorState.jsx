import { AlertTriangle } from "lucide-react";

export default function ErrorState({ title = "Something went wrong", message, children }) {
  return (
    <div role="alert" className="card mx-auto max-w-md p-8 text-center">
      <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-full border border-danger/40 bg-danger/10 text-danger">
        <AlertTriangle size={20} />
      </div>
      <h2 className="font-display text-lg font-semibold">{title}</h2>
      {message && <p className="mt-2 text-sm leading-relaxed text-muted">{message}</p>}
      {children && <div className="mt-6 flex flex-wrap justify-center gap-3">{children}</div>}
    </div>
  );
}
