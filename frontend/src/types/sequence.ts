export interface Sequence {
  id: number
  name: string
  description: string | null
  created_at: string
}

export interface SequenceCreate {
  name: string
  description?: string | null
}

export interface SequenceUpdate {
  name?: string
  description?: string | null
}
