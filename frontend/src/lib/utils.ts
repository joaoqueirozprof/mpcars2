import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'R$ 0,00'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function parseCurrency(value: string): number {
  if (!value) return 0
  const digits = value.replace(/\D/g, '')
  if (!digits) return 0
  return parseFloat(digits) / 100
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-'
  const d = typeof date === 'string' ? new Date(date) : date
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '-'
  const d = typeof date === 'string' ? new Date(date) : date
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatPhone(value: string): string {
  if (!value) return ''
  const cleaned = value.replace(/\D/g, '')
  if (cleaned.length <= 10) {
    return cleaned.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3')
  }
  return cleaned.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3')
}

export function formatCPF(value: string): string {
  if (!value) return ''
  const cleaned = value.replace(/\D/g, '')
  return cleaned.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
}

export function formatCNPJ(value: string): string {
  if (!value) return ''
  const cleaned = value.replace(/\D/g, '')
  return cleaned.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
}

export function formatCEP(value: string): string {
  if (!value) return ''
  const cleaned = value.replace(/\D/g, '')
  return cleaned.replace(/(\d{5})(\d{3})/, '$1-$2')
}

export function formatPlaca(value: string): string {
  if (!value) return ''
  const cleaned = value.replace(/\D/g, '').toUpperCase()
  return cleaned.replace(/([A-Z]{3})(\d{4})/, '$1-$2')
}

export function getStatusColor(status: string): string {
  const statusLower = status.toLowerCase()
  if (['disponivel', 'pago', 'ativo', 'concluida'].includes(statusLower))
    return 'bg-green-100 text-green-800'
  if (['alugado', 'em_progresso'].includes(statusLower))
    return 'bg-blue-100 text-blue-800'
  if (['atraso', 'manutencao', 'atencao', 'vencido'].includes(statusLower))
    return 'bg-amber-100 text-amber-800'
  if (['inativo', 'cancelado', 'cancelada'].includes(statusLower))
    return 'bg-red-100 text-red-800'
  return 'bg-slate-100 text-slate-800'
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    disponivel: 'Disponível',
    alugado: 'Alugado',
    manutencao: 'Manutenção',
    inativo: 'Inativo',
    ativo: 'Ativo',
    finalizado: 'Finalizado',
    cancelado: 'Cancelado',
    atraso: 'Atraso',
    pago: 'Pago',
    pendente: 'Pendente',
    vencido: 'Vencido',
    em_progresso: 'Em Progresso',
    concluida: 'Concluída',
    cancelada: 'Cancelada',
    convertida: 'Convertida',
    critica: 'Crítica',
    atencao: 'Atenção',
    info: 'Informação',
  }
  return labels[status.toLowerCase()] || status
}

export function calculateDays(startDate: string | Date, endDate: string | Date): number {
  const start = typeof startDate === 'string' ? new Date(startDate) : startDate
  const end = typeof endDate === 'string' ? new Date(endDate) : endDate
  const diffTime = Math.abs(end.getTime() - start.getTime())
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}

export function isExpiringSoon(expiryDate: string | Date, days: number = 30): boolean {
  const expiry = typeof expiryDate === 'string' ? new Date(expiryDate) : expiryDate
  const today = new Date()
  const diffTime = expiry.getTime() - today.getTime()
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays <= days && diffDays > 0
}

export function isExpired(expiryDate: string | Date): boolean {
  const expiry = typeof expiryDate === 'string' ? new Date(expiryDate) : expiryDate
  const today = new Date()
  return expiry < today
}

export function validateEmail(email: string): boolean {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

export function validateCPF(cpf: string): boolean {
  const cleaned = cpf.replace(/\D/g, '')
  if (cleaned.length !== 11) return false
  if (/^(\d)\1{10}$/.test(cleaned)) return false

  let sum = 0
  for (let i = 0; i < 9; i++) {
    sum += parseInt(cleaned[i]) * (10 - i)
  }
  let remainder = sum % 11
  let digit1 = remainder < 2 ? 0 : 11 - remainder

  sum = 0
  for (let i = 0; i < 10; i++) {
    sum += parseInt(cleaned[i]) * (11 - i)
  }
  remainder = sum % 11
  let digit2 = remainder < 2 ? 0 : 11 - remainder

  return (
    parseInt(cleaned[9]) === digit1 && parseInt(cleaned[10]) === digit2
  )
}

export function validateCNPJ(cnpj: string): boolean {
  const cleaned = cnpj.replace(/\D/g, '')
  if (cleaned.length !== 14) return false
  if (/^(\d)\1{13}$/.test(cleaned)) return false

  let size = cleaned.length - 2
  let numbers = cleaned.substring(0, size)
  let digits = cleaned.substring(size)
  let sum = 0
  let pos = size - 7

  for (let i = size; i >= 1; i--) {
    sum += numbers.charAt(size - i) * pos--
    if (pos < 2) pos = 9
  }

  let result = sum % 11 < 2 ? 0 : 11 - (sum % 11)
  if (result !== parseInt(digits.charAt(0))) return false

  size = size + 1
  numbers = cleaned.substring(0, size)
  sum = 0
  pos = size - 7

  for (let i = size; i >= 1; i--) {
    sum += numbers.charAt(size - i) * pos--
    if (pos < 2) pos = 9
  }

  result = sum % 11 < 2 ? 0 : 11 - (sum % 11)
  return result === parseInt(digits.charAt(1))
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .substring(0, 2)
}

export function truncate(text: string, length: number): string {
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
