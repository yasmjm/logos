import { type FormEvent, useState } from 'react'

import type { IncidentCategory, IncidentDetail, IncidentUpdate, Severity } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/lib/labels'

const MIN = 5
const MAX = 2000

/** Edits a frozen snapshot: polling never touches the form, and the version sent is
 *  the one from when editing began (a change in between correctly answers 409). */
export function EditForm({
  snapshot,
  saving,
  onSave,
  onCancel,
}: {
  snapshot: IncidentDetail
  saving: boolean
  onSave: (changes: Omit<IncidentUpdate, 'version'>) => void
  onCancel: () => void
}) {
  const [severity, setSeverity] = useState<Severity>(snapshot.severity)
  const [category, setCategory] = useState<IncidentCategory>(snapshot.category)
  const [description, setDescription] = useState(snapshot.description)

  const trimmed = description.trim()
  const changes: Omit<IncidentUpdate, 'version'> = {
    ...(severity !== snapshot.severity && { severity }),
    ...(category !== snapshot.category && { category }),
    ...(trimmed !== snapshot.description && { description: trimmed }),
  }
  const invalid = trimmed.length < MIN || trimmed.length > MAX
  const unchanged = Object.keys(changes).length === 0

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!invalid && !unchanged) onSave(changes)
  }

  return (
    <form onSubmit={submit} className="grid gap-3 rounded-md border bg-surface-2 p-3" aria-label="Editar incidente">
      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="edit-severity">Criticidade</Label>
          <Select value={severity} onValueChange={(v) => setSeverity(v as Severity)}>
            <SelectTrigger id="edit-severity" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(SEVERITY_LABELS) as Severity[]).map((value) => (
                <SelectItem key={value} value={value}>
                  {SEVERITY_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="edit-category">Categoria</Label>
          <Select value={category} onValueChange={(v) => setCategory(v as IncidentCategory)}>
            <SelectTrigger id="edit-category" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(CATEGORY_LABELS) as IncidentCategory[]).map((value) => (
                <SelectItem key={value} value={value}>
                  {CATEGORY_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="edit-description">Descrição</Label>
        <Textarea
          id="edit-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          aria-invalid={invalid}
          aria-describedby="edit-description-help"
        />
        <p id="edit-description-help" className="text-xs text-text-subtle tabular-nums">
          {trimmed.length < MIN ? `Mínimo de ${MIN} caracteres.` : `${trimmed.length}/${MAX}`}
        </p>
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={saving || invalid || unchanged}>
          {saving ? 'Salvando…' : 'Salvar alterações'}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}
