import { api, USE_MOCK } from "./client";
import { ENDPOINTS } from "./endpoints";
import {
  mockListProjects, mockCreateProject, mockUploadDataset,
  mockStartWorkflow, mockWorkflowStatus, mockWorkflowResults,
} from "./mock";

/**
 * API CONTRACT (what the FastAPI backend should return)
 *
 * Project            { project_id, name, problem_statement, dataset_name, created_at, status }
 * Workflow status    { project_id, state: "queued"|"running"|"completed"|"failed",
 *                      agents: [{ key: "data"|"strategy"|"training",
 *                                 status: "waiting"|"running"|"done"|"error",
 *                                 message, output }] }
 * Results            { project_id, project_name, problem_statement, target_column,
 *                      dataset:  { filename, rows, columns, missing_values, duplicates,
 *                                  numerical_features, categorical_features, preprocessing[] },
 *                      strategy: { problem_type, primary_metric, models[] },
 *                      models:   [{ name, score }],
 *                      final_model: { name, score, metric } }
 */

export async function listProjects() {
  if (USE_MOCK) return mockListProjects();
  const { data } = await api.get(ENDPOINTS.listProjects);
  return data;
}

export async function createProject(payload) {
  // payload: { name, problem_statement, target_column }
  if (USE_MOCK) return mockCreateProject(payload);
  const { data } = await api.post(ENDPOINTS.createProject, payload);
  return data; // { project_id }
}

export async function uploadDataset(projectId, file, onProgress) {
  if (USE_MOCK) return mockUploadDataset(projectId, file, onProgress);
  const form = new FormData();
  form.append("project_id", projectId);
  form.append("file", file);
  const { data } = await api.post(ENDPOINTS.uploadDataset, form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
    onUploadProgress: (e) => e.total && onProgress?.(Math.round((e.loaded / e.total) * 100)),
  });
  return data;
}

export async function startWorkflow(projectId) {
  if (USE_MOCK) return mockStartWorkflow(projectId);
  const { data } = await api.post(ENDPOINTS.startWorkflow, { project_id: projectId });
  return data;
}

export async function getWorkflowStatus(projectId) {
  if (USE_MOCK) return mockWorkflowStatus(projectId);
  const { data } = await api.get(ENDPOINTS.workflowStatus, { params: { project_id: projectId } });
  return data;
}

export async function getWorkflowResults(projectId) {
  if (USE_MOCK) return mockWorkflowResults(projectId);
  const { data } = await api.get(ENDPOINTS.workflowResults, { params: { project_id: projectId } });
  return data;
}
