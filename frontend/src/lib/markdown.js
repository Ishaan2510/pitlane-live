// A small Markdown-to-HTML renderer for the site's own content pages (src/content/*.md).
// It covers what those files use: # headings, paragraphs, - lists, ``` code blocks,
// | tables |, and inline `code`, **bold** and [links](url). Everything is escaped
// first, so the output is safe for v-html. Not a general Markdown parser.

const escape = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

function inline(text) {
  return escape(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) => (/^(\/|https:\/\/)/.test(url) ? `<a href="${url}">${label}</a>` : label))
}

const cells = line => line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim())

/**
 * @param source  Markdown text
 * @param values  { name: value } substituted for {{name}} before rendering
 */
export function renderMarkdown(source, values = {}) {
  const text = source.replace(/\{\{(\w+)\}\}/g, (_, key) => (values[key] ?? '…'))
  const lines = text.replace(/\r/g, '').split('\n')
  const out = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (line.startsWith('```')) {
      const code = []
      for (i++; i < lines.length && !lines[i].startsWith('```'); i++) code.push(lines[i])
      i++
      out.push(`<pre><code>${escape(code.join('\n'))}</code></pre>`)
    } else if (/^#{1,4} /.test(line)) {
      const level = line.indexOf(' ')
      out.push(`<h${level}>${inline(line.slice(level + 1))}</h${level}>`)
      i++
    } else if (/^- /.test(line)) {
      const items = []
      for (; i < lines.length && /^(- |  \S)/.test(lines[i]); i++) {
        if (lines[i].startsWith('- ')) items.push(lines[i].slice(2))
        else items[items.length - 1] += ' ' + lines[i].trim()          // a wrapped list item
      }
      out.push(`<ul>${items.map(item => `<li>${inline(item)}</li>`).join('')}</ul>`)
    } else if (line.startsWith('|') && /^\|[\s:|-]+\|$/.test((lines[i + 1] || '').trim())) {
      const head = cells(line), rows = []
      for (i += 2; i < lines.length && lines[i].startsWith('|'); i++) rows.push(cells(lines[i]))
      out.push(`<div class="md-table"><table><thead><tr>${head.map(c => `<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>`
        + rows.map(r => `<tr>${r.map(c => `<td>${inline(c)}</td>`).join('')}</tr>`).join('') + '</tbody></table></div>')
    } else {
      const para = []
      for (; i < lines.length && lines[i].trim() && !/^(#{1,4} |- |```|\|)/.test(lines[i]); i++) para.push(lines[i].trim())
      out.push(`<p>${inline(para.join(' '))}</p>`)
    }
  }
  return out.join('\n')
}
