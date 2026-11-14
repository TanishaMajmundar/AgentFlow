// Single source of truth for backend routes.
// If your FastAPI routes differ, change them HERE and nothing else.
export const ENDPOINTS = {
  listProjects: "/projects",            // GET   -> Project[]
  createProject: "/projects",           // POST  -> { project_id }
  uploadDataset: "/upload-dataset",     // POST  multipart: project_id, file
  startWorkflow: "/workflow/start",     // POST  { project_id }
  workflowStatus: "/workflow/status",   // GET   ?project_id=
  workflowResults: "/workflow/results", // GET   ?project_id=
};
