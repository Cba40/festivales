import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'

export type AccommodationType = 'hotel' | 'hostel' | 'camping' | 'other'

export interface AccommodationDTO {
  id: string
  event_id: string
  name: string
  type: AccommodationType
  address: string | null
  reference: string | null
  latitude: number | null
  longitude: number | null
  phone: string | null
  website: string | null
  official_info_url: string | null
  active: boolean
}

export interface AccommodationCreateDTO {
  name: string
  type: AccommodationType
  address?: string | null
  reference?: string | null
  latitude?: number | null
  longitude?: number | null
  phone?: string | null
  website?: string | null
  official_info_url?: string | null
  active?: boolean
}

export interface AccommodationUpdateDTO {
  name?: string
  type?: AccommodationType
  address?: string | null
  reference?: string | null
  latitude?: number | null
  longitude?: number | null
  phone?: string | null
  website?: string | null
  official_info_url?: string | null
  active?: boolean
}

export async function getAccommodations(
  eventId: string,
  includeInactive = true
): Promise<AccommodationDTO[]> {
  const { data } = await apiClient.get<AccommodationDTO[]>(
    endpoints.accommodationAdmin.list(eventId),
    { params: { include_inactive: includeInactive } }
  )
  return data
}

export async function createAccommodation(
  eventId: string,
  payload: AccommodationCreateDTO
): Promise<AccommodationDTO> {
  const { data } = await apiClient.post<AccommodationDTO>(
    endpoints.accommodationAdmin.create(eventId),
    payload
  )
  return data
}

export async function updateAccommodation(
  eventId: string,
  id: string,
  payload: AccommodationUpdateDTO
): Promise<AccommodationDTO> {
  const { data } = await apiClient.put<AccommodationDTO>(
    endpoints.accommodationAdmin.update(eventId, id),
    payload
  )
  return data
}

export async function deleteAccommodation(
  eventId: string,
  id: string
): Promise<void> {
  await apiClient.delete(endpoints.accommodationAdmin.delete(eventId, id))
}
