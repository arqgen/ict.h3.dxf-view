// Espelha os payloads de src/api/models/document.py e os eventos do agno.

export type BBox = [number, number, number, number]

/** Primitivas achatadas. As chaves sao curtas porque o payload de um DXF
 *  grande e dominado por elas. */
export type Shape =
  | { k: 'p'; pts: [number, number][]; c: boolean }
  | { k: 'd'; p: [number, number] }
  | { k: 't'; p: [number, number]; s: string; h: number; r: number }

export interface PrimEntity {
  id: string
  type: string
  layer: string
  color: string
  bbox: BBox | null
  shapes: Shape[]
}

export interface LayerInfo {
  name: string
  color: string
  count: number
  by_type: Record<string, number>
  bbox: BBox | null
  frozen: boolean
  on: boolean
}

export interface DocumentInfo {
  document_id: string
  filename: string
  units: string
  acad_version: string
  bbox: BBox | null
  entity_count: number
  layer_count: number
  block_count: number
  insert_count: number
  by_type: Record<string, number>
  layers: LayerInfo[]
  warnings: string[]
}

export interface EntityDetails {
  id: string
  type: string
  layer: string
  color: string
  bbox: BBox | null
  closed: boolean
  length: number | null
  area: number | null
  text: string | null
  block: string | null
  raw: Record<string, unknown>
}

/** O documento carregado: metadados + geometria + indice por id. */
export interface LoadedDocument {
  info: DocumentInfo
  entities: PrimEntity[]
  byId: Map<string, PrimEntity>
}

// --------------------------------------------------------------------------
// Eventos do agno encaminhados pelo SSE
// --------------------------------------------------------------------------

export interface ToolExecution {
  tool_call_id?: string
  tool_name: string
  tool_args?: Record<string, unknown>
  result?: string | null
  tool_call_error?: boolean
}

export interface AgnoEvent {
  event: string
  content?: string
  reasoning_content?: string
  tool?: ToolExecution
  error?: string
}

/** Pedido de reenquadramento. O `nonce` existe porque a IA pode pedir zoom na
 *  MESMA regiao duas vezes — sem ele o efeito nao se repetiria. */
export interface ViewRequest {
  bbox: BBox
  nonce: number
}

/** O unico ponto por onde uma acao da IA muta a interface.
 *
 *  Cada alvo de zoom tem seu proprio metodo em vez de um `zoomTo(bbox)` unico
 *  porque quem sabe resolver um id ou um nome de layer em bbox e o `App`, que
 *  tem o documento carregado — nao o parser do stream. */
export interface ToolUI {
  highlight: (ids: string[], label: string, zoom: boolean) => void
  clearHighlight: () => void
  zoomToIds: (ids: string[]) => void
  zoomToLayer: (layer: string) => void
  zoomToBBox: (bbox: BBox) => void
  zoomToAll: () => void
  setLayerVisibility: (layers: string[], visible: boolean, isolate: boolean) => void
}

export type ChatBlock =
  | { kind: 'text'; text: string }
  | { kind: 'thinking'; text: string }
  | { kind: 'tool'; name: string; label: string; summary: string | null; error: boolean }

export interface ChatMessage {
  role: 'user' | 'assistant'
  blocks: ChatBlock[]
}
