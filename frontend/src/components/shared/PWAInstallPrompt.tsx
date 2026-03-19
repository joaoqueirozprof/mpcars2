import React, { useEffect, useState } from "react"
import { Download, RefreshCw, X, Smartphone } from "lucide-react"

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>
}

const PWAInstallPrompt: React.FC = () => {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null)
  const [showInstallBanner, setShowInstallBanner] = useState(false)
  const [showUpdateBanner, setShowUpdateBanner] = useState(false)
  const [showIOSPrompt, setShowIOSPrompt] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    // Check if already installed
    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as any).standalone === true

    if (isStandalone) return

    // Check if dismissed recently (24h cooldown)
    const dismissedAt = localStorage.getItem("pwa-install-dismissed")
    if (dismissedAt) {
      const hoursSince =
        (Date.now() - parseInt(dismissedAt)) / (1000 * 60 * 60)
      if (hoursSince < 24) {
        setDismissed(true)
        return
      }
    }

    // Android/Chrome install prompt
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e as BeforeInstallPromptEvent)
      setShowInstallBanner(true)
    }

    window.addEventListener("beforeinstallprompt", handleBeforeInstall)

    // iOS detection
    const isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent)
    const isSafari =
      /Safari/.test(navigator.userAgent) &&
      !/CriOS|FxiOS|Chrome/.test(navigator.userAgent)

    if (isIOS && isSafari && !isStandalone) {
      // Show iOS install instructions after a delay
      const timer = setTimeout(() => {
        if (!dismissed) setShowIOSPrompt(true)
      }, 3000)
      return () => {
        clearTimeout(timer)
        window.removeEventListener("beforeinstallprompt", handleBeforeInstall)
      }
    }

    // Listen for SW updates
    const handleUpdate = () => setShowUpdateBanner(true)
    window.addEventListener("sw-update-available", handleUpdate)

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall)
      window.removeEventListener("sw-update-available", handleUpdate)
    }
  }, [dismissed])

  const handleInstall = async () => {
    if (!deferredPrompt) return

    await deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice

    if (outcome === "accepted") {
      setShowInstallBanner(false)
    }

    setDeferredPrompt(null)
  }

  const handleDismiss = () => {
    setShowInstallBanner(false)
    setShowIOSPrompt(false)
    setDismissed(true)
    localStorage.setItem("pwa-install-dismissed", Date.now().toString())
  }

  const handleUpdate = () => {
    window.location.reload()
  }

  // Android/Chrome Install Banner
  if (showInstallBanner && !dismissed) {
    return (
      <div className="fixed bottom-4 left-4 right-4 z-[100] animate-fade-in-up sm:left-auto sm:right-6 sm:max-w-sm">
        <div className="rounded-2xl border border-primary-200 bg-white p-4 shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-primary-100 text-primary-dark">
              <Download size={22} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-900">
                Instalar MPCARS
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                Acesse o sistema direto do seu celular, como um app nativo.
              </p>
            </div>
            <button
              onClick={handleDismiss}
              className="flex-shrink-0 p-1 text-slate-400 hover:text-slate-600"
            >
              <X size={16} />
            </button>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleInstall}
              className="btn-primary flex-1 py-2 text-sm"
            >
              Instalar
            </button>
            <button
              onClick={handleDismiss}
              className="btn-secondary flex-1 py-2 text-sm"
            >
              Agora não
            </button>
          </div>
        </div>
      </div>
    )
  }

  // iOS Install Instructions
  if (showIOSPrompt && !dismissed) {
    return (
      <div className="fixed bottom-4 left-4 right-4 z-[100] animate-fade-in-up sm:left-auto sm:right-6 sm:max-w-sm">
        <div className="rounded-2xl border border-primary-200 bg-white p-4 shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-primary-100 text-primary-dark">
              <Smartphone size={22} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-900">
                Instalar MPCARS no iPhone
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Toque no botão{" "}
                <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs font-bold">
                  ⬆ Compartilhar
                </span>{" "}
                na barra do Safari e depois em{" "}
                <span className="font-semibold text-slate-700">
                  "Adicionar à Tela de Início"
                </span>
              </p>
            </div>
            <button
              onClick={handleDismiss}
              className="flex-shrink-0 p-1 text-slate-400 hover:text-slate-600"
            >
              <X size={16} />
            </button>
          </div>
          <button
            onClick={handleDismiss}
            className="mt-3 w-full rounded-xl bg-slate-100 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-200"
          >
            Entendi
          </button>
        </div>
      </div>
    )
  }

  // Update Available Banner
  if (showUpdateBanner) {
    return (
      <div className="fixed bottom-4 left-4 right-4 z-[100] animate-fade-in-up sm:left-auto sm:right-6 sm:max-w-sm">
        <div className="rounded-2xl border border-emerald-200 bg-white p-4 shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
              <RefreshCw size={22} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-900">
                Nova versão disponível
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                Atualize para ter acesso às melhorias mais recentes.
              </p>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleUpdate}
              className="btn-success flex-1 py-2 text-sm"
            >
              Atualizar agora
            </button>
            <button
              onClick={() => setShowUpdateBanner(false)}
              className="btn-secondary flex-1 py-2 text-sm"
            >
              Depois
            </button>
          </div>
        </div>
      </div>
    )
  }

  return null
}

export default PWAInstallPrompt
