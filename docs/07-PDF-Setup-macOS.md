# PDF Generation — macOS Setup

The `.pdf` button on `/resume/preview` compiles the stored `.tex` with **pdflatex**. That
binary is not bundled with anything in this repo, so a fresh machine needs the steps
below once. Everything here was run and verified on macOS (Apple Silicon, Homebrew at
`/opt/homebrew`) against TeX Live 2026.

Without this setup the endpoint answers **503** with an install hint rather than failing
obscurely — that is the signal you are on a machine that has not been through this page.

---

## 1. Install BasicTeX

```bash
brew install --cask basictex
```

~500 MB. The full MacTeX distribution (~6 GB) also works but is not needed — the extra
packages this repo's templates require are listed in step 3 and total a few MB.

Installs to `/usr/local/texlive/<year>basic`, with binaries symlinked into
`/Library/TeX/texbin`.

## 2. Put `pdflatex` on your PATH

BasicTeX writes `/etc/paths.d/TeX`, but `path_helper` only reads that at **login shell**
startup — a shell whose `~/.zshrc` runs a conda init (or any other tool that rebuilds
PATH) will not pick it up. Set it explicitly:

```bash
export PATH="/Library/TeX/texbin:$PATH"                       # this shell
echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc    # every future shell

which pdflatex        # → /Library/TeX/texbin/pdflatex
pdflatex --version    # → pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026)
```

This step is for running pdflatex by hand. **The app does not need it** — see
[Why no restart is needed](#why-no-restart-is-needed).

## 3. Install the packages the templates need

```bash
sudo tlmgr update --self

sudo tlmgr install fontawesome5 tcolorbox tikzfill pdfcol helvetic \
                   titlesec enumitem environ trimspaces
```

| Package | Why |
|---|---|
| `helvetic` | Helvetica T1 metrics (`phvr8t.tfm`). Every template sets the whole document in Helvetica via `\usepackage{helvet}` + `\renewcommand{\familydefault}{\sfdefault}`. `helvet` is only the wrapper — without `helvetic` the font itself is missing and **nothing compiles**. |
| `fontawesome5` | The contact-line icons (`\faPhone`, `\faEnvelope`, `\faLinkedin`, …) in every template. |
| `tcolorbox` + `environ` + `trimspaces` + `tikzfill` + `pdfcol` | The bordered `\timelinerole` boxes in Teal Timeline. Only that one template needs any of these, and only `tcolorbox` is used directly — the other four are its dependencies, surfacing one at a time as each is satisfied. Skip them and the other five templates still work; Teal Timeline fails with whichever `.sty` is missing. |
| `titlesec` | Section heading style (`\titleformat`). |
| `enumitem` | Bullet list spacing (`\setlist[itemize]`). |

Already in BasicTeX, do **not** install: `microtype`, `parskip`, `pgf`, `ragged2e`,
`geometry`, `hyperref`, `xcolor`, `colortbl`, `booktabs`, `tabularx`, `array`, `multicol`.

> `ragged2e` is *not* in a bundle called `ms` — it ships under its own name and is
> already present. `tlmgr install ms` fails with "package not present in repository".

## 4. Verify before touching the app

**Nothing in `templates/` compiles on its own** — every file there is a template now,
including `resume.tex`. A token name such as `{{FULL_NAME}}` contains an underscore,
which is math-mode-only in LaTeX, so pdflatex stops with `! Missing $ inserted.`
before it reaches anything else. That is expected and says nothing about your install:
`render()` substitutes every token before pdflatex ever sees the file.

So test the *packages* instead. This loads every one the templates use:

```bash
cat > /tmp/texcheck.tex <<'TEX'
\documentclass[10pt,letterpaper]{article}
\usepackage[margin=0.6in]{geometry}
\usepackage[table]{xcolor}
\usepackage{titlesec,enumitem,tabularx,array,hyperref,microtype}
\usepackage{parskip,multicol,booktabs,colortbl,fontawesome5,ragged2e}
\usepackage[T1]{fontenc}\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{tcolorbox}\tcbuselibrary{skins}
\begin{document}
\faCheckCircle\ All packages loaded. Helvetica renders. \faGithub\ \faLinkedin
\begin{tcolorbox}[enhanced]tcolorbox + skins + tikzfill + pdfcol work.\end{tcolorbox}
\end{document}
TEX

cd /tmp && pdflatex -interaction=nonstopmode -halt-on-error texcheck.tex && open texcheck.pdf
```

A PDF with two ticked icons and a shaded box means every package in step 3 resolved —
`tcolorbox[enhanced]` is what drags in `tikzfill` and `pdfcol`, so a clean run here
covers the whole dependency chain. Anything missing is named in the error.

To test a real document, go through the app: render a template, then download the PDF.

## 5. Use it

```
GET /api/resume/base/pdf      Authorization: Bearer <access token>
```

Returns `application/pdf` with a `Content-Disposition` filename. In the UI: Preview tab
on `/resume/preview`, then `.pdf`.

It compiles the **stored** `.tex`, not a fresh render of the template — so a resume the
model has rectified downloads as what is on screen, not as what the template would
produce today.

The Source tab offers `.tex` instead, straight from the stored source.

---

## Why no restart is needed

`modules/resume/compile.py` resolves the binary in this order:

1. `PDFLATEX_BIN` from the environment
2. `pdflatex` on `PATH`
3. `/Library/TeX/texbin/pdflatex`

A server started outside a login shell rarely inherits step 2, so step 3 is what makes it
work in practice. Install packages and click again — no API restart between attempts.

Optional `.env` settings (both have working defaults):

```bash
# PDFLATEX_BIN=/Library/TeX/texbin/pdflatex
PDFLATEX_TIMEOUT_SECONDS=30
```

## Troubleshooting

**A missing `.sty` or `.tfm`** — the toast carries the real LaTeX error, not a bare 422
(the axios interceptor unwraps blob error bodies for exactly this). Find the package that
provides the file and install it:

```bash
tlmgr search --global --file "pdfcol.sty"
sudo tlmgr install pdfcol
```

Expect to repeat this. A package's dependencies surface **one at a time** — each install
gets pdflatex one step further before it stops on the next missing file. Teal Timeline
took three rounds (`tcolorbox` → `tikzfill` → `pdfcol`) before it compiled. The step 3
command already has all of them; this loop is for anything a *new* template introduces.

**`503 pdflatex is not installed`** — step 1 never ran, or TeX lives somewhere unusual.
Point `PDFLATEX_BIN` at it.

**`pdflatex did not finish within 30s`** — raise `PDFLATEX_TIMEOUT_SECONDS`. A resume
compiles in 1–3s, so this usually means pdflatex is waiting on input; `-halt-on-error`
and `-interaction=nonstopmode` are already set to prevent that.

**Shell escape is off.** `-no-shell-escape` is passed explicitly because templates are
LaTeX uploaded through `/api/template/upload` — without it, an uploaded template is
uploaded shell. Do not remove it to make some package work.

## Verified state

Every template rendered from a real `getProfile` payload through
`modules/template/service.render`, then compiled with pdflatex:

| Template | Result |
|---|---|
| Modern Minimalist | ✅ 73 KB |
| Bold Header Band | ✅ 78 KB |
| Teal Timeline | ✅ 70 KB |
| Coral Accent Border | ✅ 78 KB |
| Purple Pills | ✅ 76 KB |
| Amber Dual Tone | ✅ 76 KB |

Six of six, 2026-09-17, with the step 3 command exactly as written above.
