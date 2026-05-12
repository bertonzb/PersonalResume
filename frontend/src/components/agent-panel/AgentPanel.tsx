import { Empty } from 'antd'
import { cn } from '@/lib/utils'
import type { AgentStep } from '@/types/agent'
import { StepCard } from './StepCard'

export interface AgentPanelProps {
  steps: AgentStep[]
  loading?: boolean
  className?: string
}

export function AgentPanel({ steps, loading, className }: AgentPanelProps) {
  return (
    <div className={cn('rounded-lg bg-gray-50 p-4', className)}>
      <h3 className="mb-3 text-sm font-medium text-gray-500">Agent 执行过程</h3>

      {steps.length === 0 && !loading && (
        <Empty description="暂无执行步骤" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      <div className="space-y-2">
        {steps.map((step, idx) => (
          <StepCard key={`${step.toolName}-${idx}`} step={step} />
        ))}
      </div>

      {loading && (
        <div className="mt-2 text-center text-sm text-gray-400">思考中...</div>
      )}
    </div>
  )
}
