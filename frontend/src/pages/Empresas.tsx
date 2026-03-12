import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Building2, X } from 'lucide-react'
import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import { Empresa, PaginatedResponse, PaginationParams } from '@/types'
import { formatPhone, formatCNPJ } from '@/lib/utils'

const Empresas: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCompany, setEditingCompany] = useState<Empresa | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [searchTerm, setSearchTerm] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState({
    nome: '',
    cnpj: '',
    telefone: '',
    email: '',
    endereco: '',
    cidade: '',
    estado: '',
    cep: '',
    responsavel: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['empresas', pagination, searchTerm],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Empresa>>('/empresas', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          search: searchTerm || undefined,
        },
      })
      return data
    },
  })

  const createMutation = useMutation({
    mutationFn: (formData: any) => api.post('/empresas', formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['empresas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Empresa criada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar empresa')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (formData: any) => api.patch(`/empresas/${editingCompany?.id}`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['empresas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Empresa atualizada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar empresa')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/empresas/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['empresas'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Empresa deletada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar empresa')
    },
  })

  const resetForm = () => {
    setFormData({
      nome: '',
      cnpj: '',
      telefone: '',
      email: '',
      endereco: '',
      cidade: '',
      estado: '',
      cep: '',
      responsavel: '',
    })
    setEditingCompany(null)
  }

  const handleOpenModal = (company?: Empresa) => {
    if (company) {
      setEditingCompany(company)
      setFormData(company)
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.nome || !formData.cnpj) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (editingCompany) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleSearch = (value: string) => {
    setSearchTerm(value)
    setPagination({ ...pagination, page: 1 })
  }

  const columns = [
    {
      key: 'nome' as const,
      label: 'Nome',
      sortable: true,
      width: '25%',
      render: (nome: string) => <span className="font-medium text-slate-900">{nome}</span>,
    },
    { key: 'cnpj' as const, label: 'CNPJ', width: '15%', render: (cnpj: string) => formatCNPJ(cnpj) },
    { key: 'telefone' as const, label: 'Telefone', render: (phone: string) => formatPhone(phone) || '-' },
    { key: 'email' as const, label: 'Email', width: '20%', render: (email: string) => email || '-' },
    { key: 'cidade' as const, label: 'Cidade', render: (cidade: string) => cidade || '-' },
    {
      key: 'id' as const,
      label: 'Ações',
      render: (_: any, row: Empresa) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleOpenModal(row)}
            className="btn-icon p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="Editar"
          >
            <Edit size={16} />
          </button>
          <button
            onClick={() => setDeleteConfirm({ isOpen: true, id: row.id })}
            className="btn-icon p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
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
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-2">
              <Building2 className="text-blue-600" size={32} />
              Empresas
            </h1>
            <p className="page-subtitle">Gerenciamento de empresas cadastradas no sistema</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2 whitespace-nowrap">
            <Plus size={20} />
            Nova Empresa
          </button>
        </div>

        <div className="card">
          <div className="mb-6">
            <label className="input-label">Buscar Empresa</label>
            <input
              type="text"
              placeholder="Digite o nome ou CNPJ da empresa..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="input-field"
            />
          </div>

          {isEmpty ? (
            <div className="empty-state py-12">
              <div className="empty-state-icon bg-blue-50 mb-4">
                <Building2 className="text-blue-600" size={40} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Nenhuma empresa encontrada</h3>
              <p className="text-slate-600 mb-4">Comece adicionando a primeira empresa ao sistema</p>
              <button onClick={() => handleOpenModal()} className="btn-primary">
                <Plus size={20} className="inline mr-2" />
                Criar Empresa
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
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
          <div className="modal-content max-w-2xl w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingCompany ? 'Editar Empresa' : 'Nova Empresa'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="btn-icon"
                title="Fechar"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)] space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Nome *</label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    className="input-field"
                    placeholder="Nome da empresa"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">CNPJ *</label>
                  <input
                    type="text"
                    value={formData.cnpj}
                    onChange={(e) => setFormData({ ...formData, cnpj: e.target.value })}
                    className="input-field"
                    placeholder="00.000.000/0000-00"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="input-field"
                    placeholder="email@empresa.com"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Telefone</label>
                  <input
                    type="tel"
                    value={formData.telefone}
                    onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                    className="input-field"
                    placeholder="(11) 9999-9999"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="input-label">Endereço</label>
                  <input
                    type="text"
                    value={formData.endereco}
                    onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
                    className="input-field"
                    placeholder="Rua, número, complemento"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Cidade</label>
                  <input
                    type="text"
                    value={formData.cidade}
                    onChange={(e) => setFormData({ ...formData, cidade: e.target.value })}
                    className="input-field"
                    placeholder="São Paulo"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Estado</label>
                  <input
                    type="text"
                    value={formData.estado}
                    onChange={(e) => setFormData({ ...formData, estado: e.target.value.toUpperCase() })}
                    maxLength={2}
                    className="input-field"
                    placeholder="SP"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">CEP</label>
                  <input
                    type="text"
                    value={formData.cep}
                    onChange={(e) => setFormData({ ...formData, cep: e.target.value })}
                    className="input-field"
                    placeholder="01234-567"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="input-label">Responsável</label>
                  <input
                    type="text"
                    value={formData.responsavel}
                    onChange={(e) => setFormData({ ...formData, responsavel: e.target.value })}
                    className="input-field"
                    placeholder="Nome do responsável"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

            </form>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="btn-secondary"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={createMutation.isPending || updateMutation.isPending}
                onClick={handleSubmit}
              >
                {createMutation.isPending || updateMutation.isPending ? 'Processando...' : editingCompany ? 'Atualizar Empresa' : 'Criar Empresa'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Empresa"
        message="Tem certeza que deseja deletar esta empresa? Esta ação não pode ser desfeita."
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

export default Empresas
