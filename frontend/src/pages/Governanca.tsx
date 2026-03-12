import React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  ExternalLink,
  FolderArchive,
  GitCommitHorizontal,
  HardDriveDownload,
  Loader2,
  RefreshCw,
  RotateCw,
  ShieldCheck,
} from 'lucide-react'
import toast from 'react-hot-toast'

import AppLayout from '@/components/layout/AppLayout'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import api from '@/services/api'
import { BackupHistoryItem, BackupOverview, BackupRunResponse, OpsReadiness, VersionStatus } from '@/types'

const getApiErrorMessage = (error: any, fallback: string) => {
  const detail = error?.response?.data?.detail ?? error?.response?.data?.message
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'string' ? item : item?.msg || item?.message))
      .filter(Boolean)[0] || fallback
  }
  return fallback
}

const getDownloadName = (headers: Record<string, string>, fallback: string) => {
  const disposition = headers['content-disposition'] || headers['Content-Disposition']
  if (!disposition) return fallback

  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utfMatch?.[1]) return decodeURIComponent(utfMatch[1])

  const asciiMatch = disposition.match(/filename="?([^"]+)"?/i)
  return asciiMatch?.[1] || fallback
}

const downloadBackupFile = async (url: string, fallbackName: string) => {
  const response = await api.get(url, { responseType: 'blob' })
  const downloadUrl = window.URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = downloadUrl
  anchor.download = getDownloadName(response.headers as Record<string, string>, fallbackName)
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.URL.revokeObjectURL(downloadUrl)
}

const getDriveStatusTone = (status?: string) => {
  switch (status) {
    case 'synced':
      return 'bg-emerald-100 text-emerald-700'
    case 'error':
      return 'bg-red-100 text-red-700'
    case 'syncing':
      return 'bg-sky-100 text-sky-700'
    case 'pending':
      return 'bg-amber-100 text-amber-700'
    default:
      return 'bg-slate-100 text-slate-700'
  }
}

const Governanca: React.FC = () => {
  const queryClient = useQueryClient()
  const { isPlatformAdmin } = useAuth()

  const backupsQuery = useQuery({
    queryKey: ['ops-backups'],
    queryFn: async () => {
      const { data } = await api.get<BackupOverview>('/ops/backups')
      return data
    },
    staleTime: 0,
    refetchOnMount: 'always',
    retry: false,
  })

  const { data: readiness, isLoading: loadingReadiness } = useQuery({
    queryKey: ['ops-readiness'],
    queryFn: async () => {
      const { data } = await api.get<OpsReadiness>('/ops/readiness')
      return data
    },
    enabled: isPlatformAdmin,
    retry: false,
  })

  const { data: versionInfo, isLoading: loadingVersion } = useQuery({
    queryKey: ['ops-version'],
    queryFn: async () => {
      const { data } = await api.get<VersionStatus>('/ops/version')
      return data
    },
    enabled: isPlatformAdmin,
    retry: false,
  })

  const runBackupMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<BackupRunResponse>('/ops/backups/run')
      return data
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Backup executado com sucesso!')
      if (data.google_drive?.status === 'error') {
        toast.error(data.google_drive.message || 'O backup local foi salvo, mas o sync com o Google Drive falhou.')
      }
      queryClient.invalidateQueries({ queryKey: ['ops-backups'] })
      if (isPlatformAdmin) {
        queryClient.invalidateQueries({ queryKey: ['ops-readiness'] })
      }
    },
    onError: (error: any) => {
      toast.error(getApiErrorMessage(error, 'Nao foi possivel executar o backup agora.'))
    },
  })

  const syncDriveMutation = useMutation({
    mutationFn: async (backupId: string) => {
      const { data } = await api.post(`/ops/backups/${backupId}/sync-google-drive`)
      return data
    },
    onSuccess: () => {
      toast.success('Backup sincronizado com o Google Drive.')
      queryClient.invalidateQueries({ queryKey: ['ops-backups'] })
    },
    onError: (error: any) => {
      toast.error(getApiErrorMessage(error, 'Nao foi possivel sincronizar com o Google Drive.'))
    },
  })

  const handleRefresh = async () => {
    const result = await backupsQuery.refetch()
    if (result.error) {
      toast.error(getApiErrorMessage(result.error, 'Nao foi possivel atualizar a lista de backups.'))
      return
    }
    toast.success('Lista de backups atualizada.')
  }

  const handleDownload = async (item: BackupHistoryItem, kind: 'bundle' | 'database' | 'assets' | 'manifest') => {
    const fallback = {
      bundle: `backup-${item.id}.tar.gz`,
      database: `${item.id}-database.sql`,
      assets: `${item.id}-assets.tar.gz`,
      manifest: `${item.id}-manifest.txt`,
    }[kind]

    try {
      await downloadBackupFile(item.downloads[kind], fallback)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Nao foi possivel baixar esse arquivo agora.'))
    }
  }

  const backups = backupsQuery.data
  const loadingBackups = backupsQuery.isLoading
  const refreshingBackups = backupsQuery.isFetching && !backupsQuery.isLoading
  const latestBackup = backups?.items?.[0]

  return (
    <AppLayout>
      <div className="space-y-6 pb-8">
        <section className="overflow-hidden rounded-[30px] border border-sky-100 bg-[linear-gradient(135deg,#e0f2fe_0%,#ffffff_52%,#f8fbff_100%)] p-6 shadow-[0_20px_55px_rgba(96,165,250,0.12)]">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_360px]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-700 ring-1 ring-sky-100">
                <ShieldCheck size={13} />
                Governanca do ambiente
              </div>
              <h1 className="mt-4 text-3xl font-display font-bold text-slate-950">
                Backups, versoes e seguranca operacional
              </h1>
              <p className="mt-3 max-w-3xl text-sm text-slate-600">
                Aqui voce acompanha onde os backups estao salvos, baixa o pacote completo quando precisar e monitora a sincronizacao automatica com o Google Drive do cliente. Checklist de producao e versoes continuam visiveis apenas para o admin principal admin@mpcars.com.
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
                <button
                  onClick={handleRefresh}
                  disabled={refreshingBackups}
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  <RefreshCw size={16} className={cn(refreshingBackups && 'animate-spin')} />
                  Atualizar lista
                </button>
                {backups?.google_drive?.folder_url && (
                  <a
                    href={backups.google_drive.folder_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary inline-flex items-center gap-2"
                  >
                    <ExternalLink size={16} />
                    Abrir pasta do Drive
                  </a>
                )}
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <div className="rounded-[24px] border border-white bg-white/90 p-5 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Onde fica salvo</p>
                  <p className="mt-3 text-lg font-display font-bold text-slate-950">{backups?.storage_label || 'Drive dedicado da VPS'}</p>
                  <p className="mt-2 break-all text-sm text-slate-500">
                    {backups?.directory || '/backups'}
                  </p>
                  <p className="mt-3 text-xs text-slate-500">
                    Esse e o caminho atual usado pela API para guardar os pacotes completos.
                  </p>
                </div>

                <div className="rounded-[24px] border border-white bg-white/90 p-5 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Google Drive</p>
                  <p className="mt-3 text-lg font-display font-bold text-slate-950">
                    {backups?.google_drive?.configured ? 'Conectado e pronto' : 'Aguardando configuracao'}
                  </p>
                  <p className="mt-2 text-sm text-slate-500">
                    {backups?.google_drive?.configured
                      ? `Sync automatico ${backups.google_drive.sync_on_backup ? 'ativo' : 'desativado'}`
                      : 'Compartilhe a pasta do cliente com a conta de servico para ativar o sync automatico.'}
                  </p>
                  <p className="mt-3 break-all text-xs text-slate-500">
                    {backups?.google_drive?.service_account_email || 'Conta de servico ainda nao configurada.'}
                  </p>
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
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Sync do Drive</p>
                  <p className="mt-2 text-base font-semibold text-slate-900">
                    {latestBackup?.google_drive?.status === 'synced'
                      ? 'Ultimo backup ja sincronizado'
                      : backups?.google_drive?.configured
                        ? 'Pronto para sincronizar automaticamente'
                        : 'Conector ainda nao configurado'}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {latestBackup?.google_drive?.folder_url
                      ? 'A pasta remota do ultimo backup ja esta disponivel.'
                      : backups?.google_drive?.folder_url
                        ? 'A pasta raiz do cliente no Drive ja esta conectada.'
                        : 'Sem pasta remota vinculada ainda.'}
                  </p>
                </div>
                {isPlatformAdmin && (
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

        <div className={cn('grid gap-6', isPlatformAdmin ? 'xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.95fr)]' : 'grid-cols-1')}>
          <section className="card">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-display font-bold text-slate-950">Historico de backups</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Baixe o pacote completo, os arquivos separados ou abra a pasta remota no Google Drive quando o sync estiver ativo.
                </p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-700">
                {refreshingBackups ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
                {refreshingBackups ? 'Atualizando lista...' : `${backups?.items?.length || 0} backup(s) encontrado(s)`}
              </div>
            </div>

            {loadingBackups ? (
              <div className="mt-6 space-y-3">
                {[...Array(3)].map((_, index) => (
                  <div key={index} className="h-28 animate-pulse rounded-[24px] bg-slate-100" />
                ))}
              </div>
            ) : backupsQuery.isError ? (
              <div className="mt-6 rounded-[24px] border border-red-100 bg-red-50 p-5">
                <p className="text-sm font-semibold text-red-800">Nao foi possivel carregar os backups.</p>
                <p className="mt-2 text-sm text-red-700">
                  {getApiErrorMessage(backupsQuery.error, 'Confira a permissao deste usuario ou a configuracao do diretorio de backup.')}
                </p>
              </div>
            ) : backups?.items?.length ? (
              <div className="mt-6 space-y-3">
                {backups.items.map((item) => (
                  <div key={item.id} className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-4">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <FolderArchive size={16} className="text-sky-600" />
                          <p className="text-sm font-semibold text-slate-900">{item.timestamp}</p>
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                            {item.size_human}
                          </span>
                          <span className={cn('rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]', getDriveStatusTone(item.google_drive?.status))}>
                            Drive {item.google_drive?.status || 'desligado'}
                          </span>
                        </div>

                        <p className="mt-2 break-all text-xs text-slate-500">{item.directory}</p>

                        <div className="mt-4 flex flex-wrap gap-2">
                          <button
                            onClick={() => handleDownload(item, 'bundle')}
                            className="btn-secondary inline-flex items-center gap-2"
                          >
                            <Download size={14} />
                            Pacote completo
                          </button>
                          {item.database_file && (
                            <button
                              onClick={() => handleDownload(item, 'database')}
                              className="btn-secondary inline-flex items-center gap-2"
                            >
                              <Download size={14} />
                              Banco
                            </button>
                          )}
                          {item.assets_file && (
                            <button
                              onClick={() => handleDownload(item, 'assets')}
                              className="btn-secondary inline-flex items-center gap-2"
                            >
                              <Download size={14} />
                              Assets
                            </button>
                          )}
                          <button
                            onClick={() => handleDownload(item, 'manifest')}
                            className="btn-secondary inline-flex items-center gap-2"
                          >
                            <Download size={14} />
                            Manifesto
                          </button>
                          {item.google_drive?.folder_url && (
                            <a
                              href={item.google_drive.folder_url}
                              target="_blank"
                              rel="noreferrer"
                              className="btn-secondary inline-flex items-center gap-2"
                            >
                              <ExternalLink size={14} />
                              Abrir no Drive
                            </a>
                          )}
                          {backups?.google_drive?.configured && item.google_drive?.status !== 'synced' && (
                            <button
                              onClick={() => syncDriveMutation.mutate(item.id)}
                              disabled={syncDriveMutation.isPending}
                              className="btn-secondary inline-flex items-center gap-2"
                            >
                              {syncDriveMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RotateCw size={14} />}
                              Sincronizar Drive
                            </button>
                          )}
                        </div>

                        {(item.google_drive?.last_error || item.google_drive?.service_account_email || item.google_drive?.synced_at) && (
                          <div className="mt-4 grid gap-3 md:grid-cols-2">
                            <div className="rounded-[20px] border border-white bg-white p-4 shadow-sm">
                              <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Conta do conector</p>
                              <p className="mt-2 break-all text-sm font-medium text-slate-900">
                                {item.google_drive?.service_account_email || backups?.google_drive?.service_account_email || 'Nao configurada'}
                              </p>
                            </div>
                            <div className="rounded-[20px] border border-white bg-white p-4 shadow-sm">
                              <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Ultimo status</p>
                              <p className="mt-2 text-sm font-medium text-slate-900">
                                {item.google_drive?.synced_at
                                  ? `Sincronizado em ${item.google_drive.synced_at}`
                                  : item.google_drive?.last_attempt_at
                                    ? `Tentativa em ${item.google_drive.last_attempt_at}`
                                    : 'Ainda sem tentativa'}
                              </p>
                              {item.google_drive?.last_error && (
                                <p className="mt-2 text-xs text-red-600">{item.google_drive.last_error}</p>
                              )}
                            </div>
                          </div>
                        )}
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
                <p className="mt-2 text-xs text-slate-400">{backups?.directory || '/backups'}</p>
              </div>
            )}
          </section>

          {isPlatformAdmin && (
            <div className="space-y-6">
              <section className="card">
                <div className="flex items-center gap-3">
                  <AlertTriangle size={20} className="text-amber-600" />
                  <div>
                    <h2 className="text-xl font-display font-bold text-slate-950">Prontidao para producao</h2>
                    <p className="text-sm text-slate-500">Somente o administrador principal ve este checklist.</p>
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

        {isPlatformAdmin && (
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
                <p className="text-sm font-semibold text-slate-900">2. Compartilhe a pasta do Drive com a conta de servico</p>
                <p className="mt-2 text-sm text-slate-500">Assim o sync automatico salva o banco e os arquivos do cliente tambem fora da VPS.</p>
              </div>
              <div className="rounded-[22px] border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-sm font-semibold text-slate-900">3. Mantenha o GitHub atualizado</p>
                <p className="mt-2 text-sm text-slate-500">Use o repositorio como ultimo estado conhecido do sistema para acelerar restauracao e redeploy.</p>
              </div>
            </div>
          </section>
        )}
      </div>
    </AppLayout>
  )
}

export default Governanca
