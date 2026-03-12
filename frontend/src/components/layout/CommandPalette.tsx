import React, { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowRight, Clock3, CornerDownLeft, Search, Sparkles } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import {
  findNavigationItem,
  getVisibleNavigationSections,
  getVisibleQuickActions,
  NavigationItem,
  QuickAction,
} from '@/config/navigation'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

type CommandEntry =
  | (NavigationItem & { type: 'page'; groupLabel: string })
  | (QuickAction & { type: 'action'; groupLabel: string })

const RECENT_COMMANDS_KEY = 'mpcars2_recent_commands'

const readRecentIds = () => {
  if (typeof window === 'undefined') return []

  try {
    const value = window.localStorage.getItem(RECENT_COMMANDS_KEY)
    const parsed = value ? JSON.parse(value) : []
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
  } catch {
    return []
  }
}

const writeRecentIds = (ids: string[]) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(RECENT_COMMANDS_KEY, JSON.stringify(ids.slice(0, 8)))
}

const searchMatches = (value: string, terms: string[]) => {
  if (!value) return true
  const normalized = value.trim().toLowerCase()
  return terms.some((term) => term.toLowerCase().includes(normalized))
}

const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const { canAccess, isAdmin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const [recentIds, setRecentIds] = useState<string[]>(readRecentIds)

  const sections = useMemo(
    () => getVisibleNavigationSections({ canAccess, isAdmin }),
    [canAccess, isAdmin]
  )
  const quickActions = useMemo(
    () => getVisibleQuickActions({ canAccess, isAdmin }),
    [canAccess, isAdmin]
  )

  const pageEntries = useMemo<CommandEntry[]>(
    () =>
      sections.flatMap((section) =>
        section.items.map((item) => ({
          ...item,
          type: 'page' as const,
          groupLabel: section.label,
        }))
      ),
    [sections]
  )

  const actionEntries = useMemo<CommandEntry[]>(
    () => quickActions.map((item) => ({ ...item, type: 'action' as const, groupLabel: 'Criacao rapida' })),
    [quickActions]
  )

  const allEntries = useMemo<CommandEntry[]>(() => [...actionEntries, ...pageEntries], [actionEntries, pageEntries])

  const currentPage = findNavigationItem(location.pathname)

  const filteredEntries = useMemo(() => {
    const searchableEntries = allEntries.filter((entry) => {
      const terms = [entry.label, entry.description, ...entry.keywords, entry.groupLabel]
      return searchMatches(query, terms)
    })

    if (query.trim()) {
      return searchableEntries
    }

    const recent = recentIds
      .map((recentId) => searchableEntries.find((entry) => entry.id === recentId))
      .filter((entry): entry is CommandEntry => Boolean(entry))

    const spotlight = searchableEntries
      .filter((entry) => entry.id !== currentPage.id)
      .slice(0, 8)

    return [...recent, ...spotlight].filter(
      (entry, index, list) => list.findIndex((item) => item.id === entry.id) === index
    )
  }, [allEntries, currentPage.id, query, recentIds])

  const groupedEntries = useMemo(() => {
    const entries = filteredEntries.length > 0 ? filteredEntries : allEntries.slice(0, 8)
    return entries.reduce<Record<string, CommandEntry[]>>((acc, entry) => {
      const key = entry.type === 'action' ? entry.groupLabel : entry.groupLabel
      if (!acc[key]) acc[key] = []
      acc[key].push(entry)
      return acc
    }, {})
  }, [allEntries, filteredEntries])

  const flatEntries = useMemo(
    () => Object.values(groupedEntries).flat(),
    [groupedEntries]
  )

  useEffect(() => {
    if (!isOpen) return

    setQuery('')
    setActiveIndex(0)

    const frameId = window.requestAnimationFrame(() => {
      inputRef.current?.focus()
    })

    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      window.cancelAnimationFrame(frameId)
      document.body.style.overflow = originalOverflow
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (!flatEntries.length) return

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setActiveIndex((current) => (current + 1) % flatEntries.length)
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setActiveIndex((current) => (current - 1 + flatEntries.length) % flatEntries.length)
      }

      if (event.key === 'Enter') {
        event.preventDefault()
        const entry = flatEntries[activeIndex]
        if (entry) {
          handleSelect(entry)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeIndex, flatEntries, isOpen, onClose])

  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  const handleSelect = (entry: CommandEntry) => {
    const nextRecentIds = [entry.id, ...recentIds.filter((item) => item !== entry.id)].slice(0, 8)
    setRecentIds(nextRecentIds)
    writeRecentIds(nextRecentIds)

    navigate({
      pathname: entry.href,
      search: entry.search || '',
    })
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="command-palette-backdrop" onClick={onClose}>
      <div
        className="command-palette-shell"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Central de comandos"
      >
        <div className="command-palette-header">
          <div className="command-palette-search">
            <Search size={18} className="text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar pagina, acao ou fluxo..."
              className="command-palette-input"
            />
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-[11px] font-medium text-slate-500 md:flex">
            <Sparkles size={14} className="text-blue-500" />
            Ctrl K para abrir de qualquer tela
          </div>
        </div>

        <div className="command-palette-hero">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-700">
              Central de comandos
            </p>
            <h2 className="mt-2 text-2xl font-display font-bold text-slate-950">
              Navegue e crie sem perder contexto
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Va para qualquer modulo, abra um cadastro novo ou continue de onde voce parou em poucos segundos.
            </p>
          </div>
          <div className="command-palette-hero-card">
            <span className="command-palette-chip">Tela atual</span>
            <p className="mt-3 text-lg font-semibold text-slate-950">{currentPage.label}</p>
            <p className="mt-1 text-sm text-slate-600">{currentPage.description}</p>
          </div>
        </div>

        <div className="command-palette-body">
          {flatEntries.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <Search size={28} />
              </div>
              <div>
                <p className="text-base font-semibold text-slate-900">Nada encontrado</p>
                <p className="text-sm text-slate-500">Tente procurar por placa, contrato, frota, clientes ou pagamentos.</p>
              </div>
            </div>
          ) : (
            <div className="space-y-5 px-4 py-4">
              {Object.entries(groupedEntries).map(([groupLabel, entries]) => (
                <div key={groupLabel}>
                  <div className="mb-2 flex items-center gap-2 px-2">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                      {groupLabel}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {entries.map((entry) => {
                      const entryIndex = flatEntries.findIndex((item) => item.id === entry.id)
                      const isActive = entryIndex === activeIndex
                      const Icon = entry.icon

                      return (
                        <button
                          key={entry.id}
                          type="button"
                          onClick={() => handleSelect(entry)}
                          onMouseEnter={() => setActiveIndex(entryIndex)}
                          className={cn(
                            'command-palette-item',
                            isActive && 'command-palette-item-active'
                          )}
                        >
                          <div className="command-palette-item-icon">
                            <Icon size={18} />
                          </div>
                          <div className="min-w-0 flex-1 text-left">
                            <div className="flex items-center gap-2">
                              <span className="truncate text-sm font-semibold text-slate-900">{entry.label}</span>
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                                {entry.type === 'action' ? 'Acao' : 'Pagina'}
                              </span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-xs text-slate-500">{entry.description}</p>
                          </div>
                          <div className="hidden items-center gap-2 md:flex">
                            {recentIds.includes(entry.id) && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-blue-600">
                                <Clock3 size={12} />
                                Recente
                              </span>
                            )}
                            <ArrowRight size={16} className="text-slate-300" />
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="command-palette-footer">
          <div className="flex items-center gap-3 text-[11px] text-slate-500">
            <span className="command-palette-key">↑↓</span>
            Navegar
          </div>
          <div className="flex items-center gap-3 text-[11px] text-slate-500">
            <span className="command-palette-key">
              <CornerDownLeft size={12} />
            </span>
            Abrir
          </div>
          <div className="flex items-center gap-3 text-[11px] text-slate-500">
            <span className="command-palette-key">Esc</span>
            Fechar
          </div>
        </div>
      </div>
    </div>
  )
}

export default CommandPalette
