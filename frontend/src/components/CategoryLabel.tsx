
import type { IncidentCategory } from '@/api/types'
import { CATEGORY_ICONS } from '@/lib/categoryIcons'
import { CATEGORY_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

/** Category as icon + label; `labelClassName` can hide the text on narrow layouts
 *  (it stays available to screen readers through the icon's title). */
export function CategoryLabel({
  category,
  className,
  labelClassName,
}: {
  category: IncidentCategory
  className?: string
  labelClassName?: string
}) {
  const Icon = CATEGORY_ICONS[category]
  const label = CATEGORY_LABELS[category]
  return (
    <span className={cn('inline-flex min-w-0 items-center gap-1.5', className)} title={label}>
      <Icon aria-hidden className="size-4 shrink-0 text-text-muted" />
      <span className={cn('truncate', labelClassName)}>{label}</span>
    </span>
  )
}
