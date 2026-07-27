import { useCallback, useEffect, useRef } from 'react'

import type { BBox, PrimEntity, Shape, ViewRequest } from '../api/types'

const HIGHLIGHT_COLOR = '#ff9500'
const SELECT_COLOR = '#22d3ee'
const AXIS_COLOR = '#2a3038'
const BACKGROUND = '#0e1116'

/** Acima disto o desenho fica ilegível e o custo de layout de texto domina o
 *  frame. Um DXF de arquitetura passa fácil de 20 mil textos. */
const MAX_TEXT_DRAW = 3000

/** Altura mínima em pixels para valer a pena desenhar um texto. */
const MIN_TEXT_PX = 6

const FIT_PADDING = 0.06
const PICK_TOLERANCE_PX = 6

interface Camera {
  cx: number
  cy: number
  scale: number
}

interface Props {
  entities: PrimEntity[]
  documentBBox: BBox | null
  hiddenLayers: Set<string>
  highlighted: Set<string>
  highlightLabel: string
  selectedId: string | null
  viewRequest: ViewRequest | null
  onPick: (id: string | null) => void
}

export function CadCanvas({
  entities,
  documentBBox,
  hiddenLayers,
  highlighted,
  highlightLabel,
  selectedId,
  viewRequest,
  onPick,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const cameraRef = useRef<Camera>({ cx: 0, cy: 0, scale: 1 })
  const sizeRef = useRef({ width: 1, height: 1 })

  // O draw mais recente vive numa ref. Um `useCallback([])` congelaria a
  // closure do primeiro render e o canvas pararia de refletir novas props —
  // com o agravante de nao dar erro nenhum, so parar de atualizar.
  const drawRef = useRef<() => void>(() => {})
  const frameRef = useRef<number | null>(null)

  const requestDraw = useCallback(() => {
    if (frameRef.current !== null) return
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null
      drawRef.current()
    })
  }, [])

  const toWorld = useCallback((px: number, py: number): [number, number] => {
    const { cx, cy, scale } = cameraRef.current
    const { width, height } = sizeRef.current
    return [cx + (px - width / 2) / scale, cy - (py - height / 2) / scale]
  }, [])

  const fitBBox = useCallback(
    (bbox: BBox | null) => {
      const { width, height } = sizeRef.current
      if (!bbox) return

      const [minX, minY, maxX, maxY] = bbox
      const boxWidth = Math.max(maxX - minX, 1e-9)
      const boxHeight = Math.max(maxY - minY, 1e-9)

      const scale = Math.min(width / boxWidth, height / boxHeight) * (1 - FIT_PADDING)

      cameraRef.current = {
        cx: (minX + maxX) / 2,
        cy: (minY + maxY) / 2,
        scale: Number.isFinite(scale) && scale > 0 ? scale : 1,
      }
      requestDraw()
    },
    [requestDraw],
  )

  // --- desenho ----------------------------------------------------------- //

  drawRef.current = () => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    const dpr = window.devicePixelRatio || 1
    const { width, height } = sizeRef.current
    const { cx, cy, scale } = cameraRef.current

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.fillStyle = BACKGROUND
    ctx.fillRect(0, 0, width, height)

    const toScreenX = (x: number) => width / 2 + (x - cx) * scale
    const toScreenY = (y: number) => height / 2 - (y - cy) * scale

    drawAxes(ctx, toScreenX, toScreenY, width, height)

    // Viewport em coordenadas de mundo, para descartar o que está fora.
    const viewport: BBox = [
      cx - width / 2 / scale,
      cy - height / 2 / scale,
      cx + width / 2 / scale,
      cy + height / 2 / scale,
    ]

    // Um Path2D por cor e um único stroke por cor: sem isso um DXF de 100 mil
    // entidades faria 100 mil chamadas de stroke e o pan ficaria inutilizável.
    const paths = new Map<string, Path2D>()
    const texts: { entity: PrimEntity; shape: Extract<Shape, { k: 't' }> }[] = []
    const visible: PrimEntity[] = []

    for (const entity of entities) {
      if (hiddenLayers.has(entity.layer)) continue
      if (entity.bbox && !intersects(entity.bbox, viewport)) continue

      visible.push(entity)

      let path = paths.get(entity.color)
      if (!path) {
        path = new Path2D()
        paths.set(entity.color, path)
      }

      for (const shape of entity.shapes) {
        if (shape.k === 't') {
          texts.push({ entity, shape })
        } else {
          addShape(path, shape, toScreenX, toScreenY)
        }
      }
    }

    ctx.lineWidth = 1
    for (const [color, path] of paths) {
      ctx.strokeStyle = color
      ctx.stroke(path)
    }

    drawTexts(ctx, texts, toScreenX, toScreenY, scale)

    // Destaque e seleção por cima de tudo.
    drawOverlay(
      ctx,
      visible.filter((entity) => highlighted.has(entity.id)),
      HIGHLIGHT_COLOR,
      toScreenX,
      toScreenY,
    )

    const selected = selectedId
      ? visible.find((entity) => entity.id === selectedId)
      : undefined
    if (selected) {
      drawOverlay(ctx, [selected], SELECT_COLOR, toScreenX, toScreenY)
    }

    if (highlightLabel && highlighted.size > 0) {
      drawLabel(ctx, `${highlightLabel} (${highlighted.size})`)
    }
  }

  // --- ciclo de vida ------------------------------------------------------ //

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const observer = new ResizeObserver(() => {
      const rect = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1

      sizeRef.current = {
        width: Math.max(rect.width, 1),
        height: Math.max(rect.height, 1),
      }
      canvas.width = Math.round(sizeRef.current.width * dpr)
      canvas.height = Math.round(sizeRef.current.height * dpr)

      requestDraw()
    })

    observer.observe(canvas)
    return () => observer.disconnect()
  }, [requestDraw])

  // Documento novo: enquadra tudo.
  useEffect(() => {
    fitBBox(documentBBox)
  }, [documentBBox, fitBBox])

  // Pedido de reenquadramento (do painel ou da IA). Depende do nonce, não só do
  // bbox, para que o mesmo enquadramento possa ser pedido duas vezes.
  useEffect(() => {
    if (viewRequest) fitBBox(viewRequest.bbox)
  }, [viewRequest?.nonce, viewRequest, fitBBox])

  useEffect(() => {
    requestDraw()
  }, [entities, hiddenLayers, highlighted, highlightLabel, selectedId, requestDraw])

  // --- interação ---------------------------------------------------------- //

  const dragRef = useRef<{
    pointerId: number
    lastX: number
    lastY: number
    moved: boolean
  } | null>(null)

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = {
      pointerId: event.pointerId,
      lastX: event.clientX,
      lastY: event.clientY,
      moved: false,
    }
  }

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return

    const dx = event.clientX - drag.lastX
    const dy = event.clientY - drag.lastY
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) drag.moved = true

    drag.lastX = event.clientX
    drag.lastY = event.clientY

    const { scale } = cameraRef.current
    cameraRef.current.cx -= dx / scale
    cameraRef.current.cy += dy / scale
    requestDraw()
  }

  const onPointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current
    dragRef.current = null
    if (!drag) return

    // Clique sem arrasto é seleção; com arrasto foi pan.
    if (drag.moved) return

    const rect = event.currentTarget.getBoundingClientRect()
    const [wx, wy] = toWorld(event.clientX - rect.left, event.clientY - rect.top)
    onPick(pick(entities, hiddenLayers, wx, wy, cameraRef.current.scale))
  }

  const onWheel = (event: React.WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault()

    const rect = event.currentTarget.getBoundingClientRect()
    const px = event.clientX - rect.left
    const py = event.clientY - rect.top
    const [beforeX, beforeY] = toWorld(px, py)

    const factor = Math.exp(-event.deltaY * 0.0015)
    cameraRef.current.scale = clamp(cameraRef.current.scale * factor, 1e-6, 1e9)

    // Mantém sob o cursor o mesmo ponto do desenho que estava antes do zoom.
    const [afterX, afterY] = toWorld(px, py)
    cameraRef.current.cx += beforeX - afterX
    cameraRef.current.cy += beforeY - afterY

    requestDraw()
  }

  const zoomByButton = (factor: number) => {
    cameraRef.current.scale = clamp(cameraRef.current.scale * factor, 1e-6, 1e9)
    requestDraw()
  }

  return (
    <div className="canvas-wrap">
      <canvas
        ref={canvasRef}
        className="cad-canvas"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
      />
      <div className="canvas-controls">
        <button type="button" onClick={() => zoomByButton(1.25)} title="Aproximar">
          +
        </button>
        <button type="button" onClick={() => zoomByButton(0.8)} title="Afastar">
          −
        </button>
        <button
          type="button"
          onClick={() => fitBBox(documentBBox)}
          title="Enquadrar tudo"
        >
          ⤢
        </button>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------- //
// Desenho
// --------------------------------------------------------------------------- //

function addShape(
  path: Path2D,
  shape: Shape,
  toScreenX: (x: number) => number,
  toScreenY: (y: number) => number,
): void {
  if (shape.k === 'p') {
    const pts = shape.pts
    if (pts.length < 2) return

    path.moveTo(toScreenX(pts[0][0]), toScreenY(pts[0][1]))
    for (let i = 1; i < pts.length; i += 1) {
      path.lineTo(toScreenX(pts[i][0]), toScreenY(pts[i][1]))
    }
    // Os pontos vêm sem o vértice de fechamento duplicado (normalizado no
    // servidor), então o fechamento é feito aqui.
    if (shape.c) path.closePath()
    return
  }

  if (shape.k === 'd') {
    const x = toScreenX(shape.p[0])
    const y = toScreenY(shape.p[1])
    path.moveTo(x - 2, y)
    path.lineTo(x + 2, y)
    path.moveTo(x, y - 2)
    path.lineTo(x, y + 2)
  }
}

function drawTexts(
  ctx: CanvasRenderingContext2D,
  texts: { entity: PrimEntity; shape: Extract<Shape, { k: 't' }> }[],
  toScreenX: (x: number) => number,
  toScreenY: (y: number) => number,
  scale: number,
): void {
  ctx.textBaseline = 'alphabetic'

  let drawn = 0
  for (const { entity, shape } of texts) {
    if (drawn >= MAX_TEXT_DRAW) break

    const pixelHeight = shape.h * scale
    if (pixelHeight < MIN_TEXT_PX) continue

    ctx.save()
    ctx.translate(toScreenX(shape.p[0]), toScreenY(shape.p[1]))
    if (shape.r) ctx.rotate((-shape.r * Math.PI) / 180)
    ctx.fillStyle = entity.color
    ctx.font = `${pixelHeight.toFixed(1)}px sans-serif`

    // MTEXT pode ter várias linhas; desenhamos de baixo para cima a partir da
    // âncora, como o AutoCAD faz.
    const lines = shape.s.split('\n')
    for (let i = 0; i < lines.length; i += 1) {
      ctx.fillText(lines[i], 0, -i * pixelHeight * 1.2)
    }

    ctx.restore()
    drawn += 1
  }
}

function drawOverlay(
  ctx: CanvasRenderingContext2D,
  entities: PrimEntity[],
  color: string,
  toScreenX: (x: number) => number,
  toScreenY: (y: number) => number,
): void {
  if (!entities.length) return

  const path = new Path2D()
  for (const entity of entities) {
    for (const shape of entity.shapes) {
      addShape(path, shape, toScreenX, toScreenY)
    }
  }

  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = 2.5
  ctx.stroke(path)

  // Caixa tracejada: entidades pequenas ficariam invisíveis só pelo traço, e a
  // espessura de linha no canvas não escala o suficiente para chamar atenção.
  ctx.setLineDash([4, 4])
  ctx.lineWidth = 1
  ctx.globalAlpha = 0.45
  for (const entity of entities) {
    if (!entity.bbox) continue
    const [minX, minY, maxX, maxY] = entity.bbox
    const x = toScreenX(minX)
    const y = toScreenY(maxY)
    ctx.strokeRect(x, y, toScreenX(maxX) - x, toScreenY(minY) - y)
  }
  ctx.restore()
}

function drawAxes(
  ctx: CanvasRenderingContext2D,
  toScreenX: (x: number) => number,
  toScreenY: (y: number) => number,
  width: number,
  height: number,
): void {
  ctx.save()
  ctx.strokeStyle = AXIS_COLOR
  ctx.lineWidth = 1

  const originY = toScreenY(0)
  const originX = toScreenX(0)

  ctx.beginPath()
  if (originY >= 0 && originY <= height) {
    ctx.moveTo(0, originY)
    ctx.lineTo(width, originY)
  }
  if (originX >= 0 && originX <= width) {
    ctx.moveTo(originX, 0)
    ctx.lineTo(originX, height)
  }
  ctx.stroke()
  ctx.restore()
}

function drawLabel(ctx: CanvasRenderingContext2D, text: string): void {
  ctx.save()
  ctx.font = '12px sans-serif'
  const padding = 8
  const metrics = ctx.measureText(text)

  ctx.fillStyle = 'rgba(255, 149, 0, 0.15)'
  ctx.strokeStyle = HIGHLIGHT_COLOR
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.rect(12, 12, metrics.width + padding * 2, 26)
  ctx.fill()
  ctx.stroke()

  ctx.fillStyle = HIGHLIGHT_COLOR
  ctx.textBaseline = 'middle'
  ctx.fillText(text, 12 + padding, 12 + 13)
  ctx.restore()
}

// --------------------------------------------------------------------------- //
// Hit-test
// --------------------------------------------------------------------------- //

function pick(
  entities: PrimEntity[],
  hiddenLayers: Set<string>,
  wx: number,
  wy: number,
  scale: number,
): string | null {
  // Tolerância constante em pixels, convertida para unidades de mundo: clicar
  // "perto" tem de significar a mesma coisa em qualquer nível de zoom.
  const tolerance = PICK_TOLERANCE_PX / scale

  let best: string | null = null
  let bestDistance = tolerance

  for (const entity of entities) {
    if (hiddenLayers.has(entity.layer)) continue

    // Descarte barato antes da distância ponto-segmento.
    if (entity.bbox && !insideExpanded(entity.bbox, wx, wy, tolerance)) continue

    for (const shape of entity.shapes) {
      const distance = distanceToShape(shape, wx, wy)
      if (distance <= bestDistance) {
        bestDistance = distance
        best = entity.id
      }
    }
  }

  return best
}

function distanceToShape(shape: Shape, wx: number, wy: number): number {
  if (shape.k === 'p') {
    const pts = shape.pts
    let min = Infinity

    for (let i = 0; i < pts.length - 1; i += 1) {
      min = Math.min(min, distanceToSegment(wx, wy, pts[i], pts[i + 1]))
    }
    if (shape.c && pts.length > 2) {
      min = Math.min(min, distanceToSegment(wx, wy, pts[pts.length - 1], pts[0]))
    }
    if (pts.length === 1) {
      min = Math.hypot(wx - pts[0][0], wy - pts[0][1])
    }
    return min
  }

  return Math.hypot(wx - shape.p[0], wy - shape.p[1])
}

function distanceToSegment(
  px: number,
  py: number,
  a: [number, number],
  b: [number, number],
): number {
  const dx = b[0] - a[0]
  const dy = b[1] - a[1]

  if (dx === 0 && dy === 0) return Math.hypot(px - a[0], py - a[1])

  let t = ((px - a[0]) * dx + (py - a[1]) * dy) / (dx * dx + dy * dy)
  t = clamp(t, 0, 1)

  return Math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))
}

// --------------------------------------------------------------------------- //

function intersects(a: BBox, b: BBox): boolean {
  return !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3])
}

function insideExpanded(bbox: BBox, x: number, y: number, pad: number): boolean {
  return (
    x >= bbox[0] - pad && x <= bbox[2] + pad && y >= bbox[1] - pad && y <= bbox[3] + pad
  )
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}
