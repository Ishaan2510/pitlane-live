import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '../markdown'

describe('renderMarkdown', () => {
  it('renders the subset the content pages use', () => {
    const html = renderMarkdown('# Title\n\nA **bold** `code` [link](/about/x) line\nthat wraps.\n\n- one\n- two\n  wrapped\n\n```\na < b\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n')
    expect(html).toContain('<h1>Title</h1>')
    expect(html).toContain('<p>A <strong>bold</strong> <code>code</code> <a href="/about/x">link</a> line that wraps.</p>')
    expect(html).toContain('<ul><li>one</li><li>two wrapped</li></ul>')
    expect(html).toContain('<pre><code>a &lt; b</code></pre>')
    expect(html).toContain('<th>A</th><th>B</th>')
    expect(html).toContain('<td>1</td><td>2</td>')
  })

  it('escapes HTML and drops links that are not ours', () => {
    const html = renderMarkdown('<script>x</script> [bad](javascript:alert(1)) [ok](https://example.org)')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('javascript:')
    expect(html).toContain('<a href="https://example.org">ok</a>')
  })

  it('fills {{placeholders}} and shows an ellipsis for a missing one', () => {
    expect(renderMarkdown('{{a}} of {{b}}', { a: 65 })).toBe('<p>65 of …</p>')
  })

  it('the strategy model page has a value for every placeholder', () => {
    const read = path => readFileSync(fileURLToPath(new URL(path, import.meta.url)), 'utf8')
    const source = read('../../content/strategy-model.md')
    const summary = JSON.parse(read('../../../public/data/manifest.json')).tyre_model
    const values = { runs: 500, ...summary, ...summary.confidence }
    const wanted = [...source.matchAll(/\{\{(\w+)\}\}/g)].map(m => m[1])
    expect(wanted.length).toBeGreaterThan(8)
    for (const key of wanted) expect(values[key], key).toBeDefined()
    expect(renderMarkdown(source, values)).not.toContain('…')
  })
})
