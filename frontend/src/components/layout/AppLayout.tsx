import React, { useEffect, useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import CommandPalette from './CommandPalette'
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext'
import { useAuth } from '@/contexts/AuthContext'
import FirstUseGuide from '@/components/onboarding/FirstUseGuide'
import ContextualTipsBanner from '@/components/onboarding/ContextualTipsBanner'

interface AppLayoutProps {
  children: React.ReactNode
}

const LayoutContent: React.FC<AppLayoutProps> = ({ children }) => {
  const { isCollapsed } = useSidebar()
  const { user } = useAuth()
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const [isGuideOpen, setIsGuideOpen] = useState(false)

  const guideStorageKey = user ? `mpcars2_guide_hidden_${user.id}` : 'mpcars2_guide_hidden'
  const guideSessionKey = user ? `mpcars2_guide_seen_${user.id}` : 'mpcars2_guide_seen'

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setIsCommandPaletteOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    if (!user) return
    if (user.perfil === 'owner') return
    if (typeof window === 'undefined') return
    if (window.localStorage.getItem(guideStorageKey) === '1') return
    if (window.sessionStorage.getItem(guideSessionKey) === '1') return

    const timer = window.setTimeout(() => {
      setIsGuideOpen(true)
      window.sessionStorage.setItem(guideSessionKey, '1')
    }, 900)

    return () => window.clearTimeout(timer)
  }, [guideSessionKey, guideStorageKey, user])

  const handleCloseGuide = () => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem(guideSessionKey, '1')
    }
    setIsGuideOpen(false)
  }

  const handleDismissGuidePermanently = () => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(guideStorageKey, '1')
      window.sessionStorage.setItem(guideSessionKey, '1')
    }
    setIsGuideOpen(false)
  }

  return (
    <div className="relative flex h-screen overflow-hidden bg-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.08),transparent_26%),radial-gradient(circle_at_top_right,rgba(16,185,129,0.07),transparent_24%),linear-gradient(180deg,#f8fafc_0%,#f1f5f9_100%)]" />
      <Sidebar onOpenCommandPalette={() => setIsCommandPaletteOpen(true)} />

      {/* Main content area - shifts based on sidebar */}
      <div
        className={`relative flex flex-1 flex-col overflow-hidden transition-all duration-300 ease-in-out ${
          isCollapsed ? 'md:ml-24' : 'md:ml-[292px]'
        }`}
      >
        <Header
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          onOpenGuide={() => setIsGuideOpen(true)}
        />
        <main className="relative flex-1 overflow-y-auto">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.10),transparent_55%)]" />
          <div className="relative p-4 md:p-6 lg:p-8">
            <ContextualTipsBanner onOpenGuide={() => setIsGuideOpen(true)} />
            {children}
          </div>
        </main>
      </div>
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
      <FirstUseGuide
        isOpen={isGuideOpen}
        onClose={handleCloseGuide}
        onDismissPermanently={handleDismissGuidePermanently}
      />
    </div>
  )
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <SidebarProvider>
      <LayoutContent>{children}</LayoutContent>
    </SidebarProvider>
  )
}

export default AppLayout
