/**
 * The Preview, Diff and Source views all read these lines, so they can never disagree.
 * Lines come from the tailored `.tex` as stored, and `changes` mark which of them moved
 * and what each was — never re-derived from the base resume, which Regenerate rewrites.
 */
export function buildDocument(resume) {
    const changed = new Map(resume.changes.map((change) => [change.lineNo, change]));
    const text = resume.tex.endsWith("\n") ? resume.tex.slice(0, -1) : resume.tex;

    const lines = text.split("\n").map((line, i) => {
        const n = i + 1;
        const change = changed.get(n);
        return change ? { n, text: line, add: true, was: change.previous } : { n, text: line };
    });

    return {
        file: resume.filePath.split("/").pop(),
        filePath: resume.filePath,
        incorporated: resume.incorporated,
        declined: resume.declined,
        lines,
        added: lines.filter((l) => l.add).length,
        removed: lines.filter((l) => l.was != null).length,
    };
}

/** Changed lines plus surrounding context, with a gap marker where lines are skipped. */
export function deriveHunks(lines, context = 3) {
    const keep = new Set();
    lines.forEach((line, i) => {
        if (!line.add) return;
        const from = Math.max(0, i - context);
        const to = Math.min(lines.length - 1, i + context);
        for (let j = from; j <= to; j++) keep.add(j);
    });

    const hunks = [];
    let previous = null;
    for (const i of [...keep].sort((a, b) => a - b)) {
        if (previous !== null && i > previous + 1) hunks.push({ gap: true });
        hunks.push(lines[i]);
        previous = i;
    }
    return hunks;
}
