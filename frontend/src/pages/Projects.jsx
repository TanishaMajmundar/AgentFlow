import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Plus } from "lucide-react";
import { listProjects } from "../api/projects";
import { getErrorMessage } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import ErrorState from "../components/ErrorState";
import { Skeleton } from "../components/Skeleton";
import { formatDate } from "../lib/format";
import { useAuth } from "../context/AuthContext";

export default function Projects() {
  const { user } = useAuth();
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
    refetchInterval: (q) => (q.state.data?.some((p) => p.status === "running" || p.status === "queued") ? 3000 : false),
  });

  const first = (user?.name || "").split(" ")[0];

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-8 md:py-14">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="label-mono">Workspace</p>
          <h1 className="mt-3 font-display text-[clamp(32px,4vw,46px)] font-medium leading-tight">
            {first ? <>Welcome back, <span className="italic text-brand">{first}.</span></> : "Your projects"}
          </h1>
          <p className="mt-2 text-[15px] text-muted">Every ML project you've handed to AgentFlow.</p>
        </div>
        <Link to="/projects/new" className="btn-primary"><Plus size={16} /> New project</Link>
      </div>

      <div className="mt-12 border-t border-line">
        {isLoading && (
          <div className="flex flex-col gap-3 pt-6" aria-busy="true">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-[76px]" />)}
          </div>
        )}

        {isError && (
          <div className="pt-8">
            <ErrorState title="Couldn't load your projects" message={getErrorMessage(error)}>
              <button onClick={() => refetch()} className="btn-primary" disabled={isFetching}>
                {isFetching ? "Retrying…" : "Try again"}
              </button>
            </ErrorState>
          </div>
        )}

        {data && data.length === 0 && (
          <div className="py-20 text-center">
            <p className="font-display text-[28px] italic text-dim">A blank page.</p>
            <p className="mx-auto mt-3 max-w-sm text-[15px] text-muted">
              Upload a dataset and describe your problem — the agents take it from there.
            </p>
            <Link to="/projects/new" className="btn-primary mt-8">
              Create your first project <ArrowRight size={15} className="nudge" />
            </Link>
          </div>
        )}

        {data && data.length > 0 && (
          <ul className="stagger">
            {data.map((p) => (
              <li key={p.project_id} className="border-b border-line">
                <Link
                  to={`/projects/${p.project_id}/${p.status === "completed" ? "results" : "workflow"}`}
                  className="group grid items-center gap-x-6 gap-y-2 py-6 transition-colors duration-200 sm:grid-cols-[1fr_auto]"
                >
                  <div className="min-w-0">
                    <h2 className="truncate font-display text-[22px] font-medium leading-tight transition-colors duration-200 group-hover:text-brand">
                      {p.name}
                    </h2>
                    <p className="mt-1 line-clamp-1 text-[14px] text-muted">{p.problem_statement}</p>
                    <p className="mt-2 text-[12px] text-dim">
                      <span className="font-mono">{p.dataset_name || "no dataset"}</span> · {formatDate(p.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <StatusBadge status={p.status} />
                    <ArrowRight size={16} className="text-dim transition duration-300 group-hover:translate-x-1 group-hover:text-brand" />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
