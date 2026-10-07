"""Local example: copy into Test code before using. Does not run on opening."""
import csv
from pathlib import Path

def inspect_csv(path):
    """Validate the sample schema; returns observations without inventing measurements."""
    with Path(path).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or set(rows[0]) != {"case", "input", "expected"}:
        raise ValueError("Expected non-empty CSV with case,input,expected columns")
    return {"rows": len(rows), "schema_checked": True}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path of your explicitly chosen CSV")
    args = parser.parse_args()
    print(inspect_csv(args.input))
