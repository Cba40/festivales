import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import type { EmergencyType } from './emergencyAdmin'

export type ProtocolContext = 'festival' | 'transporte' | 'hospedaje'

export interface ProtocolDTO {
  id: string
  context: ProtocolContext
  title: string
  description: string | null
  icon: string
  steps: string[]
  priority: number
  order: number
  target_type: EmergencyType | null
  active: boolean
}

export interface ProtocolCreateDTO {
  context: ProtocolContext
  title: string
  description?: string | null
  icon: string
  steps: string[]
  priority: number
  order: number
  target_type?: EmergencyType | null
  active: boolean
}

export interface ProtocolUpdateDTO {
  context?: ProtocolContext
  title?: string
  description?: string | null
  icon?: string
  steps?: string[]
  priority?: number
  order?: number
  target_type?: EmergencyType | null
  active?: boolean
}

export async function getProtocols(context?: string): Promise<ProtocolDTO[]> {
  const { data } = await apiClient.get<ProtocolDTO[]>(
    endpoints.emergencyAdmin.listProtocols(context)
  )
  return data
}

export async function createProtocol(payload: ProtocolCreateDTO): Promise<ProtocolDTO> {
  const { data } = await apiClient.post<ProtocolDTO>(
    endpoints.emergencyAdmin.createProtocol(),
    payload
  )
  return data
}

export async function updateProtocol(
  id: string,
  payload: ProtocolUpdateDTO
): Promise<ProtocolDTO> {
  const { data } = await apiClient.put<ProtocolDTO>(
    endpoints.emergencyAdmin.updateProtocol(id),
    payload
  )
  return data
}

export async function deleteProtocol(id: string): Promise<void> {
  await apiClient.delete(endpoints.emergencyAdmin.deleteProtocol(id))
}