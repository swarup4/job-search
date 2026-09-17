/** A selector stable enough to store in `FieldFill.selector` and find again on
 * the next render — an id or a name where the page gives one, a path otherwise. */
export function selectorFor(el: Element): string {
    if (el.id) return `#${CSS.escape(el.id)}`;

    const automation = el.getAttribute("data-automation-id");
    if (automation) return `[data-automation-id="${CSS.escape(automation)}"]`;

    const name = el.getAttribute("name");
    if (name) {
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute("type");
        const typePart = type ? `[type="${CSS.escape(type)}"]` : "";
        return `${tag}[name="${CSS.escape(name)}"]${typePart}`;
    }

    return pathTo(el);
}

function pathTo(el: Element): string {
    const parts: string[] = [];
    let node: Element | null = el;

    while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 6) {
        const tag = node.tagName.toLowerCase();
        if (tag === "body" || tag === "html") break;

        const parent: Element | null = node.parentElement;
        if (!parent) {
            parts.unshift(tag);
            break;
        }

        const sameTag = Array.from(parent.children).filter((child) => child.tagName === node!.tagName);
        parts.unshift(sameTag.length > 1 ? `${tag}:nth-of-type(${sameTag.indexOf(node) + 1})` : tag);
        node = parent;
    }

    return parts.join(" > ");
}

export function findBySelector(selector: string, doc: Document = document): HTMLElement | null {
    try {
        return doc.querySelector<HTMLElement>(selector);
    } catch {
        return null;
    }
}
