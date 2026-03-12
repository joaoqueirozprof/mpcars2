import React, { useEffect, useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import CommandPalette from './CommandPalette'
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext'

interface AppLayoutProps {
  children: React.ReactNode
}

const LayoutContent: React.FC<AppLayoutProps> = ({ children }) => {
  const { isCollapsed } = useSidebar()
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)

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
        <Header onOpenCommandPalette={() => setIsCommandPaletteOpen(true)} />
        <main className="relative flex-1 overflow-y-auto">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.10),transparent_55%)]" />
          <div className="relative p-4 md:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
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
