import { Link } from "react-router-dom";
import Logo from "../Logo";
import ThemeToggle from "../ThemeToggle";
import { AGENTS } from "../../lib/constants";
import { rgb } from "../../lib/theme";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen">
      <aside className="scope-dark relative hidden flex-col justify-between border-r border-line bg-deep p-12 text-ink lg:flex lg:w-[44%]">
        <Logo size={21} />

        <div>
          <p className="reveal label-mono !text-brand" style={{ "--i": 0 }}>Multi-agent AutoML</p>
          <h2 className="reveal mt-5 max-w-[430px] font-display text-[40px] font-medium leading-[1.1]" style={{ "--i": 1 }}>
            Give it a dataset and a goal. <span className="italic text-brand">Watch the agents</span> do the rest.
          </h2>
        </div>

        <ol className="stagger">
          {AGENTS.map((a, i) => (
            <li key={a.key} className="flex items-baseline gap-5 border-t border-line py-4">
              <span className="w-6 font-display text-[15px] italic text-dim">0{i + 1}</span>
              <span className="flex-1 text-[15px]">{a.label}</span>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: rgb(a.token) }} aria-hidden="true" />
            </li>
          ))}
          <li className="flex items-baseline gap-5 border-t border-line py-4">
            <span className="w-6 font-display text-[15px] italic text-dim">04</span>
            <span className="flex-1 text-[15px]">Final model, back to you</span>
            <span className="h-1.5 w-1.5 rounded-full bg-brand" aria-hidden="true" />
          </li>
        </ol>
      </aside>

      <main className="relative flex flex-1 items-center justify-center px-6 py-12">
        <div className="absolute left-6 top-6 lg:hidden"><Logo size={18} /></div>
        <ThemeToggle className="absolute right-6 top-6" />
        <div className="w-full max-w-[390px] animate-fade-in">
          <h1 className="font-display text-[34px] font-medium leading-tight">{title}</h1>
          <p className="mt-2 text-[15px] text-muted">{subtitle}</p>
          {children}
          <p className="mt-7 text-center text-sm text-muted">{footer}</p>
          <p className="mt-10 text-center text-xs text-dim">
            <Link to="/" className="link-underline hover:text-ink">← Back to home</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
