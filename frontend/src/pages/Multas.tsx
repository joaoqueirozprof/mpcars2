import React, { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Clock3, Edit, Plus, Search, ShieldAlert, Trash2, X } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'

import AppLayout from '@/components/layout/AppLayout'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import DataTable from '@/components/shared/DataTable'
import { formatCurrency, formatDate } from '@/lib/utils'
import api from '@/services/api'
import { Multa, PaginatedResponse, PaginationParams } from '@/types'

const Multas: React.FC = () => {
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingFine, setEditingFine] = useState<Multa | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState({
    veiculo_id: '',
    numero_infracao: '',
    data_infracao: '',
    valor: 0,
    data_vencimento: '',
    data_pagamento: '',
    status: 'pendente' as 'pendente' | 'pago' | 'vencido',
    descricao: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['multas', pagination, statusFilter, searchTerm],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Multa>>('/multas', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          status: statusFilter !== 'todos' ? statusFilter : undefined,
          search: searchTerm || undefined,
        },
      })
      return data
    },
  })

  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/veiculos', { params: { limit: 1000 } })
      return (data.data || []).map((veiculo: any) => ({
        ...veiculo,
        quilometragem: veiculo.km_atual || 0,
        cor: veiculo.cor || '',
      }))
    },
  })

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/multas', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['multas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Multa criada com sucesso!')
    },
    onError: (error: any) => toast.error(error.response?.data?.message || 'Erro ao criar multa'),
  })

  const updateMutation = useMutation({
    mutationFn: (payload: any) => api.patch(`/multas/${editingFine?.id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['multas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Multa atualizada com sucesso!')
    },
    onError: (error: any) => toast.error(error.response?.data?.message || 'Erro ao atualizar multa'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/multas/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['multas'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Multa deletada com sucesso!')
    },
    onError: (error: any) => toast.error(error.response?.data?.message || 'Erro ao deletar multa'),
  })

  const resetForm = () => {
    setFormData({
      veiculo_id: '',
      numero_infracao: '',
      data_infracao: '',
      valor: 0,
      data_vencimento: '',
      data_pagamento: '',
      status: 'pendente',
      descricao: '',
    })
    setEditingFine(null)
  }

  const handleOpenModal = (fine?: Multa) => {
    if (fine) {
      setEditingFine(fine)
      setFormData({
        veiculo_id: String(fine.veiculo_id),
        numero_infracao: fine.numero_infracao,
        data_infracao: fine.data_infracao ? fine.data_infracao.slice(0, 10) : '',
        valor: Number(fine.valor || 0),
        data_vencimento: fine.data_vencimento ? fine.data_vencimento.slice(0, 10) : '',
        data_pagamento: fine.data_pagamento ? fine.data_pagamento.slice(0, 10) : '',
        status: fine.status,
        descricao: fine.descricao || '',
      })
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  useEffect(() => {
    if (searchParams.get('quick') !== 'create') return

    handleOpenModal()
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('quick')
    setSearchParams(nextParams, { replace: true })
  }, [searchParams, setSearchParams])

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()

    if (!formData.veiculo_id || !formData.numero_infracao || formData.valor <= 0) {
      toast.error('Preencha todos os campos obrigatorios')
      return
    }

    const payload = {
      ...formData,
      veiculo_id: String(formData.veiculo_id),
      status: formData.data_pagamento ? 'pago' : formData.status,
    }

    if (editingFine) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setPagination({ ...pagination, page: 1 })
  }

  const summary = useMemo(() => {
    const list = data?.data || []
    const pendentes = list.filter((fine) => fine.status === 'pendente').length
    const vencidas = list.filter((fine) => fine.status === 'vencido').length
    const pagas = list.filter((fine) => fine.status === 'pago').length
    const valorAberto = list
      .filter((fine) => fine.status !== 'pago')
      .reduce((total, fine) => total + Number(fine.valor || 0), 0)

    return {
      total: data?.total || 0,
      pendentes,
      vencidas,
      pagas,
      valorAberto,
    }
  }, [data])

  const urgentFines = useMemo(
    () => (data?.data || []).filter((fine) => fine.status === 'vencido').slice(0, 3),
    [data]
  )

  const columns = [
    {
      key: 'numero_infracao' as const,
      label: 'Numero',
      sortable: true,
      width: '15%',
      render: (numero: string) => <span className="font-medium text-slate-900">{numero}</span>,
    },
    {
      key: 'veiculo_id' as const,
      label: 'Veiculo',
      render: (_: any, row: any) => <span className="text-slate-900">{row.veiculo?.placa || '-'}</span>,
    },
    {
      key: 'data_infracao' as const,
      label: 'Data infracao',
      render: (date: string) => <span className="text-slate-700">{formatDate(date)}</span>,
    },
    {
      key: 'valor' as const,
      label: 'Valor',
      render: (value: number) => <span className="font-semibold text-red-600">{formatCurrency(value)}</span>,
    },
    {
      key: 'data_vencimento' as const,
      label: 'Vencimento',
      render: (date: string) => <span className="text-slate-700">{formatDate(date)}</span>,
    },
    {
      key: 'status' as const,
      label: 'Status',
      render: (status: string) => (
        <div className="flex items-center gap-1">
          {status === 'pago' && <span className="badge-success">Pago</span>}
          {status === 'pendente' && <span className="badge-warning">Pendente</span>}
          {status === 'vencido' && <span className="badge-danger">Vencido</span>}
        </div>
      ),
    },
    {
      key: 'id' as const,
      label: 'Acoes',
      render: (_: any, row: Multa) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleOpenModal(row)}
            className="btn-icon rounded transition-colors hover:bg-blue-50 hover:text-blue-600"
            title="Editar"
          >
            <Edit size={16} />
          </button>
          <button
            onClick={() => setDeleteConfirm({ isOpen: true, id: row.id })}
            className="btn-icon rounded transition-colors hover:bg-red-50 hover:text-red-600"
            title="Deletar"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ),
    },
  ]

  const isLoaded = !isLoading && data?.data
  const isEmpty = isLoaded && data.data.length === 0

  return (
    <AppLayout>
      <div className="space-y-6 stagger-children">
        <section className="rounded-[30px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(254,226,226,0.9),transparent_30%),linear-gradient(135deg,#fff7ed_0%,#ffffff_58%,#f8fafc_100%)] p-6 shadow-[0_18px_48px_rgba(15,23,42,0.08)]">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-rose-700 ring-1 ring-rose-100">
                <ShieldAlert size={13} />
                Controle de risco
              </div>
              <h1 className="mt-4 flex items-center gap-3 text-3xl font-display font-bold text-slate-950">
                <AlertTriangle className="text-red-600" size={30} />
                Multas e infracoes
              </h1>
              <p className="mt-3 text-sm text-slate-600">
                Acompanhe vencimentos, placas impactadas e o valor em aberto para evitar perda de prazo e custo desnecessario.
              </p>
            </div>

            <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2 whitespace-nowrap">
              <Plus size={20} />
              Nova Multa
            </button>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-[24px] border border-white/70 bg-white/90 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Total listado</p>
              <p className="mt-3 text-3xl font-display font-bold text-slate-950">{summary.total}</p>
              <p className="mt-2 text-sm text-slate-500">Itens visiveis com os filtros atuais</p>
            </div>
            <div className="rounded-[24px] border border-white/70 bg-white/90 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Pendentes</p>
              <p className="mt-3 text-3xl font-display font-bold text-amber-600">{summary.pendentes}</p>
              <p className="mt-2 text-sm text-slate-500">Ainda aguardando pagamento</p>
            </div>
            <div className="rounded-[24px] border border-white/70 bg-white/90 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Vencidas</p>
              <p className="mt-3 text-3xl font-display font-bold text-red-600">{summary.vencidas}</p>
              <p className="mt-2 text-sm text-slate-500">Precisam de acao imediata</p>
            </div>
            <div className="rounded-[24px] border border-white/70 bg-white/90 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Valor em aberto</p>
              <p className="mt-3 text-3xl font-display font-bold text-slate-950">{formatCurrency(summary.valorAberto)}</p>
              <p className="mt-2 text-sm text-slate-500">Pendentes e vencidas somadas</p>
            </div>
          </div>
        </section>

        {urgentFines.length > 0 && (
          <div className="rounded-[26px] border border-red-200 bg-red-50/70 p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-red-600">Atencao imediata</p>
                <h2 className="mt-1 text-lg font-display font-bold text-red-950">Multas vencidas na fila</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {urgentFines.map((fine) => (
                  <span key={fine.id} className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-red-700 ring-1 ring-red-200">
                    <Clock3 size={12} />
                    {fine.numero_infracao} - {formatCurrency(fine.valor)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
          <div className="flex gap-2 flex-wrap">
            {['todos', 'pendente', 'pago', 'vencido'].map((status) => (
              <button
                key={status}
                onClick={() => handleStatusFilter(status)}
                className={`filter-tab ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {status === 'todos' ? 'Todos' : status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <Search size={18} className="text-slate-400" />
              <input
                type="text"
                placeholder="Buscar por numero da infracao, placa ou descricao..."
                value={searchTerm}
                onChange={(event) => {
                  setSearchTerm(event.target.value)
                  setPagination({ ...pagination, page: 1 })
                }}
                className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
              />
            </div>
          </div>
        </div>

        <div className="card">
          {isEmpty ? (
            <div className="empty-state py-12">
              <div className="empty-state-icon mb-4 bg-red-50">
                <AlertTriangle className="text-red-600" size={40} />
              </div>
              <h3 className="mb-2 text-lg font-semibold text-slate-900">Nenhuma multa registrada</h3>
              <p className="mb-4 text-slate-600">Quando houver uma infracao, voce pode registrar aqui para nao perder o controle do vencimento.</p>
              <button onClick={() => handleOpenModal()} className="btn-primary">
                <Plus size={20} className="mr-2 inline" />
                Nova Multa
              </button>
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={data?.data || []}
              isLoading={isLoading}
              pagination={{
                page: pagination.page,
                limit: pagination.limit,
                total: data?.total || 0,
                onPageChange: (page) => setPagination({ ...pagination, page }),
              }}
            />
          )}
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && setIsModalOpen(false)}>
          <div className="modal-content max-w-2xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <h3 className="text-lg font-display font-bold text-slate-900">{editingFine ? 'Editar Multa' : 'Nova Multa'}</h3>
              <button onClick={() => setIsModalOpen(false)} className="btn-icon" title="Fechar">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex min-h-0 flex-col">
              <div className="modal-scroll-body space-y-4">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <label className="input-label">Veiculo *</label>
                    <select
                      value={formData.veiculo_id}
                      onChange={(event) => setFormData({ ...formData, veiculo_id: event.target.value })}
                      className="input-field"
                      disabled={createMutation.isPending || updateMutation.isPending}
                    >
                      <option value="">Selecione um veiculo</option>
                      {veiculos?.map((veiculo) => (
                        <option key={veiculo.id} value={veiculo.id}>
                          {veiculo.placa} - {veiculo.marca} {veiculo.modelo}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="input-label">Numero da infracao *</label>
                    <input
                      type="text"
                      value={formData.numero_infracao}
                      onChange={(event) => setFormData({ ...formData, numero_infracao: event.target.value })}
                      className="input-field"
                      placeholder="Numero da infracao"
                      disabled={createMutation.isPending || updateMutation.isPending}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <div>
                    <label className="input-label">Data infracao</label>
                    <input
                      type="date"
                      value={formData.data_infracao}
                      onChange={(event) => setFormData({ ...formData, data_infracao: event.target.value })}
                      className="input-field"
                      disabled={createMutation.isPending || updateMutation.isPending}
                    />
                  </div>
                  <div>
                    <label className="input-label">Valor *</label>
                    <input
                      type="number"
                      value={formData.valor}
                      onChange={(event) => setFormData({ ...formData, valor: parseFloat(event.target.value || '0') })}
                      step="0.01"
                      min="0"
                      className="input-field"
                      placeholder="0,00"
                      disabled={createMutation.isPending || updateMutation.isPending}
                    />
                  </div>
                  <div>
                    <label className="input-label">Status</label>
                    <select
                      value={formData.status}
                      onChange={(event) => setFormData({ ...formData, status: event.target.value as any })}
                      className="input-field"
                      disabled={createMutation.isPending || updateMutation.isPending}
                    >
                      <option value="pendente">Pendente</option>
                      <option value="pago">Pago</option>
                      <option value="vencido">Vencido</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <label className="input-label">Data vencimento</label>
                    <input
                      type="date"
                      value={formData.data_vencimento}
                      onChange={(event) => setFormData({ ...formData, data_vencimento: event.target.value })}
                      className="input-field"
                      disabled={createMutation.isPending || updateMutation.isPending}
                    />
                  </div>
                  <div>
                    <label className="input-label">Data pagamento</label>
                    <input
                      type="date"
                      value={formData.data_pagamento}
                      onChange={(event) => setFormData({ ...formData, data_pagamento: event.target.value, status: event.target.value ? 'pago' : formData.status })}
                      className="input-field"
                      disabled={createMutation.isPending || updateMutation.isPending}
                    />
                  </div>
                </div>

                <div>
                  <label className="input-label">Descricao da infracao</label>
                  <textarea
                    value={formData.descricao}
                    onChange={(event) => setFormData({ ...formData, descricao: event.target.value })}
                    className="input-field"
                    rows={4}
                    placeholder="Descreva o ocorrido"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                  {createMutation.isPending || updateMutation.isPending ? 'Processando...' : editingFine ? 'Atualizar Multa' : 'Criar Multa'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Multa"
        message="Tem certeza que deseja deletar esta multa? Esta acao nao pode ser desfeita."
        confirmText="Deletar"
        cancelText="Cancelar"
        isDanger={true}
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteConfirm.id && deleteMutation.mutate(deleteConfirm.id)}
        onCancel={() => setDeleteConfirm({ isOpen: false })}
      />
    </AppLayout>
  )
}

export default Multas
