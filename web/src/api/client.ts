import type {
  AgnoEvent,
  BBox,
  DocumentInfo,
  EntityDetails,
  LoadedDocument,
  PrimEntity,
  ToolUI,
} from './types'

/** Rotulos em pt-BR para os chips de ferramenta no chat. */
const TOOL_LABELS: Record<string, string> = {
  list_layers: 'listando layers',
  count_entities: 'contando entidades',
  query_entities: 'buscando entidades',
  get_entity_details: 'lendo detalhes da entidade',
  search_text: 'procurando textos',
  measure: 'medindo',
  get_block_definition: 'lendo definição de bloco',
  get_header_variables: 'lendo cabeçalho do arquivo',
  highlight_entities: 'destacando no desenho',
  clear_highlight: 'limpando destaque',
  zoom_to: 'reenquadrando a vista',
  set_layer_visibility: 'ajustando layers',
}

export function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? name
}

/** As 4 ferramentas cujo efeito é visual. Aplicadas a partir do stream. */
const UI_TOOLS = new Set([
  'highlight_entities',
  'clear_highlight',
  'zoom_to',
  'set_layer_visibility',
])

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
  } catch {
    return `${response.status} ${response.statusText}`
  }
}

export async function uploadDocument(file: File): Promise<LoadedDocument> {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch('/api/documents', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await readError(response))

  const info: DocumentInfo = await response.json()
  const entities = await fetchPrims(info.document_id)

  return {
    info,
    entities,
    byId: new Map(entities.map((entity) => [entity.id, entity])),
  }
}

async function fetchPrims(documentId: string): Promise<PrimEntity[]> {
  const response = await fetch(`/api/documents/${documentId}/prims`)
  if (!response.ok) throw new Error(await readError(response))

  const body = await response.json()
  return body.entities as PrimEntity[]
}

export async function fetchEntityDetails(
  documentId: string,
  entityId: string,
): Promise<EntityDetails> {
  const response = await fetch(
    `/api/documents/${documentId}/entities/${encodeURIComponent(entityId)}`,
  )
  if (!response.ok) throw new Error(await readError(response))
  return response.json()
}

interface ChatHandlers {
  onText: (delta: string) => void
  onThinking: (delta: string) => void
  onToolStarted: (name: string) => void
  onToolCompleted: (name: string, summary: string | null, error: boolean) => void
  onError: (message: string) => void
}

/**
 * Envia a pergunta e consome o stream SSE.
 *
 * As acoes de interface saem daqui: quando um `ToolCallStarted` traz o nome de
 * uma das 4 ferramentas de UI, aplicamos `tool_args` no viewer imediatamente.
 * Fazemos isso no *started* e nao no *completed* porque os argumentos ja estao
 * completos no inicio da chamada — o destaque aparece antes do texto da
 * resposta, que e a sensacao correta.
 */
export async function sendChat(
  params: {
    message: string
    chatId: string
    documentId: string
    signal: AbortSignal
  },
  handlers: ChatHandlers,
  ui: ToolUI,
): Promise<void> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: params.message,
      chat_id: params.chatId,
      document_id: params.documentId,
    }),
    signal: params.signal,
  })

  if (!response.ok) {
    handlers.onError(await readError(response))
    return
  }
  if (!response.body) {
    handlers.onError('resposta sem corpo')
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Frames SSE são separados por linha em branco.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      const line = frame.split('\n').find((l) => l.startsWith('data: '))
      if (!line) continue

      let event: AgnoEvent
      try {
        event = JSON.parse(line.slice(6))
      } catch {
        continue
      }

      dispatch(event, handlers, ui)
    }
  }
}

function dispatch(event: AgnoEvent, handlers: ChatHandlers, ui: ToolUI): void {
  switch (event.event) {
    case 'RunContent':
      if (event.content) handlers.onText(event.content)
      return

    case 'ReasoningContentDelta':
    case 'ReasoningStep':
      if (event.reasoning_content) handlers.onThinking(event.reasoning_content)
      return

    case 'ToolCallStarted':
      if (!event.tool) return
      handlers.onToolStarted(event.tool.tool_name)
      if (UI_TOOLS.has(event.tool.tool_name)) {
        applyUiTool(event.tool.tool_name, event.tool.tool_args ?? {}, ui)
      }
      return

    case 'ToolCallCompleted':
      if (!event.tool) return
      handlers.onToolCompleted(
        event.tool.tool_name,
        summaryOf(event.tool.result),
        Boolean(event.tool.tool_call_error),
      )
      return

    case 'ToolCallError':
      if (!event.tool) return
      handlers.onToolCompleted(event.tool.tool_name, event.error ?? null, true)
      return

    case 'RunError':
      handlers.onError(event.error ?? 'erro na execução')
      return

    default:
      return
  }
}

/** O resumo em pt-BR que cada tool coloca no resultado. */
function summaryOf(result: string | null | undefined): string | null {
  if (!result) return null
  try {
    const parsed = JSON.parse(result)
    return typeof parsed.resumo === 'string' ? parsed.resumo : null
  } catch {
    return null
  }
}

function applyUiTool(
  name: string,
  args: Record<string, unknown>,
  ui: ToolUI,
): void {
  switch (name) {
    case 'highlight_entities': {
      const ids = asStringArray(args.ids)
      if (!ids.length) return
      ui.highlight(ids, asString(args.label), args.zoom !== false)
      return
    }

    case 'clear_highlight':
      ui.clearHighlight()
      return

    case 'zoom_to': {
      const target = asString(args.target) || 'ids'

      if (target === 'all') {
        ui.zoomToAll()
        return
      }
      if (target === 'bbox') {
        const bbox = asBBox(args.bbox)
        if (bbox) ui.zoomToBBox(bbox)
        return
      }
      if (target === 'layer') {
        const layer = asString(args.layer)
        if (layer) ui.zoomToLayer(layer)
        return
      }
      const ids = asStringArray(args.ids)
      if (ids.length) ui.zoomToIds(ids)
      return
    }

    case 'set_layer_visibility': {
      const layers = asStringArray(args.layers)
      if (!layers.length) return
      ui.setLayerVisibility(layers, args.visible !== false, args.isolate === true)
      return
    }
  }
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string')
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function asBBox(value: unknown): BBox | null {
  if (!Array.isArray(value) || value.length !== 4) return null
  if (!value.every((n) => typeof n === 'number')) return null
  return value as BBox
}
