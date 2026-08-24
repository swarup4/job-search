/**
 * The fixture stores the base document once plus per-job line changes, so the Diff
 * and Source views can never disagree — both read the same composed document.
 * Replace `resume.json` with the server's response and these two functions stay.
 */
export function buildDocument(resume, jobId) {
    const job = resume.jobs[jobId] ?? resume.jobs[Object.keys(resume.jobs)[0]];

    const lines = resume.base.map((text, i) => {
        const n = i + 1;
        const tailored = job.changes[n];
        return tailored ? { n, text: tailored, add: true, was: text } : { n, text };
    });

    return {
        file: job.file,
        from: resume.template,
        incorporated: job.incorporated,
        declined: job.declined,
        lines,
        added: lines.filter((l) => l.add).length,
        removed: lines.filter((l) => l.was).length,
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
