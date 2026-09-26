import MarkdownIt from "markdown-it";

/**
 * Job descriptions arrive as markdown converted from a third party's page, and are
 * rendered with dangerouslySetInnerHTML — so raw HTML inside them is escaped rather
 * than passed through (`html: false`), and markdown-it's default link check already
 * refuses `javascript:` and `data:` URLs. The same settings the AI tier renders
 * `htmlString` with, so both paths produce the same markup.
 */
const md = new MarkdownIt({ html: false, linkify: true });

const renderLinkOpen =
    md.renderer.rules.link_open ?? ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options));

// Links in a posting lead off the app, so they open in a new tab without handing the
// page a reference back to this one.
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    tokens[idx].attrSet("target", "_blank");
    tokens[idx].attrSet("rel", "noopener noreferrer");
    return renderLinkOpen(tokens, idx, options, env, self);
};

export function renderMarkdown(text) {
    return md.render(text ?? "");
}
