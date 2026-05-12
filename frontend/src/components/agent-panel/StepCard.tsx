import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  SearchOutlined,
  FileTextOutlined,
  GlobalOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { cn } from '@/lib/utils'
import type { AgentStep } from '@/types/agent'

export interface StepCardProps {
  step: AgentStep
  className?: string
}

const toolIcons: Record<string, React.ReactNode> = {
  doc_retrieval: <SearchOutlined />,
  web_search: <GlobalOutlined />,
  doc_summary: <FileTextOutlined />,
}

const statusIcons: Record<string, React.ReactNode> = {
  done: <CheckCircleOutlined className="text-green-500" />,
  error: <CloseCircleOutlined className="text-red-500" />,
  thinking: <LoadingOutlined className="text-blue-400" />,
  acting: <LoadingOutlined className="text-orange-400" />,
  observing: <LoadingOutlined className="text-purple-400" />,
}

export function StepCard({ step, className }: StepCardProps) {
  const icon = toolIcons[step.toolName] || <ToolOutlined />

  return (
    <div className={cn('rounded-lg border p-3 text-sm', className)}>
      <div className="mb-1 flex items-center gap-2">
        <span className="text-base">{icon}</span>
        <span className="font-medium">{step.toolName}</span>
        {statusIcons[step.status]}
        <span className="ml-auto text-xs text-gray-400">
          {step.durationMs > 0 ? `${(step.durationMs / 1000).toFixed(1)}s` : ''}
        </span>
      </div>
      <div className="mt-1 space-y-1">
        <div>
          <span className="text-gray-400">入参: </span>
          <span className="text-gray-600">{step.input?.slice(0, 100) || '—'}</span>
        </div>
        <div>
          <span className="text-gray-400">出参: </span>
          <span className="text-gray-600">{step.output?.slice(0, 100) || '—'}</span>
        </div>
      </div>
    </div>
  )
}
