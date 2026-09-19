import hashlib

from beanie import PydanticObjectId

from config.errors import NotFound
from modules.capture.models import Capture, CaptureCreate, CaptureCreated, CaptureStatus


class CaptureNotFound(NotFound):
    def __init__(self, capture_id: PydanticObjectId) -> None:
        super().__init__(f"capture {capture_id} not found")


def compute_content_hash(payload: CaptureCreate) -> str:
    """URL and text together, not text alone: the same boilerplate shell served by
    two postings is two captures, and a page recaptured after it changed is a new
    row rather than a silent overwrite. The fragment is dropped — `#apply` is the
    same page."""
    seed = f"{payload.url.split('#')[0]}|{payload.markdown}"
    return hashlib.sha256(seed.encode()).hexdigest()


async def create_capture(user_id: PydanticObjectId, payload: CaptureCreate) -> CaptureCreated:
    contentHash = payload.contentHash or compute_content_hash(payload)

    existing = await Capture.find_one(Capture.userId == user_id, Capture.contentHash == contentHash)
    if existing is not None:
        # Recapturing an unchanged page is not an error — the extension says
        # "already captured" and the user carries on.
        return CaptureCreated(id=existing.id, duplicate=True)

    capture = Capture(
        **payload.model_dump(exclude={"contentHash"}),
        userId=user_id,
        contentHash=contentHash,
        markdownLength=len(payload.markdown),
    )
    await capture.insert()
    return CaptureCreated(id=capture.id, duplicate=False)


async def get_capture(user_id: PydanticObjectId, capture_id: PydanticObjectId) -> Capture:
    """Another user's capture id is "not found" rather than "forbidden" — the caller
    has no business learning that it exists."""
    capture = await Capture.find_one(Capture.id == capture_id, Capture.userId == user_id)
    if capture is None:
        raise CaptureNotFound(capture_id)
    return capture


async def list_captures(
    user_id: PydanticObjectId,
    capture_status: CaptureStatus | None = None,
    url: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> list[Capture]:
    query: dict[str, object] = {"userId": user_id}
    if capture_status is not None:
        query["status"] = capture_status
    if url:
        query["url"] = url

    return await Capture.find(query).sort(-Capture.capturedAt).skip(skip).limit(limit).to_list()
