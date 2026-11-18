import { useMemo, useState } from "react";
import { Link, useMatch, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Loader2, LogOut, Plus, Search } from "lucide-react";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";
import { Skeleton } from "./Skeleton";
import { useAuth } from "../context/AuthContext";
import { listProjects } from "../api/projects";
import { rgb } from "../lib/theme";
import { timeAgo } from "../lib/format";

const DOT = { queued: "muted", running: "training", completed: "data", failed: "danger" };

function StatusDot({ status }) {
  const token = DOT[status] || "muted";
  return (
    <span className="flex h-3 w-3 shrink-0 items-center justify-center" title={status}>
      {status === "running" ? (
        <Loader2 size={12} className="animate-spin" style={{ color: rgb(token) }} aria-label="Running" />
      ) : (
        <span className="h-2 w-2 rounded-full" style={{ background: rgb(token) }} />
      )}
    </span>
  );
}

/**
 * Logged-in navigation: the user's projects, newest first, with live status.
 * Always rendered in the espresso palette (scope-dark) regardless of page theme.
 */
export default function Sidebar({ onNavigate }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const match = useMatch("/projects/:projectId/*");
  const activeId = match?.params.projectId && match.params.projectId !== "new" ? match.params.projectId : null;
  const onNew = !!useMatch("/projects/new");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
    refetchInterval: (q) => (q.state.data?.some((p) => p.status === "running" || p.status === "queued") ? 3000 : false),
  });

  const [query, setQuery] = useState("");
  const list = useMemo(() => {
    const t = query.trim().toLowerCase();
    return (data || []).filter((p) => !t || p.name.toLowerCase().includes(t));
  }, [data, query]);

  const initial = (user?.name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <div className="scope-dark flex h-full flex-col border-r border-line bg-deep text-ink">
      <div className="px-5 pb-4 pt-6"><Logo size={19} to="/projects" /></div>

      <div className="px-4">
        <Link
          to="/projects/new"
          onClick={onNavigate}
          className={`btn-primary w-full ${onNew ? "ring-2 ring-brand/40 ring-offset-2 ring-offset-deep" : ""}`}
        >
          <Plus size={15} /> New project
        </Link>
      </div>

      <div className="mt-7 flex items-center justify-between px-5">
        <Link to="/projects" onClick={onNavigate} className="label-mono !text-dim transition hover:!text-ink">Your projects</Link>
        {data && <span className="font-mono text-meta text-dim">{data.length}</span>}
      </div>

      {data && data.length > 5 && (
        <div className="relative mx-4 mt-3">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-dim" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter projects"
            aria-label="Filter projects"
            className="input !bg-transparent !py-2 !pl-9 !text-[13px]"
          />
        </div>
      )}

      <nav aria-label="Your projects" className="scroll-slim mt-3 flex-1 overflow-y-auto px-2 pb-3">
        {isLoading && (
          <div className="flex flex-col gap-2 px-2 pt-1">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-11" />)}
          </div>
        )}

        {isError && (
          <div className="px-3 py-4 text-sm text-muted">
            Couldn't load projects.{" "}
            <button onClick={() => refetch()} className="link-underline text-ink">Try again</button>
          </div>
        )}

        {data && data.length === 0 && (
          <p className="px-3 py-4 text-sm leading-relaxed text-dim">
            Nothing here yet. Your projects will be listed here once you create one.
          </p>
        )}

        {data && data.length > 0 && list.length === 0 && (
          <p className="px-3 py-4 text-sm text-dim">No project matches “{query}”.</p>
        )}

        <ul className="flex flex-col gap-0.5">
          {list.map((p) => {
            const active = p.project_id === activeId;
            return (
              <li key={p.project_id}>
                <Link
                  to={`/projects/${p.project_id}/${p.status === "completed" ? "results" : "workflow"}`}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  title={`${p.name}\n${p.dataset_name || "no dataset"}`}
                  className={`relative flex items-start gap-3 rounded-md px-3 py-2.5 transition-colors duration-150 ${
                    active ? "bg-panel2" : "hover:bg-panel2/60"
                  }`}
                >
                  <span
                    className={`absolute bottom-2 left-0 top-2 w-[2px] rounded-full bg-brand ${active ? "opacity-100" : "opacity-0"}`}
                  />
                  <span className="mt-[5px]"><StatusDot status={p.status} /></span>
                  <span className="min-w-0 flex-1">
                    <span className={`line-clamp-2 break-words text-[14px] leading-snug ${active ? "font-medium text-ink" : "text-ink/90"}`}>
                      {p.name}
                    </span>
                    <span className="mt-1 flex items-baseline gap-2 text-meta text-muted">
                      <span className="min-w-0 flex-1 truncate font-mono">{p.dataset_name || "no dataset"}</span>
                      <span className="shrink-0 whitespace-nowrap text-dim">{timeAgo(p.created_at)}</span>
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="flex items-center gap-3 border-t border-line px-4 py-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line2 font-display text-[15px] italic text-brand">
          {initial}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] text-ink">{user?.name}</span>
          <span className="block truncate text-meta text-dim">{user?.email}</span>
        </span>
        <ThemeToggle />
        <button
          onClick={() => { logout(); navigate("/"); }}
          aria-label="Log out"
          title="Log out"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line text-muted transition hover:border-danger/60 hover:text-danger"
        >
          <LogOut size={15} />
        </button>
      </div>
    </div>
  );
}
