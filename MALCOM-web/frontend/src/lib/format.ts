import hljs from "highlight.js/lib/core";
import json from "highlight.js/lib/languages/json";

hljs.registerLanguage("json", json);

// Detect a JSON payload and return pretty-printed, syntax-highlighted HTML.
// Returns null when the text is not a JSON object/array.
export function formatJson(text: string): string | null {
  if (!text) return null;
  let trimmed = text.trim();
  // Strip a surrounding markdown code fence (```json … ``` or ``` … ```), which
  // LLMs often emit around JSON even when told not to.
  const fence = trimmed.match(/^```[a-zA-Z0-9]*\s*\n?([\s\S]*?)\n?```$/);
  if (fence) trimmed = fence[1].trim();
  const looksJson =
    (trimmed.startsWith("{") || trimmed.startsWith("[")) &&
    (trimmed.endsWith("}") || trimmed.endsWith("]"));
  if (!looksJson) return null;
  try {
    const pretty = JSON.stringify(JSON.parse(trimmed), null, 2);
    return hljs.highlight(pretty, { language: "json" }).value;
  } catch {
    return null;
  }
}

// Highlight arbitrary content for the file preview. JSON files are pretty
// printed; everything else is shown verbatim (escaped) with no highlighting.
export function previewHtml(path: string, content: string): string {
  if (path.endsWith(".json")) {
    let text = content;
    try {
      text = JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      /* leave as-is */
    }
    return hljs.highlight(text, { language: "json" }).value;
  }
  return escapeHtml(content);
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
