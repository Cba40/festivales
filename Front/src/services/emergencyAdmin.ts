import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'

export type EmergencyType =
  | 'policia'
  | 'bomberos'
  | 'salud'
  | 'defensa_civil'
  | 'numero_emergencia'
  | 'otro'

export interface CityDTO {
  id: string
  name: string
  province: string | null
  country: string
}

export interface EmergencyAdminDTO {
  id: string
  city_id: string
  name: string
  type: EmergencyType
  phone: string | null
  emergency_number: string | null
  address: string | null
  reference: string | null
  latitude: number | null
  longitude: number | null
  services: string | null
  schedule: string | null
  active: boolean
}

export interface EmergencyCreateDTO {
  city_id: string
  name: string
  type: EmergencyType
  phone?: string | null
  emergency_number?: string | null
  address?: string | null
  reference?: string | null
  latitude?: number | null
  longitude?: number | null
  services?: string | null
  schedule?: string | null
  active?: boolean
}

export interface EmergencyUpdateDTO {
  city_id?: string
  name?: string
  type?: EmergencyType
  phone?: string | null
  emergency_number?: string | null
  address?: string | null
  reference?: string | null
  latitude?: number | null
  longitude?: number | null
  services?: string | null
  schedule?: string | null
  active?: boolean
}

export async function getCities(): Promise<CityDTO[]> {
  const { data } = await apiClient.get<CityDTO[]>(endpoints.emergencyAdmin.cities)
  return data
}

export async function getEmergencies(
  cityId?: string,
  includeInactive = true
): Promise<EmergencyAdminDTO[]> {
  const { data } = await apiClient.get<EmergencyAdminDTO[]>(
    endpoints.emergencyAdmin.list(cityId),
    { params: { include_inactive: includeInactive } }
  )
  return data
}

export async function createEmergency(
  payload: EmergencyCreateDTO
): Promise<EmergencyAdminDTO> {
  const { data } = await apiClient.post<EmergencyAdminDTO>(
    endpoints.emergencyAdmin.create(),
    payload
  )
  return data
}

export async function updateEmergency(
  id: string,
  payload: EmergencyUpdateDTO
): Promise<EmergencyAdminDTO> {
  const { data } = await apiClient.put<EmergencyAdminDTO>(
    endpoints.emergencyAdmin.update(id),
    payload
  )
  return data
}

export async function deleteEmergency(id: string): Promise<void> {
  await apiClient.delete(endpoints.emergencyAdmin.delete(id))
}
