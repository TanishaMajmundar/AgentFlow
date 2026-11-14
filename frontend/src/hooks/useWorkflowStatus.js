import { useQuery } from "@tanstack/react-query";
import { getWorkflowStatus } from "../api/projects";
import { POLL_INTERVAL_MS } from "../lib/constants";

const TERMINAL = ["completed", "failed"];

/**
 * Polls GET /workflow/status every 1.5s and stops automatically
 * once the workflow reaches a terminal state.
 */
export function useWorkflowStatus(projectId) {
  return useQuery({
    queryKey: ["workflow", projectId],
    queryFn: () => getWorkflowStatus(projectId),
    refetchInterval: (query) =>
      TERMINAL.includes(query.state.data?.state) ? false : POLL_INTERVAL_MS,
    retry: 2,
    staleTime: 0,
  });
}
