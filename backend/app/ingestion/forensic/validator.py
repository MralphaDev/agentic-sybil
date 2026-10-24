import math


REQUIRED_COLUMNS = {
    "address",
    "is_contract",
    "is_exchange",
    "supply_percentage",
    "token_amount",
}


def validate_headers(headers: list[str]) -> None:
    # Check for missing or duplicate headers
    if not headers:
        raise ValueError("CSV header is missing.")

    if len(headers) != len(set(headers)):
        raise ValueError("CSV contains duplicate columns.")

    missing = REQUIRED_COLUMNS - set(headers)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def validate_rows(rows: list[dict]) -> None:
    # Ensure at least one data row exists
    if not rows:
        raise ValueError("CSV contains no data rows.")

    for row_number, row in enumerate(rows, start=2):
        # Validate required address
        if not row.get("address"):
            raise ValueError(
                f"Row {row_number}: address cannot be empty."
            )

        # Validate boolean fields
        for column in ("is_contract", "is_exchange"):
            if not isinstance(row.get(column), bool):
                raise ValueError(
                    f"Row {row_number}: '{column}' must be true or false."
                )

        # Validate numeric fields
        for column in ("supply_percentage", "token_amount"):
            value = row.get(column)

            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(
                    f"Row {row_number}: '{column}' must be numeric."
                )

            if not math.isfinite(value):
                raise ValueError(
                    f"Row {row_number}: '{column}' must be finite."
                )