EXPECTED_COLUMNS = [
    "address",
    "is_contract",
    "is_exchange",
    "name",
    "supply_percentage",
    "token_amount",
]


def normalize_headers(headers: list[str]) -> list[str]:
    """Trim whitespace and lowercase column names."""

    return [header.strip().lower() for header in headers]


def normalize_rows(rows: list[dict]) -> list[dict]:
    """Normalize row values and retain canonical output columns."""

    normalized_rows = []

    for row in rows:
        # Trim whitespace from string values.
        normalized_row = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in row.items()
        }

        # Convert boolean strings to Python bool values.
        for column in ("is_contract", "is_exchange"):
            value = normalized_row.get(column)

            if isinstance(value, str):
                normalized_value = value.lower()

                if normalized_value in {"true", "false"}:
                    normalized_row[column] = (
                        normalized_value == "true"
                    )

        # Convert numeric strings to floats.
        for column in ("supply_percentage", "token_amount"):
            value = normalized_row.get(column)

            if isinstance(value, str):
                try:
                    normalized_row[column] = float(value)
                except ValueError:
                    # Leave invalid values unchanged for validation.
                    pass

        # Exclude "type" and all other noncanonical columns.
        normalized_row = {
            column: normalized_row[column]
            for column in EXPECTED_COLUMNS
            if column in normalized_row
        }

        normalized_rows.append(normalized_row)

    return normalized_rows