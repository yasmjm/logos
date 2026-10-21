import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LoaderCircle } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { toast } from 'sonner'

import { ApiError } from '@/api/errors'
import { createManualIncident, fetchFleetTrucks } from '@/api/incidents'
import type { IncidentCategory, ManualIncidentInput, Severity } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useQueueFilters } from '@/features/queue/useQueueFilters'
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/lib/labels'

type Field = 'truck_code' | 'category' | 'severity' | 'description' | 'highway' | 'km' | 'location_note'
type Form = Record<Field, string>
type Errors = Partial<Record<Field, string>>

const EMPTY: Form = { truck_code: '', category: '', severity: '', description: '', highway: '', km: '', location_note: '' }
const DESCRIPTION_MIN = 5
const FIELDS = Object.keys(EMPTY) as Field[]

/** Essential fields, checked as the analyst types (the API checks them again). */
function validate(form: Form): Errors {
  const errors: Errors = {}
  if (!form.truck_code.trim()) errors.truck_code = 'Informe o código do caminhão.'
  else if (form.truck_code.trim().length > 20) errors.truck_code = 'Use no máximo 20 caracteres.'
  if (!form.category) errors.category = 'Escolha a categoria.'
  if (!form.severity) errors.severity = 'Escolha a criticidade.'
  if (form.description.trim().length < DESCRIPTION_MIN) errors.description = `Descreva com pelo menos ${DESCRIPTION_MIN} caracteres.`
  return errors
}

/** 422 problem+json: each error names its field ("field 'truck_code'"). */
function fieldErrors(error: unknown): { fields: Errors; other: string | null } {
  if (!(error instanceof ApiError)) return { fields: {}, other: 'Não foi possível registrar. Nada foi criado; tente de novo.' }
  if (error.status !== 422) return { fields: {}, other: `${error.detail} Nada foi criado.` }
  const fields: Errors = {}
  const rest: string[] = []
  for (const item of error.body?.errors ?? []) {
    const name = /field '([a-z_]+)'/.exec(item.location)?.[1] as Field | undefined
    if (name && FIELDS.includes(name)) fields[name] ??= item.message
    else rest.push(item.message)
  }
  return { fields, other: rest.length ? rest.join(' ') : null }
}

export function NewIncidentDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
        {open && <NewIncidentForm onDone={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function NewIncidentForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const { selectIncident } = useQueueFilters()
  const fleet = useQuery({ queryKey: ['fleet'], queryFn: fetchFleetTrucks, staleTime: 5 * 60_000 })
  const [form, setForm] = useState<Form>(EMPTY)
  const [touched, setTouched] = useState<Partial<Record<Field, boolean>>>({})
  const [submitted, setSubmitted] = useState(false)
  const [serverErrors, setServerErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<string | null>(null)

  const local = validate(form)
  const shown = (field: Field) => serverErrors[field] ?? ((touched[field] || submitted) ? local[field] : undefined)

  const create = useMutation({
    mutationFn: createManualIncident,
    retry: false, // a write: never repeated automatically
    onSuccess: (incident) => {
      toast.success(`Incidente registrado: ${incident.truck_code}`)
      // Refetch: the new row arrives with the highlight, and its panel opens.
      void queryClient.invalidateQueries({ queryKey: ['incidents'] })
      selectIncident(incident.id)
      onDone()
    },
    onError: (error) => {
      const { fields, other } = fieldErrors(error)
      setServerErrors(fields)
      setFormError(other)
    },
  })

  const set = (field: Field, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    setServerErrors((current) => {
      const next = { ...current }
      delete next[field]
      return next
    })
  }
  const touch = (field: Field) => setTouched((current) => ({ ...current, [field]: true }))

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setSubmitted(true)
    setFormError(null)
    if (Object.keys(local).length || create.isPending) return
    const optional = (value: string) => value.trim() || undefined
    const body: ManualIncidentInput = {
      truck_code: form.truck_code.trim().toUpperCase(),
      category: form.category as IncidentCategory,
      severity: form.severity as Severity,
      description: form.description.trim(),
      highway: optional(form.highway),
      km: optional(form.km),
      location_note: optional(form.location_note),
    }
    create.mutate(body)
  }

  const describedBy = (field: Field) => (shown(field) ? `new-${field}-error` : undefined)
  const errorText = (field: Field) =>
    shown(field) ? (
      <p id={`new-${field}-error`} className="text-xs text-danger">
        {shown(field)}
      </p>
    ) : null

  return (
    <form onSubmit={submit} noValidate className="grid gap-4">
      <DialogHeader>
        <DialogTitle>Novo incidente</DialogTitle>
        <DialogDescription>Registro manual, por exemplo quando o motorista liga para a central.</DialogDescription>
      </DialogHeader>

      <div className="grid gap-1.5">
        <Label htmlFor="new-truck_code">Caminhão</Label>
        <Input
          id="new-truck_code"
          list="new-fleet"
          autoComplete="off"
          placeholder="TRK-1001"
          className="font-mono"
          value={form.truck_code}
          onChange={(event) => set('truck_code', event.target.value)}
          onBlur={() => touch('truck_code')}
          aria-invalid={Boolean(shown('truck_code'))}
          aria-describedby={describedBy('truck_code')}
          autoFocus
        />
        <datalist id="new-fleet">
          {fleet.data?.map((truck) => (
            <option key={truck.code} value={truck.code}>
              {truck.client_name}
            </option>
          ))}
        </datalist>
        {errorText('truck_code')}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label htmlFor="new-category">Categoria</Label>
          <Select value={form.category} onValueChange={(value) => (set('category', value), touch('category'))}>
            <SelectTrigger id="new-category" className="w-full" aria-invalid={Boolean(shown('category'))} aria-describedby={describedBy('category')}>
              <SelectValue placeholder="Escolha" />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(CATEGORY_LABELS) as IncidentCategory[]).map((category) => (
                <SelectItem key={category} value={category}>
                  {CATEGORY_LABELS[category]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errorText('category')}
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="new-severity">Criticidade</Label>
          <Select value={form.severity} onValueChange={(value) => (set('severity', value), touch('severity'))}>
            <SelectTrigger id="new-severity" className="w-full" aria-invalid={Boolean(shown('severity'))} aria-describedby={describedBy('severity')}>
              <SelectValue placeholder="Escolha" />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(SEVERITY_LABELS) as Severity[]).map((severity) => (
                <SelectItem key={severity} value={severity}>
                  {SEVERITY_LABELS[severity]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errorText('severity')}
        </div>
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="new-description">Descrição</Label>
        <Textarea
          id="new-description"
          rows={3}
          maxLength={2000}
          value={form.description}
          onChange={(event) => set('description', event.target.value)}
          onBlur={() => touch('description')}
          aria-invalid={Boolean(shown('description'))}
          aria-describedby={describedBy('description')}
        />
        {errorText('description')}
      </div>

      <fieldset className="grid gap-3">
        <legend className="mb-1 text-xs text-text-muted">Localização (opcional; nunca impede o registro)</legend>
        <div className="grid grid-cols-[1fr_7rem] gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="new-highway">Rodovia</Label>
            <Input id="new-highway" placeholder="BR-116" value={form.highway} onChange={(event) => set('highway', event.target.value)} aria-describedby={describedBy('highway')} />
            {errorText('highway')}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="new-km">Km</Label>
            <Input id="new-km" inputMode="decimal" placeholder="231,5" value={form.km} onChange={(event) => set('km', event.target.value)} aria-describedby={describedBy('km')} />
            {errorText('km')}
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="new-location_note">Referência de local</Label>
          <Input id="new-location_note" placeholder="Perto do posto, sentido SP" value={form.location_note} onChange={(event) => set('location_note', event.target.value)} aria-describedby={describedBy('location_note')} />
          {errorText('location_note')}
        </div>
      </fieldset>

      {formError && (
        <p role="alert" className="text-sm text-danger">
          {formError}
        </p>
      )}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone} disabled={create.isPending}>
          Cancelar
        </Button>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending && <LoaderCircle aria-hidden className="animate-spin" />}
          {create.isPending ? 'Registrando…' : 'Registrar incidente'}
        </Button>
      </DialogFooter>
    </form>
  )
}
