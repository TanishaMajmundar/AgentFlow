import { Link } from "react-router-dom";
import Logo from "../Logo";
import { PipelineVertical } from "../PipelineFlow";
import ThemeToggle from "../ThemeToggle";
import AmbientGlow from "../AmbientGlow";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen">
      <aside className="bg-grid relative hidden flex-col justify-between border-r border-edge bg-deep p-10 lg:flex lg:w-[42%]">
        <AmbientGlow />
        <div className="relative z-10"><Logo /></div>
        <div className="relative z-10 flex-1"><PipelineVertical /></div>
        <div className="relative z-10">
          <p className="max-w-[340px] font-display text-xl font-medium leading-snug">
            Give it a dataset and a goal.<br />Watch the agents do the rest.
          </p>
          <p className="mt-3 font-mono text-[11.5px] text-dim">DATA → STRATEGY → TRAINING → RESULT</p>
        </div>
      </aside>

      <main className="relative flex flex-1 items-center justify-center px-6 py-12">
        <div className="absolute left-6 top-6 lg:hidden"><Logo size={18} /></div>
        <ThemeToggle className="absolute right-6 top-6" />
        <div className="w-full max-w-[380px] animate-fade-in">
          <h1 className="font-display text-[28px] font-semibold">{title}</h1>
          <p className="mt-2 text-sm text-muted">{subtitle}</p>
          {children}
          <p className="mt-6 text-center text-sm text-muted">{footer}</p>
          <p className="mt-10 text-center text-xs text-dim">
            <Link to="/" className="hover:text-ink">← Back to home</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
