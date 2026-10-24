
import csv
import io

from app.ingestion.forensic.normalizer import (
    normalize_headers,
    normalize_rows,
)
from app.ingestion.forensic.validator import (
    validate_headers,
    validate_rows,
)


def clean_csv(content: bytes) -> list[dict]:
    """Parse, filter, normalize, and validate a forensic CSV."""

    # 1. Validate file content.
    if not content or not content.strip():
        raise ValueError("CSV file is empty.")

    # 2. Decode CSV content.
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding.") from exc

    # 3. Parse CSV.
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV header is missing.")

    # 4. Normalize headers.
    headers = normalize_headers(list(reader.fieldnames))
    reader.fieldnames = headers

    # 5. Validate headers.
    if "type" not in headers:
        raise ValueError('CSV is missing required column: "type"')

    validate_headers(headers)

    # 6. Filter out rows where type is "time".
    rows = [
        row
        for row in reader
        if (row.get("type") or "").strip().lower() != "time"
    ]

    # 7. Normalize row values and retain canonical output columns.
    rows = normalize_rows(rows)

    # 8. Validate normalized row values.
    validate_rows(rows)

    # 9. Return cleaned records.
    return rows
