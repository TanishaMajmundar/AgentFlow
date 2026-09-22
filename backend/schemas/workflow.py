from pydantic import BaseModel
from typing import Optional


class WorkflowRequest(BaseModel):
    project_name: str
    problem_statement: str
    target_column: str
    dataset_path: Optional[str] = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    project_name: str
    status: str
    current_agent: Optional[str] = None