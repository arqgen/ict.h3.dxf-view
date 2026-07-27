import type { ReactNode } from 'react'

/**
 * Renderizador mínimo de markdown: negrito, código inline, listas e parágrafos.
 *
 * Um parser completo seria uma dependência a mais para cobrir o que o agente de
 * fato produz — conclusão em negrito e listas curtas.
 */
export function Markdownish({ text }: { text: string }) {
  const lines = text.split('\n')
  const blocks: ReactNode[] = []
  let listItems: ReactNode[] = []

  const flushList = () => {
    if (!listItems.length) return
    blocks.push(<ul key={`ul-${blocks.length}`}>{listItems}</ul>)
    listItems = []
  }

  lines.forEach((line, index) => {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/)
    if (bullet) {
      listItems.push(<li key={index}>{inline(bullet[1])}</li>)
      return
    }

    flushList()

    if (!line.trim()) return

    const heading = line.match(/^(#{1,4})\s+(.*)$/)
    if (heading) {
      blocks.push(
        <p key={index} className="md-heading">
          {inline(heading[2])}
        </p>,
      )
      return
    }

    blocks.push(<p key={index}>{inline(line)}</p>)
  })

  flushList()

  return <>{blocks}</>
}

/** Aplica negrito (`**x**`) e código inline (`` `x` ``). */
function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g

  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    const token = match[0]
    if (token.startsWith('**')) {
      parts.push(<strong key={match.index}>{token.slice(2, -2)}</strong>)
    } else {
      parts.push(<code key={match.index}>{token.slice(1, -1)}</code>)
    }

    lastIndex = match.index + token.length
  }

  if (lastIndex < text.length) parts.push(text.slice(lastIndex))

  return parts
}
