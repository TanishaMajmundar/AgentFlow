import { Database, Brain, Cpu } from "lucide-react";

// The three agents in the AgentFlow pipeline, in execution order.
// `key` must match the agent keys returned by GET /workflow/status.
export const AGENTS = [
  {
    key: "data",
    label: "Data Agent",
    tag: "DATA AGENT",
    token: "data",
    icon: Database,
    running: "Analyzing dataset…",
    blurb:
      "Profiles your dataset, flags missing values and duplicates, and prepares it for modeling — encoding, scaling, cleaning.",
  },
  {
    key: "strategy",
    label: "ML Strategy Agent",
    tag: "ML STRATEGY AGENT",
    token: "strategy",
    icon: Brain,
    running: "Identifying problem type…",
    blurb:
      "Reads your problem statement, decides the task type, and chooses which model families and metrics fit it best.",
  },
  {
    key: "training",
    label: "Training & Improvement Agent",
    tag: "TRAINING & IMPROVEMENT AGENT",
    token: "training",
    icon: Cpu,
    running: "Training candidate models…",
    blurb:
      "Trains and tunes the candidate models, comparing runs until it converges on the strongest performer.",
  },
];

// Token names (see src/index.css) — resolved to real colors by rgb() in lib/theme.js
export const BRAND_TOKEN = "brand";
export const DONE_TOKEN = "data";
export const ERROR_TOKEN = "danger";
export const MAX_UPLOAD_MB = 50;
export const POLL_INTERVAL_MS = 1500;
