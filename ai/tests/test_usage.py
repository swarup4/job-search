"""Writing a run's model calls to the usage log: batched, and never able to fail the
run it describes."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from api import usage as usage_api
from config.llm import Call, Usage
from mcp_servers.jobpilot_api.client import JobPilotApiError


def usage_of(calls: int) -> Usage:
    usage = Usage()
    for number in range(calls):
        usage.add(
            Call(
                step="Comparison",
                model="localhost/qwen",
                version=1,
                attempt=1,
                prompt_tokens=100 + number,
                cached_tokens=0,
                completion_tokens=20,
                elapsed_ms=900,
            ),
            system_tokens=10,
        )
    return usage


class Recorder:
    def __init__(self, failure: Exception | None = None) -> None:
        self.batches: list[tuple[str, str | None, list[dict[str, Any]]]] = []
        self.failure = failure

    async def record_usage(
        self, run_kind: str, run_id: str | None, calls: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if self.failure is not None:
            raise self.failure
        self.batches.append((run_kind, run_id, calls))
        return {"stored": len(calls)}


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    fake = Recorder()
    monkeypatch.setattr(usage_api, "client", fake)
    return fake


async def test_a_runs_calls_are_posted_with_its_kind_and_id(recorder: Recorder) -> None:
    await usage_api.store_usage("scoring", "run-1", usage_of(3))

    [(kind, run_id, calls)] = recorder.batches
    assert (kind, run_id) == ("scoring", "run-1")
    assert [call["promptTokens"] for call in calls] == [100, 101, 102]
    assert calls[0]["step"] == "Comparison" and calls[0]["promptVersion"] == 1


async def test_a_run_that_called_no_model_posts_nothing(recorder: Recorder) -> None:
    await usage_api.store_usage("analysis", "run-1", Usage())

    assert recorder.batches == []


async def test_a_long_run_is_posted_in_batches(recorder: Recorder) -> None:
    await usage_api.store_usage("scoring", "run-1", usage_of(usage_api.BATCH + 7))

    assert [len(calls) for _, _, calls in recorder.batches] == [usage_api.BATCH, 7]


@pytest.mark.parametrize(
    "failure",
    [JobPilotApiError(401, "expired"), httpx.ConnectError("refused")],
    ids=["expired-token", "server-down"],
)
async def test_a_usage_record_that_cannot_be_written_does_not_raise(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """The run's results are already stored; losing its usage must not fail it."""
    monkeypatch.setattr(usage_api, "client", Recorder(failure))

    await usage_api.store_usage("scoring", "run-1", usage_of(2))
