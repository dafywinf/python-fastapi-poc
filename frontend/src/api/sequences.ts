import type { Sequence, SequenceCreate, SequenceUpdate } from '../types/sequence'

const BASE_URL = '/sequences'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(detail.detail ?? response.statusText)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const sequencesApi = {
  list(): Promise<Sequence[]> {
    return request<Sequence[]>(BASE_URL + '/')
  },

  get(id: number): Promise<Sequence> {
    return request<Sequence>(`${BASE_URL}/${id}`)
  },

  create(payload: SequenceCreate): Promise<Sequence> {
    return request<Sequence>(BASE_URL + '/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  update(id: number, payload: SequenceUpdate): Promise<Sequence> {
    return request<Sequence>(`${BASE_URL}/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  delete(id: number): Promise<void> {
    return request<void>(`${BASE_URL}/${id}`, { method: 'DELETE' })
  },
}
