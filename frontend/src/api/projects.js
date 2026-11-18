import { api, USE_MOCK } from "./client";
import { ENDPOINTS } from "./endpoints";
import {
  mockListProjects, mockCreateProject, mockUploadDataset,
  mockStartWorkflow, mockWorkflowStatus, mockWorkflowResults,
} from "./mock";

/**
 * API CONTRACT (FastAPI backend)
 *
 * POST /projects                  { name, problem_statement }      -> { project_id }
 * POST /projects/{id}/dataset     multipart file                   -> { columns, ... }
 * POST /projects/{id}/analyze                                      -> { recommended, reason, confidence,
 *                                    ambiguous, problem_type, alternatives[], columns[], validation }
 * PUT  /projects/{id}/target      { target_column }                -> { problem_type, warnings[] }
 * POST /projects/{id}/start                                        -> { status: "started" }
 * GET  /projects/{id}/status      -> { state, agents:[{key,status,message,output}], ... }
 * GET  /projects/{id}/results     -> { dataset, strategy, models[], final_model }   (409 if not finished)
 */

export async function listProjects() {
  if (USE_MOCK) return mockListProjects();
  const { data } = await api.get(ENDPOINTS.listProjects);
  return data;
}

export async function createProject(payload) {
  // payload: { name, problem_statement, target_column }  (target_column is only used by the mock)
  if (USE_MOCK) return mockCreateProject(payload);
  const { data } = await api.post(ENDPOINTS.createProject, {
    name: payload.name,
    problem_statement: payload.problem_statement,
  });
  return data; // { project_id }
}

export async function uploadDataset(projectId, file, onProgress) {
  if (USE_MOCK) return mockUploadDataset(projectId, file, onProgress);
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post(ENDPOINTS.uploadDataset(projectId), form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
    onUploadProgress: (e) => e.total && onProgress?.(Math.round((e.loaded / e.total) * 100)),
  });
  return data;
}

export async function analyzeProject(projectId, columns = []) {
  if (USE_MOCK) {
    // The mock backend has no target detection: fall back to the last column.
    const last = columns[columns.length - 1] ?? null;
    return {
      recommended: last,
      reason: "Mock mode: the last column was suggested by default.",
      confidence: 0.5,
      ambiguous: false,
      problem_type: null,
      alternatives: [],
      columns: columns.map((name) => ({ name, usable: true, note: "" })),
      validation: { warnings: [] },
    };
  }
  const { data } = await api.post(ENDPOINTS.analyzeProject(projectId), null, { timeout: 120000 });
  return data;
}

export async function setProjectTarget(projectId, targetColumn) {
  if (USE_MOCK) return { project_id: projectId, target_column: targetColumn, warnings: [] };
  const { data } = await api.put(ENDPOINTS.setTarget(projectId), { target_column: targetColumn });
  return data;
}

export async function startWorkflow(projectId) {
  if (USE_MOCK) return mockStartWorkflow(projectId);
  const { data } = await api.post(ENDPOINTS.startWorkflow(projectId));
  return data;
}

export async function getWorkflowStatus(projectId) {
  if (USE_MOCK) return mockWorkflowStatus(projectId);
  const { data } = await api.get(ENDPOINTS.workflowStatus(projectId));
  return data;
}

export async function getWorkflowResults(projectId) {
  if (USE_MOCK) return mockWorkflowResults(projectId);
  const { data } = await api.get(ENDPOINTS.workflowResults(projectId));
  return data;
}

export async function getDataReport(projectId) {
  if (USE_MOCK) return null;
  const { data } = await api.get(ENDPOINTS.dataReport(projectId));
  return data;
}

export async function getModelInfo(projectId) {
  if (USE_MOCK) return null;
  const { data } = await api.get(ENDPOINTS.modelInfo(projectId));
  return data;
}

export async function downloadModel(projectId, filename = "best_model.pkl") {
  if (USE_MOCK) throw new Error("Model download needs the real backend (VITE_USE_MOCK=false).");
  const res = await api.get(ENDPOINTS.modelDownload(projectId), { responseType: "blob", timeout: 120000 });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}