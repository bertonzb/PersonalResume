export type AgentStatus = 'thinking' | 'acting' | 'observing' | 'done' | 'error'

export interface AgentStep {
  stepNumber: number
  toolName: string
  input: string
  output: string
  status: AgentStatus
  durationMs: number
}
