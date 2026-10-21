import { RadioTower } from 'lucide-react'

export function LogoMark() {
  return (
    <span className="inline-flex items-center gap-2 font-semibold tracking-tight text-text">
      <span className="inline-flex size-7 items-center justify-center rounded-md border border-border-strong bg-surface-2">
        <RadioTower aria-hidden className="size-4" />
      </span>
      Logos
    </span>
  )
}
