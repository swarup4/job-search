"""Compiling a resume `.tex` to PDF — the one place this server shells out.

FR-4.4 said `.tex` only; this is that decision reversed for the download button, and
nothing else in the pipeline gained a PDF. The compiler is external, so its absence
is a 503 rather than a crash.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path

from config.errors import DomainError, Invalid

# BasicTeX installs here, and a server started outside a login shell will not have
# it on PATH.
TEXBIN = "/Library/TeX/texbin"


class CompilerMissing(DomainError):
    status = 503

    def __init__(self) -> None:
        super().__init__(
            "pdflatex is not installed — `brew install --cask basictex`, "
            "or point PDFLATEX_BIN at it"
        )


class CompileFailed(Invalid):
    """The document reached pdflatex and pdflatex refused it."""


def _binary() -> str:
    configured = os.environ.get("PDFLATEX_BIN")
    if configured:
        return configured
    found = shutil.which("pdflatex") or shutil.which("pdflatex", path=TEXBIN)
    if found is None:
        raise CompilerMissing()
    return found


def _first_error(log: str) -> str:
    """pdflatex announces the failure on a line opening with `!`; the two that
    follow carry the line number and the offending source."""
    lines = log.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("!"):
            return " ".join(part.strip() for part in lines[index : index + 3] if part.strip())
    return "pdflatex produced no PDF"


async def to_pdf(source: str) -> bytes:
    binary = _binary()
    limit = float(os.environ.get("PDFLATEX_TIMEOUT_SECONDS", "30"))

    with tempfile.TemporaryDirectory(prefix="jobpilot-tex-") as workspace:
        folder = Path(workspace)
        (folder / "resume.tex").write_text(source, encoding="utf-8")

        process = await asyncio.create_subprocess_exec(
            binary,
            "-interaction=nonstopmode",
            "-halt-on-error",
            # A template is LaTeX somebody uploaded. `\write18` would make it shell
            # somebody uploaded, so it is refused explicitly rather than by default.
            "-no-shell-escape",
            "resume.tex",
            cwd=folder,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        try:
            output, _ = await asyncio.wait_for(process.communicate(), limit)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise CompileFailed(f"pdflatex did not finish within {limit:.0f}s") from None

        pdf = folder / "resume.pdf"
        if process.returncode != 0 or not pdf.is_file():
            raise CompileFailed(_first_error(output.decode(errors="replace")))
        return pdf.read_bytes()


def pdf_filename(name: str) -> str:
    """A download name, not an identifier — mirrors `template.service.tex_filename`."""
    safe = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "resume"
    return f"{safe}.pdf"
