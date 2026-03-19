import React, { useState } from "react"
import { Link, useLocation } from "react-router-dom"
import {
  Car,
  DollarSign,
  FileText,
  LayoutDashboard,
  Menu,
} from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { cn } from "@/lib/utils"
import MoreSheet from "./MoreSheet"

interface NavItem {
  id: string
  label: string
  icon: React.ElementType
  href: string
  slug?: string
}

const navItems: NavItem[] = [
  {
    id: "dashboard",
    label: "Inicio",
    icon: LayoutDashboard,
    href: "/dashboard",
    slug: "dashboard",
  },
  {
    id: "veiculos",
    label: "Veiculos",
    icon: Car,
    href: "/veiculos",
    slug: "veiculos",
  },
  {
    id: "contratos",
    label: "Contratos",
    icon: FileText,
    href: "/contratos",
    slug: "contratos",
  },
  {
    id: "financeiro",
    label: "Financeiro",
    icon: DollarSign,
    href: "/financeiro",
    slug: "financeiro",
  },
]

const BottomNav: React.FC = () => {
  const location = useLocation()
  const { canAccess } = useAuth()
  const [moreOpen, setMoreOpen] = useState(false)

  const visibleItems = navItems.filter(
    (item) => !item.slug || canAccess(item.slug)
  )

  const isActive = (href: string) =>
    location.pathname === href ||
    (href !== "/dashboard" && location.pathname.startsWith(`${href}/`))

  const isMoreActive = !visibleItems.some((item) => isActive(item.href))

  return (
    <>
      {/* Spacer */}
      <div className="h-[calc(4rem+env(safe-area-inset-bottom,0px))] md:hidden" />

      {/* Bottom Nav */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 md:hidden border-t border-slate-200/60 bg-white/95 backdrop-blur-xl"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      >
        <div className="flex items-stretch h-16">
          {visibleItems.map((item) => {
            const active = isActive(item.href)
            const Icon = item.icon
            return (
              <Link
                key={item.id}
                to={item.href}
                className={cn(
                  "flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors duration-150",
                  active ? "text-primary-dark" : "text-slate-400 active:text-slate-600"
                )}
              >
                <div
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200",
                    active && "bg-primary-100"
                  )}
                >
                  <Icon
                    size={20}
                    strokeWidth={active ? 2.5 : 1.5}
                  />
                </div>
                <span
                  className={cn(
                    "text-[11px] leading-tight",
                    active ? "font-bold" : "font-medium"
                  )}
                >
                  {item.label}
                </span>
              </Link>
            )
          })}

          {/* More button */}
          <button
            onClick={() => setMoreOpen(true)}
            className={cn(
              "flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors duration-150",
              isMoreActive
                ? "text-primary-dark"
                : "text-slate-400 active:text-slate-600"
            )}
          >
            <div
              className={cn(
                "flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200",
                isMoreActive && "bg-primary-100"
              )}
            >
              <Menu size={20} strokeWidth={isMoreActive ? 2.5 : 1.5} />
            </div>
            <span
              className={cn(
                "text-[11px] leading-tight",
                isMoreActive ? "font-bold" : "font-medium"
              )}
            >
              Mais
            </span>
          </button>
        </div>
      </nav>

      <MoreSheet isOpen={moreOpen} onClose={() => setMoreOpen(false)} />
    </>
  )
}

export default BottomNav
