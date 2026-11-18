// Single source of truth for backend routes.
// Routes that need a project id are functions.
export const ENDPOINTS = {
  listProjects: "/projects",                          // GET
  createProject: "/projects",                         // POST { name, problem_statement }
  uploadDataset: (id) => `/projects/${id}/dataset`,   // POST multipart: file
  analyzeProject: (id) => `/projects/${id}/analyze`,  // POST -> target recommendation
  setTarget: (id) => `/projects/${id}/target`,        // PUT { target_column }
  startWorkflow: (id) => `/projects/${id}/start`,     // POST
  workflowStatus: (id) => `/projects/${id}/status`,   // GET
  workflowResults: (id) => `/projects/${id}/results`, // GET (409 until finished)
  dataReport: (id) => `/projects/${id}/data-report`, // GET
  modelDownload: (id) => `/projects/${id}/model/download`, // GET (file)
  modelInfo: (id) => `/projects/${id}/model/info`,         // GET
};