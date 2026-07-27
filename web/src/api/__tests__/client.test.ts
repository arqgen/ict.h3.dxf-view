/**
 * Verifica o caminho SSE -> ToolUI contra um stream REAL do agno.
 *
 * `recorded-stream.txt` foi capturado de `POST /api/chat` respondendo
 * "Qual e a maior entidade fechada do desenho? Me mostre onde ela esta." sobre
 * o DXF sintetico dos testes do backend. Usar a gravacao em vez de um evento
 * escrito a mao e o ponto: se o formato de evento do agno mudar, este teste
 * quebra — e a premissa de que o viewer consegue ler `tool_args` do stream e
 * exatamente o que sustenta as 4 ferramentas de interface.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ToolUI } from '../types'
import { sendChat, toolLabel } from '../client'

const RECORDED = readFileSync(join(__dirname, 'recorded-stream.txt'), 'utf-8')

function streamOf(body: string): Response {
  const encoder = new TextEncoder()
  // Fatiado em pedaços pequenos de propósito, para que frames caiam partidos
  // entre chunks — é assim que a rede se comporta e onde um parser ingênuo falha.
  const chunks: Uint8Array[] = []
  for (let i = 0; i < body.length; i += 64) {
    chunks.push(encoder.encode(body.slice(i, i + 64)))
  }

  let index = 0
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (index >= chunks.length) {
        controller.close()
        return
      }
      controller.enqueue(chunks[index])
      index += 1
    },
  })

  return new Response(stream, { status: 200 })
}

function makeUi() {
  return {
    highlight: vi.fn(),
    clearHighlight: vi.fn(),
    zoomToIds: vi.fn(),
    zoomToLayer: vi.fn(),
    zoomToBBox: vi.fn(),
    zoomToAll: vi.fn(),
    setLayerVisibility: vi.fn(),
  } satisfies ToolUI
}

function makeHandlers() {
  return {
    text: '' as string,
    thinking: '' as string,
    started: [] as string[],
    completed: [] as { name: string; summary: string | null; error: boolean }[],
    errors: [] as string[],
  }
}

/** O corpo do stream vem do `fetch` stubado, não daqui. */
async function run() {
  const ui = makeUi()
  const captured = makeHandlers()

  await sendChat(
    {
      message: 'pergunta',
      chatId: 'c1',
      documentId: 'd1',
      signal: new AbortController().signal,
    },
    {
      onText: (delta) => {
        captured.text += delta
      },
      onThinking: (delta) => {
        captured.thinking += delta
      },
      onToolStarted: (name) => captured.started.push(name),
      onToolCompleted: (name, summary, error) =>
        captured.completed.push({ name, summary, error }),
      onError: (message) => captured.errors.push(message),
    },
    ui,
  )

  return { ui, captured }
}

describe('sendChat sobre um stream gravado do agno', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => streamOf(RECORDED)),
    )
  })

  it('acumula o texto da resposta', async () => {
    const { captured } = await run()

    expect(captured.text).toContain('LWPOLYLINE')
    expect(captured.text).toContain('280')
    expect(captured.errors).toEqual([])
  })

  it('reporta as ferramentas chamadas, na ordem', async () => {
    const { captured } = await run()

    expect(captured.started).toEqual(['query_entities', 'highlight_entities'])
  })

  it('extrai o resumo em pt-BR do resultado de cada ferramenta', async () => {
    const { captured } = await run()

    expect(captured.completed).toHaveLength(2)
    expect(captured.completed[0].summary).toBe('2 entidades encontradas, 2 devolvidas')
    expect(captured.completed[1].summary).toBe('1 entidades destacadas no desenho')
    expect(captured.completed.every((item) => !item.error)).toBe(true)
  })

  it('aplica highlight_entities no viewer com os argumentos do evento', async () => {
    const { ui } = await run()

    expect(ui.highlight).toHaveBeenCalledTimes(1)
    expect(ui.highlight).toHaveBeenCalledWith(
      ['90'],
      'Maior entidade fechada — contorno',
      true,
    )
  })

  it('nao dispara acoes de interface que a IA nao pediu', async () => {
    const { ui } = await run()

    expect(ui.clearHighlight).not.toHaveBeenCalled()
    expect(ui.setLayerVisibility).not.toHaveBeenCalled()
    expect(ui.zoomToAll).not.toHaveBeenCalled()
  })
})

describe('despacho das ferramentas de interface', () => {
  const frame = (event: Record<string, unknown>) =>
    `data: ${JSON.stringify(event)}\n\n`

  const started = (tool_name: string, tool_args: Record<string, unknown>) =>
    frame({ event: 'ToolCallStarted', tool: { tool_name, tool_args } })

  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  async function dispatch(body: string) {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => streamOf(body)),
    )
    return run()
  }

  it('zoom_to target=all', async () => {
    const { ui } = await dispatch(started('zoom_to', { target: 'all' }))
    expect(ui.zoomToAll).toHaveBeenCalledTimes(1)
  })

  it('zoom_to target=bbox', async () => {
    const { ui } = await dispatch(
      started('zoom_to', { target: 'bbox', bbox: [0, 0, 20, 14] }),
    )
    expect(ui.zoomToBBox).toHaveBeenCalledWith([0, 0, 20, 14])
  })

  it('zoom_to target=layer', async () => {
    const { ui } = await dispatch(
      started('zoom_to', { target: 'layer', layer: 'CONTORNO' }),
    )
    expect(ui.zoomToLayer).toHaveBeenCalledWith('CONTORNO')
  })

  it('zoom_to target=ids', async () => {
    const { ui } = await dispatch(started('zoom_to', { target: 'ids', ids: ['1', '2'] }))
    expect(ui.zoomToIds).toHaveBeenCalledWith(['1', '2'])
  })

  it('zoom_to sem target explicito trata como ids', async () => {
    const { ui } = await dispatch(started('zoom_to', { ids: ['7'] }))
    expect(ui.zoomToIds).toHaveBeenCalledWith(['7'])
  })

  it('set_layer_visibility com isolate', async () => {
    const { ui } = await dispatch(
      started('set_layer_visibility', {
        layers: ['PAREDES'],
        visible: true,
        isolate: true,
      }),
    )
    expect(ui.setLayerVisibility).toHaveBeenCalledWith(['PAREDES'], true, true)
  })

  it('set_layer_visibility ocultando', async () => {
    const { ui } = await dispatch(
      started('set_layer_visibility', { layers: ['COTAS'], visible: false }),
    )
    expect(ui.setLayerVisibility).toHaveBeenCalledWith(['COTAS'], false, false)
  })

  it('highlight_entities sem zoom explicito faz zoom (default do servidor)', async () => {
    const { ui } = await dispatch(started('highlight_entities', { ids: ['5'] }))
    expect(ui.highlight).toHaveBeenCalledWith(['5'], '', true)
  })

  it('highlight_entities com zoom=false nao reenquadra', async () => {
    const { ui } = await dispatch(
      started('highlight_entities', { ids: ['5'], zoom: false }),
    )
    expect(ui.highlight).toHaveBeenCalledWith(['5'], '', false)
  })

  it('ignora highlight sem ids em vez de limpar o destaque atual', async () => {
    const { ui } = await dispatch(started('highlight_entities', { ids: [] }))
    expect(ui.highlight).not.toHaveBeenCalled()
  })

  it('ferramenta de consulta nao toca no viewer', async () => {
    const { ui, captured } = await dispatch(
      started('count_entities', { group_by: 'layer' }),
    )
    expect(captured.started).toEqual(['count_entities'])
    expect(Object.values(ui).every((fn) => fn.mock.calls.length === 0)).toBe(true)
  })

  it('encaminha RunError', async () => {
    const { captured } = await dispatch(frame({ event: 'RunError', error: 'boom' }))
    expect(captured.errors).toEqual(['boom'])
  })

  it('encaminha o raciocinio', async () => {
    const { captured } = await dispatch(
      frame({ event: 'ReasoningContentDelta', reasoning_content: 'hmm' }),
    )
    expect(captured.thinking).toBe('hmm')
  })

  it('ignora frames malformados sem derrubar o stream', async () => {
    const { captured } = await dispatch(
      'data: {isto nao e json\n\n' + frame({ event: 'RunContent', content: 'ok' }),
    )
    expect(captured.text).toBe('ok')
    expect(captured.errors).toEqual([])
  })
})

describe('rotulos das ferramentas', () => {
  it('traduz os nomes conhecidos', () => {
    expect(toolLabel('highlight_entities')).toBe('destacando no desenho')
    expect(toolLabel('count_entities')).toBe('contando entidades')
  })

  it('devolve o nome cru para o desconhecido', () => {
    expect(toolLabel('ferramenta_nova')).toBe('ferramenta_nova')
  })
})
