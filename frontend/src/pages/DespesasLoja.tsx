import React, { useState, useEffect, useCallback } from 'react'
import { Store, Plus, Pencil, Trash2, Search, X, DollarSign, TrendingDown } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import AppLayout from '@/components/layout/AppLayout'
import CurrencyInput from '@/components/shared/CurrencyInput'
import toast from 'react-hot-toast'
import api from '@/services/api'
import { useDebounce } from '../hooks/useDebounce'

interface DespesaLoja {
  id: number
  categoria: string
  descricao: string
  valor: number
  mes: number
  ano: number
  data: string | null
}

const CATEGORIAS = [
  'Aluguel',
  'Energia',
  'Agua',
  'Internet/Telefone',
  'Material de Escritorio',
  'Limpeza',
  'Salarios',
  'Impostos',
  'Contador',
  'Marketing',
  'Manutencao Loja',
  'Seguranca',
  'Software/Sistema',
  'Outros',
]

const MESES = [
  { value: 1, label: 'Janeiro' },
  { value: 2, label: 'Fevereiro' },
  { value: 3, label: 'Marco' },
  { value: 4, label: 'Abril' },
  { value: 5, label: 'Maio' },
  { value: 6, label: 'Junho' },
  { value: 7, label: 'Julho' },
  { value: 8, label: 'Agosto' },
  { value: 9, label: 'Setembro' },
  { value: 10, label: 'Outubro' },
  { value: 11, label: 'Novembro' },
  { value: 12, label: 'Dezembro' },
]

const DespesasLoja: React.FC = () => {
  const { user } = useAuth()
  const [despesas, setDespesas] = useState<DespesaLoja[]>([])
  const [loading, setLoading] = useState(true)
  const [totalPages, setTotalPages] = useState(1)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  // Filters
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 300)
  const [filterCategoria, setFilterCategoria] = useState('')
  const [filterMes, setFilterMes] = useState('')
  const [filterAno, setFilterAno] = useState(String(new Date().getFullYear()))

  // Modal
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState({
    categoria: 'Outros',
    descricao: '',
    valor: '' as any,
    mes: String(new Date().getMonth() + 1),
    ano: String(new Date().getFullYear()),
  })

  // Summary
  const [resumo, setResumo] = useState<any>(null)

  // Delete confirmation
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const loadDespesas = useCallback(async () => {
    setLoading(true)
    try {
      let url = `/despesas-loja/?page=${page}&limit=20`
      if (debouncedSearch) url += `&search=${encodeURIComponent(debouncedSearch)}`
      if (filterCategoria) url += `&categoria=${encodeURIComponent(filterCategoria)}`
      if (filterMes) url += `&mes=${filterMes}`
      if (filterAno) url += `&ano=${filterAno}`

      const res = await api.get(url)
      setDespesas(res.data?.data || [])
      setTotal(res.data?.total || 0)
      setTotalPages(res.data?.totalPages || 1)
    } catch {
      toast.error('Erro ao carregar despesas')
    } finally {
      setLoading(false)
    }
  }, [page, debouncedSearch, filterCategoria, filterMes, filterAno])

  const loadResumo = useCallback(async () => {
    try {
      let url = '/despesas-loja/resumo'
      if (filterAno) url += `?ano=${filterAno}`
      const res = await api.get(url)
      setResumo(res.data)
    } catch { }
  }, [filterAno])

  useEffect(() => {
    let cancelled = false
    loadDespesas().finally(() => { if (cancelled) return })
    loadResumo()
    return () => { cancelled = true }
  }, [loadDespesas, loadResumo])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      categoria: formData.categoria,
      descricao: formData.descricao,
      valor: parseFloat(formData.valor),
      mes: parseInt(formData.mes),
      ano: parseInt(formData.ano),
    }

    if (!payload.descricao || !payload.valor || payload.valor <= 0) {
      toast.error('Preencha todos os campos corretamente')
      return
    }

    try {
      if (editingId) {
        await api.put(`/despesas-loja/${editingId}`, payload)
        toast.success('Despesa atualizada!')
      } else {
        await api.post('/despesas-loja/', payload)
        toast.success('Despesa cadastrada!')
      }
      setShowModal(false)
      resetForm()
      loadDespesas()
      loadResumo()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Erro ao salvar despesa')
    }
  }

  const handleEdit = (d: DespesaLoja) => {
    setEditingId(d.id)
    setFormData({
      categoria: d.categoria || 'Outros',
      descricao: d.descricao || '',
      valor: String(d.valor),
      mes: String(d.mes),
      ano: String(d.ano),
    })
    setShowModal(true)
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await api.delete(`/despesas-loja/${deleteId}`)
      toast.success('Despesa excluida!')
      setDeleteId(null)
      loadDespesas()
      loadResumo()
    } catch {
      toast.error('Erro ao excluir despesa')
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setFormData({
      categoria: 'Outros',
      descricao: '',
      valor: '' as any,
      mes: String(new Date().getMonth() + 1),
      ano: String(new Date().getFullYear()),
    })
  }

  const openNew = () => {
    resetForm()
    setShowModal(true)
  }

  useEffect(() => {
    if (searchParams.get('quick') !== 'create') return

    openNew()
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('quick')
    setSearchParams(nextParams, { replace: true })
  }, [searchParams, setSearchParams])

  const formatCurrency = (v: number) =>
    `R$ ${v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const getMesLabel = (m: number) => MESES.find(x => x.value === m)?.label || String(m)

  return (
    <AppLayout>
      <div className="space-y-6 stagger-children">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">Despesas da Loja</h1>
            <p className="page-subtitle">Gerenciamento de despesas gerais da loja</p>
          </div>
          <button onClick={openNew} className="btn-primary flex items-center gap-2">
            <Plus size={18} /> Nova Despesa
          </button>
        </div>

        {/* Summary Cards */}
        {resumo && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-red-100 text-red-700">
                  <TrendingDown size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Total Despesas {filterAno || ''}</p>
                  <p className="text-2xl font-bold text-slate-900">{formatCurrency(resumo.total || 0)}</p>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-orange-100 text-orange-700">
                  <Store size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Quantidade</p>
                  <p className="text-2xl font-bold text-slate-900">{resumo.quantidade || 0} despesas</p>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-blue-100 text-blue-700">
                  <DollarSign size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Media Mensal</p>
                  <p className="text-2xl font-bold text-slate-900">
                    {formatCurrency(resumo.total > 0 ? resumo.total / 12 : 0)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="card">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
            <div className="md:col-span-2">
              <label className="input-label">Buscar</label>
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1) }}
                  placeholder="Buscar por descricao..."
                  className="input-field pl-10"
                />
              </div>
            </div>
            <div>
              <label className="input-label">Categoria</label>
              <select value={filterCategoria} onChange={(e) => { setFilterCategoria(e.target.value); setPage(1) }} className="input-field">
                <option value="">Todas</option>
                {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="input-label">Mes</label>
              <select value={filterMes} onChange={(e) => { setFilterMes(e.target.value); setPage(1) }} className="input-field">
                <option value="">Todos</option>
                {MESES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div>
              <label className="input-label">Ano</label>
              <select value={filterAno} onChange={(e) => { setFilterAno(e.target.value); setPage(1) }} className="input-field">
                <option value="">Todos</option>
                {[2024, 2025, 2026, 2027].map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          {loading ? (
            <div className="text-center py-12">
              <span className="animate-spin inline-block w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></span>
              <p className="text-sm text-slate-500 mt-3">Carregando...</p>
            </div>
          ) : despesas.length === 0 ? (
            <div className="text-center py-12">
              <Store size={48} className="mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">Nenhuma despesa encontrada.</p>
              <button onClick={openNew} className="btn-primary mt-4 text-sm">
                <Plus size={16} className="inline mr-1" /> Cadastrar Despesa
              </button>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="text-left text-xs font-medium text-slate-500 uppercase px-4 py-3">Mes/Ano</th>
                      <th className="text-left text-xs font-medium text-slate-500 uppercase px-4 py-3">Categoria</th>
                      <th className="text-left text-xs font-medium text-slate-500 uppercase px-4 py-3">Descricao</th>
                      <th className="text-right text-xs font-medium text-slate-500 uppercase px-4 py-3">Valor</th>
                      <th className="text-center text-xs font-medium text-slate-500 uppercase px-4 py-3">Acoes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {despesas.map((d) => (
                      <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-slate-900">
                          {getMesLabel(d.mes)}/{d.ano}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs px-2 py-1 rounded-full bg-orange-100 text-orange-700 font-medium">
                            {d.categoria}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700">{d.descricao}</td>
                        <td className="px-4 py-3 text-sm text-right font-bold text-red-600">
                          {formatCurrency(d.valor)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <button onClick={() => handleEdit(d)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-600" title="Editar">
                              <Pencil size={16} />
                            </button>
                            <button onClick={() => setDeleteId(d.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-600" title="Excluir">
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200">
                <p className="text-sm text-slate-500">Mostrando {despesas.length} de {total}</p>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page <= 1}
                    className="btn-secondary text-xs py-1 px-3"
                  >
                    Anterior
                  </button>
                  <span className="text-sm text-slate-600 px-3 py-1">{page} / {totalPages}</span>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page >= totalPages}
                    className="btn-secondary text-xs py-1 px-3"
                  >
                    Proximo
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal Create/Edit */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingId ? 'Editar Despesa' : 'Nova Despesa da Loja'}
              </h3>
              <button onClick={() => setShowModal(false)} className="p-1 rounded-lg hover:bg-slate-100">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="input-label">Mes</label>
                  <select value={formData.mes} onChange={(e) => setFormData({...formData, mes: e.target.value})} className="input-field">
                    {MESES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="input-label">Ano</label>
                  <select value={formData.ano} onChange={(e) => setFormData({...formData, ano: e.target.value})} className="input-field">
                    {[2024, 2025, 2026, 2027].map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="input-label">Categoria</label>
                <select value={formData.categoria} onChange={(e) => setFormData({...formData, categoria: e.target.value})} className="input-field">
                  {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="input-label">Descricao</label>
                <input
                  type="text"
                  value={formData.descricao}
                  onChange={(e) => setFormData({...formData, descricao: e.target.value})}
                  className="input-field"
                  placeholder="Descreva a despesa..."
                  required
                />
              </div>
              <CurrencyInput
                label="Valor (R$)"
                value={parseFloat(formData.valor) || 0}
                onChange={(valor) => setFormData({ ...formData, valor: String(valor) })}
              />
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary flex-1">
                  {editingId ? 'Salvar' : 'Cadastrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setDeleteId(null)}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Confirmar Exclusao</h3>
            <p className="text-sm text-slate-600 mb-4">Tem certeza que deseja excluir esta despesa? Esta acao nao pode ser desfeita.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="btn-secondary flex-1">Cancelar</button>
              <button onClick={handleDelete} className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors flex-1">
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

export default DespesasLoja
