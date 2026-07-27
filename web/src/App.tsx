import { useCallback, useMemo, useRef, useState } from 'react'

import { fetchEntityDetails, uploadDocument } from './api/client'
import type {
  BBox,
  EntityDetails,
  LoadedDocument,
  ToolUI,
  ViewRequest,
} from './api/types'
import { ChatPanel } from './components/ChatPanel'
import { SidePanel } from './components/SidePanel'
import { CadCanvas } from './viewer/CadCanvas'

const MIN_SPLIT = 22
const MAX_SPLIT = 70

export default function App() {
  const [loaded, setLoaded] = useState<LoadedDocument | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [hiddenLayers, setHiddenLayers] = useState<Set<string>>(new Set())
  const [highlighted, setHighlighted] = useState<Set<string>>(new Set())
  const [highlightLabel, setHighlightLabel] = useState('')
  const [selected, setSelected] = useState<EntityDetails | null>(null)
  const [viewRequest, setViewRequest] = useState<ViewRequest | null>(null)
  const [splitPct, setSplitPct] = useState(34)
  const [dragOver, setDragOver] = useState(false)

  const nonceRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  /** Um pedido de enquadramento sempre carrega um nonce novo, para que pedir a
   *  mesma região duas vezes reenquadre nas duas. */
  const requestView = useCallback((bbox: BBox | null) => {
    if (!bbox) return
    nonceRef.current += 1
    setViewRequest({ bbox, nonce: nonceRef.current })
  }, [])

  const bboxOfIds = useCallback(
    (ids: string[], document: LoadedDocument | null): BBox | null => {
      if (!document) return null

      let result: BBox | null = null
      for (const id of ids) {
        const entity = document.byId.get(id)
        if (!entity?.bbox) continue
        result = result
          ? [
              Math.min(result[0], entity.bbox[0]),
              Math.min(result[1], entity.bbox[1]),
              Math.max(result[2], entity.bbox[2]),
              Math.max(result[3], entity.bbox[3]),
            ]
          : entity.bbox
      }
      return result
    },
    [],
  )

  const openFile = async (file: File) => {
    setLoading(true)
    setError(null)

    try {
      const document = await uploadDocument(file)
      setLoaded(document)
      setHiddenLayers(new Set())
      setHighlighted(new Set())
      setHighlightLabel('')
      setSelected(null)
      setViewRequest(null)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc))
    } finally {
      setLoading(false)
    }
  }

  const pickEntity = async (id: string | null) => {
    if (!id || !loaded) {
      setSelected(null)
      return
    }
    try {
      setSelected(await fetchEntityDetails(loaded.info.document_id, id))
    } catch {
      setSelected(null)
    }
  }

  // O seam por onde as 4 ferramentas de interface da IA mutam a tela. Nada mais
  // no frontend fala com o canvas em nome do agente.
  const ui = useMemo<ToolUI>(
    () => ({
      highlight: (ids, label, zoom) => {
        setHighlighted(new Set(ids))
        setHighlightLabel(label)
        if (zoom) requestView(bboxOfIds(ids, loaded))
      },
      clearHighlight: () => {
        setHighlighted(new Set())
        setHighlightLabel('')
      },
      zoomToIds: (ids) => requestView(bboxOfIds(ids, loaded)),
      zoomToLayer: (name) => {
        const layer = loaded?.info.layers.find(
          (item) => item.name.toLowerCase() === name.toLowerCase(),
        )
        requestView(layer?.bbox ?? null)
      },
      zoomToBBox: (bbox) => requestView(bbox),
      zoomToAll: () => requestView(loaded?.info.bbox ?? null),
      setLayerVisibility: (layers, visible, isolate) => {
        if (!loaded) return

        const targets = new Set(
          layers
            .map(
              (name) =>
                loaded.info.layers.find(
                  (item) => item.name.toLowerCase() === name.toLowerCase(),
                )?.name,
            )
            .filter((name): name is string => Boolean(name)),
        )

        if (isolate) {
          setHiddenLayers(
            new Set(
              loaded.info.layers
                .map((item) => item.name)
                .filter((name) => !targets.has(name)),
            ),
          )
          return
        }

        setHiddenLayers((current) => {
          const next = new Set(current)
          for (const name of targets) {
            if (visible) next.delete(name)
            else next.add(name)
          }
          return next
        })
      },
    }),
    [loaded, bboxOfIds, requestView],
  )

  const startSplitDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault()
    const container = event.currentTarget.parentElement
    if (!container) return

    const move = (moveEvent: PointerEvent) => {
      const rect = container.getBoundingClientRect()
      const pct = ((moveEvent.clientX - rect.left) / rect.width) * 100
      setSplitPct(Math.min(MAX_SPLIT, Math.max(MIN_SPLIT, pct)))
    }
    const up = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }

    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }

  return (
    <div
      className={`app${dragOver ? ' drag-over' : ''}`}
      onDragOver={(event) => {
        event.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragOver(false)
        const file = event.dataTransfer.files?.[0]
        if (file) openFile(file)
      }}
    >
      <header className="topbar">
        <h1>Visualizador CAD</h1>
        <div className="topbar-actions">
          {loaded && <span className="filename">{loaded.info.filename}</span>}
          <input
            ref={fileInputRef}
            type="file"
            accept=".dxf,application/dxf,text/plain"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) openFile(file)
              event.target.value = ''
            }}
          />
          <button type="button" onClick={() => fileInputRef.current?.click()}>
            {loaded ? 'Trocar arquivo' : 'Abrir DXF'}
          </button>
        </div>
      </header>

      {error && (
        <div className="banner banner-error">
          {error}
          <button type="button" onClick={() => setError(null)}>
            fechar
          </button>
        </div>
      )}

      <div className="split">
        <div className="split-left" style={{ width: `${splitPct}%` }}>
          <ChatPanel document={loaded} ui={ui} />
        </div>

        <div className="divider" onPointerDown={startSplitDrag} />

        <div className="split-right">
          {loading && <div className="overlay">indexando desenho…</div>}

          {!loaded && !loading && (
            <div className="dropzone">
              <p>Arraste um arquivo .dxf aqui</p>
              <p className="hint">ou use o botão “Abrir DXF”</p>
            </div>
          )}

          {loaded && (
            <>
              <CadCanvas
                entities={loaded.entities}
                documentBBox={loaded.info.bbox}
                hiddenLayers={hiddenLayers}
                highlighted={highlighted}
                highlightLabel={highlightLabel}
                selectedId={selected?.id ?? null}
                viewRequest={viewRequest}
                onPick={pickEntity}
              />
              <SidePanel
                document={loaded}
                hiddenLayers={hiddenLayers}
                selected={selected}
                onToggleLayer={(name) =>
                  setHiddenLayers((current) => {
                    const next = new Set(current)
                    if (next.has(name)) next.delete(name)
                    else next.add(name)
                    return next
                  })
                }
                onIsolateLayer={(name) => ui.setLayerVisibility([name], true, true)}
                onShowAllLayers={() => setHiddenLayers(new Set())}
                onHideAllLayers={() =>
                  setHiddenLayers(new Set(loaded.info.layers.map((item) => item.name)))
                }
                onZoomToLayer={(name) => ui.zoomToLayer(name)}
                onZoomToSelected={() => {
                  if (selected?.bbox) requestView(selected.bbox)
                }}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
