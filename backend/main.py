import csv
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.repository import Repository
from backend.services.dataset_service import save_dataset
from backend.orchestrator.orchestrator import AgentFlowOrchestrator
from backend.schemas.workflow import (
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatusResponse,
    WorkflowResultsResponse,
)
from backend.orchestrator.target_detector import detect_target, validate_target, load_dataset_frame

from backend.services.frontend_adapter import build_status, build_results
from backend.orchestrator.target_analysis import analyze_target

app = FastAPI(
    title="AgentFlow Backend",
    description="Backend and orchestration API for AgentFlow",
    version="1.0.0"
)

# Lets the React app (Vite runs on port 5173) call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

repo = Repository()
try:
    from backend.agents.real_data_agent import real_data_agent
except Exception as e:   # missing packages etc.: fall back to the mock so the API still starts
    print(f"[AgentFlow] Real Data Agent unavailable, using the mock instead: {e}")
    real_data_agent = None

orchestrator = AgentFlowOrchestrator(repo=repo, data_agent=real_data_agent)


@app.on_event("startup")
def on_startup():
    init_db()                # connects to MongoDB, fails with a clear error if it's not running
    repo.mark_interrupted()  # any workflow left "running" from a crash is marked failed


@app.get("/")
def root():
    return {"message": "AgentFlow Backend is running"}


@app.post("/dataset/upload")
def upload_dataset(file: UploadFile = File(...)):
    try:
        info = save_dataset(file)
        repo.save_dataset(info)
        return info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/workflow/start", response_model=WorkflowResponse)
def start_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):

    if not request.dataset_path or not Path(request.dataset_path).is_file():
        raise HTTPException(status_code=400, detail="Dataset not found. Upload it first.")

    with open(request.dataset_path, newline="", encoding="utf-8-sig") as f:
        header = next(csv.reader(f), [])
    if request.target_column.strip() not in [h.strip() for h in header]:
        raise HTTPException(
            status_code=400,
            detail=f"Target column '{request.target_column}' not in dataset"
        )

    workflow = orchestrator.start_workflow(
        project_name=request.project_name,
        problem_statement=request.problem_statement,
        target_column=request.target_column.strip(),
        dataset_id=request.dataset_id,
        dataset_path=request.dataset_path,
    )

    # Runs the agents AFTER the response is sent, so this call returns immediately
    background_tasks.add_task(orchestrator.run_workflow, workflow["workflow_id"])
    return workflow


@app.get("/workflow/{workflow_id}/status", response_model=WorkflowStatusResponse)
def get_workflow_status(workflow_id: str):
    workflow = orchestrator.get_workflow_status(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.get("/workflow/{workflow_id}/results", response_model=WorkflowResultsResponse)
def get_workflow_results(workflow_id: str):
    wf = orchestrator.get_workflow_status(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf["status"] in ("created", "running"):
        raise HTTPException(status_code=409, detail="Workflow not finished yet")
    return wf


@app.get("/workflows")
def list_workflows():
    return repo.list_workflows()


class ProjectCreate(BaseModel):
    name: str
    problem_statement: str


@app.post("/projects")
def create_project(body: ProjectCreate):
    wf = orchestrator.create_project(body.name.strip(), body.problem_statement.strip())
    return {"project_id": wf["workflow_id"]}


@app.post("/projects/{project_id}/dataset")
def upload_project_dataset(project_id: str, file: UploadFile = File(...)):
    wf = orchestrator.get_workflow_status(project_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        info = save_dataset(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    repo.save_dataset(info)
    wf["dataset_id"] = info["dataset_id"]
    wf["dataset_path"] = info["dataset_path"]
    wf["dataset_name"] = info["filename"]
    wf["columns"] = info["columns"]
    orchestrator.workflows[project_id] = wf   # keep it runnable even after a restart
    repo.save_workflow(wf)
    return info


@app.get("/projects")
def list_projects():
    out = []
    for wf in repo.list_workflows():
        out.append({
            "project_id": wf.get("project_id", wf["workflow_id"]),
            "name": wf["project_name"],
            "problem_statement": wf.get("problem_statement", ""),
            "dataset_name": wf.get("dataset_name"),
            "created_at": wf.get("created_at"),
            "status": "queued" if wf["status"] == "created" else wf["status"],
        })
    return out


class TargetUpdate(BaseModel):
    target_column: str


@app.put("/projects/{project_id}/target")
def set_project_target(project_id: str, body: TargetUpdate):
    wf = orchestrator.get_workflow_status(project_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Project not found")
    path = wf.get("dataset_path")
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=400, detail="Upload a dataset first")
    target = body.target_column.strip()
    check = validate_target(load_dataset_frame(path), target)
    if not check["valid"]:
        raise HTTPException(status_code=400, detail=" ".join(check["problems"]))
    wf["target_column"] = target
    orchestrator.workflows[project_id] = wf
    repo.save_workflow(wf)
    return {"project_id": project_id, "target_column": target,
            "problem_type": check["problem_type"], "warnings": check["warnings"]}


@app.post("/projects/{project_id}/start")
def start_project(project_id: str, background_tasks: BackgroundTasks):
    wf = orchestrator.get_workflow_status(project_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not wf.get("dataset_path") or not Path(wf["dataset_path"]).is_file():
        raise HTTPException(status_code=400, detail="Upload a dataset first")
    if not wf.get("target_column"):
        raise HTTPException(status_code=400, detail="Confirm the target column first")
    if wf["status"] == "running":
        raise HTTPException(status_code=409, detail="Workflow is already running")

    # reset so a project can be run again after a failure
    wf["status"] = "created"
    wf["error"] = None
    wf["results"] = {}
    wf["final_model"] = None
    wf["mock_agents"] = []
    wf["current_agent"] = None
    wf["agents"] = {k: "pending" for k in
                    ("data_agent", "ml_strategy_agent", "training_agent", "final_model_selection")}
    orchestrator.workflows[project_id] = wf
    repo.save_workflow(wf)

    background_tasks.add_task(orchestrator.run_workflow, project_id)
    return {"project_id": project_id, "status": "started"}


@app.post("/projects/{project_id}/analyze")
def analyze_project(project_id: str):
    wf = orchestrator.get_workflow_status(project_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Project not found")
    path = wf.get("dataset_path")
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=400, detail="Upload a dataset first")
    try:
        df = load_dataset_frame(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read the dataset: {e}")
    result = analyze_target(df, wf.get("problem_statement", ""))
    wf["target_recommendation"] = result
    orchestrator.workflows[project_id] = wf
    repo.save_workflow(wf)
    return result

@app.get("/projects/{project_id}/status")
def project_status(project_id: str):
    wf = orchestrator.get_workflow_status(project_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return build_status(wf)


@app.get("/projects/{project_id}/results")
def project_results(project_id: str):
    wf = orchestrator.get_workflow_status(project_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if wf["status"] != "completed":
        raise HTTPException(status_code=409, detail=wf.get("error") or "This workflow hasn't finished yet.")
    return build_results(wf)


@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    wf = orchestrator.get_workflow_status(project_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if wf["status"] == "running":
        raise HTTPException(status_code=409, detail="Cannot delete a running project")
    orchestrator.workflows.pop(project_id, None)
    repo.delete_workflow(project_id)
    return {"deleted": project_id}