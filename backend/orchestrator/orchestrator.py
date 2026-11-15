import uuid

from backend.agents.mock_agents import (
    mock_data_agent, mock_ml_strategy_agent, mock_training_agent,
)
from backend.orchestrator.model_selection import select_best_model
from backend.repository import Repository


class AgentFlowOrchestrator:

    def __init__(self, data_agent=None, strategy_agent=None, training_agent=None, repo=None):
        self.workflows = {}  # in-memory cache of active workflows
        self.repo = repo or Repository()
        self.data_agent = data_agent or mock_data_agent
        self.strategy_agent = strategy_agent or mock_ml_strategy_agent
        self.training_agent = training_agent or mock_training_agent

    def start_workflow(self, project_name, problem_statement, target_column,
                       dataset_id=None, dataset_path=None):
        workflow_id = "WF-" + uuid.uuid4().hex[:8].upper()
        workflow = {
            "workflow_id": workflow_id,
            "project_name": project_name,
            "problem_statement": problem_statement,
            "target_column": target_column,
            "dataset_id": dataset_id,
            "dataset_path": dataset_path,
            "status": "created",
            "current_agent": None,
            "agents": {
                "data_agent": "pending",
                "ml_strategy_agent": "pending",
                "training_agent": "pending",
                "final_model_selection": "pending",
            },
            "results": {},
            "final_model": None,
            "mock_agents": [],
            "error": None,
        }
        self.workflows[workflow_id] = workflow
        self.repo.save_workflow(workflow)
        return workflow

    def get_workflow_status(self, workflow_id: str):
        wf = self.workflows.get(workflow_id)
        if wf is not None:
            return wf
        return self.repo.get_workflow(workflow_id)  # e.g. after a restart

    def _step(self, wf, key, fn, *args):
        wf["current_agent"] = key
        wf["agents"][key] = "running"
        self.repo.save_workflow(wf)
        try:
            output = fn(*args)
        except Exception:
            wf["agents"][key] = "failed"
            self.repo.save_workflow(wf)
            raise
        wf["results"][key] = output
        if isinstance(output, dict) and output.get("is_mock"):
            wf["mock_agents"].append(key)
        wf["agents"][key] = "completed"
        self.repo.save_workflow(wf)
        return output

    def run_workflow(self, workflow_id: str):
        wf = self.workflows[workflow_id]
        wf["status"] = "running"
        self.repo.save_workflow(wf)
        try:
            data_out = self._step(wf, "data_agent", self.data_agent,
                                  wf["dataset_path"], wf["target_column"],
                                  wf["problem_statement"])
            plan = self._step(wf, "ml_strategy_agent", self.strategy_agent,
                              wf["problem_statement"], wf["target_column"], data_out)
            train_out = self._step(wf, "training_agent", self.training_agent,
                                   data_out, plan)

            wf["current_agent"] = "final_model_selection"
            wf["agents"]["final_model_selection"] = "running"
            self.repo.save_workflow(wf)
            best = select_best_model(train_out.get("results", []),
                                     plan["primary_metric"],
                                     plan.get("metric_direction"))
            if best is None:
                wf["agents"]["final_model_selection"] = "failed"
                raise ValueError("No model had a valid value for the primary metric")
            wf["final_model"] = best
            wf["agents"]["final_model_selection"] = "completed"
            wf["current_agent"] = None
            wf["status"] = "completed"
        except Exception as e:
            wf["status"] = "failed"
            wf["error"] = str(e)
        self.repo.save_workflow(wf)