import { Ambulance, Car, CloudRain, Construction, Wrench, type LucideIcon } from 'lucide-react'

import type { IncidentCategory } from '@/api/types'

export const CATEGORY_ICONS: Record<IncidentCategory, LucideIcon> = {
  vehicle_accident: Car,
  accident_with_victims: Ambulance,
  adverse_weather: CloudRain,
  mechanical_failure: Wrench,
  road_blockage: Construction,
}
