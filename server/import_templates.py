"""One-shot import of the on-disk template folders into the `templates` collection.

    python import_templates.py

Reads every `templates/<folder>/` holding a `template.json` and a `.tex`, and inserts
it. Templates whose name is already present are skipped, so re-running is safe — except
that a missing preview image is restored from the folder. Once in the database the
folders are only kept as your own source copies — nothing else reads them.
"""

import asyncio
import json
from pathlib import Path

from beanie import PydanticObjectId

from config.database import connect, disconnect
from modules.template.models import Template
from modules.template.service import infer_style, previews_dir, validate_source

ROOT = Path(__file__).resolve().parent.parent / "templates"


def _copy_preview(source: Path, template_id: PydanticObjectId) -> str:
    previews_dir().mkdir(parents=True, exist_ok=True)
    target = previews_dir() / f"{template_id}.png"
    target.write_bytes(source.read_bytes())
    return str(target)


async def main() -> None:
    await connect()
    imported = skipped = repaired = 0

    for folder in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name != "previews"):
        spec_file = folder / "template.json"
        tex_files = sorted(folder.glob("*.tex"))
        if not spec_file.is_file() or not tex_files:
            continue

        spec = json.loads(spec_file.read_text())
        name = spec.pop("name", folder.name)

        source_preview = folder / "Template_Preview.png"
        existing = await Template.find_one(Template.name == name)
        if existing is not None:
            # A database imported on another machine, or restored, keeps preview paths
            # whose files are not here. Re-running puts them back.
            if source_preview.is_file() and not (
                existing.previewPath and Path(existing.previewPath).is_file()
            ):
                existing.previewPath = _copy_preview(source_preview, existing.id)
                await existing.save()
                print(f"  repair  {name} (preview restored)")
                repaired += 1
            else:
                print(f"  skip    {name} (already imported)")
                skipped += 1
            continue

        source = tex_files[0].read_text()
        templateId = PydanticObjectId()
        previewPath = (
            _copy_preview(source_preview, templateId) if source_preview.is_file() else None
        )

        await Template(
            id=templateId,
            name=name,
            tex=source,
            style=infer_style(source),
            tokens=validate_source(source),
            previewPath=previewPath,
        ).insert()
        print(f"  import  {name:24} from {folder.name}")
        imported += 1

    print(f"\n{imported} imported, {repaired} previews restored, {skipped} already present")
    await disconnect()


if __name__ == "__main__":
    asyncio.run(main())
