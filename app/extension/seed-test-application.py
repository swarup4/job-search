"""Stages one application against a real job posting so the extension has
something to fill. Local dev only — it writes a throwaway job to your database
and touches nothing else."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000/api"


def call(path: str, payload: dict | None = None, token: str | None = None, method: str = "GET") -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(f"{API}{path}", data=body, method="POST" if body else method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read() or "{}")
    except urllib.error.HTTPError as error:
        sys.exit(f"{path} -> {error.code}: {error.read().decode()}")


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("usage: seed-test-application.py <email> <password> <apply-url>")

    email, password, apply_url = sys.argv[1], sys.argv[2], sys.argv[3]

    token = call("/account/login", {"email": email, "password": password})["accessToken"]

    profile = call("/profile/getProfile", token=token)
    details = profile.get("profile") or {}
    if not details.get("phone") and not details.get("location"):
        print("! Your profile has no phone or location — the fill will be thin.")
        print("  Add them in the dashboard under My Details first.")

    ats = "other"
    for name in ("lever", "greenhouse", "workday"):
        if name in apply_url:
            ats = name
    if "linkedin.com" in apply_url:
        ats = "linkedin_easy_apply"

    job = call(
        "/job",
        {
            "title": "Extension smoke test",
            "company": {"name": "Test Co"},
            "location": "Remote",
            "source": "career_page",
            "sourceUrl": apply_url,
            "jdText": "Seeded by seed-test-application.py to exercise the extension.",
        },
        token=token,
    )

    application = call(
        "/application",
        {
            "jobId": job["id"],
            # Not validated on stage — the tailoring pipeline that would produce a
            # real one is Phase 5.
            "resumeId": job["id"],
            "texPath": "templates/base_resume.tex",
            "ats": ats,
            "applyUrl": apply_url,
        },
        token=token,
    )

    print(f"\nStaged application {application['id']} ({ats})")
    print(f"Now open {apply_url} in Chrome and click the JobPilot icon.")


if __name__ == "__main__":
    main()
