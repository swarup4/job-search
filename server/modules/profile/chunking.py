"""Cutting a profile into retrievable units, section by section. (P6-02)

One bullet, one skill, one credential each. A single whole-profile vector averages a
career into something that matches every job weakly, and retrieval has to hand back
the span it matched so the user can see why it was returned.

These unit boundaries are the ones `NEAR_MISS_THRESHOLD` was calibrated against in
`ai/rag/embeddings.py` — the AI tier used to cut the profile up this way itself, per
job, until P6-04 gave the pieces somewhere to live. Spans go in raw, with their
context carried alongside in `sourceRef` rather than glued onto the front, so a
cosine measured against a chunk still means what it meant then.
"""

from beanie import PydanticObjectId

from modules.profile.models import UserProfile
from modules.resume_chunk import ChunkFields, ChunkSection
from modules.resume_chunk.models import MAX_CHUNK_CHARS, MIN_CHUNK_CHARS


def chunk_profile(user: UserProfile) -> list[ChunkFields]:
    """Everything in My Details, in the order the screen shows it."""
    chunks: list[ChunkFields] = []

    personal = user.profile
    if personal is not None:
        _add(chunks, ChunkSection.HEADLINE, personal.headline, "Headline")
        _add(chunks, ChunkSection.SUMMARY, personal.summary, "Summary")

    for role in user.work:
        where = f"{role.title} — {role.company}"
        _add(chunks, ChunkSection.EXPERIENCE, f"{role.title} at {role.company}", where, role.id)
        for bullet in role.bullets:
            _add(chunks, ChunkSection.EXPERIENCE, bullet, where, role.id)
        for project in role.projects:
            for bullet in project.bullets:
                _add(
                    chunks,
                    ChunkSection.PROJECT,
                    bullet,
                    f"{project.name} — {role.company}",
                    role.id,
                )

    for group in user.skill:
        for item in group.items:
            # One chunk per skill, not one per group: a group is a heading the user
            # chose, and embedding "Python, TypeScript, Go, SQL" as a unit returns
            # all four whenever a job asks for any one of them.
            _add(chunks, ChunkSection.SKILL, item, group.name, group.id)

    for certification in user.certification:
        _add(
            chunks,
            ChunkSection.CERTIFICATION,
            f"{certification.name} — {certification.issuer}",
            certification.issuer,
            certification.id,
        )

    for degree in user.education:
        _add(
            chunks,
            ChunkSection.EDUCATION,
            f"{degree.degree}, {degree.institution}",
            degree.institution,
            degree.id,
        )

    return chunks


def _add(
    chunks: list[ChunkFields],
    section: ChunkSection,
    text: str | None,
    source_ref: str = "",
    source_id: PydanticObjectId | None = None,
) -> None:
    """Append one chunk, unless the text is too short to retrieve anything by.

    Over-long text is truncated rather than dropped: a bullet somebody used as a
    paragraph is still theirs, and refusing to index it would fail their next save.
    """
    cleaned = " ".join((text or "").split())
    if len(cleaned) < MIN_CHUNK_CHARS:
        return
    chunks.append(
        ChunkFields(
            section=section,
            text=cleaned[:MAX_CHUNK_CHARS],
            sourceRef=source_ref,
            sourceId=source_id,
        )
    )
