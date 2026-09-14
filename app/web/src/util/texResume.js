/**
 * A rendered template's `.tex` → the blocks `ResumeDocument` draws.
 *
 * `texToBlocks` reads the tailored document line by line, because that screen lets
 * you click a line. This one reads the whole file: the six templates wrap their
 * skills table and their timeline roles in braces that stay open across several
 * lines, so a line is not a unit here — a brace-balanced chunk is.
 *
 * It understands the commands `modules/template/latex.py` emits and nothing else.
 * Add a builder there and add its command here, or it renders as plain text.
 */

const SYMBOL = {
    textperiodcentered: "·",
    textbullet: "·",
    textemdash: "—",
    textendash: "–",
    textbackslash: "\\",
    textasciitilde: "~",
    textasciicircum: "^",
    enspace: " ",
    quad: " ",
    qquad: " ",
    hfill: " ",
};

/** Commands whose arguments are styling values, not text: drop the lot. */
const DROP_ARGS = {
    color: 1,
    fontsize: 2,
    rule: 2,
    vspace: 1,
    hspace: 1,
    setlength: 2,
    definecolor: 3,
    colorlet: 2,
    hypersetup: 1,
    includegraphics: 1,
    label: 1,
    arraystretch: 1,
};

/** Commands whose last argument is the visible text. */
const LAST_ARG = { href: 2, textcolor: 2 };

export function texToResume(source) {
    const blocks = [];
    const state = { job: null, project: null, head: [], heading: true };

    for (const chunk of chunks(body(source))) {
        readChunk(chunk, blocks, state);
    }

    // A template with no section at all: the header never got flushed.
    blocks.push(...header(state.head));
    return blocks;
}

function readChunk(chunk, blocks, state) {
    // Decoration, not content: the band behind Template 2's header is drawn with
    // coordinates, and nothing inside it is text.
    if (/\\(fill|draw|clip|path|shade)\b/.test(chunk)) return;

    const section = args(chunk, "seclabel", 1) ?? args(chunk, "section", 1);
    if (section) {
        // Everything before the first section is the header. Keying on that rather
        // than on \begin{center} is what makes the tikz and minipage headers work.
        if (state.heading) {
            blocks.push(...header(state.head));
            state.head = [];
            state.heading = false;
        }
        blocks.push({ kind: "section", text: plain(section[0]) });
        state.job = null;
        state.project = null;
        return;
    }

    if (state.heading) {
        if (!/^\s*\\(begin|end)\{/.test(strip(chunk))) state.head.push(chunk);
        return;
    }

    const role = args(chunk, "jobtitle", 4);
    if (role) {
        state.job = {
            kind: "job",
            title: plain(role[0]),
            company: join([plain(role[1]), plain(role[3])]),
            dates: plain(role[2]),
            bullets: [],
            projects: [],
        };
        state.project = null;
        blocks.push(state.job);
        return;
    }

    const timeline = args(chunk, "timelinerole", 4);
    if (timeline) {
        state.job = {
            kind: "job",
            title: plain(timeline[0]),
            company: plain(timeline[1]),
            dates: plain(timeline[2]),
            bullets: items(timeline[3]),
            projects: [],
        };
        state.project = null;
        blocks.push(state.job);
        return;
    }

    const project = args(chunk, "projectlabel", 1);
    if (project && state.job) {
        state.project = { name: plain(project[0]), bullets: [] };
        state.job.projects.push(state.project);
        return;
    }

    const education = args(chunk, "educrow", 3);
    if (education) {
        blocks.push({
            kind: "degree",
            degree: plain(education[0]),
            institution: plain(education[1]),
            location: "",
            dates: plain(education[2]),
        });
        return;
    }

    const certification = args(chunk, "certrow", 3);
    if (certification) {
        blocks.push({
            kind: "cert",
            name: plain(certification[0]),
            issuer: plain(certification[1]),
            year: plain(certification[2]),
        });
        return;
    }

    if (chunk.includes("\\skilltag{")) {
        blocks.push({ kind: "pills", items: every(chunk, "skilltag").map(([item]) => plain(item)) });
        return;
    }

    if (chunk.includes("\\begin{tabularx}")) {
        blocks.push(...grid(chunk));
        return;
    }

    const bullets = items(chunk);
    if (bullets.length) {
        const target = state.project ?? state.job;
        if (target) target.bullets.push(...bullets);
        else blocks.push(...bullets.map((text) => ({ kind: "paragraph", text })));
        return;
    }

    if (/^\s*\\(begin|end)\{/.test(chunk)) return;

    const text = plain(chunk);
    if (text) blocks.push({ kind: "paragraph", text });
}

/** Layout commands that carry no text, cleared so the structural tests can see past them. */
function strip(chunk) {
    return chunk
        .replace(/\\(noindent|centering|par|raggedright|small|bfseries|itshape|selectfont)\b/g, "")
        .replace(/\\(vspace|hspace)\*?\{[^{}]*\}/g, "")
        .trim();
}

/** The name, then the headline, then every contact entry on one line. */
function header(lines) {
    const isContact = (line) => line.includes("\\contactitem") || /\\fa[A-Z]/.test(line);
    const out = [];

    const contact = [];

    lines.forEach((line) => {
        if (isContact(line)) {
            contact.push(...entries(line));
            return;
        }
        // A tikz node closes with a semicolon that is syntax, not punctuation.
        const text = plain(line).replace(/;$/, "").trim();
        if (text) out.push({ kind: out.length ? "headerLine" : "name", text });
    });

    if (contact.length) out.push({ kind: "headerLine", text: contact.join(" · ") });
    return out;
}

/**
 * The contact entries of one header line. `contactitem` templates name each one;
 * `plain` templates emit bare icons separated by \enspace, and a template may put
 * the whole line in one brace group — so neither a line nor a chunk is one entry.
 */
function entries(line) {
    if (line.includes("\\contactitem")) {
        return every(line, "contactitem", 2)
            .map(([, value]) => plain(value))
            .filter(Boolean);
    }
    return line
        .split(/\\enspace/)
        .map(plain)
        .filter(Boolean);
}

/** One tabularx row per skill group; the cells are that group's items. */
function grid(chunk) {
    const start = chunk.indexOf("}", chunk.indexOf("\\begin{tabularx}") + 16);
    const inner = chunk.slice(start + 1, chunk.indexOf("\\end{tabularx}"));
    // The first {…} after \begin{tabularx}{width} is the column spec, not content.
    const rows = inner.replace(/^\s*\{[^{}]*\}/, "").split("\\\\");

    return rows
        .map((row) =>
            row
                .split("&")
                .map(plain)
                .filter(Boolean)
                .join(", ")
        )
        .filter(Boolean)
        .map((value) => ({ kind: "skill", label: "", value }));
}

function items(source) {
    if (!source.includes("\\item")) return [];
    return source
        .split(/\\item(?![a-zA-Z])/)
        .slice(1)
        .map(plain)
        .filter(Boolean);
}

function join(parts) {
    return parts.filter(Boolean).join(" · ");
}

/** Everything between \begin{document} and \end{document} — the preamble is styling. */
function body(source) {
    const start = source.indexOf("\\begin{document}");
    const end = source.indexOf("\\end{document}");
    return source.slice(
        start === -1 ? 0 : start + "\\begin{document}".length,
        end === -1 ? source.length : end
    );
}

/**
 * Split into brace-balanced chunks, dropping comments. A newline inside an open
 * brace is not a break: `\timelinerole{…}{…}{…}{% \item … }` is one command even
 * though it is written over five lines.
 */
function chunks(source) {
    const out = [];
    let current = "";
    let depth = 0;

    for (let i = 0; i < source.length; i++) {
        const char = source[i];

        if (char === "\\") {
            current += source.slice(i, i + 2);
            i += 1;
            continue;
        }
        if (char === "%") {
            while (i + 1 < source.length && source[i + 1] !== "\n") i += 1;
            continue;
        }
        if (char === "\n") {
            if (depth === 0) {
                out.push(current);
                current = "";
            } else {
                current += " ";
            }
            continue;
        }
        if (char === "{") depth += 1;
        else if (char === "}") depth = Math.max(0, depth - 1);
        current += char;
    }

    out.push(current);
    return out.filter((chunk) => chunk.trim());
}

/** The `count` brace groups of `\name` in `chunk`, or null if it is not there. */
function args(chunk, name, count) {
    const at = chunk.indexOf(`\\${name}`);
    if (at === -1) return null;

    const after = chunk[at + name.length + 1];
    if (after && /[a-zA-Z]/.test(after)) return null;

    const read = groups(chunk, at + name.length + 1, count);
    return read.args.length === count ? read.args : null;
}

/** Every occurrence of a command — `\skilltag{Python}\ \skilltag{Go}` is two. */
function every(chunk, name, count = 1) {
    const out = [];
    let from = 0;

    for (;;) {
        const at = chunk.indexOf(`\\${name}{`, from);
        if (at === -1) return out;
        const read = groups(chunk, at + name.length + 1, count);
        if (read.args.length < count) return out;
        out.push(read.args);
        from = read.end;
    }
}

function groups(source, from, count) {
    const args = [];
    let i = from;

    while (args.length < count) {
        while (i < source.length && /\s/.test(source[i])) i += 1;
        if (source[i] !== "{") break;

        i += 1;
        const start = i;
        let depth = 0;
        for (; i < source.length; i += 1) {
            const char = source[i];
            if (char === "\\") {
                i += 1;
                continue;
            }
            if (char === "{") depth += 1;
            else if (char === "}") {
                if (depth === 0) break;
                depth -= 1;
            }
        }
        args.push(source.slice(start, i));
        i += 1;
    }

    return { args, end: i };
}

/** LaTeX → readable text. Good enough for a preview, not a general detex. */
function plain(source) {
    let out = "";

    for (let i = 0; i < source.length; i += 1) {
        const char = source[i];

        if (char === "{" || char === "}" || char === "&") continue;
        if (char !== "\\") {
            out += char;
            continue;
        }

        const rest = source.slice(i + 1);

        const escaped = rest.match(/^[&%$#_{}]/);
        if (escaped) {
            out += escaped[0];
            i += 1;
            continue;
        }

        if (rest.startsWith("\\")) {
            // A line break, optionally carrying its own spacing: `\\[3pt]`.
            const spacing = rest.slice(1).match(/^\[[^\]]*\]/);
            i += 1 + (spacing ? spacing[0].length : 0);
            out += " ";
            continue;
        }

        const named = rest.match(/^[a-zA-Z]+\*?/);
        if (!named) {
            out += " ";
            continue;
        }

        const name = named[0];
        let next = i + 1 + name.length;

        // Optional arguments are always settings — `\\begin{tikzpicture}[overlay]`,
        // `\\node[fill=accent]`. Never text, so they never reach the output.
        for (;;) {
            const optional = source.slice(next).match(/^\s*\[[^\]]*\]/);
            if (!optional) break;
            next += optional[0].length;
        }

        // FontAwesome icons carry meaning the preview shows as the value beside them.
        if (/^fa[A-Z]/.test(name) || SYMBOL[name] !== undefined) {
            out += SYMBOL[name] ?? "";
            if (source.slice(next, next + 2) === "{}") next += 2;
            i = next - 1;
            continue;
        }

        if (DROP_ARGS[name] !== undefined) {
            i = groups(source, next, DROP_ARGS[name]).end - 1;
            continue;
        }

        if (LAST_ARG[name] !== undefined) {
            const read = groups(source, next, LAST_ARG[name]);
            out += plain(read.args[read.args.length - 1] ?? "");
            i = read.end - 1;
            continue;
        }

        // Anything else is a styling wrapper: drop the token, keep what it wraps.
        i = next - 1;
    }

    return out
        .replace(/---/g, "—")
        .replace(/--/g, "–")
        .replace(/``|''/g, '"')
        .replace(/\s+/g, " ")
        .replace(/\s+([,.;:])/g, "$1")
        .trim();
}
