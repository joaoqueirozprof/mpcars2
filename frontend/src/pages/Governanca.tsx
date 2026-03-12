import React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  FolderArchive,
  GitCommitHorizontal,
  HardDriveDownload,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import toast from 'react-hot-toast'

import AppLayout from '@/components/layout/AppLayout'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import api from '@/services/api'
import { BackupOverview, BackupRunResponse, OpsReadiness, VersionStatus } from '@/types'

const Governanca: React.FC = () => {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isAdmin = user?.perfil === 'admin'

  const { data: backups, isLoading: loadingBackups } = useQuery({
    queryKey: ['ops-backups'],
    queryFn: async () => {
      const { data } = await api.get<BackupOverview>('/ops/backups')
      return data
    },
  })

  const { data: readiness, isLoading: loadingReadiness } = useQuery({
    queryKey: ['ops-readiness'],
    queryFn: async () => {
      const { data } = await api.get<OpsReadiness>('/ops/readiness')
      return data
    },
    enabled: isAdmin,
    retry: false,
  })

  const { data: versionInfo, isLoading: loadingVersion } = useQuery({
    queryKey: ['ops-version'],
    queryFn: async () => {
      const { data } = await api.get<VersionStatus>('/ops/version')
      return data
    },
    enabled: isAdmin,
    retry: false,
  })

  const runBackupMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<BackupRunResponse>('/ops/backups/run')
      return data
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Backup executado com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['ops-backups'] })
      if (isAdmin) {
        queryClient.invalidateQueries({ queryKey: ['ops-readiness'] })
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Nao foi possivel executar o backup agora.')
    },
  })

  const latestBackup = backups?.items?.[0]

  return (
    <AppLayout>
      <div className="space-y-6 pb-8">
        <section className="overflow-hidden rounded-[30px] border border-sky-100 bg-[linear-gradient(135deg,#e0f2fe_0%,#ffffff_52%,#f8fbff_100%)] p-6 shadow-[0_20px_55px_rgba(96,165,250,0.12)]">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_340px]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-700 ring-1 ring-sky-100">
                <ShieldCheck size={13} />
                Governanca do ambiente
              </div>
              <h1 className="mt-4 text-3xl font-display font-bold text-slate-950">
                Backups, versoes e seguranca operacional
              </h1>
              <p className="mt-3 max-w-3xl text-sm text-slate-600">
                Este painel fica reservado para acessos de governanca. Aqui voce acompanha os ultimos backups, dispara um backup manual e, quando for administrador da plataforma, enxerga tambem prontidao de producao e versoes do sistema.
              </p>

              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  onClick={() => runBackupMutation.mutate()}
                  disabled={runBackupMutation.isPending}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {runBackupMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <HardDriveDownload size={16} />}
                  Fazer backup agora
                </button>
                <div className="inline-flex items-center gap-2 rounded-2xl border border-sky-100 bg-white px-4 py-3 text-sm text-slate-600">
                  <Database size={16} className="text-sky-600" />
                  {backups?.storage_label || 'Drive dedicado da VPS'}
                </div>
              </div>
            </div>

            <div className="rounded-[26px] border border-white/80 bg-white/90 p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Resumo rapido
              </p>
              <div className="mt-4 space-y-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Ultimo backup</p>
                  <p className="mt-2 text-base font-semibold text-slate-900">
                    {latestBackup?.timestamp || 'Nenhum backup encontrado'}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {latestBackup?.size_human || 'Sem historico salvo ainda'}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Retencao</p>
                  <p className="mt-2 text-base font-semibold text-slate-900">
                    {backups?.retention_days || 14} dias
                  </p>
                  <p className="mt-1 text-sm text-slate-500">{backups?.directory || '/backups'}</p>
                </div>
                {isAdmin && (
                  <div
                    className={cn(
                      'rounded-2xl border p-4',
                      readiness?.ready_for_production
                        ? 'border-emerald-200 bg-emerald-50'
                        : 'border-amber-200 bg-amber-50',
                    )}
                  >
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Producao</p>
                    <p className="mt-2 text-base font-semibold text-slate-900">
                      {loadingReadiness
                        ? 'Conferindo ambiente...'
                        : readiness?.ready_for_production
                          ? 'Pronto para operar'
                          : 'Ainda precisa de ajustes'}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {loadingReadiness
                        ? 'Aguarde alguns segundos.'
                        : `${readiness?.summary.critical || 0} critico(s) e ${readiness?.summary.warning || 0} alerta(s).`}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        <div className={cn('grid gap-6', isAdmin ? 'xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.95fr)]' : 'grid-cols-1')}>
          <section className="card">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-display font-bold text-slate-950">Historico de backups</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Veja os backups completos gerados no drive configurado e o tamanho aproximado de cada pacote.
                </p>
              </div>
              <button
                onClick={() => queryClient.invalidateQueries({ queryKey: ['ops-backups'] })}
                className="btn-secondary inline-flex items-center gap-2"
              >
                <RefreshCw size={16} />
                Atualizar lista
              </button>
            </div>

            {loadingBackups ? (
              <div className="mt-6 space-y-3">
                {[...Array(3)].map((_, index) => (
                  <div key={index} className="h-24 animate-pulse rounded-[24px] bg-slate-100" />
                ))}
              </div>
            ) : backups?.items?.length ? (
              <div className="mt-6 space-y-3">
                {backups.items.map((item) => (
                  <div key={item.id} className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <FolderArchive size={16} className="text-sky-600" />
                          <p className="text-sm font-semibold text-slate-900">{item.timestamp}</p>
                        </div>
                        <p className="mt-2 break-all text-xs text-slate-500">{item.directory}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {item.database_file && (
                            <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                              dump do banco
                            </span>
                          )}
                          {item.assets_file && (
                            <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                              uploads e pdfs
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-white bg-white px-4 py-3 text-right shadow-sm">
                        <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Tamanho</p>
                        <p className="mt-2 text-lg font-display font-bold text-slate-950">{item.size_human}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state py-12">
                <div className="empty-state-icon">
                  <Database size={26} className="text-slate-400" />
                </div>
                <p className="text-sm font-medium text-slate-500">
                  Nenhum backup encontrado no diretorio configurado.
                </p>
              </div>
            )}
          </section>

          {isAdmin && (
            <div className="space-y-6">
              <section className="card">
                <div className="flex items-center gap-3">
                  <AlertTriangle size={20} className="text-amber-600" />
                  <div>
                    <h2 className="text-xl font-display font-bold text-slate-950">Prontidao para producao</h2>
                    <p className="text-sm text-slate-500">Somente o administrador ve este checklist.</p>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-3 gap-3">
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">OK</p>
                    <p className="mt-2 text-2xl font-display font-bold text-emerald-700">{readiness?.summary.ok || 0}</p>
                  </div>
                  <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Alertas</p>
                    <p className="mt-2 text-2xl font-display font-bold text-amber-700">{readiness?.summary.warning || 0}</p>
                  </div>
                  <div className="rounded-2xl border border-red-100 bg-red-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Criticos</p>
                    <p className="mt-2 text-2xl font-display font-bold text-red-700">{readiness?.summary.critical || 0}</p>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  {(readiness?.checks || []).filter((check) => check.status !== 'ok').slice(0, 4).map((check) => (
                    <div
                      key={check.id}
                      className={cn(
                        'rounded-[22px] border p-4',
                        check.status === 'critical'
                          ? 'border-red-200 bg-red-50/80'
                          : 'border-amber-200 bg-amber-50/80',
                      )}
                    >
                      <p className="text-sm font-semibold text-slate-900">{check.title}</p>
                      <p className="mt-1 text-sm text-slate-600">{check.action}</p>
                    </div>
                  ))}
                  {!loadingReadiness && !(readiness?.checks || []).some((check) => check.status !== 'ok') && (
                    <div className="rounded-[22px] border border-emerald-200 bg-emerald-50/70 p-4 text-sm text-emerald-700">
                      Nenhum ajuste pendente detectado no checklist.
                    </div>
                  )}
                </div>
              </section>

              <section className="card">
                <div className="flex items-center gap-3">
                  <GitCommitHorizontal size={20} className="text-sky-600" />
                  <div>
                    <h2 className="text-xl font-display font-bold text-slate-950">Versoes do sistema</h2>
                    <p className="text-sm text-slate-500">Visivel apenas para o administrador da plataforma.</p>
                  </div>
                </div>

                {loadingVersion ? (
                  <div className="mt-5 h-40 animate-pulse rounded-[24px] bg-slate-100" />
                ) : versionInfo ? (
                  <div className="mt-5 space-y-4">
                    <div className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Atual</p>
                          <p className="mt-2 text-lg font-display font-bold text-slate-950">
                            {versionInfo.short_hash} · {versionInfo.branch}
                          </p>
                          <p className="mt-1 text-sm text-slate-500">{versionInfo.last_message}</p>
                        </div>
                        <span
                          className={cn(
                            'rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]',
                            versionInfo.dirty
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-emerald-100 text-emerald-700',
                          )}
                        >
                          {versionInfo.dirty ? 'alteracoes locais' : 'sincronizado'}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {versionInfo.recent_commits.map((commit) => (
                        <div key={`${commit.short_hash}-${commit.committed_at}`} className="rounded-[22px] border border-slate-200 bg-white p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold text-slate-900">{commit.short_hash}</p>
                              <p className="mt-1 text-sm text-slate-600">{commit.title}</p>
                            </div>
                            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-500">
                              <Clock3 size={13} />
                              {commit.committed_at}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="mt-5 rounded-[22px] border border-amber-100 bg-amber-50 p-4 text-sm text-amber-700">
                    Nao foi possivel ler as informacoes do repositorio git neste ambiente.
                  </div>
                )}
              </section>
            </div>
          )}
        </div>

        {isAdmin && (
          <section className="card">
            <div className="flex items-center gap-3">
              <CheckCircle2 size={20} className="text-emerald-600" />
              <div>
                <h2 className="text-xl font-display font-bold text-slate-950">Boas praticas desta area</h2>
                <p className="text-sm text-slate-500">Fluxo simples para operar com seguranca.</p>
              </div>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <div className="rounded-[22px] border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-sm font-semibold text-slate-900">1. Gere backup antes de manutencao maior</p>
                <p className="mt-2 text-sm text-slate-500">Sempre rode um backup manual antes de subir alteracoes importantes no ambiente real.</p>
              </div>
              <div className="rounded-[22px] border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-sm font-semibold text-slate-900">2. Confira os criticos antes do go-live</p>
                <p className="mt-2 text-sm text-slate-500">Secret key, senha do banco e conta padrao sao pontos que precisam estar fechados antes de abrir para usuarios reais.</p>
              </div>
              <div className="rounded-[22px] border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-sm font-semibold text-slate-900">3. Mantenha o GitHub atualizado</p>
                <p className="mt-2 text-sm text-slate-500">Use o repositório como ultimo estado conhecido do sistema para acelerar restauracao e redeploy.</p>
              </div>
            </div>
          </section>
        )}
      </div>
    </AppLayout>
  )
}

export default Governanca
