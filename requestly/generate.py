"""Generate this Requestly local project from server/main.py and ai/main.py.

    python requestly/generate.py            # add endpoints that appeared; leave existing ones alone
    python requestly/generate.py --force    # rewrite every request from the spec

Each tier gets its own folder in the one collection — `server/<tag>/…` and `ai/<tag>/…` —
so both share the collection's variables, including the token Login fills in.

Requestly's desktop app owns this folder once you open it, so the default run is additive:
a request you have customised in the app is never overwritten, and entity UUIDs are reused
so regenerating produces a readable git diff rather than a churn of new ids.

On-disk format per Requestly's own AGENTS.md: every request directory needs all five
__*.json files or the app hides it as corrupted.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

COLLECTION = "JobPilot API"
SCHEMA = "https://assets.requestly.com/local/v1.15.0"
METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


@dataclass(frozen=True)
class Tier:
    name: str
    url_variable: str
    base_url: str
    public_paths: frozenset[str]


TIERS = (
    # NFR-4: both tiers bind loopback only.
    Tier(
        name="server",
        url_variable="base_url",
        base_url="http://127.0.0.1:8000",
        # Every route is behind a bearer token except these: the server guards the rest
        # with CurrentUser / Depends(verify_token), which is a plain dependency rather than
        # an OpenAPI security scheme — so the spec cannot tell us and this list must.
        public_paths=frozenset(
            {"/health", "/api/account/signup", "/api/account/login", "/api/account/refresh"}
        ),
    ),
    Tier(
        name="ai",
        url_variable="ai_base_url",
        base_url="http://127.0.0.1:8001",
        public_paths=frozenset({"/health"}),
    ),
)

# Filled in by the login request, then sent by every other one.
TOKEN_VARIABLE = "access_token"
AUTH_HEADER = {
    "key": "Authorization",
    "value": "Bearer {{" + TOKEN_VARIABLE + "}}",
    "isEnabled": True,
}


# ---------------------------------------------------------------- the spec


SPEC_SCRIPT = "import json, main; print(json.dumps(main.create_app().openapi()))"


def build_spec(tier: Tier) -> dict[str, Any]:
    """Both tiers name their app module `main` and need their own dependencies, so each
    spec is read in a subprocess on that tier's venv rather than imported here."""
    directory = REPO / tier.name
    interpreter = directory / ".venv" / "bin" / "python"
    if not interpreter.exists():
        raise SystemExit(f"{tier.name} dependencies missing and no venv at {interpreter}")
    output = subprocess.run(
        [str(interpreter), "-c", SPEC_SCRIPT],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    spec = json.loads(output)
    spec["servers"] = [{"url": tier.base_url, "description": f"local — {tier.name}/main.py"}]
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
        return schema.get("minimum", 0)
    if kind == "boolean":
        return False
    return "string"


def _is_file(schema: dict[str, Any]) -> bool:
    # OpenAPI 3.1 (what FastAPI emits) says contentMediaType; 3.0 said format: binary.
    if schema.get("contentMediaType") or schema.get("format") == "binary":
        return True
    for key in ("anyOf", "oneOf", "allOf"):
        if any(_is_file(variant) for variant in schema.get(key, [])):
            return True
    return False


def form_rows_for(schema: dict[str, Any], schemas: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per multipart field. FastAPI renders UploadFile as a binary string,
    which is how a file part is told apart from a text one."""
    if "$ref" in schema:
        schema = schemas.get(schema["$ref"].rsplit("/", 1)[-1], {})

    required = set(schema.get("required", []))
    rows: list[dict[str, Any]] = []
    for index, (name, sub) in enumerate(schema.get("properties", {}).items(), start=1):
        file_part = _is_file(sub)
        default = sub.get("default")
        rows.append(
            {
                "id": index,
                "key": name,
                # A file has to be picked in the app; a text part can carry its default.
                "value": "" if file_part or default is None else str(default),
                "isEnabled": name in required or (not file_part and default is not None),
                "description": sub.get("description", ""),
                "type": "file" if file_part else "text",
                "contentType": "",
            }
        )
    return rows


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
    body: tuple[str, Any] | None,
    needs_auth: bool = True,
) -> None:
    """`body` is (kind, payload): ("json", example) or ("multipart/form-data", rows)."""
    path.mkdir(parents=True, exist_ok=True)
    kind = body[0] if body else "none"

    def headers(*rows: dict[str, Any]) -> list[dict[str, Any]]:
        out = [dict(row) for row in rows]
        if needs_auth:
            out.append(dict(AUTH_HEADER))
        for index, row in enumerate(out):
            row["id"] = index
        return out

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
            "contentType": kind,
        },
    )

    if body is None:
        _write(path / "__body.json", {"$schema": f"{SCHEMA}/body.json", "contentType": "none"})
        _write(path / "__headers.json", headers())
    elif kind == "multipart/form-data":
        _write(
            path / "__body.json",
            {
                "$schema": f"{SCHEMA}/body.json",
                "contentType": "multipart/form-data",
                "formData": body[1],
            },
        )
        # The boundary is the transport's to set — a hand-written header breaks it,
        # so multipart gets the auth header and no Content-Type.
        _write(path / "__headers.json", headers())
    else:
        _write(
            path / "__body.json",
            {
                "$schema": f"{SCHEMA}/body.json",
                "contentType": "json",
                "raw": json.dumps(body[1], indent=2),
                "rawContentType": "application/json",
            },
        )
        _write(
            path / "__headers.json",
            headers({"key": "Content-Type", "value": "application/json", "isEnabled": True}),
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


def _add_missing_variables(path: Path, variables: dict[str, Any], *, nested: bool) -> None:
    """Variables are yours to edit in the app: only ones the file lacks are added, so a
    value you changed — or the token Login stored — survives every re-run. An environment
    keeps them under `variables`; a collection's file is the mapping itself."""
    document = json.loads(path.read_text())
    existing = document["variables"] if nested else document
    for name, value in variables.items():
        if name not in existing:
            rank = f"a{len([key for key in existing if key != '$schema'])}"
            existing[name] = _variable(value, rank)
    _write(path, document)


def build_project(spec: dict[str, Any], tier: Tier, rank: str, force: bool) -> tuple[int, int]:
    schemas = spec.get("components", {}).get("schemas", {})
    tier_folder = ROOT / "apis" / COLLECTION / tier.name
    write_collection(tier_folder, rank)

    created = skipped = 0
    for folder_rank, (tag, operations) in enumerate(
        sorted(operations_by_tag(spec).items())
    ):
        folder = tier_folder / tag
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

            content = operation.get("requestBody", {}).get("content", {})
            body: tuple[str, Any] | None = None
            if "application/json" in content:
                body = ("json", example_for(content["application/json"]["schema"], schemas, frozenset()))
            elif "multipart/form-data" in content:
                body = (
                    "multipart/form-data",
                    form_rows_for(content["multipart/form-data"]["schema"], schemas),
                )

            # Requestly resolves path variables with the same {{...}} syntax as any variable.
            url = "{{" + tier.url_variable + "}}" + path.replace("{", "{{").replace("}", "}}")
            write_request(
                request,
                f"a{rank}",
                method,
                url,
                query,
                variables,
                body,
                needs_auth=path not in tier.public_paths,
            )
            created += 1

    return created, skipped


def write_project_config() -> None:
    _write(
        ROOT / "__requestly.json",
        {"version": "1.2.0", "include": ["**"], "exclude": []},
    )

    collection = ROOT / "apis" / COLLECTION
    write_collection(collection, "a0")
    base_urls = {tier.url_variable: tier.base_url for tier in TIERS}

    variables = collection / "__variables.json"
    if not variables.exists():
        _write(variables, {"$schema": f"{SCHEMA}/collection-variables.json"})
    _add_missing_variables(variables, base_urls, nested=False)

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
                "variables": {},
            },
        )
    _add_missing_variables(named_env, base_urls, nested=True)


def main() -> None:
    force = "--force" in sys.argv
    write_project_config()

    for index, tier in enumerate(TIERS):
        spec = build_spec(tier)
        _write(ROOT / f"openapi.{tier.name}.json", spec)
        created, skipped = build_project(spec, tier, f"a{index}", force)
        print(f"{tier.name}: {created} request(s) written, {skipped} left untouched")

    if not force:
        print("run with --force to rewrite existing requests from the spec")


if __name__ == "__main__":
    main()
