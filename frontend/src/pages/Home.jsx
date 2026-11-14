import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import Logo from "../components/Logo";
import PipelineFlow from "../components/PipelineFlow";
import { AGENTS, BRAND_TOKEN } from "../lib/constants";
import { rgb } from "../lib/theme";
import ThemeToggle from "../components/ThemeToggle";
import AmbientGlow from "../components/AmbientGlow";
import Reveal from "../components/Reveal";
import { useAuth } from "../context/AuthContext";

const STAGES = [
  ...AGENTS.map((a) => ({ ...a, title: a.label, desc: a.blurb })),
  {
    key: "final", title: "Final Selection", token: BRAND_TOKEN, icon: CheckCircle2,
    desc: "Returns the selected model, its metrics, and a comparison of everything that was tried — back to your dashboard.",
  },
];

export default function Home() {
  const { user } = useAuth();
  const startTo = user ? "/projects/new" : "/signup";

  return (
    <div className="min-h-screen">
      <nav className="relative z-20 flex items-center justify-between px-6 py-5 md:px-10" aria-label="Main">
        <Logo />
        <div className="hidden items-center gap-8 font-mono text-[12.5px] text-muted md:flex">
          <a href="#how-it-works" className="transition hover:text-ink">HOW IT WORKS</a>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {user ? (
            <Link to="/projects" className="btn-primary !py-2">Open app</Link>
          ) : (
            <>
              <Link to="/login" className="rounded-md px-3 py-2 text-sm text-muted transition hover:text-ink">Log in</Link>
              <Link to="/signup" className="btn-primary !py-2">Get started</Link>
            </>
          )}
        </div>
      </nav>

      <section className="bg-grid relative border-b border-edge px-6 pb-20 pt-16 md:px-10">
        <AmbientGlow />
        <div className="relative z-10 mx-auto max-w-3xl text-center">
          <div className="reveal mx-auto inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1 font-mono text-[11px] text-muted" style={{ "--i": 0 }}>
            <span className="relative flex h-1.5 w-1.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-data opacity-70" /><span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-data" /></span> MULTI-AGENT AUTOML
          </div>
          <h1 className="mt-6 font-display text-[clamp(32px,5vw,52px)] font-semibold leading-[1.12]">
            <span className="reveal block" style={{ "--i": 1 }}>Describe the problem.</span>
            <span className="reveal block" style={{ "--i": 2 }}>Upload the data.</span>
            <span className="reveal block text-brand" style={{ "--i": 3 }}>Let the agents build the model.</span>
          </h1>
          <p className="reveal mx-auto mt-5 max-w-[520px] text-[15.5px] leading-relaxed text-muted" style={{ "--i": 4 }}>
            AgentFlow hands your dataset to a team of specialized agents that analyze, strategize,
            train, and hand back a finished model — while you watch every step.
          </p>
          <div className="reveal mt-8 flex flex-wrap items-center justify-center gap-3" style={{ "--i": 5 }}>
            <Link to={startTo} className="btn-primary">
              Create your first project <ArrowRight size={15} className="nudge" />
            </Link>
            {!user && <Link to="/login" className="btn-ghost">I have an account</Link>}
          </div>
        </div>

        <div className="card reveal relative z-10 mx-auto mt-16 max-w-3xl rounded-2xl px-8 py-6" style={{ "--i": 6 }}>
          <div className="flex items-center justify-between font-mono text-[10.5px] text-dim">
            <span>heart_disease.csv</span><span>LIVE PIPELINE</span>
          </div>
          <PipelineFlow />
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-5xl px-6 py-20 md:px-10">
        <h2 className="font-display text-[26px] font-semibold">How it works</h2>
        <p className="mb-10 mt-2 text-sm text-muted">Four agents, one pipeline, no manual handoffs.</p>
        <div className="grid gap-4 md:grid-cols-2">
          {STAGES.map((s, i) => {
            const Icon = s.icon;
            return (
              <Reveal key={s.key} delay={(i % 2) * 120}>
                <div className="card-hover h-full p-6">
                  <div className="flex items-start justify-between">
                    <span
                      className="flex h-10 w-10 items-center justify-center rounded-lg border"
                      style={{ color: rgb(s.token), borderColor: rgb(s.token, 0.27), background: rgb(s.token, 0.08) }}
                    >
                      <Icon size={18} />
                    </span>
                    <span className="font-mono text-xs text-dim">0{i + 1}</span>
                  </div>
                  <h3 className="mt-4 font-display text-base font-medium">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{s.desc}</p>
                </div>
              </Reveal>
            );
          })}
        </div>
      </section>

      <footer className="flex items-center justify-between border-t border-edge px-6 py-8 md:px-10">
        <Logo size={16} />
        <span className="font-mono text-[11px] text-dim">CAPSTONE BUILD</span>
      </footer>
    </div>
  );
}
