import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FileText, Plus } from "lucide-react";
import { listProjects } from "../api/projects";
import { getErrorMessage } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import ErrorState from "../components/ErrorState";
import PipelineFlow from "../components/PipelineFlow";
import { Skeleton } from "../components/Skeleton";
import { formatDate } from "../lib/format";

export default function Projects() {
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
    // keep the list fresh while anything is still running
    refetchInterval: (q) => (q.state.data?.some((p) => p.status === "running" || p.status === "queued") ? 3000 : false),
  });

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold">Projects</h1>
          <p className="mt-1 text-sm text-muted">Every ML project you've handed to AgentFlow.</p>
        </div>
        <Link to="/projects/new" className="btn-primary"><Plus size={16} /> New project</Link>
      </div>

      <div className="mt-8">
        {isLoading && (
          <div className="grid gap-4 md:grid-cols-2" aria-busy="true">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[132px]" />)}
          </div>
        )}

        {isError && (
          <ErrorState title="Couldn't load your projects" message={getErrorMessage(error)}>
            <button onClick={() => refetch()} className="btn-primary" disabled={isFetching}>
              {isFetching ? "Retrying…" : "Try again"}
            </button>
          </ErrorState>
        )}

        {data && data.length === 0 && (
          <div className="card mx-auto max-w-xl px-8 py-12 text-center">
            <div className="mx-auto max-w-sm"><PipelineFlow compact /></div>
            <h2 className="mt-6 font-display text-lg font-semibold">No projects yet</h2>
            <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
              Upload a dataset and describe your problem — the agents take it from there.
            </p>
            <Link to="/projects/new" className="btn-primary mt-6">
              Create your first project <ArrowRight size={15} className="nudge" />
            </Link>
          </div>
        )}

        {data && data.length > 0 && (
          <ul className="stagger grid gap-4 md:grid-cols-2">
            {data.map((p) => (
              <li key={p.project_id}>
                <Link
                  to={`/projects/${p.project_id}/${p.status === "completed" ? "results" : "workflow"}`}
                  className="card-hover block h-full p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="font-display text-base font-medium">{p.name}</h2>
                    <StatusBadge status={p.status} />
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-muted">{p.problem_statement}</p>
                  <div className="mt-4 flex items-center justify-between font-mono text-[11px] text-dim">
                    <span className="inline-flex items-center gap-1.5"><FileText size={12} />{p.dataset_name || "no dataset"}</span>
                    <span>{formatDate(p.created_at)}</span>
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
