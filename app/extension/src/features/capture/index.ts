import TurndownService from "turndown";

import { MAX_MARKDOWN, MAX_LINKS } from "@/shared/config";
import type { CapturePayload, CaptureRegion } from "@/shared/types";

/** Turns the posting on an arbitrary career page into markdown. Runs in the
 * page's world, so it makes no network call and never sees the token. */

/** Nothing here survives into markdown anyway — removing it first keeps it out
 * of the text-length measurements the region heuristic runs on. */
const STRIP = "script, style, noscript, template, svg, canvas, iframe, object, embed, link, meta";

/** Page furniture. Its text is real text, which is the only reason size alone
 * would pick it. */
const FURNITURE =
    /(^|[-_\s])(nav|navigation|menu|header|masthead|footer|sidebar|aside|breadcrumb|cookie|consent|banner|promo|newsletter|subscribe|social|share|related|recommend|comment|modal|popup)([-_\s]|$)/i;

/**
 * Furniture safe to delete outright once a region is chosen. Narrower than
 * `FURNITURE`, which only penalises a score: `job-header` matches that one and
 * must survive this one, so nothing here is a word a posting uses about itself.
 */
const DROPPABLE =
    /(^|[-_\s])(related|recommend|similar|morejobs|othersjobs|cookie|consent|newsletter|subscribe|social|share|breadcrumb)([-_\s]|$)/i;

const DROPPABLE_TAGS = "nav, footer, aside, [role='navigation'], [role='contentinfo']";

/** Words a job description has and a landing page does not. */
const SIGNAL =
    /(responsibilit|qualificat|requirement|what you.{0,4}ll do|about (the|this) (role|job|position)|who you are|minimum|preferred)/i;

const MIN_TEXT = 300;

function textOf(node: Element): string {
    return (node.textContent ?? "").replace(/\s+/g, " ").trim();
}

function linkLength(node: Element): number {
    let total = 0;
    for (const anchor of node.querySelectorAll("a")) total += textOf(anchor).length;
    return total;
}

function score(node: Element): number {
    const text = textOf(node);
    if (text.length < MIN_TEXT) return 0;

    // A link-dense block is a nav or a results list, not one posting.
    let value = text.length - linkLength(node);
    if (FURNITURE.test(`${node.id} ${node.className}`)) value *= 0.3;
    if (SIGNAL.test(text)) value *= 1.5;
    return value;
}

/** The winning block is usually the description alone, with the job title in a
 * sibling above it. Climbing while the parent adds little text takes the title. */
function widen(node: Element): Element {
    let best = node;
    const floor = textOf(node).length;
    while (best.parentElement && best.parentElement !== document.body) {
        if (textOf(best.parentElement).length > floor * 1.3) break;
        best = best.parentElement;
    }
    return best;
}

function pick(root: Document | Element): { region: Element; kind: CaptureRegion } {
    const declared: [CaptureRegion, string][] = [
        ["main", "main"],
        ["main", "[role='main']"],
        ["article", "article"],
    ];

    for (const [kind, selector] of declared) {
        const [largest] = [...root.querySelectorAll(selector)].sort(
            (a, b) => textOf(b).length - textOf(a).length,
        );
        if (largest && textOf(largest).length >= MIN_TEXT) return { region: largest, kind };
    }

    let best: Element | null = null;
    let bestScore = 0;
    for (const node of root.querySelectorAll("div, section, td")) {
        if (node.childElementCount === 0) continue;
        const value = score(node);
        if (value > bestScore) {
            bestScore = value;
            best = node;
        }
    }

    // Saying "body" out loud matters: it tells whatever reads this that it is
    // looking at a whole page rather than at a posting.
    const body = root instanceof Document ? root.body : root;
    if (!best) return { region: body, kind: "body" };
    return { region: widen(best), kind: "heuristic" };
}

/**
 * Resolved against the page rather than read off the `href` property. The
 * property resolves relative links too, but only while the node belongs to a
 * document with a base URL — and a capture that quietly stores `/apply` instead
 * of the apply URL is the one failure that looks like a success.
 */
/** `baseURI` first because a `<base href>` is what relative links on the page
 * actually resolve against; the page URL when there is no usable one. */
function baseUrl(): string {
    try {
        const declared = new URL(document.baseURI);
        if (declared.protocol === "http:" || declared.protocol === "https:") return declared.href;
    } catch {
        // No base, or an unusable one.
    }
    return location.href;
}

function absolute(raw: string, base: string): string | null {
    try {
        // `mailto:` and `tel:` parse fine and fail the protocol check, which is
        // what should happen — they are content, not addresses to rewrite.
        const url = new URL(raw, base);
        return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
    } catch {
        return null;
    }
}

/**
 * `widen` climbs to pick up the job title, and on a page whose posting and
 * "related jobs" rail share a parent it takes the rail too. Removing furniture
 * after the fact beats tuning the climb, because the `body` fallback needs it
 * regardless. The text guard is what stops this eating the posting itself when a
 * site names the description container something in the list.
 */
function stripFurniture(copy: Element): void {
    const total = textOf(copy).length;
    const doomed = [...copy.querySelectorAll(DROPPABLE_TAGS)];

    for (const node of copy.querySelectorAll("[class], [id]")) {
        if (DROPPABLE.test(`${node.id} ${node.className}`)) doomed.push(node);
    }

    for (const node of doomed) {
        // No need to skip one already taken out with its parent: the clone is
        // detached, so `isConnected` is false throughout it and `remove()` on an
        // orphan is a no-op anyway.
        if (total > 0 && textOf(node).length > total * 0.4) continue;
        node.remove();
    }
}

/** Works on a clone — the user is still looking at the live page. */
function prepare(region: Element, base: string): Element {
    const copy = region.cloneNode(true) as Element;
    for (const node of copy.querySelectorAll(STRIP)) node.remove();
    stripFurniture(copy);

    for (const anchor of copy.querySelectorAll("a[href]")) {
        const resolved = absolute(anchor.getAttribute("href") ?? "", base);
        if (resolved) anchor.setAttribute("href", resolved);
    }
    // An inline base64 image is an entire file pasted into the attribute, and the
    // markdown drops images anyway — this only keeps it out of the intermediate.
    for (const image of copy.querySelectorAll("img[src]")) image.removeAttribute("src");

    return copy;
}

function collectLinks(region: Element, base: string): string[] {
    const seen = new Set<string>();
    for (const anchor of region.querySelectorAll("a[href]")) {
        const resolved = absolute(anchor.getAttribute("href") ?? "", base);
        if (!resolved) continue;
        seen.add(resolved.split("#")[0] ?? resolved);
        if (seen.size >= MAX_LINKS) break;
    }
    return [...seen];
}

function converter(): TurndownService {
    const service = new TurndownService({
        headingStyle: "atx",
        bulletListMarker: "-",
        codeBlockStyle: "fenced",
    });

    // Turndown keeps these as raw HTML otherwise, which is the one thing this
    // capture is not supposed to store.
    service.remove(["script", "style", "noscript", "form", "button", "input", "select"]);

    // An image carries nothing a job parser wants, and its alt text is usually a
    // logo's company name repeated on every posting.
    service.addRule("dropImages", {
        filter: "img",
        replacement: () => "",
    });

    return service;
}

export function capturePage(): CapturePayload {
    const base = baseUrl();
    const { region, kind } = pick(document);
    const prepared = prepare(region, base);

    const markdown = converter()
        .turndown(prepared.innerHTML)
        // Turndown leaves runs of blank lines where it dropped nodes.
        .replace(/\n{3,}/g, "\n\n")
        .trim();

    // Refused rather than truncated: half a posting is not a capture, and this is
    // the last point where the size is known before it crosses two hops.
    if (markdown.length > MAX_MARKDOWN) {
        throw new Error(
            `This page is ${Math.round(markdown.length / 1000)}k characters as markdown — too large to capture.`,
        );
    }
    if (!markdown) {
        throw new Error("Found no readable content on this page.");
    }

    return {
        url: location.href,
        pageTitle: document.title,
        markdown,
        region: kind,
        textLength: textOf(prepared).length,
        links: collectLinks(prepared, base),
    };
}
