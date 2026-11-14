# AgentFlow — Frontend

React interface for AgentFlow, the multi-agent AutoML platform.
The user creates a project, uploads a CSV, picks a target column, starts the pipeline,
watches **Data Agent → ML Strategy Agent → Training & Improvement Agent** run, and views the results.

The frontend only talks to the FastAPI backend. It never calls an agent directly.

## Stack
React 18 · Vite · React Router · Tailwind CSS · Axios · TanStack React Query · Recharts · Lucide

## Run it
```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production build -> dist/
```
Works immediately with **no backend**: `VITE_USE_MOCK=true` (default) uses an in-browser mock
that behaves like the real API (real CSV stats, timed agent progress, persisted in localStorage).

## Connect the real FastAPI backend
1. Copy `.env.example` to `.env`
2. Set `VITE_USE_MOCK=false` and `VITE_API_URL=http://localhost:8000`
3. Enable CORS in FastAPI for `http://localhost:5173`
4. If your routes differ, edit **only** `src/api/endpoints.js`

### Expected API contract (also documented in `src/api/projects.js`)
| Action | Request | Response |
|---|---|---|
| Create project | `POST /projects` `{name, problem_statement, target_column}` | `{project_id}` |
| Upload dataset | `POST /upload-dataset` multipart `project_id`, `file` | `{filename}` |
| Start workflow | `POST /workflow/start` `{project_id}` | `{project_id, state}` |
| Poll status | `GET /workflow/status?project_id=` | `{state, agents:[{key,status,message,output}], project_name, dataset_name}` |
| Results | `GET /workflow/results?project_id=` | `{dataset, strategy, models:[{name,score}], final_model}` — return **409** if not finished |
| List projects | `GET /projects` | `[{project_id,name,problem_statement,dataset_name,created_at,status}]` |

`state`: `queued | running | completed | failed` · agent `key`: `data | strategy | training` ·
agent `status`: `waiting | running | done | error`.

## Theming (dark / light)
- Toggle in the top bar of every page. The choice is saved in `localStorage` (`af_theme`) and applied
  before first paint (script in `index.html`) so there is no flash. Default is dark.
- All colors are CSS variables defined once in `src/index.css` (`:root` = dark, `[data-theme="light"]` = light).
  Tailwind reads them in `tailwind.config.js`, so classes like `bg-panel` or `border-brand/40` switch automatically.
- **To restyle a theme, edit the variables in `index.css` — nothing else.**
- In inline styles use `rgb("token", alpha)` from `src/lib/theme.js`; Recharts colors come from `useChartColors()`.
- The switch plays a circular reveal from the toggle button (View Transitions API) with a cross-fade fallback.

## Animations
Page transitions, staggered lists/forms, scroll-reveal (`Reveal`), count-up numbers (`CountUp`),
drifting background glow (`AmbientGlow`), shimmer skeletons, live pipeline with pop/ring/draw-check effects,
button shine + arrow nudge, animated theme toggle. All respect `prefers-reduced-motion`, and
scroll-reveal content is forced visible when printing.

## Folder structure
```
src/
  api/         client (axios), endpoints, projects (API calls), mock (fake backend)
  components/  Logo, PipelineFlow (animated pipeline), AgentCard, Dropzone, Field, StatCard,
               StatusBadge, ErrorState, Skeleton, ProtectedRoute, layouts/
  context/     AuthContext (demo auth), ThemeContext (dark/light)
  hooks/       useWorkflowStatus (polling every 1.5s, stops when finished)
  lib/         constants (agent definitions), csv (client-side CSV parsing), format
  pages/       Home, Login, Signup, Projects, CreateProject, Workflow, Results, NotFound
```

## Routes
`/` · `/login` · `/signup` · `/projects` · `/projects/new` · `/projects/:id/workflow` · `/projects/:id/results`
(everything under `/projects` requires login)

## Demo tips
- Name a project with **`[fail]`** in it to see the failed-workflow state (Training Agent errors).
- Use any CSV; the dataset summary on the results page is computed from your real file.

## Known limitations
- **Auth is a demo**: it stores a fake session in localStorage. Replace `login()/signup()` in
  `AuthContext.jsx` once the backend has auth endpoints.
- CSV parsing in the browser doesn't support line breaks inside quoted cells (only affects the
  preview/mock stats; the real backend parses the uploaded file itself).
- Mock model scores are simulated, not real training results.
