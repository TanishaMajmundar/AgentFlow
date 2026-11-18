import { Link, useParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, RotateCcw } from "lucide-react";
import { useWorkflowStatus } from "../hooks/useWorkflowStatus";
import { startWorkflow } from "../api/projects";
import { getErrorMessage, getErrorStatus } from "../api/client";
import PipelineFlow from "../components/PipelineFlow";
import AgentCard from "../components/AgentCard";
import StatusBadge from "../components/StatusBadge";
import ErrorState from "../components/ErrorState";
import { Skeleton } from "../components/Skeleton";
import { AGENTS } from "../lib/constants";

const AGENT_STATE = { waiting: "idle", running: "running", done: "done", error: "error" };

export default function Workflow() {
  const { projectId } = useParams();
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error, refetch, isFetching } = useWorkflowStatus(projectId);

  const retry = useMutation({
    mutationFn: () => startWorkflow(projectId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workflow", projectId] }),
  });

  const Back = (
    <Link to="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-ink">
      <ArrowLeft size={14} /> Projects
    </Link>
  );

  if (isError) {
    const notFound = getErrorStatus(error) === 404;
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8 md:py-10">
        {Back}
        <div className="mt-8">
          <ErrorState
            title={notFound ? "Project not found" : "Couldn't load workflow status"}
            message={getErrorMessage(error)}
          >
            {!notFound && (
              <button className="btn-primary" onClick={() => refetch()} disabled={isFetching}>
                {isFetching ? "Retrying…" : "Try again"}
              </button>
            )}
            <Link to="/projects" className="btn-ghost">Back to projects</Link>
          </ErrorState>
        </div>
      </main>
    );
  }

  if (isLoading || !data) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8 md:py-10" aria-busy="true">
        {Back}
        <Skeleton className="mt-6 h-[110px]" />
        <div className="mt-5 flex flex-col gap-4">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-[84px]" />)}
        </div>
      </main>
    );
  }

  const byKey = Object.fromEntries(data.agents.map((a) => [a.key, a]));
  const completed = data.state === "completed";
  const failed = data.state === "failed";
  const failedAgent = data.agents.find((a) => a.status === "error");

  const states = {
    input: "done",
    ...Object.fromEntries(AGENTS.map((m) => [m.key, AGENT_STATE[byKey[m.key]?.status || "waiting"]])),
    result: completed ? "done" : "idle",
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8 md:py-10">
      {Back}

      <div className="mt-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold">{data.project_name || "AgentFlow pipeline"}</h1>
          <p className="mt-1 font-mono text-xs text-dim">{data.dataset_name}</p>
        </div>
        <StatusBadge status={data.state} />
      </div>

      <div className="card mt-6 rounded-2xl px-3 py-5 sm:px-8">
        <PipelineFlow states={states} />
      </div>

        <div className="stagger mt-5 grid items-start gap-4 lg:grid-cols-3" aria-live="polite">
        {AGENTS.map((meta) => <AgentCard key={meta.key} meta={meta} agent={byKey[meta.key]} />)}
      </div>

      {completed && (
        <div className="card mt-6 animate-fade-in p-5">
          <div className="flex flex-wrap items-center gap-4">
            <span className="relative flex h-11 w-11 shrink-0 items-center justify-center">
              <span className="absolute inset-0 animate-ring-burst rounded-full border-2 border-data" />
              <span className="flex h-11 w-11 items-center justify-center rounded-full border border-data/40 bg-data/10 text-data">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M5 12.5l4.5 4.5L19 7.5" strokeDasharray="24" strokeDashoffset="24" className="animate-draw-check" />
                </svg>
              </span>
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-display font-medium">All agents finished</p>
              <p className="text-sm text-muted">Your model is trained and ready to review.</p>
            </div>
            <Link to={`/projects/${projectId}/results`} className="btn-primary">
              View results <ArrowRight size={15} className="nudge" />
            </Link>
          </div>
        </div>
      )}

      {failed && (
        <div role="alert" className="mt-6 animate-fade-in rounded-xl border border-danger/40 bg-danger/10 p-5">
          <p className="font-medium text-danger">The workflow stopped.</p>
          <p className="mt-1 text-sm text-muted">
            {failedAgent?.message || "An agent reported an error."}
          </p>
          {retry.isError && <p className="mt-2 text-sm text-danger">{getErrorMessage(retry.error)}</p>}
          <div className="mt-4 flex flex-wrap gap-3">
            <button className="btn-primary" onClick={() => retry.mutate()} disabled={retry.isPending}>
              <RotateCcw size={14} /> {retry.isPending ? "Restarting…" : "Retry workflow"}
            </button>
            <Link to="/projects" className="btn-ghost">Back to projects</Link>
          </div>
        </div>
      )}
    </main>
  );
}
