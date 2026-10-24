import csv
from pathlib import Path

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
orchestrator = AgentFlowOrchestrator(repo=repo)


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