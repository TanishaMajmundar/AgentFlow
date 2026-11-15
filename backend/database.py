import os
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)


def get_db():
    # DB name is read at call time so tests can point at a separate database
    return client[os.getenv("MONGODB_DB", "agentflow")]


def init_db():
    client.admin.command("ping")  # fails fast with a clear error if Mongo isn't running
    db = get_db()
    db.workflows.create_index("status")
    db.workflows.create_index("created_at")