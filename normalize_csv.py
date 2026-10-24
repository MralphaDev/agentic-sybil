from pathlib import Path

import pandas as pd


# Directory containing this script.
DIRECTORY = Path(__file__).resolve().parent

# Canonical output schema.
EXPECTED_COLUMNS = [
    "address",
    "is_contract",
    "is_exchange",
    "name",
    "supply_percentage",
    "token_amount",
]

INPUT_PREFIX = "bubblemap-addresses-export"
OUTPUT_FILENAME = "normalized.csv"


def normalize_csv() -> None:
    """Find, filter, and normalize a Bubblemap CSV in this directory."""

    input_files = sorted(
        path
        for path in DIRECTORY.glob(f"{INPUT_PREFIX}*.csv")
        if path.is_file()
    )

    if not input_files:
        raise FileNotFoundError(
            f"No CSV file starting with '{INPUT_PREFIX}' "
            f"found in {DIRECTORY}"
        )

    if len(input_files) > 1:
        files = "\n".join(f"  - {path.name}" for path in input_files)
        raise ValueError(
            f"Found multiple matching CSV files:\n{files}\n"
            "Please keep only one input file in the directory."
        )

    input_path = input_files[0]
    output_path = DIRECTORY / OUTPUT_FILENAME

    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must be different.")

    # Read all values as strings to preserve addresses and formatting.
    df = pd.read_csv(input_path, dtype=str)

    # Remove accidental whitespace around column names.
    df.columns = df.columns.str.strip()

    # Filter holder rows before removing the type column.
    if "type" not in df.columns:
        raise ValueError('CSV is missing required column: "type"')

    is_not_time = df["type"].str.strip().str.lower() != "time"
    df = df[is_not_time]

    input_rows = len(df)

    # Validate the required output columns.
    missing_columns = [
        column for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "CSV is missing required columns: "
            + ", ".join(missing_columns)
        )

    # Keep only the required columns, excluding "type".
    df = df[EXPECTED_COLUMNS]

    # Write directly to the same directory as this script.
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Input file:   {input_path.name}")
    print(f"Input rows:   {input_rows}")
    print(f"Output rows:  {len(df)}")
    print(f"Output file:  {output_path}")
    print("Normalization completed.")


if __name__ == "__main__":
    normalize_csv()
