import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { NewIncidentDialog } from '@/features/incident/NewIncidentDialog'

/** Typing in a field, or a dialog already open: N is just a letter there. */
function shortcutAllowed(event: KeyboardEvent): boolean {
  if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) return false
  const target = event.target as HTMLElement | null
  if (target?.closest('input, textarea, select, [contenteditable="true"], [role="combobox"]')) return false
  return !document.querySelector('[role="dialog"], [role="alertdialog"], [role="menu"]')
}

/** "Novo incidente" in the header; shortcut N. */
export function NewIncidentButton() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() !== 'n' || !shortcutAllowed(event)) return
      event.preventDefault()
      setOpen(true)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)} aria-keyshortcuts="N" title="Novo incidente (N)">
        <Plus aria-hidden />
        <span className="sr-only sm:not-sr-only">Novo incidente</span>
      </Button>
      <NewIncidentDialog open={open} onOpenChange={setOpen} />
    </>
  )
}
