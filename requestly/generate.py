"""Generate this Requestly local project from server/main.py.

    python requestly/generate.py            # add endpoints that appeared; leave existing ones alone
    python requestly/generate.py --force    # rewrite every request from the spec

Requestly's desktop app owns this folder once you open it, so the default run is additive:
a request you have customised in the app is never overwritten, and entity UUIDs are reused
so regenerating produces a readable git diff rather than a churn of new ids.

On-disk format per Requestly's own AGENTS.md: every request directory needs all five
__*.json files or the app hides it as corrupted.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SERVER = REPO / "server"

COLLECTION = "JobPilot API"
BASE_URL = "http://127.0.0.1:8000"  # NFR-4: the API binds loopback only
SCHEMA = "https://assets.requestly.com/local/v1.15.0"
METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


# ---------------------------------------------------------------- the spec


def _reexec_in_server_venv() -> None:
    """The spec comes from importing the app, so it needs server's dependencies."""
    interpreter = SERVER / ".venv" / "bin" / "python"
    if not interpreter.exists():
        raise SystemExit(f"server dependencies missing and no venv at {interpreter}")
    os.execv(
        str(interpreter),
        [str(interpreter), str(Path(__file__).resolve()), *sys.argv[1:]],
    )


def build_spec() -> dict[str, Any]:
    sys.path.insert(0, str(SERVER))
    try:
        from main import create_app
    except ModuleNotFoundError:
        _reexec_in_server_venv()

    spec = create_app().openapi()
    spec["servers"] = [{"url": BASE_URL, "description": "local — server/main.py"}]
    # FastAPI documents a 200 and a 422 for every route; Requestly turns each into a
    # saved example under the request, which is noise in a client collection.
    for operations in spec["paths"].values():
        for method in METHODS:
            operations.get(method, {}).pop("responses", None)
    _prune_schemas(spec)
    return spec


def _refs(node: Any) -> set[str]:
    if isinstance(node, dict):
        found: set[str] = set()
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.add(value.rsplit("/", 1)[-1])
            else:
                found |= _refs(value)
        return found
    if isinstance(node, list):
        return set().union(*(_refs(item) for item in node)) if node else set()
    return set()


def _prune_schemas(spec: dict[str, Any]) -> None:
    """Drop the response-only models stripping `responses` just orphaned."""
    schemas = spec.get("components", {}).get("schemas", {})
    reachable = _refs(spec["paths"])
    while True:
        nested = _refs([schemas.get(name, {}) for name in reachable])
        if nested <= reachable:
            break
        reachable |= nested
    for name in set(schemas) - reachable:
        del schemas[name]


# ------------------------------------------------------- schema → example body


def example_for(
    schema: dict[str, Any], schemas: dict[str, Any], seen: frozenset[str]
) -> Any:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name in seen:  # self-referential model — stop rather than recurse forever
            return {}
        return example_for(schemas.get(name, {}), schemas, seen | {name})

    if "default" in schema:
        return schema["default"]
    if "example" in schema:
        return schema["example"]
    if "enum" in schema:
        return schema["enum"][0]

    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            variants = [v for v in schema[key] if v.get("type") != "null"]
            return example_for(variants[0], schemas, seen) if variants else None

    kind = schema.get("type")
    if kind == "object":
        properties = schema.get("properties", {})
        return {
            name: example_for(sub, schemas, seen) for name, sub in properties.items()
        }
    if kind == "array":
        return [example_for(schema.get("items", {}), schemas, seen)]
    if kind == "integer" or kind == "number":
        return 0
    if kind == "boolean":
        return False
    return "string"


# ------------------------------------------------------------ file writing


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _keep_id(path: Path) -> str:
    """Reuse the UUID already on disk so regenerating doesn't reshuffle the index."""
    metadata = path / "__metadata.json"
    if metadata.exists():
        return json.loads(metadata.read_text())["id"]
    return str(uuid.uuid4())


def write_collection(path: Path, rank: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _write(
        path / "__metadata.json",
        {
            "$schema": f"{SCHEMA}/metadata.json",
            "type": "collection",
            "id": _keep_id(path),
            "rank": rank,
        },
    )


def write_request(
    path: Path,
    rank: str,
    method: str,
    url: str,
    query_params: list[dict[str, Any]],
    path_variables: list[dict[str, Any]],
    body: Any,
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    content_type = "json" if body is not None else "none"

    _write(
        path / "__metadata.json",
        {
            "$schema": f"{SCHEMA}/metadata.json",
            "type": "api",
            "entryType": "http",
            "id": _keep_id(path),
            "rank": rank,
            "url": url,
            "method": method.upper(),
            "contentType": content_type,
        },
    )

    if body is None:
        _write(
            path / "__body.json",
            {"$schema": f"{SCHEMA}/body.json", "contentType": "none"},
        )
        _write(path / "__headers.json", [])
    else:
        _write(
            path / "__body.json",
            {
                "$schema": f"{SCHEMA}/body.json",
                "contentType": "json",
                "raw": json.dumps(body, indent=2),
                "rawContentType": "application/json",
            },
        )
        _write(
            path / "__headers.json",
            [
                {
                    "id": 0,
                    "key": "Content-Type",
                    "value": "application/json",
                    "isEnabled": True,
                }
            ],
        )

    _write(path / "__query-params.json", query_params)
    _write(path / "__path-variables.json", path_variables)


def _variable(value: str, rank: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "id": str(uuid.uuid4()),
        "syncValue": value,
        "type": "string",
        "isEnabled": True,
        "rank": rank,
        "createdAt": now,
        "updatedAt": now,
        "createdBy": None,
        "updatedBy": None,
    }


# ------------------------------------------------------------ the project


def operations_by_tag(
    spec: dict[str, Any],
) -> dict[str, list[tuple[str, str, dict[str, Any]]]]:
    """Group operations into one folder per server module, the way the repo is laid out."""
    grouped: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    for path, operations in spec["paths"].items():
        for method in METHODS:
            operation = operations.get(method)
            if operation is None:
                continue
            # /health carries no tag; fall back to its own path segment.
            tag = operation.get("tags", [path.strip("/").split("/")[0]])[0]
            grouped.setdefault(tag, []).append((path, method, operation))
    return grouped


def build_project(spec: dict[str, Any], force: bool) -> tuple[int, int]:
    schemas = spec.get("components", {}).get("schemas", {})
    collection = ROOT / "apis" / COLLECTION

    write_collection(collection, "a0")

    # Variables are yours to edit in the app — write them once, never on a re-run.
    variables = collection / "__variables.json"
    if not variables.exists():
        _write(
            variables,
            {
                "$schema": f"{SCHEMA}/collection-variables.json",
                "base_url": _variable(BASE_URL, "a0"),
            },
        )

    created = skipped = 0
    for folder_rank, (tag, operations) in enumerate(
        sorted(operations_by_tag(spec).items())
    ):
        folder = collection / tag
        write_collection(folder, f"a{folder_rank}")

        for rank, (path, method, operation) in enumerate(operations):
            name = operation.get("summary") or operation["operationId"]
            request = folder / name

            if request.exists() and not force:
                skipped += 1
                continue

            parameters = operation.get("parameters", [])
            query = [
                {
                    "id": index,
                    "key": parameter["name"],
                    "value": str(parameter["schema"].get("default", "")),
                    "isEnabled": parameter.get("required", False),
                    "description": parameter.get("description", ""),
                }
                for index, parameter in enumerate(parameters)
                if parameter["in"] == "query"
            ]
            variables = [
                {
                    "key": parameter["name"],
                    "value": "",
                    "description": parameter.get("description", ""),
                }
                for parameter in parameters
                if parameter["in"] == "path"
            ]

            content = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json")
            )
            body = (
                example_for(content["schema"], schemas, frozenset())
                if content
                else None
            )

            # Requestly resolves path variables with the same {{...}} syntax as any variable.
            url = "{{base_url}}" + path.replace("{", "{{").replace("}", "}}")
            write_request(request, f"a{rank}", method, url, query, variables, body)
            created += 1

    return created, skipped


def write_project_config() -> None:
    _write(
        ROOT / "__requestly.json",
        {"version": "1.2.0", "include": ["**"], "exclude": []},
    )

    environments = ROOT / "environments"
    environments.mkdir(parents=True, exist_ok=True)

    global_env = environments / "__global.json"
    if not global_env.exists():
        _write(
            global_env,
            {
                "$schema": f"{SCHEMA}/environment.json",
                "id": str(uuid.uuid4()),
                "variables": {},
            },
        )

    named_env = environments / f"{COLLECTION}.json"
    if not named_env.exists():
        _write(
            named_env,
            {
                "$schema": f"{SCHEMA}/environment.json",
                "id": str(uuid.uuid4()),
                "variables": {"base_url": _variable(BASE_URL, "a0")},
            },
        )


def main() -> None:
    force = "--force" in sys.argv
    spec = build_spec()

    _write(ROOT / "openapi.json", spec)
    write_project_config()
    created, skipped = build_project(spec, force)

    print(f"{created} request(s) written, {skipped} left untouched")
    if skipped and not force:
        print("run with --force to rewrite them from the spec")


if __name__ == "__main__":
    main()
