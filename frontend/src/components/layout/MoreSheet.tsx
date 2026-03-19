import React, { useEffect } from "react"
import { Link, useLocation } from "react-router-dom"
import { X } from "lucide-react"
import { getVisibleNavigationSections } from "@/config/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { cn } from "@/lib/utils"

interface MoreSheetProps {
  isOpen: boolean
  onClose: () => void
}

// Items already shown in bottom nav — skip them in the sheet
const bottomNavIds = new Set(["dashboard", "veiculos", "contratos", "financeiro"])

const sectionTone: Record<string, string> = {
  blue: "text-sky-600",
  emerald: "text-emerald-600",
  amber: "text-amber-600",
  slate: "text-slate-500",
}

const MoreSheet: React.FC<MoreSheetProps> = ({ isOpen, onClose }) => {
  const location = useLocation()
  const { canAccess, isAdmin, logout } = useAuth()

  const sections = getVisibleNavigationSections({ canAccess, isAdmin })
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => !bottomNavIds.has(item.id)),
    }))
    .filter((section) => section.items.length > 0)

  // Close on route change
  useEffect(() => {
    onClose()
  }, [location.pathname])

  // Lock body scroll
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden"
      return () => {
        document.body.style.overflow = ""
      }
    }
  }, [isOpen])

  if (!isOpen) return null

  const isActive = (href: string) =>
    location.pathname === href ||
    (href !== "/dashboard" && location.pathname.startsWith(`${href}/`))

  return (
    <div className="fixed inset-0 z-[60] md:hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Sheet */}
      <div
        className="absolute bottom-0 left-0 right-0 bg-white rounded-t-[28px] shadow-2xl animate-slide-up"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      >
        {/* Handle + Close */}
        <div className="flex items-center justify-between px-5 pt-3 pb-2">
          <div className="w-10 h-1 bg-slate-300 rounded-full" />
          <button
            onClick={onClose}
            className="w-9 h-9 flex items-center justify-center rounded-full bg-slate-100 text-slate-500 active:bg-slate-200"
          >
            <X size={18} />
          </button>
        </div>

        {/* Menu */}
        <div className="max-h-[60vh] overflow-y-auto px-3 pb-4">
          {sections.map((section) => (
            <div key={section.id} className="mb-4">
              <p
                className={cn(
                  "px-3 mb-1.5 text-[10px] font-bold uppercase tracking-[0.2em]",
                  sectionTone[section.tone]
                )}
              >
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon
                  const active = isActive(item.href)

                  return (
                    <Link
                      key={item.href}
                      to={item.href}
                      onClick={onClose}
                      className={cn(
                        "flex items-center gap-3 px-3 py-3 rounded-2xl transition-colors",
                        active
                          ? "bg-primary text-white"
                          : "text-slate-700 active:bg-slate-50"
                      )}
                    >
                      <div
                        className={cn(
                          "flex h-9 w-9 items-center justify-center rounded-xl",
                          active
                            ? "bg-white/20 text-white"
                            : "bg-slate-100 text-slate-600"
                        )}
                      >
                        <Icon size={18} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[14px] font-semibold truncate">
                          {item.label}
                        </p>
                        <p
                          className={cn(
                            "text-[11px] truncate",
                            active ? "text-white/70" : "text-slate-400"
                          )}
                        >
                          {item.description}
                        </p>
                      </div>
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}

          {/* Logout */}
          <div className="border-t border-slate-100 pt-3 mt-2">
            <button
              onClick={() => {
                onClose()
                logout()
              }}
              className="flex items-center gap-3 w-full px-3 py-3 rounded-2xl text-red-600 active:bg-red-50 transition-colors"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-50 text-red-500">
                <X size={18} />
              </div>
              <span className="text-[14px] font-semibold">Sair do sistema</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MoreSheet
