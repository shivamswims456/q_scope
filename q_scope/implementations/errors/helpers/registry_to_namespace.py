import json
from pathlib import Path
from collections import defaultdict

SRC = Path("errors/oauth_errors.json")
DST = Path("errors")

def constant_name(key: str) -> str:
    return key.upper().replace(".", "_")

def main():
    data = json.loads(SRC.read_text())
    errors = data["errors"]

    buckets = defaultdict(dict)

    for code in errors:
        parts = code.split(".")
        if len(parts) == 2:
            bucket = "oauth"
            name = parts[1]
        else:
            bucket = parts[1]
            name = "_".join(parts[2:])

        buckets[bucket][name] = code

    for bucket, items in buckets.items():
        class_name = f"{bucket.capitalize()}Errors"
        path = DST / f"{bucket}.py"

        lines = [
            "# AUTO-GENERATED FILE — DO NOT EDIT",
            "# Source: oauth_errors.json",
            "",
            f"class {class_name}:",
        ]

        for name, code in sorted(items.items()):
            lines.append(f"    {name.upper()} = \"{code}\"")

        path.write_text("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()

