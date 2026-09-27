import uuid
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_dataset(file: UploadFile):

    if not file.filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are allowed")

    dataset_id = "DS-" + uuid.uuid4().hex[:8].upper()

    file_path = UPLOAD_DIR / f"{dataset_id}_{file.filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "dataset_path": str(file_path),
        "status": "uploaded"
    }