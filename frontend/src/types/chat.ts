export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceItem[]
  status?: 'sending' | 'done' | 'error'
  createdAt: string
}

export interface SourceItem {
  chunkId: string
  content: string
  score: number
}

export interface ChatResponse {
  id: string
  reply: string
  sources: SourceItem[]
  traceId: string
  createdAt: string
}
