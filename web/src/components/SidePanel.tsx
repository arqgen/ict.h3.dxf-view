import { useState } from 'react'

import type { EntityDetails, LoadedDocument } from '../api/types'

interface Props {
  document: LoadedDocument
  hiddenLayers: Set<string>
  selected: EntityDetails | null
  onToggleLayer: (name: string) => void
  onIsolateLayer: (name: string) => void
  onShowAllLayers: () => void
  onHideAllLayers: () => void
  onZoomToLayer: (name: string) => void
  onZoomToSelected: () => void
}

type Tab = 'layers' | 'info'

export function SidePanel({
  document: loaded,
  hiddenLayers,
  selected,
  onToggleLayer,
  onIsolateLayer,
  onShowAllLayers,
  onHideAllLayers,
  onZoomToLayer,
  onZoomToSelected,
}: Props) {
  const [tab, setTab] = useState<Tab>('layers')
  const [filter, setFilter] = useState('')

  const { info } = loaded
  const needle = filter.trim().toLowerCase()
  const layers = needle
    ? info.layers.filter((layer) => layer.name.toLowerCase().includes(needle))
    : info.layers

  return (
    <aside className="side">
      <nav className="tabs">
        <button
          type="button"
          className={tab === 'layers' ? 'active' : ''}
          onClick={() => setTab('layers')}
        >
          Layers
        </button>
        <button
          type="button"
          className={tab === 'info' ? 'active' : ''}
          onClick={() => setTab('info')}
        >
          Info
        </button>
      </nav>

      {tab === 'layers' && (
        <div className="side-body">
          <input
            type="search"
            placeholder="filtrar layers…"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
          <div className="row-actions">
            <button type="button" onClick={onShowAllLayers}>
              mostrar todos
            </button>
            <button type="button" onClick={onHideAllLayers}>
              ocultar todos
            </button>
          </div>

          <ul className="layer-list">
            {layers.map((layer) => (
              <li key={layer.name}>
                <label>
                  <input
                    type="checkbox"
                    checked={!hiddenLayers.has(layer.name)}
                    onChange={() => onToggleLayer(layer.name)}
                  />
                  <span className="swatch" style={{ background: layer.color }} />
                  <span className="layer-name" title={layer.name}>
                    {layer.name}
                  </span>
                  <span className="layer-count">{layer.count}</span>
                </label>
                <div className="layer-buttons">
                  <button
                    type="button"
                    title="Isolar este layer"
                    onClick={() => onIsolateLayer(layer.name)}
                  >
                    isolar
                  </button>
                  <button
                    type="button"
                    title="Enquadrar este layer"
                    disabled={!layer.bbox}
                    onClick={() => onZoomToLayer(layer.name)}
                  >
                    zoom
                  </button>
                </div>
                {layer.frozen && <span className="badge">congelada</span>}
              </li>
            ))}
            {!layers.length && <li className="empty">nenhum layer encontrado</li>}
          </ul>
        </div>
      )}

      {tab === 'info' && (
        <div className="side-body">
          <dl className="info">
            <dt>Arquivo</dt>
            <dd>{info.filename}</dd>
            <dt>Versão</dt>
            <dd>{info.acad_version}</dd>
            <dt>Unidade</dt>
            <dd>{info.units}</dd>
            <dt>Entidades</dt>
            <dd>{info.entity_count}</dd>
            <dt>Layers</dt>
            <dd>{info.layer_count}</dd>
            <dt>Blocos</dt>
            <dd>
              {info.block_count} ({info.insert_count} inserções)
            </dd>
            <dt>Extensão</dt>
            <dd>{info.bbox ? formatBBox(info.bbox) : '—'}</dd>
          </dl>

          <h3>Entidades por tipo</h3>
          <ul className="type-list">
            {Object.entries(info.by_type).map(([type, count]) => (
              <li key={type}>
                <span>{type}</span>
                <span>{count}</span>
              </li>
            ))}
          </ul>

          {info.warnings.length > 0 && (
            <>
              <h3>Avisos do parser</h3>
              <ul className="warnings">
                {info.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {selected && (
        <div className="selection">
          <header>
            <h3>Entidade {selected.id}</h3>
            <button type="button" onClick={onZoomToSelected}>
              dar zoom nesta
            </button>
          </header>
          <dl className="info">
            <dt>Tipo</dt>
            <dd>{selected.type}</dd>
            <dt>Layer</dt>
            <dd>{selected.layer}</dd>
            {selected.block && (
              <>
                <dt>Bloco</dt>
                <dd>{selected.block}</dd>
              </>
            )}
            {selected.length !== null && (
              <>
                <dt>Comprimento</dt>
                <dd>
                  ~{round(selected.length)} {shortUnit(loaded.info.units)}
                </dd>
              </>
            )}
            {selected.area !== null && (
              <>
                <dt>Área</dt>
                <dd>
                  ~{round(selected.area)} {shortUnit(loaded.info.units)}²
                </dd>
              </>
            )}
            {selected.text && (
              <>
                <dt>Texto</dt>
                <dd className="mono">{selected.text}</dd>
              </>
            )}
          </dl>

          <details>
            <summary>props DXF</summary>
            <pre className="raw">{JSON.stringify(selected.raw, null, 2)}</pre>
          </details>
        </div>
      )}
    </aside>
  )
}

function formatBBox(bbox: [number, number, number, number]): string {
  const [minX, minY, maxX, maxY] = bbox
  return `${round(minX)}, ${round(minY)} → ${round(maxX)}, ${round(maxY)}`
}

function round(value: number): string {
  return value.toFixed(3).replace(/\.?0+$/, '')
}

/** Abreviação para caber ao lado de um número no painel. */
function shortUnit(units: string): string {
  const map: Record<string, string> = {
    metros: 'm',
    centimetros: 'cm',
    milimetros: 'mm',
    polegadas: 'in',
    pes: 'ft',
    quilometros: 'km',
  }
  return map[units] ?? 'un'
}
