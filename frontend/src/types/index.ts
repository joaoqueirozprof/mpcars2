export interface User {
  id: string;
  nome: string;
  email: string;
  empresa_id?: string;
  perfil: string;
  role?: 'admin' | 'gerente' | 'operador' | 'cliente';
  ativo: boolean;
  permitted_pages?: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Cliente {
  id: string;
  nome: string;
  email: string;
  telefone: string;
  cpf_cnpj: string;
  endereco: string;
  cidade: string;
  estado: string;
  cep: string;
  tipo: 'pessoa_fisica' | 'pessoa_juridica';
  empresa_id: string;
  ativo: boolean;
  data_cadastro: string;
}

export interface Veiculo {
  id: string;
  placa: string;
  marca: string;
  modelo: string;
  ano: number;
  cor: string;
  status: 'disponivel' | 'alugado' | 'manutencao' | 'inativo';
  quilometragem: number;
  km_atual?: number;
  empresa_id: string;
  data_compra: string;
  valor_aquisicao: number;
  valor_diaria?: number;
  observacoes: string;
  foto_url: string | null;
  ativo: boolean;
}

export interface Contrato {
  id: string;
  numero: string;
  cliente_id: string;
  veiculo_id: string;
  data_inicio: string;
  data_fim: string;
  data_finalizacao?: string;
  data_devolucao_real?: string;
  quilometragem_inicial: number;
  quilometragem_final?: number;
  km_atual_veiculo?: number;
  valor_diaria: number;
  valor_total: number;
  status: 'ativo' | 'finalizado' | 'cancelado' | 'atraso';
  empresa_id: string;
  observacoes: string;
  hora_saida?: string;
  combustivel_saida?: string;
  combustivel_retorno?: string;
  km_livres?: number;
  qtd_diarias?: number;
  valor_hora_extra?: number;
  valor_km_excedente?: number;
  valor_avarias?: number;
  taxa_combustivel?: number;
  taxa_limpeza?: number;
  taxa_higienizacao?: number;
  taxa_pneus?: number;
  taxa_acessorios?: number;
  valor_franquia_seguro?: number;
  taxa_administrativa?: number;
  desconto?: number;
  tipo?: 'cliente' | 'empresa';
  cliente?: { nome: string };
  veiculo?: {
    marca: string;
    modelo: string;
    placa: string;
    km_atual?: number;
    checklist?: Record<string, boolean>;
  };
}

export interface Empresa {
  id: string;
  nome: string;
  cnpj: string;
  telefone: string;
  email: string;
  endereco: string;
  cidade: string;
  estado: string;
  cep: string;
  responsavel: string;
  ativo: boolean;
}

export interface Motorista {
  id: string;
  nome: string;
  cpf: string;
  cnh: string;
  telefone: string;
  email: string;
  empresa_id: string;
  ativo: boolean;
}

export interface Financeiro {
  id: string;
  data: string;
  tipo: 'receita' | 'despesa';
  categoria: string;
  descricao: string;
  valor: number;
  empresa_id: string;
  contrato_id?: string;
  veiculo_id?: string;
  comprovante_url?: string;
  status: 'pendente' | 'pago' | 'cancelado';
}

export interface Seguro {
  id: string;
  veiculo_id: string;
  seguradora: string;
  numero_apolice: string;
  data_inicio: string;
  data_fim: string;
  valor_mensal: number;
  cobertura: string;
  empresa_id: string;
  ativo: boolean;
}

export interface IPVA {
  id: string;
  veiculo_id: string;
  ano: number;
  valor: number;
  data_vencimento: string;
  data_pagamento?: string;
  empresa_id: string;
  status: 'pendente' | 'pago' | 'vencido';
}

export interface Multa {
  id: string;
  veiculo_id: string;
  numero_infracao: string;
  data_infracao: string;
  valor: number;
  data_vencimento: string;
  data_pagamento?: string;
  empresa_id: string;
  status: 'pendente' | 'pago' | 'vencido';
  descricao: string;
}

export interface Manutencao {
  id: string;
  veiculo_id: string;
  data_manutencao: string;
  tipo: 'preventiva' | 'corretiva';
  descricao: string;
  valor: number;
  oficina: string;
  quilometragem: number;
  empresa_id: string;
  status: 'pendente' | 'em_progresso' | 'concluida' | 'cancelada';
}

export interface Reserva {
  id: string;
  cliente_id: string;
  veiculo_id: string;
  data_inicio: string;
  data_fim: string;
  data_reserva: string;
  empresa_id?: string;
  status: 'ativa' | 'pendente' | 'confirmada' | 'cancelada' | 'convertida';
  status_original?: 'pendente' | 'confirmada' | 'cancelada' | 'convertida';
  valor_estimado?: number;
  cliente?: { nome: string };
  veiculo?: {
    placa: string;
    marca?: string;
    modelo?: string;
  };
}

export interface DashboardStats {
  total_veiculos: number;
  veiculos_alugados: number;
  veiculos_disponiveis: number;
  total_clientes: number;
  contratos_ativos: number;
  receita_mensal: number;
  taxa_ocupacao: number;
  ticket_medio: number;
  variacao_receita_mensal: number;
  receita_vs_despesas: Array<{ mes: string; receita: number; despesa: number }>;
  top_clientes: Array<{ nome: string; valor_total: number; contratos: number }>;
  top_veiculos: Array<{ placa: string; modelo: string; alugadas: number; receita?: number }>;
  alertas: Array<{ id: string; tipo: string; titulo: string; descricao: string; urgencia: 'critica' | 'atencao' | 'info'; }>;
  contratos_atrasados: Contrato[];
  proximos_vencimentos: Array<{ id: string; titulo: string; data_vencimento: string; tipo: string }>;
}

export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  search?: string;
  filters?: Record<string, any>;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}
