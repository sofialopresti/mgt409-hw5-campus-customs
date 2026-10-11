// Who's on the team: names, roles, and each agent's muted color.
export type AgentId = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export type AgentMeta = { id: AgentId; name: string; role: string; color: string; tint: string }

export const AGENTS: AgentMeta[] = [
  { id: 'boss', name: 'The Boss', role: 'Reads tickets · makes the call', color: '#4B5A6E', tint: '#E6E9EE' },
  { id: 'inventory', name: 'Inventory', role: 'Stock · vendors · restocks', color: '#A67C52', tint: '#F1E8DE' },
  { id: 'accounting', name: 'Accounting', role: 'Cash · invoices · margins', color: '#6F8F72', tint: '#E5ECE3' },
  { id: 'facilities', name: 'Facilities', role: 'Rent · lease · the shop', color: '#B08A45', tint: '#F2EBDD' },
  { id: 'customer_service', name: 'Customer Service', role: 'Talks to customers', color: '#A26D7E', tint: '#F1E5E8' },
]

export const agentMeta = (id: string | null | undefined): AgentMeta | undefined =>
  AGENTS.find((a) => a.id === id)
