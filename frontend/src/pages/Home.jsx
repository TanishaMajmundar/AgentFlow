import { Link } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
import Logo from "../components/Logo";
import ThemeToggle from "../components/ThemeToggle";
import Reveal from "../components/Reveal";
import { AGENTS } from "../lib/constants";
import { rgb } from "../lib/theme";
import { useAuth } from "../context/AuthContext";

const SHORT = {
  data: "Profiles and cleans your dataset",
  strategy: "Picks the task type and metrics",
  training: "Trains and tunes candidate models",
  final: "Returns the best model and its scores",
};

const STAGES = [
  ...AGENTS.map((a) => ({ key: a.key, title: a.label, desc: a.blurb, token: a.token })),
  {
    key: "final", token: "brand", title: "Final selection",
    desc: "Returns the selected model, its metrics, and a comparison of everything that was tried — back to your workspace.",
  },
];

export default function Home() {
  const { user } = useAuth();
  const startTo = user ? "/projects/new" : "/signup";

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 md:px-10">
        <Logo size={21} />
        <nav className="flex items-center gap-5" aria-label="Main">
          <a href="#how-it-works" className="link-underline hidden text-sm text-muted hover:text-ink sm:inline">How it works</a>
          <ThemeToggle />
          {user ? (
            <Link to="/projects" className="btn-primary">Open workspace</Link>
          ) : (
            <>
              <Link to="/login" className="link-underline text-sm">Log in</Link>
              <Link to="/signup" className="btn-primary">Get started</Link>
            </>
          )}
        </nav>
      </header>

      {/* hero */}
      <section className="mx-auto grid max-w-6xl gap-14 px-6 pb-24 pt-10 md:px-10 lg:grid-cols-12 lg:pt-20">
        <div className="lg:col-span-7">
          <p className="reveal label-mono flex items-center gap-3" style={{ "--i": 0 }}>
            <span className="h-px w-10 bg-brand" /> Multi-agent AutoML
          </p>
          <h1 className="mt-7 font-display text-[clamp(38px,5vw,62px)] font-medium leading-[1.02]">
            <span className="reveal block" style={{ "--i": 1 }}>Describe the problem.</span>
            <span className="reveal block" style={{ "--i": 2 }}>Upload the data.</span>
            <span className="reveal block italic text-brand" style={{ "--i": 3 }}>Let the agents build the model.</span>
          </h1>
          <p className="reveal mt-8 max-w-[480px] text-[17px] leading-relaxed text-muted" style={{ "--i": 4 }}>
            AgentFlow hands your dataset to a team of specialized agents that analyze, strategize,
            train, and hand back a finished model — while you watch every step.
          </p>
          <div className="reveal mt-10 flex flex-wrap items-center gap-5" style={{ "--i": 5 }}>
            <Link to={startTo} className="btn-primary !px-6 !py-3">
              Create your first project <ArrowRight size={15} className="nudge" />
            </Link>
            {!user && <Link to="/login" className="link-underline text-sm">I already have an account</Link>}
          </div>
        </div>

        {/* a run, laid out like a ledger */}
        <div className="reveal lg:col-span-5 lg:pt-4" style={{ "--i": 4 }}>
          <div className="card p-7">
            <div className="flex items-center justify-between border-b border-line pb-4 text-xs text-dim">
              <span className="font-mono">heart_disease.csv</span>
              <span className="label-mono !text-[10px]">One run, start to finish</span>
            </div>
            <ol className="relative mt-6 space-y-7 pl-11">
              <span className="absolute bottom-3 left-[13px] top-3 w-px bg-line" aria-hidden="true">
                <span className="absolute -left-[3px] h-[7px] w-[7px] animate-travel-v rounded-full bg-brand" />
              </span>
              {STAGES.map((s, i) => (
                <li key={s.key} className="relative">
                  <span
                    className="absolute -left-11 top-0 flex h-7 w-7 items-center justify-center rounded-full border bg-panel font-display text-[13px] italic"
                    style={{ borderColor: rgb(s.token), color: rgb(s.token) }}
                  >
                    {i + 1}
                  </span>
                  <p className="font-display text-[17px] font-medium leading-tight">{s.title}</p>
                  <p className="mt-1 text-[13px] leading-snug text-muted">{SHORT[s.key]}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* how it works — editorial ledger */}
      <section id="how-it-works" className="border-t border-line">
        <div className="mx-auto max-w-6xl px-6 py-20 md:px-10">
          <Reveal>
            <h2 className="font-display text-[clamp(30px,4vw,44px)] font-medium leading-tight">
              Four stages, <span className="italic text-brand">no manual handoffs.</span>
            </h2>
          </Reveal>
          <div className="mt-12">
            {STAGES.map((s, i) => (
              <Reveal key={s.key} delay={60}>
                <div className="grid gap-4 border-t border-line py-8 md:grid-cols-12 md:gap-8">
                  <span className="font-display text-[34px] italic leading-none md:col-span-2" style={{ color: rgb(s.token) }}>
                    0{i + 1}
                  </span>
                  <h3 className="font-display text-[22px] font-medium leading-tight md:col-span-4">{s.title}</h3>
                  <p className="text-[15px] leading-relaxed text-muted md:col-span-6">{s.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* closing band */}
      <section className="scope-dark bg-deep text-ink">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-8 px-6 py-16 md:px-10">
          <h2 className="max-w-[520px] font-display text-[clamp(28px,3.6vw,40px)] font-medium leading-tight">
            Ready when <span className="italic text-brand">your data is.</span>
          </h2>
          <Link to={startTo} className="btn-primary !px-6 !py-3">
            {user ? "New project" : "Start for free"} <ArrowRight size={15} className="nudge" />
          </Link>
        </div>
      </section>

      <footer className="mx-auto flex max-w-6xl items-center justify-between px-6 py-8 md:px-10">
        <Logo size={16} />
        <span className="flex items-center gap-2 text-xs text-dim"><Check size={12} /> Capstone build</span>
      </footer>
    </div>
  );
}
