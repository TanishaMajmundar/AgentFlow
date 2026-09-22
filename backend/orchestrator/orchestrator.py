import uuid


class AgentFlowOrchestrator:

    def __init__(self):
        self.workflows = {}

    def start_workflow(
        self,
        project_name: str,
        problem_statement: str,
        target_column: str,
        dataset_path: str | None = None
    ):

        workflow_id = "WF-" + uuid.uuid4().hex[:8].upper()

        workflow = {
            "workflow_id": workflow_id,
            "project_name": project_name,
            "problem_statement": problem_statement,
            "target_column": target_column,
            "dataset_path": dataset_path,

            "status": "running",
            "current_agent": None,

            "agents": {
                "data_agent": "pending",
                "ml_strategy_agent": "pending",
                "training_agent": "pending"
            }
        }

        self.workflows[workflow_id] = workflow

        return workflow