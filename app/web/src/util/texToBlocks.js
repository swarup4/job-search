/**
 * Turns the tailored .tex into renderable blocks for the visual preview.
 *
 * It parses only the custom commands base_resume.tex actually emits — \section,
 * \skillrow, \jobtitle, \item, \certrow, \degreerow — and treats everything else as
 * text. That is deliberate: parsing the document rather than re-reading profile.json
 * means the preview shows the SAME lines as the Diff and Source views, including any
 * rewrite the user accepted. Add a command to the template and you add it here too.
 */

const PATTERNS = [
    [/^\\section\{([^{}]*)\}/, (m) => ({ kind: "section", text: detex(m[1]) })],
    [
        /^\s*\\skillrow\{([^{}]*)\}\{([^{}]*)\}/,
        (m) => ({ kind: "skill", label: detex(m[1]), value: detex(m[2]) }),
    ],
    [
        /^\\jobtitle\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}/,
        (m) => ({ kind: "job", title: detex(m[1]), company: detex(m[2]), dates: detex(m[3]), bullets: [] }),
    ],
    [
        /^\\certrow\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}/,
        (m) => ({ kind: "cert", name: detex(m[1]), issuer: detex(m[2]), year: detex(m[3]) }),
    ],
    [
        /^\\degreerow\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}/,
        (m) => ({ kind: "degree", degree: detex(m[1]), institution: detex(m[2]), location: detex(m[3]), dates: detex(m[4]) }),
    ],
    [/^\s*\\item\s+(.*)$/, (m) => ({ kind: "item", text: detex(m[1]) })],
];

export function texToBlocks(lines) {
    const body = sliceBody(lines);
    const blocks = [];
    let inCenter = false;
    let seenName = false;

    for (const raw of body) {
        const line = raw.trimEnd();
        if (!line.trim()) continue;

        if (line.includes("\\begin{center}")) { inCenter = true; continue; }
        if (line.includes("\\end{center}")) { inCenter = false; continue; }

        const matched = PATTERNS.find(([re]) => re.test(line));
        if (matched) {
            const block = matched[1](line.match(matched[0]));
            if (block.kind === "item") {
                const job = [...blocks].reverse().find((b) => b.kind === "job");
                if (job) job.bullets.push(block.text);
                else blocks.push({ kind: "paragraph", text: block.text });
            } else {
                blocks.push(block);
            }
            continue;
        }

        // \begin/\end of an environment carries no content of its own
        if (/^\s*\\(begin|end)\{/.test(line)) continue;

        const text = detex(line);
        if (!text) continue;

        if (inCenter) {
            blocks.push({ kind: seenName ? "headerLine" : "name", text });
            seenName = true;
        } else {
            blocks.push({ kind: "paragraph", text });
        }
    }

    return blocks;
}

/** Everything between \begin{document} and \end{document}; the preamble is styling. */
function sliceBody(lines) {
    const texts = lines.map((l) => l.text);
    const start = texts.findIndex((t) => t.includes("\\begin{document}"));
    const end = texts.findIndex((t) => t.includes("\\end{document}"));
    return texts.slice(start === -1 ? 0 : start + 1, end === -1 ? texts.length : end);
}

/** LaTeX → plain text. Good enough for a preview, not a general detex. */
function detex(input) {
    return input
        .replace(/\\textbullet\{\}/g, "·")
        .replace(/\\textemdash\{\}/g, "—")
        .replace(/\\textendash\{\}/g, "–")
        .replace(/\\textbackslash\{\}/g, "\\")
        .replace(/\\textasciitilde\{\}/g, "~")
        .replace(/\\(?:vspace|hspace)\*?\{[^{}]*\}/g, "")
        .replace(/\\([&%$#_])/g, "$1")
        .replace(/\\[a-zA-Z]+\*?/g, "")
        .replace(/[{}]/g, "")
        .replace(/--/g, "–")
        .replace(/\s+/g, " ")
        .trim();
}
