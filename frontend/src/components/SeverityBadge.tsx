import { CircleAlert, Info, TriangleAlert, type LucideIcon } from 'lucide-react'

import type { Severity } from '@/api/types'
import { SEVERITY_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

const STYLES: Record<Severity, { icon: LucideIcon; className: string }> = {
  high: { icon: TriangleAlert, className: 'text-sev-high bg-sev-high-bg border-sev-high-border' },
  medium: {
    icon: CircleAlert,
    className: 'text-sev-medium bg-sev-medium-bg border-sev-medium-border',
  },
  low: { icon: Info, className: 'text-sev-low bg-sev-low-bg border-sev-low-border' },
}

/** Severity is never color alone: color + icon + label. */
export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const { icon: Icon, className: tone } = STYLES[severity]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-xs font-semibold',
        tone,
        className,
      )}
    >
      <Icon aria-hidden className="size-3.5" strokeWidth={2.25} />
      {SEVERITY_LABELS[severity]}
    </span>
  )
}
