"""Template storage, validation and rendering — and this module's queries.

The `.tex` lives in the row, so uploading is one insert and there is no folder to
drift out of sync. Only the preview image stays on disk.
"""

import re
from datetime import UTC, datetime
from pathlib import Path

from beanie import PydanticObjectId
from pydantic import ValidationError

from config.errors import Conflict, Invalid, NotFound
from modules.profile import Profile
from modules.template.latex import (
    certifications_block,
    contact_block,
    education_block,
    experience_block,
    skills_grid,
    skills_pills,
)
from modules.template.latex import (
    tex as escape,
)
from modules.template.models import (
    ContactStyle,
    ExperienceStyle,
    SkillsStyle,
    Template,
    TemplateStyle,
    TemplateUpdate,
)

SUPPORTED_TOKENS = frozenset(
    {
        "FULL_NAME",
        "HEADLINE",
        "CONTACT",
        "SUMMARY",
        "SKILLS",
        "EXPERIENCE",
        "EDUCATION",
        "CERTIFICATIONS",
    }
)

MAX_TEX_BYTES = 1_000_000
MAX_PREVIEW_BYTES = 5_000_000

# Uppercase-only, so it cannot collide with the LaTeX braces the builders emit.
_TOKEN_RE = re.compile(r"\{\{[A-Z_]+\}\}")


class TemplateNotFound(NotFound):
    def __init__(self, template_id: PydanticObjectId | str) -> None:
        super().__init__(f"no resume template {template_id}")


class TemplateRejected(Invalid):
    """The upload is not a template this renderer can fill."""


class TemplateExists(Conflict):
    def __init__(self, name: str) -> None:
        super().__init__(f"a template named '{name}' already exists")


def previews_dir() -> Path:
    # server/modules/template/service.py -> repo root
    return Path(__file__).resolve().parents[3] / "templates" / "previews"


def name_from_filename(filename: str | None) -> str:
    """`Ocean_Blue.tex` -> `Ocean Blue`, so an upload need carry nothing but the file."""
    stem = Path(filename or "").stem
    pretty = re.sub(r"[_-]+", " ", stem).strip()
    return pretty or "Untitled template"


def tex_filename(name: str) -> str:
    """A download name, not an identifier — the id is what addresses a template."""
    safe = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "resume"
    return f"{safe}.tex"


# `%%!` is a LaTeX comment, so a directive line is inert in the document itself.
_DIRECTIVE_RE = re.compile(r"^%%!\s*(.+)$", re.MULTILINE)
_GRID_RE = re.compile(r"\\begin\{tabularx\}\{[^}]*\}\{([^}]+)\}\s*\n\s*\{\{SKILLS\}\}")


def infer_style(source: str) -> TemplateStyle:
    """Read the layout off the template's own LaTeX.

    A template already says how it is built: it defines the commands it uses and
    wraps its skills block in the environment it wants. Asking the uploader to
    restate that is asking them to repeat themselves — and to get it wrong.

    `location` is the exception. Whether a role reads "Bengaluru, India" or
    "Bengaluru" is an editorial choice with no trace in the file, so it defaults
    and is only settable through a directive.
    """
    fields: dict[str, object] = {}

    grid = _GRID_RE.search(source)
    if grid:
        fields["skills"] = SkillsStyle.GRID
        fields["columns"] = len(re.findall(r"[A-Za-z]", grid.group(1))) or 4
    elif r"\newcommand{\skilltag}" in source:
        fields["skills"] = SkillsStyle.PILLS

    if r"\newcommand{\timelinerole}" in source:
        fields["experience"] = ExperienceStyle.TIMELINEROLE
    if r"\newcommand{\contactitem}" not in source:
        fields["contact"] = ContactStyle.PLAIN

    # An explicit directive wins over anything inferred.
    for line in _DIRECTIVE_RE.findall(source):
        for pair in line.split():
            key, _, value = pair.partition("=")
            if key in TemplateStyle.model_fields and value:
                fields[key] = value

    try:
        return TemplateStyle(**fields)
    except ValidationError as exc:
        raise TemplateRejected(f"the %%! directive is not valid: {exc.errors()[0]['msg']}") from exc


def validate_source(source: str) -> list[str]:
    """A template with no tokens renders as a fixed document — almost certainly a
    finished resume uploaded by mistake rather than a template."""
    found = sorted({token[2:-2] for token in _TOKEN_RE.findall(source)})
    if not found:
        raise TemplateRejected(
            "no {{TOKEN}} placeholders found — supported: " + ", ".join(sorted(SUPPORTED_TOKENS))
        )
    unknown = sorted(set(found) - SUPPORTED_TOKENS)
    if unknown:
        raise TemplateRejected(
            "unknown placeholders "
            + ", ".join("{{" + token + "}}" for token in unknown)
            + " — supported: "
            + ", ".join(sorted(SUPPORTED_TOKENS))
        )
    return found


async def create_template(
    name: str,
    source: str,
    preview: bytes | None = None,
) -> Template:
    if len(source.encode()) > MAX_TEX_BYTES:
        raise TemplateRejected(f"the .tex exceeds {MAX_TEX_BYTES} bytes")
    if preview is not None and len(preview) > MAX_PREVIEW_BYTES:
        raise TemplateRejected(f"the preview exceeds {MAX_PREVIEW_BYTES} bytes")

    tokens = validate_source(source)
    style = infer_style(source)
    if await Template.find_one(Template.name == name) is not None:
        raise TemplateExists(name)

    # Generated up front so the preview file can be named after the row it belongs to.
    template_id = PydanticObjectId()
    preview_path: str | None = None
    if preview is not None:
        previews_dir().mkdir(parents=True, exist_ok=True)
        target = previews_dir() / f"{template_id}.png"
        target.write_bytes(preview)
        preview_path = str(target)

    template = Template(
        id=template_id,
        name=name,
        tex=source,
        style=style,
        tokens=tokens,
        preview_path=preview_path,
    )
    await template.insert()
    return template


async def get_template(template_id: PydanticObjectId) -> Template:
    template = await Template.get(template_id)
    if template is None:
        raise TemplateNotFound(template_id)
    return template


async def list_templates(status: bool | None = None) -> list[Template]:
    query = {"status": status} if status is not None else {}
    return await Template.find(query).sort("+name").to_list()


async def update_template(template_id: PydanticObjectId, payload: TemplateUpdate) -> Template:
    template = await get_template(template_id)
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return template

    for field, value in changes.items():
        setattr(template, field, value)
    template.updated_at = datetime.now(UTC)
    await template.save()
    return template


def _skills(profile: Profile, style: TemplateStyle) -> str:
    if style.skills is SkillsStyle.GRID:
        return skills_grid(profile.skill_groups, style.columns)
    return skills_pills(profile.skill_groups)


def render(template: Template, profile: Profile) -> str:
    style = template.style
    blocks = {
        "{{FULL_NAME}}": escape(profile.personal.name),
        "{{HEADLINE}}": escape(profile.personal.headline or ""),
        "{{CONTACT}}": contact_block(profile.personal, profile.email, style.contact),
        "{{SUMMARY}}": escape(profile.summary or ""),
        "{{SKILLS}}": _skills(profile, style),
        "{{EXPERIENCE}}": experience_block(profile.experience, style.experience, style.location),
        "{{EDUCATION}}": education_block(profile.education),
        "{{CERTIFICATIONS}}": certifications_block(profile.certifications),
    }

    source = template.tex
    for token, value in blocks.items():
        source = source.replace(token, value)

    leftover = sorted(set(_TOKEN_RE.findall(source)))
    if leftover:
        raise TemplateRejected(
            f"{template.name} has placeholders nothing fills: {', '.join(leftover)}"
        )
    return source
