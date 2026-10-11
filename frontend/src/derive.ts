// Turns the audit-trail event stream from GET /events into what the board shows.
import type { AgentEvent, TicketDecision } from './api'
import type { AgentId } from './agentList'

const STALE_RUN_MS = 10 * 60 * 1000 // a run with no "finished" after 10 min is treated as abandoned

export type AgentState = { status: 'idle' | 'working' | 'done'; line: string | null; summary: string | null }

export type LedgerEntry = {
  seq: number; amount: number; cashAfter: number; payee: string; message: string; approvedBy: string
}

/** Only events since the last database reset describe the current shop. */
export function sinceLastReset(events: AgentEvent[]): AgentEvent[] {
  let start = 0
  events.forEach((e, i) => {
    if (e.event === 'database_reset' || (e.event === 'run_started' && e.detail === null && isFullRun(e))) start = i
  })
  return events.slice(start)
}

// A CLI full run (backend.run) also resets the database before it starts.
function isFullRun(e: AgentEvent) {
  return e.ticket_id === null && e.agent === null
}

/** The run that is still going right now, if any, and which ticket it is on. */
export function activeRun(events: AgentEvent[]): { runId: string; ticketId: number | null } | null {
  const finished = new Set(events.filter((e) => e.event === 'run_finished').map((e) => e.run_id))
  const started = [...events].reverse().find((e) => e.event === 'run_started' && !finished.has(e.run_id))
  if (!started || Date.now() - Date.parse(started.logged_at) > STALE_RUN_MS) return null
  const inRun = events.filter((e) => e.run_id === started.run_id && e.ticket_id !== null)
  return { runId: started.run_id, ticketId: inRun.at(-1)?.ticket_id ?? started.ticket_id }
}

/** All events for one ticket from its most recent agent run. */
export function latestRunEvents(events: AgentEvent[], ticketId: number): AgentEvent[] {
  const mine = events.filter((e) => e.ticket_id === ticketId)
  const lastAgentEvent = [...mine].reverse().find((e) => e.event === 'agent_started')
  if (!lastAgentEvent) return mine.filter((e) => e.agent === 'human')
  const runId = lastAgentEvent.run_id
  return mine.filter((e) => e.run_id === runId || (e.agent === 'human' && e.seq > lastAgentEvent.seq))
}

export function agentStates(runEvents: AgentEvent[]): Record<AgentId, AgentState> {
  const states = {} as Record<AgentId, AgentState>
  for (const id of ['boss', 'inventory', 'accounting', 'facilities', 'customer_service'] as AgentId[]) {
    states[id] = { status: 'idle', line: null, summary: null }
  }
  for (const e of runEvents) {
    const s = e.agent ? states[e.agent as AgentId] : undefined
    if (!s) continue
    if (e.event === 'agent_started') {
      s.status = 'working'
      s.line = e.agent === 'boss' ? 'Reading the ticket…' : shorten(e.summary, 90)
    } else if (e.event === 'tool_call' && s.status === 'working') {
      s.line = toolSentence(e.tool_calls[0]?.tool)
    } else if (e.event === 'agent_loop') {
      s.status = 'done'
      s.summary = e.detail?.summary ?? e.detail?.final_call ?? e.summary
      s.line = null
    }
  }
  return states
}

export function latestDecision(runEvents: AgentEvent[]): TicketDecision | null {
  const e = [...runEvents].reverse().find((x) => x.event === 'ticket_decision')
  return (e?.detail as TicketDecision | undefined) ?? null
}

export function ledger(events: AgentEvent[]): LedgerEntry[] {
  return events
    .filter((e) => e.event === 'payment_result' && e.detail?.status === 'paid')
    .map((e) => ({
      seq: e.seq,
      amount: e.detail!.amount,
      cashAfter: e.detail!.cash_after,
      payee: /to (.+?) from /.exec(e.detail!.message)?.[1] ?? `${e.detail!.kind} ${e.detail!.ref_id}`,
      message: e.detail!.message,
      approvedBy: e.detail!.approved_by,
    }))
}

const TOOL_SENTENCES: Record<string, string> = {
  get_ticket: 'Reading the ticket',
  view_board: 'Checking the board',
  ask_inventory: 'Asking Inventory',
  ask_accounting: 'Asking Accounting',
  ask_facilities: 'Asking Facilities',
  ask_customer_service: 'Asking Customer Service',
  check_stock: 'Counting stock on the shelf',
  list_stock_issues: 'Scanning for low stock',
  list_vendors: 'Flipping through vendors',
  quote_restock: 'Pricing a restock',
  draft_vendor_message: 'Drafting a note to a vendor',
  get_cash_position: 'Checking the bank balance',
  list_invoices: 'Going through invoices',
  check_margin: 'Running the margin math',
  preview_payment: 'Previewing a payment',
  pay: 'Preparing a payment for you to approve',
  prepare_purchase_order: 'Writing up a purchase order',
  list_leases: 'Pulling the lease',
  get_lease: 'Reading the lease',
  draft_facilities_note: 'Drafting a note to the landlord',
  get_product: 'Looking up the product',
  draft_customer_message: 'Drafting a message to the customer',
  get_outgoing_payment_tickets: 'Reviewing money going out',
  get_incoming_payment_tickets: 'Reviewing potential sales',
  get_inventory_change_tickets: 'Reviewing stock impact',
}

export function toolSentence(tool: string | undefined): string {
  if (!tool) return 'Thinking…'
  return (TOOL_SENTENCES[tool] ?? tool.replaceAll('_', ' ')) + '…'
}

export function shorten(text: string | null | undefined, max: number): string | null {
  if (!text) return null
  return text.length > max ? text.slice(0, max - 1).trimEnd() + '…' : text
}

export function formatArgs(args: Record<string, unknown> | null): string {
  if (!args) return ''
  return Object.entries(args)
    .filter(([, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${k}=${shorten(typeof v === 'string' ? v : JSON.stringify(v), 28)}`)
    .join(', ')
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })

export const STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  resolved: 'All done',
  waiting_on_human: 'Waiting on you',
  waiting_on_restock: 'Waiting on restock',
  blocked: 'Blocked',
}
