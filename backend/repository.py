import copy
from datetime import datetime, timezone

from backend.database import get_db


def _now():
    return datetime.now(timezone.utc)


class Repository:

    def save_workflow(self, wf: dict):
        snapshot = copy.deepcopy(wf)  # so later in-memory edits don't alias
        snapshot["updated_at"] = _now()
        get_db().workflows.update_one(
            {"_id": wf["workflow_id"]},
            {"$set": snapshot, "$setOnInsert": {"created_at": _now()}},
            upsert=True,
        )

    def get_workflow(self, workflow_id: str):
        return get_db().workflows.find_one(
            {"_id": workflow_id}, {"_id": 0, "created_at": 0, "updated_at": 0}
        )

    def list_workflows(self):
        cursor = get_db().workflows.find(
            {}, {"_id": 0, "updated_at": 0}
        ).sort("created_at", -1)
        return list(cursor)

    def mark_interrupted(self):
        """Workflows still 'running'/'created' at startup were cut off by a restart."""
        count = 0
        for doc in get_db().workflows.find({"status": {"$in": ["running", "created"]}}):
            agents = {k: ("failed" if v == "running" else v)
                      for k, v in doc.get("agents", {}).items()}
            get_db().workflows.update_one(
                {"_id": doc["_id"]},
                {"$set": {"status": "failed", "agents": agents,
                          "current_agent": None,
                          "error": "Interrupted by server restart"}},
            )
            count += 1
        return count

    def save_dataset(self, info: dict):
        doc = {**info, "created_at": _now()}
        get_db().datasets.replace_one({"_id": info["dataset_id"]}, doc, upsert=True)