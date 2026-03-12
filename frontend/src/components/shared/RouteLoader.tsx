import React from 'react'

const RouteLoader: React.FC = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.12),transparent_30%),linear-gradient(180deg,#f8fafc_0%,#eff6ff_100%)] px-6">
      <div className="w-full max-w-xl rounded-[32px] border border-white/80 bg-white/90 p-8 text-center shadow-[0_24px_70px_rgba(15,23,42,0.10)] backdrop-blur">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] bg-slate-950 text-xl font-display font-bold text-white shadow-[0_18px_36px_rgba(15,23,42,0.22)]">
          M
        </div>
        <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-700">
          MPCARS
        </p>
        <h1 className="mt-2 text-3xl font-display font-bold text-slate-950">
          Preparando seu painel
        </h1>
        <p className="mt-3 text-sm text-slate-500">
          Estamos carregando o modulo com prioridade para manter a navegacao mais rapida e leve.
        </p>

        <div className="mt-7 space-y-3">
          <div className="h-3 overflow-hidden rounded-full bg-slate-100">
            <div className="route-loader-bar h-full rounded-full bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="route-loader-card" />
            <div className="route-loader-card route-loader-card-delay" />
            <div className="route-loader-card route-loader-card-delay-2" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default RouteLoader
