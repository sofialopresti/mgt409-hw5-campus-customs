// Client for the Campus Customs desk API (backend/main.py).
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type Ticket = {
  id: number
  type: string
  requester: string
  subject: string
  status: string
  state: 'resolved' | 'open'
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  notes: string | null
  created_at: string
}

export type TicketDecision = {
  ticket_id: number
  agents_consulted: string[]
  final_call: string
  status: string
  human_follow_ups: string[]
}

export type RunStatus = {
  run_id: string
  ticket_id: number
  state: 'running' | 'finished' | 'failed'
  started_at: string
  finished_at: string | null
  decision: TicketDecision | null
  error: string | null
}

export type ToolCall = { tool: string; args: Record<string, unknown> | null; outcome: string | null }

export type AgentEvent = {
  seq: number
  run_id: string
  logged_at: string
  event: string
  agent: string | null
  ticket_id: number | null
  summary: string | null
  tools_used: string[]
  tool_calls: ToolCall[]
  detail: Record<string, any> | null
}

export type BoardItem = {
  id: number
  kind: 'payment_request' | 'purchase_order' | string
  author: string
  ticket_id: number | null
  title: string
  body: string
  status: string
  created_on: string
  data: Record<string, any>
}

export type Cash = { account: string; balance: number; as_of: string }

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(`Can't reach the desk API at ${API_URL}. Is uvicorn running?`)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join('; ') : detail
    throw new ApiError(message || `${res.status} ${res.statusText}`)
  }
  return body as T
}

export const api = {
  tickets: () => request<Ticket[]>('/tickets'),
  runTicket: (id: number) => request<RunStatus>(`/tickets/${id}/run`, { method: 'POST' }),
  run: (runId: string) => request<RunStatus>(`/runs/${runId}`),
  events: (sinceSeq = 0, limit = 500) => request<AgentEvent[]>(`/events?since_seq=${sinceSeq}&limit=${limit}`),
  approvals: () => request<BoardItem[]>('/approvals'),
  approve: (id: number, approvedBy: string) =>
    request<{ approved: number; kind: string; result: Record<string, any> }>(`/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  cash: () => request<Cash>('/cash'),
  reset: () => request<{ reset: boolean; date_today: string }>('/reset', { method: 'POST' }),
}
