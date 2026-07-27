import { useEffect, useMemo, useRef, useState } from 'react'

import { sendChat, toolLabel } from '../api/client'
import type { ChatBlock, ChatMessage, LoadedDocument, ToolUI } from '../api/types'
import { Markdownish } from './Markdownish'

const SUGGESTIONS = [
  'Faça um resumo do que existe neste desenho.',
  'Quais são os layers com mais entidades?',
  'Qual é a maior área fechada? Destaque no desenho.',
  'Existe algum texto de escala ou título?',
  'Quantas inserções de bloco existem e de quais blocos?',
]

interface Props {
  document: LoadedDocument | null
  ui: ToolUI
}

export function ChatPanel({ document: loaded, ui }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [showThinking, setShowThinking] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  // Uma sessão do agno por documento: o histórico de um desenho não faz sentido
  // aplicado a outro, e os ids de entidade sequer coincidem.
  const chatId = useMemo(
    () => `${loaded?.info.document_id ?? 'none'}-${Math.random().toString(36).slice(2)}`,
    [loaded?.info.document_id],
  )

  useEffect(() => {
    setMessages([])
  }, [loaded?.info.document_id])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages])

  /** Aplica uma mutação ao último bloco da última mensagem do assistente. */
  const mutateLast = (fn: (blocks: ChatBlock[]) => ChatBlock[]) => {
    setMessages((current) => {
      if (!current.length) return current
      const copy = current.slice()
      const last = copy[copy.length - 1]
      copy[copy.length - 1] = { ...last, blocks: fn(last.blocks) }
      return copy
    })
  }

  /** Deltas consecutivos do mesmo tipo são concatenados no mesmo bloco, senão o
   *  chat viraria uma pilha de fragmentos de uma palavra. */
  const appendDelta = (kind: 'text' | 'thinking', delta: string) => {
    mutateLast((blocks) => {
      const last = blocks[blocks.length - 1]
      if (last && last.kind === kind) {
        const updated = blocks.slice()
        updated[updated.length - 1] = { kind, text: last.text + delta }
        return updated
      }
      return [...blocks, { kind, text: delta }]
    })
  }

  const submit = async (question: string) => {
    const trimmed = question.trim()
    if (!trimmed || busy || !loaded) return

    setInput('')
    setBusy(true)

    setMessages((current) => [
      ...current,
      { role: 'user', blocks: [{ kind: 'text', text: trimmed }] },
      { role: 'assistant', blocks: [] },
    ])

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await sendChat(
        {
          message: trimmed,
          chatId,
          documentId: loaded.info.document_id,
          signal: controller.signal,
        },
        {
          onText: (delta) => appendDelta('text', delta),
          onThinking: (delta) => appendDelta('thinking', delta),
          onToolStarted: (name) =>
            mutateLast((blocks) => [
              ...blocks,
              {
                kind: 'tool',
                name,
                label: toolLabel(name),
                summary: null,
                error: false,
              },
            ]),
          onToolCompleted: (name, summary, error) =>
            mutateLast((blocks) => {
              // Completa o chip pendente mais recente desta ferramenta.
              const index = findLastIndex(
                blocks,
                (block) =>
                  block.kind === 'tool' && block.name === name && block.summary === null,
              )
              if (index < 0) return blocks

              const updated = blocks.slice()
              const chip = updated[index] as Extract<ChatBlock, { kind: 'tool' }>
              updated[index] = { ...chip, summary, error }
              return updated
            }),
          onError: (message) =>
            appendDelta('text', `\n\n**Erro:** ${message}`),
        },
        ui,
      )
    } catch (error) {
      if (!controller.signal.aborted) {
        appendDelta('text', `\n\n**Erro:** ${describeError(error)}`)
      }
    } finally {
      abortRef.current = null
      setBusy(false)
    }
  }

  const stop = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setBusy(false)
  }

  return (
    <section className="chat">
      <header className="chat-header">
        <h2>Assistente</h2>
        <label className="toggle">
          <input
            type="checkbox"
            checked={showThinking}
            onChange={(event) => setShowThinking(event.target.checked)}
          />
          mostrar raciocínio
        </label>
      </header>

      <div className="chat-log" ref={scrollRef}>
        {!loaded && (
          <p className="empty">Abra um arquivo DXF para começar a conversar sobre ele.</p>
        )}

        {loaded && !messages.length && (
          <div className="suggestions">
            <p className="empty">Pergunte algo sobre o desenho:</p>
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="suggestion"
                onClick={() => submit(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {messages.map((message, index) => (
          <article key={index} className={`msg msg-${message.role}`}>
            {message.blocks.map((block, blockIndex) => (
              <BlockView key={blockIndex} block={block} showThinking={showThinking} />
            ))}
            {message.role === 'assistant' &&
              index === messages.length - 1 &&
              busy &&
              !message.blocks.length && <p className="pending">pensando…</p>}
          </article>
        ))}
      </div>

      <form
        className="chat-form"
        onSubmit={(event) => {
          event.preventDefault()
          submit(input)
        }}
      >
        <textarea
          value={input}
          placeholder={loaded ? 'Pergunte sobre o desenho…' : 'Abra um DXF primeiro'}
          disabled={!loaded || busy}
          rows={2}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            // Enter envia; Shift+Enter quebra linha.
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              submit(input)
            }
          }}
        />
        {busy ? (
          <button type="button" className="danger" onClick={stop}>
            parar
          </button>
        ) : (
          <button type="submit" disabled={!loaded || !input.trim()}>
            enviar
          </button>
        )}
      </form>
    </section>
  )
}

function BlockView({
  block,
  showThinking,
}: {
  block: ChatBlock
  showThinking: boolean
}) {
  if (block.kind === 'text') {
    return (
      <div className="block-text">
        <Markdownish text={block.text} />
      </div>
    )
  }

  if (block.kind === 'thinking') {
    if (!showThinking) return null
    return <div className="block-thinking">{block.text}</div>
  }

  return (
    <div className={`chip${block.error ? ' chip-error' : ''}`}>
      <span className="chip-label">{block.label}</span>
      {block.summary ? (
        <span className="chip-summary">{block.summary}</span>
      ) : (
        <span className="chip-summary chip-pending">…</span>
      )}
    </div>
  )
}

function findLastIndex<T>(items: T[], predicate: (item: T) => boolean): number {
  for (let i = items.length - 1; i >= 0; i -= 1) {
    if (predicate(items[i])) return i
  }
  return -1
}

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
