from fastapi import FastAPI, HTTPException

from backend.orchestrator.orchestrator import AgentFlowOrchestrator
from backend.schemas.workflow import (
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatusResponse
)


app = FastAPI(
    title="AgentFlow Backend",
    description="Backend and orchestration API for AgentFlow",
    version="1.0.0"
)


orchestrator = AgentFlowOrchestrator()


@app.get("/")
def root():
    return {
        "message": "AgentFlow Backend is running"
    }


@app.post("/workflow/start", response_model=WorkflowResponse)
def start_workflow(request: WorkflowRequest):

    workflow = orchestrator.start_workflow(
        project_name=request.project_name,
        problem_statement=request.problem_statement,
        target_column=request.target_column,
        dataset_path=request.dataset_path
    )

    return workflow


@app.get(
    "/workflow/{workflow_id}/status",
    response_model=WorkflowStatusResponse
)
def get_workflow_status(workflow_id: str):

    workflow = orchestrator.get_workflow_status(workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found"
        )

    return workflow