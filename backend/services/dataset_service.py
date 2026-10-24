import csv
import io
import uuid
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _detect_delimiter(header_line: str) -> str:
    candidates = [",", ";", "\t", "|"]
    counts = {d: header_line.count(d) for d in candidates}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def save_dataset(file: UploadFile):

    safe_name = Path(file.filename or "").name
    if not safe_name.lower().endswith(".csv"):
        raise ValueError("Only CSV files are allowed")

    raw = file.file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("File is not a readable UTF-8 CSV")

    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise ValueError("CSV file is empty or has no header")

    delimiter = _detect_delimiter(lines[0])

    dataset_id = "DS-" + uuid.uuid4().hex[:8].upper()
    file_path = UPLOAD_DIR / f"{dataset_id}_{safe_name}"

    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))

    # Excel re-save case: each row became ONE field holding the whole line
    if rows and len(rows[0]) == 1 and delimiter in rows[0][0]:
        rows = [
            next(csv.reader([r[0]], delimiter=delimiter))
            for r in rows if r
        ]

    # Always store a standard comma-separated file
    with open(file_path, "w", encoding="utf-8", newline="") as out:
        csv.writer(out).writerows(rows)

    with open(file_path, newline="", encoding="utf-8") as f:
        columns = [c.strip() for c in next(csv.reader(f), [])]

    if len(columns) < 2:
        file_path.unlink(missing_ok=True)
        raise ValueError("Could not detect columns. Check the file's delimiter.")

    return {
        "dataset_id": dataset_id,
        "filename": safe_name,
        "dataset_path": str(file_path),
        "columns": columns,
        "detected_delimiter": delimiter,
        "status": "uploaded",
    }