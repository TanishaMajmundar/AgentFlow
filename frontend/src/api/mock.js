// In-browser mock of the FastAPI backend so the whole UI works with no server.
// Enabled when VITE_USE_MOCK is not "false". It mimics the real contract:
// status is computed from elapsed time since the workflow started, so progress
// survives page refreshes — just like polling a real backend would.
//
// Demo trick: put "[fail]" in a project name to see the Training Agent fail.

import { analyzeCsv } from "../lib/csv";

const LS_KEY = "af_mock_projects";
const STEP_MS = 2600; // how long each agent "runs"
const AGENT_KEYS = ["data", "strategy", "training"];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const load = () => { try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch { return {}; } };
const save = (db) => localStorage.setItem(LS_KEY, JSON.stringify(db));
const uid = () => "prj_" + Math.random().toString(36).slice(2, 10);

function hash01(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return (h % 1000) / 1000;
}

function httpError(status, detail) {
  const e = new Error(detail);
  e.status = status;
  e.response = { status, data: { detail } };
  return e;
}

function getProject(id) {
  const p = load()[id];
  if (!p) throw httpError(404, "Project not found.");
  return p;
}

function strategyFor(p) {
  const regression = p.stats.targetNumeric && p.stats.targetUnique > 10;
  return regression
    ? {
        problem_type: "regression",
        primary_metric: "R² Score",
        models: ["Linear Regression", "Random Forest Regressor", "Gradient Boosting", "Tuned Gradient Boosting"],
      }
    : {
        problem_type: "classification",
        primary_metric: "F1 Score",
        models: ["Logistic Regression", "SVM", "Random Forest", "Tuned Random Forest"],
      };
}

function scoresFor(p, strategy) {
  const h = hash01(p.name + p.dataset_name);
  const base = 0.74 + h * 0.06;
  const offsets = [0, 0.03, 0.06, 0.1];
  return strategy.models.map((name, i) => ({
    name,
    score: Math.min(0.99, +(base + offsets[i] + (hash01(name + p.name) - 0.5) * 0.01).toFixed(3)),
  }));
}

function agentOutputs(p) {
  const strategy = strategyFor(p);
  const results = scoresFor(p, strategy);
  const best = results.reduce((a, b) => (b.score > a.score ? b : a));
  const preprocessing = ["Removed duplicates"];
  if (p.stats.missing_values > 0) preprocessing.push("Imputed missing values");
  if (p.stats.categorical_features > 0) preprocessing.push("Encoded categorical variables");
  if (p.stats.numerical_features > 0) preprocessing.push("Scaled numerical features");
  return {
    data: {
      rows: p.stats.rows,
      columns: p.stats.columns,
      missing_values: p.stats.missing_values,
      duplicates: p.stats.duplicates,
      numerical_features: p.stats.numerical_features,
      categorical_features: p.stats.categorical_features,
      preprocessing,
    },
    strategy,
    training: { results, best },
  };
}

function computeStatus(p) {
  const waiting = AGENT_KEYS.map((key) => ({ key, status: "waiting", message: "Waiting", output: null }));
  if (!p.started_at) return { project_id: p.project_id, state: "queued", agents: waiting };

  const elapsed = Date.now() - p.started_at;
  const outputs = agentOutputs(p);
  const shouldFail = /\[fail\]/i.test(p.name);
  const runningMsg = {
    data: "Analyzing dataset…",
    strategy: "Identifying problem type…",
    training: "Training candidate models…",
  };

  let state = "running";
  const agents = AGENT_KEYS.map((key, i) => {
    const start = i * STEP_MS;
    const end = (i + 1) * STEP_MS;
    if (elapsed >= end) {
      if (key === "training" && shouldFail) {
        state = "failed";
        return { key, status: "error", message: "Training failed: model did not converge (out of memory).", output: null };
      }
      return { key, status: "done", message: "Completed", output: outputs[key] };
    }
    if (elapsed >= start) return { key, status: "running", message: runningMsg[key], output: null };
    return { key, status: "waiting", message: "Waiting", output: null };
  });

  if (state !== "failed" && elapsed >= AGENT_KEYS.length * STEP_MS) state = "completed";
  return { project_id: p.project_id, state, agents };
}

/* ------------------------- public mock API ------------------------- */

export async function mockListProjects() {
  await sleep(250);
  return Object.values(load())
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .map((p) => ({
      project_id: p.project_id,
      name: p.name,
      problem_statement: p.problem_statement,
      dataset_name: p.dataset_name,
      created_at: p.created_at,
      status: computeStatus(p).state,
    }));
}

export async function mockCreateProject({ name, problem_statement, target_column }) {
  await sleep(350);
  const db = load();
  const project_id = uid();
  db[project_id] = {
    project_id, name, problem_statement, target_column,
    created_at: new Date().toISOString(),
    dataset_name: null, stats: null, started_at: null,
  };
  save(db);
  return { project_id };
}

export async function mockUploadDataset(project_id, file, onProgress) {
  const p = getProject(project_id);
  const text = await file.text();
  // simulate upload progress so the progress bar is visible
  for (let pct = 10; pct <= 100; pct += 15) {
    onProgress?.(Math.min(pct, 100));
    await sleep(90);
  }
  onProgress?.(100);
  const db = load();
  db[project_id] = { ...p, dataset_name: file.name, stats: analyzeCsv(text, p.target_column) };
  save(db);
  return { filename: file.name };
}

export async function mockStartWorkflow(project_id) {
  await sleep(300);
  const p = getProject(project_id);
  if (!p.stats) throw httpError(400, "Upload a dataset before starting the workflow.");
  const db = load();
  db[project_id] = { ...p, started_at: Date.now() };
  save(db);
  return { project_id, state: "running" };
}

export async function mockWorkflowStatus(project_id) {
  await sleep(150);
  return { ...computeStatus(getProject(project_id)), project_name: getProject(project_id).name, dataset_name: getProject(project_id).dataset_name };
}

export async function mockWorkflowResults(project_id) {
  await sleep(250);
  const p = getProject(project_id);
  const status = computeStatus(p);
  if (status.state !== "completed") throw httpError(409, "This workflow hasn't finished yet.");
  const out = agentOutputs(p);
  return {
    project_id,
    project_name: p.name,
    problem_statement: p.problem_statement,
    target_column: p.target_column,
    dataset: { filename: p.dataset_name, ...out.data },
    strategy: out.strategy,
    models: out.training.results,
    final_model: { ...out.training.best, metric: out.strategy.primary_metric },
  };
}
