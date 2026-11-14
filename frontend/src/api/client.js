import axios from "axios";

export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
});

// Attach auth token (once the backend adds auth) to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("af_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/** Converts any thrown value into a message that is safe to show the user. */
export function getErrorMessage(err) {
  if (axios.isAxiosError(err)) {
    if (!err.response) return "Can't reach the AgentFlow server. Check that the backend is running.";
    const detail = err.response.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg; // FastAPI validation errors
    return `Request failed (${err.response.status}).`;
  }
  return err?.message || "Something went wrong.";
}

export const getErrorStatus = (err) => err?.response?.status ?? err?.status;
