import csv
import json
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import Tuple, Union

import pandas as pd
from agentflow_data_agent.core.handoff_schemas import MemoryMetrics


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitizes column names to eliminate special characters that crash gradient tree boosters."""
    clean_cols = []
    for i, col in enumerate(df.columns):
        c = str(col).strip()
        c = re.sub(r"[\[\]<>,:\"\'\s\+\-\/\\]+", "_", c).strip("_")
        if not c or c[0].isdigit():
            c = f"col_{c}" if c else f"col_{i}"
        clean_cols.append(c)
    df.columns = clean_cols
    return df


def load_dataset(file_path: Union[str, Path], output_dir: Union[str, Path] = "./artifacts") -> pd.DataFrame:
    path = Path(file_path).resolve()
    out_path = Path(output_dir).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".zip":
        with zipfile.ZipFile(path, "r") as z:
            candidates = [
                f for f in z.namelist()
                if not f.startswith("__MACOSX")
                and Path(f).suffix.lower() in {".csv", ".tsv", ".parquet", ".xlsx", ".json", ".feather"}
            ]
            if not candidates:
                raise ValueError(f"No supported tabular dataset found inside ZIP archive: {path}")

            best_member = max(candidates, key=lambda x: z.getinfo(x).file_size)
            extract_path = (out_path / Path(best_member).name).resolve()
            if not str(extract_path).startswith(str(out_path)):
                raise SecurityError("Zip-Slip path traversal attempt detected.")

            with z.open(best_member) as src, open(extract_path, "wb") as dst:
                dst.write(src.read())
            return load_dataset(extract_path, output_dir=output_dir)

    if suffix in {".csv", ".tsv", ".txt", ".data"}:
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc, errors="replace") as f:
                    sample = f.read(16384)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
                    sep = dialect.delimiter
                except Exception:
                    sep = "\t" if suffix == ".tsv" else ","

                df = pd.read_csv(path, sep=sep, encoding=enc, low_memory=False)
                if df.shape[1] == 1 and ";" in str(df.columns[0]):
                    df = pd.read_csv(path, sep=";", encoding=enc, low_memory=False)
                return clean_column_names(df)
            except Exception:
                continue
        raise ValueError(f"Failed to parse delimited file: {path}")

    if suffix == ".parquet":
        try:
            return clean_column_names(pd.read_parquet(path))
        except Exception:
            raise ValueError(f"Unable to read Parquet file. Ensure pyarrow or fastparquet is installed: {path}")

    if suffix in {".xlsx", ".xls"}:
        return clean_column_names(pd.read_excel(path))

    if suffix == ".json":
        try:
            return clean_column_names(pd.read_json(path))
        except Exception:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return clean_column_names(pd.json_normalize(data))

    if suffix == ".feather":
        return clean_column_names(pd.read_feather(path))

    if suffix in {".db", ".sqlite", ".sqlite3"}:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if not tables:
            conn.close()
            raise ValueError(f"No tables found in SQLite database: {path}")
        first_table = tables[0][0]
        if not re.match(r"^[A-Za-z0-9_]+$", first_table):
            conn.close()
            raise ValueError(f"Invalid table name detected: {first_table}")
        df = pd.read_sql_query(f"SELECT * FROM \"{first_table}\"", conn)
        conn.close()
        return clean_column_names(df)

    raise ValueError(f"Unsupported dataset format: {suffix}")


def optimize_memory(df: pd.DataFrame) -> Tuple[pd.DataFrame, MemoryMetrics]:
    """Downcasts numeric types to reduce RAM footprint by up to 70%."""
    init_mem = df.memory_usage(deep=True).sum() / (1024 ** 2)
    df_opt = df.copy()

    for col in df_opt.columns:
        col_type = df_opt[col].dtype
        if pd.api.types.is_float_dtype(col_type):
            df_opt[col] = pd.to_numeric(df_opt[col], downcast="float")
        elif pd.api.types.is_integer_dtype(col_type):
            df_opt[col] = pd.to_numeric(df_opt[col], downcast="integer")

    opt_mem = df_opt.memory_usage(deep=True).sum() / (1024 ** 2)
    red_pct = max(0.0, (init_mem - opt_mem) / max(init_mem, 1e-6) * 100.0)
    return df_opt, MemoryMetrics(
        initial_memory_mb=round(float(init_mem), 3),
        optimized_memory_mb=round(float(opt_mem), 3),
        memory_reduction_pct=round(float(red_pct), 2),
    )
