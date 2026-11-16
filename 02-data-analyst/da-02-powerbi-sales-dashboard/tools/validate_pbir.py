"""Validate every PBIP/PBIR JSON file against Microsoft's published schemas (offline).

Usage:
    python tools/validate_pbir.py <path to a checkout of github.com/microsoft/json-schemas>
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.simplefilter("ignore", DeprecationWarning)
from jsonschema import Draft7Validator, RefResolver  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "https://developer.microsoft.com/json-schemas/"


def load_store(schemas_root: Path) -> dict[str, dict]:
    store = {}
    for path in (schemas_root / "fabric").rglob("*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        rel = path.relative_to(schemas_root).as_posix()
        store[PREFIX + rel] = doc
        store[path.as_uri()] = doc
        if isinstance(doc, dict) and isinstance(doc.get("$id"), str):
            store[doc["$id"]] = doc
    return store


def main() -> int:
    warnings.simplefilter("ignore", DeprecationWarning)
    schemas_root = Path(sys.argv[1])
    store = load_store(schemas_root)
    targets = [
        p for p in ROOT.rglob("*")
        if p.suffix in {".json", ".pbir", ".pbism", ".pbip"}
        and not {".venv", "StaticResources", "docs"} & set(p.parts)
    ]
    total = 0
    for path in sorted(targets):
        doc = json.loads(path.read_text(encoding="utf-8"))
        url = doc.get("$schema") if isinstance(doc, dict) else None
        if not url:
            continue
        schema = store[url]
        resolver = RefResolver(base_uri=url, referrer=schema, store=store)
        errors = list(Draft7Validator(schema, resolver=resolver).iter_errors(doc))
        total += len(errors)
        print(f"{'ok' if not errors else 'FAIL':5} {path.relative_to(ROOT).as_posix()}")
        for e in errors[:5]:
            print("      ->", "/".join(map(str, e.absolute_path)) or "(root)", ":", e.message[:240])
    print(f"\n{len(targets)} files checked, {total} schema errors")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
