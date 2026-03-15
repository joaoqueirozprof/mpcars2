--
-- PostgreSQL database dump
--

\restrict 1DzNglDLSAwiMZDiJPgYdmoNnUpJbAXfF3zLEYplEXuDfBONd1bcre2CF6SqjUf

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_logs; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.activity_logs (
    id integer NOT NULL,
    usuario_id integer,
    usuario_nome character varying,
    usuario_email character varying,
    acao character varying,
    recurso character varying,
    recurso_id integer,
    descricao character varying,
    ip_address character varying,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.activity_logs OWNER TO mpcars2;

--
-- Name: activity_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.activity_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.activity_logs_id_seq OWNER TO mpcars2;

--
-- Name: activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.activity_logs_id_seq OWNED BY public.activity_logs.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO mpcars2;

--
-- Name: alerta_historico; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.alerta_historico (
    id integer NOT NULL,
    tipo_alerta character varying,
    urgencia character varying,
    entidade_tipo character varying,
    entidade_id integer,
    titulo character varying,
    descricao text,
    data_criacao timestamp without time zone DEFAULT now(),
    resolvido boolean,
    resolvido_por character varying,
    data_resolucao timestamp without time zone
);


ALTER TABLE public.alerta_historico OWNER TO mpcars2;

--
-- Name: alerta_historico_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.alerta_historico_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.alerta_historico_id_seq OWNER TO mpcars2;

--
-- Name: alerta_historico_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.alerta_historico_id_seq OWNED BY public.alerta_historico.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now(),
    acao character varying,
    tabela character varying,
    registro_id integer,
    dados_anteriores json,
    dados_novos json,
    usuario character varying,
    ip_address character varying
);


ALTER TABLE public.audit_logs OWNER TO mpcars2;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO mpcars2;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: checkin_checkout; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.checkin_checkout (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    tipo character varying,
    data_hora timestamp without time zone DEFAULT now(),
    km double precision,
    nivel_combustivel character varying,
    itens_checklist json,
    avarias text
);


ALTER TABLE public.checkin_checkout OWNER TO mpcars2;

--
-- Name: checkin_checkout_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.checkin_checkout_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.checkin_checkout_id_seq OWNER TO mpcars2;

--
-- Name: checkin_checkout_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.checkin_checkout_id_seq OWNED BY public.checkin_checkout.id;


--
-- Name: clientes; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.clientes (
    id integer NOT NULL,
    nome character varying NOT NULL,
    cpf character varying NOT NULL,
    rg character varying,
    data_nascimento date,
    telefone character varying,
    email character varying,
    endereco_residencial character varying,
    numero_residencial character varying,
    complemento_residencial character varying,
    cidade_residencial character varying,
    estado_residencial character varying,
    cep_residencial character varying,
    endereco_comercial character varying,
    numero_comercial character varying,
    complemento_comercial character varying,
    cidade_comercial character varying,
    estado_comercial character varying,
    cep_comercial character varying,
    numero_cnh character varying,
    validade_cnh date,
    categoria_cnh character varying,
    hotel_apartamento character varying,
    score integer,
    empresa_id integer,
    data_cadastro timestamp without time zone DEFAULT now(),
    ativo boolean,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.clientes OWNER TO mpcars2;

--
-- Name: clientes_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.clientes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clientes_id_seq OWNER TO mpcars2;

--
-- Name: clientes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.clientes_id_seq OWNED BY public.clientes.id;


--
-- Name: configuracoes; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.configuracoes (
    id integer NOT NULL,
    chave character varying NOT NULL,
    valor text,
    data_atualizacao timestamp without time zone DEFAULT now()
);


ALTER TABLE public.configuracoes OWNER TO mpcars2;

--
-- Name: configuracoes_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.configuracoes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracoes_id_seq OWNER TO mpcars2;

--
-- Name: configuracoes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.configuracoes_id_seq OWNED BY public.configuracoes.id;


--
-- Name: contratos; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.contratos (
    id integer NOT NULL,
    numero character varying NOT NULL,
    cliente_id integer NOT NULL,
    veiculo_id integer NOT NULL,
    data_inicio timestamp without time zone NOT NULL,
    data_fim timestamp without time zone NOT NULL,
    km_inicial double precision,
    km_final double precision,
    valor_diaria numeric(10,2) NOT NULL,
    valor_total numeric(10,2),
    status character varying,
    cartao_numero character varying,
    cartao_bandeira character varying,
    cartao_validade character varying,
    cartao_titular character varying,
    cartao_codigo character varying,
    cartao_preautorizacao character varying,
    observacoes text,
    hora_saida character varying,
    combustivel_saida character varying,
    combustivel_retorno character varying,
    km_livres double precision,
    qtd_diarias integer,
    valor_hora_extra numeric(10,2),
    valor_km_excedente numeric(10,2),
    valor_avarias numeric(10,2),
    desconto numeric(10,2),
    tipo character varying,
    data_criacao timestamp without time zone DEFAULT now(),
    data_finalizacao timestamp without time zone,
    updated_at timestamp without time zone DEFAULT now(),
    cartao_ultimos4 character varying(4),
    taxa_combustivel numeric(10,2),
    taxa_limpeza numeric(10,2),
    taxa_higienizacao numeric(10,2),
    taxa_pneus numeric(10,2),
    taxa_acessorios numeric(10,2),
    valor_franquia_seguro numeric(10,2),
    taxa_administrativa numeric(10,2),
    status_pagamento character varying DEFAULT 'pendente'::character varying,
    forma_pagamento character varying,
    data_vencimento_pagamento date,
    data_pagamento date,
    valor_recebido numeric(10,2)
);


ALTER TABLE public.contratos OWNER TO mpcars2;

--
-- Name: contratos_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.contratos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contratos_id_seq OWNER TO mpcars2;

--
-- Name: contratos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.contratos_id_seq OWNED BY public.contratos.id;


--
-- Name: despesa_contrato; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.despesa_contrato (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    tipo character varying,
    descricao character varying,
    valor numeric(10,2),
    data_registro timestamp without time zone DEFAULT now(),
    responsavel character varying
);


ALTER TABLE public.despesa_contrato OWNER TO mpcars2;

--
-- Name: despesa_contrato_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.despesa_contrato_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.despesa_contrato_id_seq OWNER TO mpcars2;

--
-- Name: despesa_contrato_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.despesa_contrato_id_seq OWNED BY public.despesa_contrato.id;


--
-- Name: despesa_loja; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.despesa_loja (
    id integer NOT NULL,
    mes integer,
    ano integer,
    categoria character varying,
    valor numeric(10,2),
    descricao character varying,
    data timestamp without time zone DEFAULT now()
);


ALTER TABLE public.despesa_loja OWNER TO mpcars2;

--
-- Name: despesa_loja_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.despesa_loja_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.despesa_loja_id_seq OWNER TO mpcars2;

--
-- Name: despesa_loja_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.despesa_loja_id_seq OWNED BY public.despesa_loja.id;


--
-- Name: despesa_nf; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.despesa_nf (
    id integer NOT NULL,
    uso_id integer,
    veiculo_id integer NOT NULL,
    tipo character varying,
    descricao character varying,
    valor numeric(10,2),
    data timestamp without time zone DEFAULT now()
);


ALTER TABLE public.despesa_nf OWNER TO mpcars2;

--
-- Name: despesa_nf_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.despesa_nf_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.despesa_nf_id_seq OWNER TO mpcars2;

--
-- Name: despesa_nf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.despesa_nf_id_seq OWNED BY public.despesa_nf.id;


--
-- Name: despesa_operacional; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.despesa_operacional (
    id integer NOT NULL,
    tipo character varying,
    origem_tabela character varying,
    origem_id integer,
    veiculo_id integer,
    empresa_id integer,
    descricao character varying,
    valor numeric(10,2),
    data timestamp without time zone DEFAULT now(),
    categoria character varying,
    mes integer,
    ano integer
);


ALTER TABLE public.despesa_operacional OWNER TO mpcars2;

--
-- Name: despesa_operacional_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.despesa_operacional_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.despesa_operacional_id_seq OWNER TO mpcars2;

--
-- Name: despesa_operacional_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.despesa_operacional_id_seq OWNED BY public.despesa_operacional.id;


--
-- Name: despesa_veiculo; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.despesa_veiculo (
    id integer NOT NULL,
    veiculo_id integer NOT NULL,
    tipo character varying,
    valor numeric(10,2) NOT NULL,
    descricao character varying,
    km double precision,
    data timestamp without time zone DEFAULT now(),
    pneu boolean
);


ALTER TABLE public.despesa_veiculo OWNER TO mpcars2;

--
-- Name: despesa_veiculo_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.despesa_veiculo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.despesa_veiculo_id_seq OWNER TO mpcars2;

--
-- Name: despesa_veiculo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.despesa_veiculo_id_seq OWNED BY public.despesa_veiculo.id;


--
-- Name: documentos; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.documentos (
    id integer NOT NULL,
    tipo_entidade character varying,
    entidade_id integer,
    nome_arquivo character varying,
    nome_original character varying,
    tipo_documento character varying,
    caminho character varying,
    tamanho double precision,
    data_upload timestamp without time zone DEFAULT now()
);


ALTER TABLE public.documentos OWNER TO mpcars2;

--
-- Name: documentos_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.documentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.documentos_id_seq OWNER TO mpcars2;

--
-- Name: documentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.documentos_id_seq OWNED BY public.documentos.id;


--
-- Name: empresas; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.empresas (
    id integer NOT NULL,
    nome character varying NOT NULL,
    cnpj character varying NOT NULL,
    razao_social character varying NOT NULL,
    endereco character varying,
    cidade character varying,
    estado character varying,
    cep character varying,
    telefone character varying,
    email character varying,
    contato_principal character varying,
    data_cadastro timestamp without time zone DEFAULT now(),
    ativo boolean,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.empresas OWNER TO mpcars2;

--
-- Name: empresas_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.empresas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.empresas_id_seq OWNER TO mpcars2;

--
-- Name: empresas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.empresas_id_seq OWNED BY public.empresas.id;


--
-- Name: ipva_aliquota; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.ipva_aliquota (
    id integer NOT NULL,
    estado character varying NOT NULL,
    tipo_veiculo character varying NOT NULL,
    aliquota double precision,
    descricao character varying
);


ALTER TABLE public.ipva_aliquota OWNER TO mpcars2;

--
-- Name: ipva_aliquota_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.ipva_aliquota_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ipva_aliquota_id_seq OWNER TO mpcars2;

--
-- Name: ipva_aliquota_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.ipva_aliquota_id_seq OWNED BY public.ipva_aliquota.id;


--
-- Name: ipva_parcela; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.ipva_parcela (
    id integer NOT NULL,
    ipva_id integer NOT NULL,
    veiculo_id integer NOT NULL,
    numero_parcela integer,
    valor numeric(10,2),
    vencimento date,
    data_pagamento date,
    status character varying
);


ALTER TABLE public.ipva_parcela OWNER TO mpcars2;

--
-- Name: ipva_parcela_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.ipva_parcela_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ipva_parcela_id_seq OWNER TO mpcars2;

--
-- Name: ipva_parcela_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.ipva_parcela_id_seq OWNED BY public.ipva_parcela.id;


--
-- Name: ipva_registro; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.ipva_registro (
    id integer NOT NULL,
    veiculo_id integer NOT NULL,
    ano_referencia integer,
    valor_venal numeric(10,2),
    aliquota double precision,
    valor_ipva numeric(10,2),
    valor_pago numeric(10,2),
    data_vencimento date,
    data_pagamento date,
    status character varying,
    data_criacao timestamp without time zone DEFAULT now(),
    qtd_parcelas integer,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ipva_registro OWNER TO mpcars2;

--
-- Name: ipva_registro_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.ipva_registro_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ipva_registro_id_seq OWNER TO mpcars2;

--
-- Name: ipva_registro_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.ipva_registro_id_seq OWNED BY public.ipva_registro.id;


--
-- Name: lancamentos_financeiros; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.lancamentos_financeiros (
    id integer NOT NULL,
    data date NOT NULL,
    tipo character varying NOT NULL,
    categoria character varying NOT NULL,
    descricao character varying NOT NULL,
    valor numeric(10,2) NOT NULL,
    status character varying,
    data_criacao timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.lancamentos_financeiros OWNER TO mpcars2;

--
-- Name: lancamentos_financeiros_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.lancamentos_financeiros_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lancamentos_financeiros_id_seq OWNER TO mpcars2;

--
-- Name: lancamentos_financeiros_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.lancamentos_financeiros_id_seq OWNED BY public.lancamentos_financeiros.id;


--
-- Name: manutencoes; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.manutencoes (
    id integer NOT NULL,
    veiculo_id integer NOT NULL,
    tipo character varying,
    descricao character varying,
    km_realizada double precision,
    km_proxima double precision,
    data_realizada date,
    data_proxima date,
    custo numeric(10,2),
    oficina character varying,
    status character varying,
    data_criacao timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.manutencoes OWNER TO mpcars2;

--
-- Name: manutencoes_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.manutencoes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.manutencoes_id_seq OWNER TO mpcars2;

--
-- Name: manutencoes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.manutencoes_id_seq OWNED BY public.manutencoes.id;


--
-- Name: motorista_empresa; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.motorista_empresa (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    cliente_id integer NOT NULL,
    cargo character varying,
    ativo boolean,
    data_vinculo timestamp without time zone DEFAULT now()
);


ALTER TABLE public.motorista_empresa OWNER TO mpcars2;

--
-- Name: motorista_empresa_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.motorista_empresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.motorista_empresa_id_seq OWNER TO mpcars2;

--
-- Name: motorista_empresa_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.motorista_empresa_id_seq OWNED BY public.motorista_empresa.id;


--
-- Name: multas; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.multas (
    id integer NOT NULL,
    veiculo_id integer NOT NULL,
    contrato_id integer,
    cliente_id integer,
    data_infracao date,
    numero_infracao character varying,
    data_vencimento date,
    valor numeric(10,2),
    pontos integer,
    gravidade character varying,
    descricao character varying,
    status character varying,
    responsavel character varying,
    data_pagamento date,
    data_criacao timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.multas OWNER TO mpcars2;

--
-- Name: multas_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.multas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.multas_id_seq OWNER TO mpcars2;

--
-- Name: multas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.multas_id_seq OWNED BY public.multas.id;


--
-- Name: parcela_seguro; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.parcela_seguro (
    id integer NOT NULL,
    seguro_id integer NOT NULL,
    veiculo_id integer NOT NULL,
    numero_parcela integer,
    valor numeric(10,2),
    vencimento date,
    data_pagamento date,
    status character varying
);


ALTER TABLE public.parcela_seguro OWNER TO mpcars2;

--
-- Name: parcela_seguro_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.parcela_seguro_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.parcela_seguro_id_seq OWNER TO mpcars2;

--
-- Name: parcela_seguro_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.parcela_seguro_id_seq OWNED BY public.parcela_seguro.id;


--
-- Name: prorrogacao_contrato; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.prorrogacao_contrato (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    data_anterior timestamp without time zone,
    data_nova timestamp without time zone,
    motivo character varying,
    diarias_adicionais integer,
    valor_adicional numeric(10,2),
    data_criacao timestamp without time zone DEFAULT now()
);


ALTER TABLE public.prorrogacao_contrato OWNER TO mpcars2;

--
-- Name: prorrogacao_contrato_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.prorrogacao_contrato_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.prorrogacao_contrato_id_seq OWNER TO mpcars2;

--
-- Name: prorrogacao_contrato_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.prorrogacao_contrato_id_seq OWNED BY public.prorrogacao_contrato.id;


--
-- Name: quilometragem; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.quilometragem (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    discriminacao character varying,
    quantidade double precision,
    preco_unitario numeric(10,2),
    preco_total numeric(10,2),
    data_registro timestamp without time zone DEFAULT now()
);


ALTER TABLE public.quilometragem OWNER TO mpcars2;

--
-- Name: quilometragem_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.quilometragem_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quilometragem_id_seq OWNER TO mpcars2;

--
-- Name: quilometragem_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.quilometragem_id_seq OWNED BY public.quilometragem.id;


--
-- Name: relatorio_nf; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.relatorio_nf (
    id integer NOT NULL,
    veiculo_id integer NOT NULL,
    empresa_id integer NOT NULL,
    uso_id integer,
    periodo_inicio date,
    periodo_fim date,
    km_percorrida double precision,
    km_excedente double precision,
    valor_total_extra numeric(10,2),
    caminho_pdf character varying,
    data_criacao timestamp without time zone DEFAULT now()
);


ALTER TABLE public.relatorio_nf OWNER TO mpcars2;

--
-- Name: relatorio_nf_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.relatorio_nf_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.relatorio_nf_id_seq OWNER TO mpcars2;

--
-- Name: relatorio_nf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.relatorio_nf_id_seq OWNED BY public.relatorio_nf.id;


--
-- Name: reservas; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.reservas (
    id integer NOT NULL,
    cliente_id integer NOT NULL,
    veiculo_id integer NOT NULL,
    data_inicio timestamp without time zone,
    data_fim timestamp without time zone,
    status character varying,
    valor_estimado numeric(10,2),
    data_criacao timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.reservas OWNER TO mpcars2;

--
-- Name: reservas_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.reservas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reservas_id_seq OWNER TO mpcars2;

--
-- Name: reservas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.reservas_id_seq OWNED BY public.reservas.id;


--
-- Name: seguros; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.seguros (
    id integer NOT NULL,
    veiculo_id integer NOT NULL,
    seguradora character varying,
    numero_apolice character varying,
    tipo_seguro character varying,
    data_inicio date,
    data_fim date,
    valor numeric(10,2),
    valor_franquia numeric(10,2),
    status character varying,
    qtd_parcelas integer,
    data_criacao timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.seguros OWNER TO mpcars2;

--
-- Name: seguros_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.seguros_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seguros_id_seq OWNER TO mpcars2;

--
-- Name: seguros_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.seguros_id_seq OWNED BY public.seguros.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    nome character varying NOT NULL,
    perfil character varying,
    ativo boolean,
    permitted_pages json,
    data_cadastro timestamp without time zone DEFAULT now(),
    password_reset_token_hash character varying,
    password_reset_expires_at timestamp without time zone,
    password_reset_requested_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO mpcars2;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO mpcars2;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: uso_veiculo_empresa; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.uso_veiculo_empresa (
    id integer NOT NULL,
    veiculo_id integer NOT NULL,
    empresa_id integer NOT NULL,
    contrato_id integer,
    km_inicial double precision,
    km_final double precision,
    km_percorrido double precision,
    data_inicio timestamp without time zone,
    data_fim timestamp without time zone,
    km_referencia double precision,
    valor_km_extra numeric(10,2),
    valor_diaria_empresa numeric(10,2),
    status character varying,
    data_criacao timestamp without time zone DEFAULT now()
);


ALTER TABLE public.uso_veiculo_empresa OWNER TO mpcars2;

--
-- Name: uso_veiculo_empresa_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.uso_veiculo_empresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uso_veiculo_empresa_id_seq OWNER TO mpcars2;

--
-- Name: uso_veiculo_empresa_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.uso_veiculo_empresa_id_seq OWNED BY public.uso_veiculo_empresa.id;


--
-- Name: veiculos; Type: TABLE; Schema: public; Owner: mpcars2
--

CREATE TABLE public.veiculos (
    id integer NOT NULL,
    placa character varying NOT NULL,
    marca character varying NOT NULL,
    modelo character varying NOT NULL,
    ano integer,
    cor character varying,
    chassis character varying,
    renavam character varying,
    combustivel character varying,
    capacidade_tanque double precision,
    km_atual double precision,
    data_aquisicao date,
    valor_aquisicao numeric(10,2),
    status character varying,
    checklist_item_1 integer,
    checklist_item_2 integer,
    checklist_item_3 integer,
    checklist_item_4 integer,
    checklist_item_5 integer,
    checklist_item_6 integer,
    checklist_item_7 integer,
    checklist_item_8 integer,
    checklist_item_9 integer,
    checklist_item_10 integer,
    categoria character varying,
    valor_diaria numeric(10,2),
    foto_url character varying,
    data_cadastro timestamp without time zone DEFAULT now(),
    ativo boolean,
    updated_at timestamp without time zone DEFAULT now(),
    checklist jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.veiculos OWNER TO mpcars2;

--
-- Name: veiculos_id_seq; Type: SEQUENCE; Schema: public; Owner: mpcars2
--

CREATE SEQUENCE public.veiculos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.veiculos_id_seq OWNER TO mpcars2;

--
-- Name: veiculos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mpcars2
--

ALTER SEQUENCE public.veiculos_id_seq OWNED BY public.veiculos.id;


--
-- Name: activity_logs id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.activity_logs ALTER COLUMN id SET DEFAULT nextval('public.activity_logs_id_seq'::regclass);


--
-- Name: alerta_historico id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.alerta_historico ALTER COLUMN id SET DEFAULT nextval('public.alerta_historico_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: checkin_checkout id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.checkin_checkout ALTER COLUMN id SET DEFAULT nextval('public.checkin_checkout_id_seq'::regclass);


--
-- Name: clientes id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.clientes ALTER COLUMN id SET DEFAULT nextval('public.clientes_id_seq'::regclass);


--
-- Name: configuracoes id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.configuracoes ALTER COLUMN id SET DEFAULT nextval('public.configuracoes_id_seq'::regclass);


--
-- Name: contratos id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.contratos ALTER COLUMN id SET DEFAULT nextval('public.contratos_id_seq'::regclass);


--
-- Name: despesa_contrato id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_contrato ALTER COLUMN id SET DEFAULT nextval('public.despesa_contrato_id_seq'::regclass);


--
-- Name: despesa_loja id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_loja ALTER COLUMN id SET DEFAULT nextval('public.despesa_loja_id_seq'::regclass);


--
-- Name: despesa_nf id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_nf ALTER COLUMN id SET DEFAULT nextval('public.despesa_nf_id_seq'::regclass);


--
-- Name: despesa_operacional id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_operacional ALTER COLUMN id SET DEFAULT nextval('public.despesa_operacional_id_seq'::regclass);


--
-- Name: despesa_veiculo id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_veiculo ALTER COLUMN id SET DEFAULT nextval('public.despesa_veiculo_id_seq'::regclass);


--
-- Name: documentos id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.documentos ALTER COLUMN id SET DEFAULT nextval('public.documentos_id_seq'::regclass);


--
-- Name: empresas id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.empresas ALTER COLUMN id SET DEFAULT nextval('public.empresas_id_seq'::regclass);


--
-- Name: ipva_aliquota id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_aliquota ALTER COLUMN id SET DEFAULT nextval('public.ipva_aliquota_id_seq'::regclass);


--
-- Name: ipva_parcela id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_parcela ALTER COLUMN id SET DEFAULT nextval('public.ipva_parcela_id_seq'::regclass);


--
-- Name: ipva_registro id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_registro ALTER COLUMN id SET DEFAULT nextval('public.ipva_registro_id_seq'::regclass);


--
-- Name: lancamentos_financeiros id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.lancamentos_financeiros ALTER COLUMN id SET DEFAULT nextval('public.lancamentos_financeiros_id_seq'::regclass);


--
-- Name: manutencoes id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.manutencoes ALTER COLUMN id SET DEFAULT nextval('public.manutencoes_id_seq'::regclass);


--
-- Name: motorista_empresa id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.motorista_empresa ALTER COLUMN id SET DEFAULT nextval('public.motorista_empresa_id_seq'::regclass);


--
-- Name: multas id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.multas ALTER COLUMN id SET DEFAULT nextval('public.multas_id_seq'::regclass);


--
-- Name: parcela_seguro id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.parcela_seguro ALTER COLUMN id SET DEFAULT nextval('public.parcela_seguro_id_seq'::regclass);


--
-- Name: prorrogacao_contrato id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.prorrogacao_contrato ALTER COLUMN id SET DEFAULT nextval('public.prorrogacao_contrato_id_seq'::regclass);


--
-- Name: quilometragem id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.quilometragem ALTER COLUMN id SET DEFAULT nextval('public.quilometragem_id_seq'::regclass);


--
-- Name: relatorio_nf id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.relatorio_nf ALTER COLUMN id SET DEFAULT nextval('public.relatorio_nf_id_seq'::regclass);


--
-- Name: reservas id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.reservas ALTER COLUMN id SET DEFAULT nextval('public.reservas_id_seq'::regclass);


--
-- Name: seguros id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.seguros ALTER COLUMN id SET DEFAULT nextval('public.seguros_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: uso_veiculo_empresa id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.uso_veiculo_empresa ALTER COLUMN id SET DEFAULT nextval('public.uso_veiculo_empresa_id_seq'::regclass);


--
-- Name: veiculos id; Type: DEFAULT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.veiculos ALTER COLUMN id SET DEFAULT nextval('public.veiculos_id_seq'::regclass);


--
-- Data for Name: activity_logs; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.activity_logs (id, usuario_id, usuario_nome, usuario_email, acao, recurso, recurso_id, descricao, ip_address, "timestamp") FROM stdin;
1	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	187.19.233.84	2026-03-10 20:58:39.076758
2	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	206.42.47.11	2026-03-11 13:31:16.083197
3	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	187.19.233.86	2026-03-11 21:53:05.699671
4	1	Administrador	admin@mpcars.com	CRIAR	Veiculo	9	Veiculo CDX8212 criado	127.0.0.1	2026-03-11 22:30:12.914569
5	1	Administrador	admin@mpcars.com	EDITAR	Veiculo	9	Veiculo CDX8212 editado	127.0.0.1	2026-03-11 22:30:12.947809
6	1	Administrador	admin@mpcars.com	CRIAR	Veiculo	10	Veiculo CDX8292 criado	127.0.0.1	2026-03-11 22:31:32.2971
7	1	Administrador	admin@mpcars.com	EDITAR	Veiculo	10	Veiculo CDX8292 editado	127.0.0.1	2026-03-11 22:31:32.311375
8	1	Administrador	admin@mpcars.com	CRIAR	Cliente	7	Cliente Cliente A 8292 criado	127.0.0.1	2026-03-11 22:31:32.354481
9	1	Administrador	admin@mpcars.com	EDITAR	Cliente	7	Cliente Cliente A 8292 editado	127.0.0.1	2026-03-11 22:31:32.382474
10	1	Administrador	admin@mpcars.com	EDITAR	Contrato	1	Contrato CT-2025-001 editado	187.19.233.86	2026-03-11 22:34:09.336013
11	1	Administrador	admin@mpcars.com	EDITAR	Contrato	3	Contrato CT-2025-003 editado	187.19.233.86	2026-03-11 22:34:12.247805
12	1	Administrador	admin@mpcars.com	CRIAR	Veiculo	11	Veiculo CDX8452 criado	127.0.0.1	2026-03-11 22:34:12.505425
13	1	Administrador	admin@mpcars.com	EDITAR	Veiculo	11	Veiculo CDX8452 editado	127.0.0.1	2026-03-11 22:34:12.530185
14	1	Administrador	admin@mpcars.com	CRIAR	Cliente	8	Cliente Cliente A 8452 criado	127.0.0.1	2026-03-11 22:34:12.609473
15	1	Administrador	admin@mpcars.com	EDITAR	Cliente	8	Cliente Cliente A 8452 editado	127.0.0.1	2026-03-11 22:34:12.642438
16	1	Administrador	admin@mpcars.com	EXCLUIR	Cliente	8	Cliente Cliente A 8452 excluído	127.0.0.1	2026-03-11 22:34:12.669713
17	1	Administrador	admin@mpcars.com	CRIAR	Cliente	9	Cliente Cliente B 8452 criado	127.0.0.1	2026-03-11 22:34:12.721884
18	1	Administrador	admin@mpcars.com	EXCLUIR	Cliente	9	Cliente Cliente B 8452 excluído	127.0.0.1	2026-03-11 22:34:12.757356
19	1	Administrador	admin@mpcars.com	CRIAR	LancamentoFinanceiro	1	Lançamento financeiro criado: Lancamento audit 1773268452	127.0.0.1	2026-03-11 22:34:12.776074
20	1	Administrador	admin@mpcars.com	EDITAR	LancamentoFinanceiro	1	Lançamento financeiro editado: Lancamento audit editado 1773268452	127.0.0.1	2026-03-11 22:34:12.796134
21	1	Administrador	admin@mpcars.com	EXCLUIR	Financeiro	1	Registro financeiro fm-1 excluído	127.0.0.1	2026-03-11 22:34:12.827634
22	1	Administrador	admin@mpcars.com	EXCLUIR	Veiculo	11	Veiculo CDX8452 excluido	127.0.0.1	2026-03-11 22:34:13.03244
23	1	Administrador	admin@mpcars.com	EDITAR	Contrato	3	Contrato CT-2025-003 editado	187.19.233.86	2026-03-11 22:34:15.032446
24	1	Administrador	admin@mpcars.com	EDITAR	Contrato	1	Contrato CT-2025-001 editado	187.19.233.86	2026-03-11 22:34:17.710022
25	1	Administrador	admin@mpcars.com	EDITAR	Contrato	5	Contrato CT-2025-005 editado	187.19.233.86	2026-03-11 22:34:24.414685
26	1	Administrador	admin@mpcars.com	EXCLUIR	Contrato	1	Contrato CT-2025-001 excluído	187.19.233.86	2026-03-11 22:34:30.313245
27	1	Administrador	admin@mpcars.com	EXCLUIR	Contrato	2	Contrato CT-2025-002 excluído	187.19.233.86	2026-03-11 22:34:32.218898
28	1	Administrador	admin@mpcars.com	EXCLUIR	Contrato	5	Contrato CT-2025-005 excluído	187.19.233.86	2026-03-11 22:34:34.246874
29	1	Administrador	admin@mpcars.com	EXCLUIR	Veiculo	4	Veiculo RNP-4D56 excluido	187.19.233.86	2026-03-11 22:34:39.465012
30	1	Administrador	admin@mpcars.com	EXCLUIR	Cliente	1	Cliente Joao Silva Santos excluído	187.19.233.86	2026-03-11 22:34:45.588814
31	1	Administrador	admin@mpcars.com	CRIAR	Veiculo	12	Veiculo CDY8529 criado	127.0.0.1	2026-03-11 22:35:29.889496
32	1	Administrador	admin@mpcars.com	CRIAR	Cliente	10	Cliente Cliente Ops 8529 criado	127.0.0.1	2026-03-11 22:35:29.901613
33	1	Administrador	admin@mpcars.com	CRIAR	Contrato	7	Contrato CTR-20260311223529961 criado	127.0.0.1	2026-03-11 22:35:29.977923
34	1	Administrador	admin@mpcars.com	EDITAR	Contrato	7	Contrato CTR-20260311223529961 editado	127.0.0.1	2026-03-11 22:35:30.009624
35	1	Administrador	admin@mpcars.com	EXCLUIR	Contrato	7	Contrato CTR-20260311223529961 excluído	127.0.0.1	2026-03-11 22:35:30.049777
36	1	Administrador	admin@mpcars.com	EXCLUIR	Cliente	10	Cliente Cliente Ops 8529 excluído	127.0.0.1	2026-03-11 22:35:30.148836
37	1	Administrador	admin@mpcars.com	EXCLUIR	Veiculo	12	Veiculo CDY8529 excluido	127.0.0.1	2026-03-11 22:35:30.168588
38	1	Administrador	admin@mpcars.com	CRIAR	Contrato	8	Contrato CTR-20260311225610124 criado	187.19.233.86	2026-03-11 22:56:10.148816
39	1	Administrador	admin@mpcars.com	EDITAR	Contrato	8	Contrato CTR-20260311225610124 editado	187.19.233.86	2026-03-11 22:56:36.50526
40	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	187.19.233.86	2026-03-12 10:57:20.885365
41	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	206.42.47.11	2026-03-12 12:46:12.09407
42	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	206.42.47.11	2026-03-12 15:35:34.370181
43	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	172.19.0.1	2026-03-12 15:36:41.964919
44	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	172.19.0.1	2026-03-12 15:38:35.742243
45	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	172.19.0.1	2026-03-12 15:39:19.584444
46	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	172.19.0.1	2026-03-12 15:39:58.044746
47	1	Administrador	admin@mpcars.com	CRIAR	usuarios	2	Criou usuario: Temp Admin QA (temp.admin.f7865909@mpcarsqa.com) [admin]	172.19.0.1	2026-03-12 15:39:58.545785
48	2	Temp Admin QA	temp.admin.f7865909@mpcarsqa.com	LOGIN	auth	\N	Login realizado: Temp Admin QA	172.19.0.1	2026-03-12 15:39:58.555249
49	1	Administrador	admin@mpcars.com	CRIAR	usuarios	3	Criou usuario: Temp Owner QA (temp.owner.f7865909@mpcarsqa.com) [owner]	172.19.0.1	2026-03-12 15:39:59.063443
50	3	Temp Owner QA	temp.owner.f7865909@mpcarsqa.com	LOGIN	auth	\N	Login realizado: Temp Owner QA	172.19.0.1	2026-03-12 15:39:59.076813
51	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	172.19.0.1	2026-03-12 15:40:37.076368
52	1	Administrador	admin@mpcars.com	EDITAR	usuarios	2	Desativou usuario: Temp Admin QA	172.19.0.1	2026-03-12 15:40:37.33985
53	1	Administrador	admin@mpcars.com	EDITAR	usuarios	3	Desativou usuario: Temp Owner QA	172.19.0.1	2026-03-12 15:40:37.355875
54	1	Administrador	admin@mpcars.com	EXCLUIR	usuarios	2	Excluiu usuario: Temp Admin QA (temp.admin.f7865909@mpcarsqa.com) [admin]	206.42.47.11	2026-03-12 16:31:17.684693
55	1	Administrador	admin@mpcars.com	EXCLUIR	usuarios	3	Excluiu usuario: Temp Owner QA (temp.owner.f7865909@mpcarsqa.com) [owner]	206.42.47.11	2026-03-12 16:31:20.274952
56	1	Administrador	admin@mpcars.com	CRIAR	usuarios	4	Criou usuario: Marcelo peterson (jc.hsilvaqueiroz@gmail.com) [gerente]	206.42.47.11	2026-03-12 16:31:43.96025
57	4	Marcelo peterson	jc.hsilvaqueiroz@gmail.com	LOGIN	auth	\N	Login realizado: Marcelo peterson	206.42.47.11	2026-03-12 16:31:54.898634
58	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	172.19.0.1	2026-03-12 16:33:11.491737
59	1	Administrador	admin@mpcars.com	CRIAR	usuarios	5	Criou usuario: Gerente Teste VPS (gerente.4c4aedbb@mpcarsqa.com) [gerente]	172.19.0.1	2026-03-12 16:33:11.976617
60	1	Administrador	admin@mpcars.com	EXCLUIR	usuarios	5	Excluiu usuario: Gerente Teste VPS (gerente.4c4aedbb@mpcarsqa.com) [gerente]	172.19.0.1	2026-03-12 16:33:12.001721
61	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	206.42.47.11	2026-03-12 16:38:15.102966
62	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	206.42.47.11	2026-03-12 17:23:38.773424
63	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	206.42.47.11	2026-03-12 18:05:32.328296
64	4	Marcelo peterson	jc.hsilvaqueiroz@gmail.com	LOGIN	auth	\N	Login realizado: Marcelo peterson	206.42.47.11	2026-03-12 18:05:46.568546
65	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	191.37.209.168	2026-03-12 20:15:49.307373
66	1	Administrador	admin@mpcars.com	EXCLUIR	usuarios	4	Excluiu usuario: Marcelo peterson (jc.hsilvaqueiroz@gmail.com) [gerente]	191.37.209.168	2026-03-12 20:16:07.214294
67	1	Administrador	admin@mpcars.com	CRIAR	usuarios	6	Criou usuario: Marcelo Petterson Alves Arnaud (marcellopetterson@hotmail.com) [owner]	191.37.209.168	2026-03-12 20:19:00.920171
68	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	LOGIN	auth	\N	Login realizado: Marcelo Petterson Alves Arnaud	191.37.209.168	2026-03-12 20:21:31.397819
69	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Veiculo	5	Veiculo RNP-5E67 excluido	191.37.209.168	2026-03-12 20:31:46.134282
70	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Veiculo	8	Veiculo RNP-8H90 excluido	191.37.209.168	2026-03-12 20:31:50.963753
71	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Veiculo	7	Veiculo RNP-7G89 excluido	191.37.209.168	2026-03-12 20:31:55.556626
72	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Veiculo	1	Veiculo RNP-1A23 excluido	191.37.209.168	2026-03-12 20:32:00.359039
73	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Veiculo	3	Veiculo RNP-3C45 excluido	191.37.209.168	2026-03-12 20:32:05.060735
74	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Veiculo	2	Veiculo RNP-2B34 excluido	191.37.209.168	2026-03-12 20:32:09.243869
75	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Contrato	8	Contrato CTR-20260311225610124 excluido	191.37.209.168	2026-03-12 20:32:32.293338
76	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EXCLUIR	Veiculo	6	Veiculo RNP-6F78 excluido	191.37.209.168	2026-03-12 20:32:57.62896
77	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	CRIAR	Veiculo	13	Veiculo SHG3G73 criado	191.37.209.168	2026-03-12 20:39:07.395874
78	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	LOGIN	auth	\N	Login realizado: Marcelo Petterson Alves Arnaud	191.37.209.168	2026-03-12 20:56:06.355363
79	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	CRIAR	Contrato	9	Contrato CTR-20260312210426977 criado	191.37.209.168	2026-03-12 21:04:26.998196
80	6	Marcelo Petterson Alves Arnaud	marcellopetterson@hotmail.com	EDITAR	Contrato	9	Contrato CTR-20260312210426977 editado	191.37.209.168	2026-03-12 21:05:23.029973
81	1	Administrador	admin@mpcars.com	LOGIN	auth	\N	Login realizado: Administrador	206.42.47.11	2026-03-13 12:09:26.898326
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.alembic_version (version_num) FROM stdin;
20260311_2300
\.


--
-- Data for Name: alerta_historico; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.alerta_historico (id, tipo_alerta, urgencia, entidade_tipo, entidade_id, titulo, descricao, data_criacao, resolvido, resolvido_por, data_resolucao) FROM stdin;
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.audit_logs (id, "timestamp", acao, tabela, registro_id, dados_anteriores, dados_novos, usuario, ip_address) FROM stdin;
\.


--
-- Data for Name: checkin_checkout; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.checkin_checkout (id, contrato_id, tipo, data_hora, km, nivel_combustivel, itens_checklist, avarias) FROM stdin;
1	9	retirada	2026-03-12 21:04:26.962937	65465	1/4	{}	\N
\.


--
-- Data for Name: clientes; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.clientes (id, nome, cpf, rg, data_nascimento, telefone, email, endereco_residencial, numero_residencial, complemento_residencial, cidade_residencial, estado_residencial, cep_residencial, endereco_comercial, numero_comercial, complemento_comercial, cidade_comercial, estado_comercial, cep_comercial, numero_cnh, validade_cnh, categoria_cnh, hotel_apartamento, score, empresa_id, data_cadastro, ativo, updated_at) FROM stdin;
2	Maria Fernanda Oliveira	987.654.321-00	7654321	1990-07-22	(84) 99877-6655	maria.fernanda@email.com	Av. Brasil, 200	200	\N	Mossoro	RN	59600-000	\N	\N	\N	\N	\N	\N	98765432100	2026-11-10	B	\N	88	\N	2026-03-08 17:56:11.670253	t	2026-03-11 13:27:57.920325
3	Carlos Eduardo Pereira	456.789.123-00	4567891	1978-12-05	(85) 99766-5544	carlos.pereira@email.com	Rua do Comercio, 78	78	\N	Fortaleza	CE	60000-000	\N	\N	\N	\N	\N	\N	45678912300	2025-08-15	AB	\N	75	\N	2026-03-08 17:56:11.670253	t	2026-03-11 13:27:57.920325
4	Ana Beatriz Costa	321.654.987-00	3216549	1995-01-30	(84) 99655-4433	ana.costa@email.com	Rua Nova, 150	150	\N	Caico	RN	59300-000	\N	\N	\N	\N	\N	\N	32165498700	2028-02-28	B	\N	100	\N	2026-03-08 17:56:11.670253	t	2026-03-11 13:27:57.920325
5	Pedro Henrique Lima	654.321.987-00	6543219	1982-09-18	(84) 99544-3322	pedro.lima@email.com	Travessa Boa Vista, 33	33	\N	Natal	RN	59000-000	\N	\N	\N	\N	\N	\N	65432198700	2026-06-01	AB	\N	82	\N	2026-03-08 17:56:11.670253	t	2026-03-11 13:27:57.920325
6	Francisca Souza Mendes	789.123.456-00	7891234	1988-04-12	(84) 99433-2211	francisca.souza@email.com	Rua Sao Jose, 67	67	\N	Pau dos Ferros	RN	59900-000	\N	\N	\N	\N	\N	\N	78912345600	2027-09-15	B	\N	90	\N	2026-03-08 17:56:11.670253	t	2026-03-12 20:33:14.355836
\.


--
-- Data for Name: configuracoes; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.configuracoes (id, chave, valor, data_atualizacao) FROM stdin;
1	empresa_nome	MPCARS Aluguel de Veiculos	2026-03-08 17:56:11.638841
2	empresa_cnpj	12.345.678/0001-90	2026-03-08 17:56:11.638841
3	empresa_telefone	(84) 99999-9999	2026-03-08 17:56:11.638841
4	empresa_email	contato@mpcars.com	2026-03-08 17:56:11.638841
5	empresa_endereco	Rua Principal, 100 - Centro, Pau dos Ferros/RN	2026-03-08 17:56:11.638841
6	valor_diaria_padrao	150.00	2026-03-08 17:56:11.638841
7	km_limite_manutencao	5000	2026-03-08 17:56:11.638841
8	dias_alerta_vencimento	30	2026-03-08 17:56:11.638841
9	taxa_multa_atraso	50.00	2026-03-08 17:56:11.638841
10	percentual_caucao	10	2026-03-08 17:56:11.638841
11	sistema_versao	2.0.0	2026-03-08 17:56:11.638841
12	timezone	America/Sao_Paulo	2026-03-08 17:56:11.638841
14	sistema_tema	light	2026-03-12 13:12:47.783224
15	sistema_notificacoes_email	false	2026-03-12 13:12:47.783224
16	sistema_notificacoes_sms	false	2026-03-12 13:12:47.783224
17	sistema_valor_diaria_padrao	150	2026-03-12 13:12:47.783224
18	sistema_taxa_juros	2	2026-03-12 13:12:47.783224
13	sistema_idioma	pt-BR	2026-03-12 13:12:58.777351
19	google_drive_auth_mode	oauth	2026-03-12 19:39:17.965978
20	google_drive_enabled	true	2026-03-12 19:39:17.965978
21	google_drive_sync_on_backup	true	2026-03-12 19:39:17.965978
24	google_drive_oauth_root_folder_name	MPCARS Backups	2026-03-12 19:39:17.965978
22	google_drive_oauth_client_id	866427375380-cnj0f5s2ibneftlhagp6pb2ehqcq35m2.apps.googleusercontent.com	2026-03-12 19:42:39.647329
23	google_drive_oauth_client_secret	enc::gAAAAABpsxcwj6ke8-H9TvqQuDobrIJX27ghkniOdHOf4udIYKuU3Mf9v2fRLGJWrIKAd-qYwOOkxUVlBLGd-CZVSgbutoYS8LovW3thHhfxukPXEwhqmA8FRx_uvF3tynqBbVK62GH7	2026-03-12 19:42:39.647329
30	google_drive_oauth_refresh_token	enc::gAAAAABpsxfjK_B6cm3H9TrgxOaqk0d3HM6q78oTsy77PNvDnMxKg7CJpGhY4Yvc2eqHeihtyXPkUKE1l_vdGC5t0MeCm9dVsaX0_YbJkhXxX1B-O5xRwkj4UIhuO0RrhRjFv1xRDAdE6kj7z6vtob-9ykHF917Lgk7pSqXdJV5T_OxE3CV5QMKL8MFwXlPaYnmQvvR_HVio2ZIiMEn1ZiCV6QQiciteew==	2026-03-12 19:45:37.368553
31	google_drive_oauth_connected_email	jcarlosyes25@gmail.com	2026-03-12 19:45:37.368553
32	google_drive_oauth_root_folder_id	1ieQCOqqWVcH2_2AP7hNdyOlr0hc19f8j	2026-03-12 19:45:37.368553
33	google_drive_oauth_connected_at	2026-03-12T19:45:39.548157+00:00	2026-03-12 19:45:37.368553
\.


--
-- Data for Name: contratos; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.contratos (id, numero, cliente_id, veiculo_id, data_inicio, data_fim, km_inicial, km_final, valor_diaria, valor_total, status, cartao_numero, cartao_bandeira, cartao_validade, cartao_titular, cartao_codigo, cartao_preautorizacao, observacoes, hora_saida, combustivel_saida, combustivel_retorno, km_livres, qtd_diarias, valor_hora_extra, valor_km_excedente, valor_avarias, desconto, tipo, data_criacao, data_finalizacao, updated_at, cartao_ultimos4, taxa_combustivel, taxa_limpeza, taxa_higienizacao, taxa_pneus, taxa_acessorios, valor_franquia_seguro, taxa_administrativa, status_pagamento, forma_pagamento, data_vencimento_pagamento, data_pagamento, valor_recebido) FROM stdin;
9	CTR-20260312210426977	2	13	2026-03-12 00:00:00	2026-03-20 00:00:00	65465	\N	150.00	1200.00	ativo	\N	\N	\N	\N	\N	\N	\N	18:04	1/4	\N	-12	8	\N	0.00	\N	0.00	cliente	2026-03-12 21:04:26.962937	\N	2026-03-12 21:05:23.004047	\N	\N	\N	\N	\N	\N	\N	\N	pendente	\N	2026-03-17	\N	\N
\.


--
-- Data for Name: despesa_contrato; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.despesa_contrato (id, contrato_id, tipo, descricao, valor, data_registro, responsavel) FROM stdin;
\.


--
-- Data for Name: despesa_loja; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.despesa_loja (id, mes, ano, categoria, valor, descricao, data) FROM stdin;
1	1	2025	\N	3500.00	Aluguel escritorio	2026-03-08 17:56:11.712616
2	1	2025	\N	450.00	Energia eletrica	2026-03-08 17:56:11.712616
3	1	2025	\N	180.00	Internet e telefone	2026-03-08 17:56:11.712616
4	2	2025	\N	3500.00	Aluguel escritorio	2026-03-08 17:56:11.712616
5	2	2025	\N	520.00	Energia eletrica	2026-03-08 17:56:11.712616
6	2	2025	\N	180.00	Internet e telefone	2026-03-08 17:56:11.712616
7	3	2025	\N	3500.00	Aluguel escritorio	2026-03-08 17:56:11.712616
8	3	2025	\N	480.00	Energia eletrica	2026-03-08 17:56:11.712616
10	3	2026	Aluguel	1500.00	teste	2026-03-13 12:26:15.045504
\.


--
-- Data for Name: despesa_nf; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.despesa_nf (id, uso_id, veiculo_id, tipo, descricao, valor, data) FROM stdin;
\.


--
-- Data for Name: despesa_operacional; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.despesa_operacional (id, tipo, origem_tabela, origem_id, veiculo_id, empresa_id, descricao, valor, data, categoria, mes, ano) FROM stdin;
\.


--
-- Data for Name: despesa_veiculo; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.despesa_veiculo (id, veiculo_id, tipo, valor, descricao, km, data, pneu) FROM stdin;
\.


--
-- Data for Name: documentos; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.documentos (id, tipo_entidade, entidade_id, nome_arquivo, nome_original, tipo_documento, caminho, tamanho, data_upload) FROM stdin;
\.


--
-- Data for Name: empresas; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.empresas (id, nome, cnpj, razao_social, endereco, cidade, estado, cep, telefone, email, contato_principal, data_cadastro, ativo, updated_at) FROM stdin;
\.


--
-- Data for Name: ipva_aliquota; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.ipva_aliquota (id, estado, tipo_veiculo, aliquota, descricao) FROM stdin;
1	SP	Automovel	4	Aliquota IPVA SP - Automovel
2	SP	Moto	1.5	Aliquota IPVA SP - Moto
3	SP	Utilitario	2	Aliquota IPVA SP - Utilitario
4	SP	Caminhao	2.5	Aliquota IPVA SP - Caminhao
5	RJ	Automovel	3.5	Aliquota IPVA RJ - Automovel
6	RJ	Moto	1	Aliquota IPVA RJ - Moto
7	RJ	Utilitario	2	Aliquota IPVA RJ - Utilitario
8	RJ	Caminhao	2.5	Aliquota IPVA RJ - Caminhao
9	MG	Automovel	3.5	Aliquota IPVA MG - Automovel
10	MG	Moto	1.5	Aliquota IPVA MG - Moto
11	MG	Utilitario	2	Aliquota IPVA MG - Utilitario
12	MG	Caminhao	2.5	Aliquota IPVA MG - Caminhao
13	BA	Automovel	3	Aliquota IPVA BA - Automovel
14	BA	Moto	1.5	Aliquota IPVA BA - Moto
15	BA	Utilitario	2	Aliquota IPVA BA - Utilitario
16	BA	Caminhao	2.5	Aliquota IPVA BA - Caminhao
17	SC	Automovel	3.5	Aliquota IPVA SC - Automovel
18	SC	Moto	1.5	Aliquota IPVA SC - Moto
19	SC	Utilitario	2	Aliquota IPVA SC - Utilitario
20	SC	Caminhao	2.5	Aliquota IPVA SC - Caminhao
21	PR	Automovel	3.5	Aliquota IPVA PR - Automovel
22	PR	Moto	1.5	Aliquota IPVA PR - Moto
23	PR	Utilitario	2	Aliquota IPVA PR - Utilitario
24	PR	Caminhao	2.5	Aliquota IPVA PR - Caminhao
25	RS	Automovel	3.5	Aliquota IPVA RS - Automovel
26	RS	Moto	1.5	Aliquota IPVA RS - Moto
27	RS	Utilitario	2	Aliquota IPVA RS - Utilitario
28	RS	Caminhao	2.5	Aliquota IPVA RS - Caminhao
29	DF	Automovel	4.5	Aliquota IPVA DF - Automovel
30	DF	Moto	2	Aliquota IPVA DF - Moto
31	DF	Utilitario	2.5	Aliquota IPVA DF - Utilitario
32	DF	Caminhao	3	Aliquota IPVA DF - Caminhao
33	RN	Automovel	3	Aliquota IPVA RN - Automovel
34	RN	Moto	1	Aliquota IPVA RN - Moto
35	RN	Utilitario	1.5	Aliquota IPVA RN - Utilitario
36	RN	Caminhao	1	Aliquota IPVA RN - Caminhao
37	CE	Automovel	3	Aliquota IPVA CE - Automovel
38	CE	Moto	1.5	Aliquota IPVA CE - Moto
39	CE	Utilitario	2	Aliquota IPVA CE - Utilitario
40	CE	Caminhao	2	Aliquota IPVA CE - Caminhao
\.


--
-- Data for Name: ipva_parcela; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.ipva_parcela (id, ipva_id, veiculo_id, numero_parcela, valor, vencimento, data_pagamento, status) FROM stdin;
4	9	13	1	308.33	2026-03-12	\N	pendente
5	9	13	2	308.33	2026-04-12	\N	pendente
6	9	13	3	308.33	2026-05-12	\N	pendente
7	9	13	4	308.33	2026-06-12	\N	pendente
8	9	13	5	308.33	2026-07-12	\N	pendente
9	9	13	6	308.35	2026-08-12	\N	pendente
\.


--
-- Data for Name: ipva_registro; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.ipva_registro (id, veiculo_id, ano_referencia, valor_venal, aliquota, valor_ipva, valor_pago, data_vencimento, data_pagamento, status, data_criacao, qtd_parcelas, updated_at) FROM stdin;
9	13	2026	18500.00	3	1850.00	\N	2026-03-12	\N	pendente	2026-03-12 20:52:04.440059	\N	2026-03-12 20:52:04.440059
\.


--
-- Data for Name: lancamentos_financeiros; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.lancamentos_financeiros (id, data, tipo, categoria, descricao, valor, status, data_criacao, updated_at) FROM stdin;
\.


--
-- Data for Name: manutencoes; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.manutencoes (id, veiculo_id, tipo, descricao, km_realizada, km_proxima, data_realizada, data_proxima, custo, oficina, status, data_criacao, updated_at) FROM stdin;
7	13	preventiva	TROCA DE OLEO E TODOS OS FILTROS	65465	74000	2026-03-12	2026-03-12	0.00	POSTO SEGUNDO MELO	concluida	2026-03-12 20:44:46.49404	2026-03-12 20:44:46.49404
\.


--
-- Data for Name: motorista_empresa; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.motorista_empresa (id, empresa_id, cliente_id, cargo, ativo, data_vinculo) FROM stdin;
\.


--
-- Data for Name: multas; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.multas (id, veiculo_id, contrato_id, cliente_id, data_infracao, numero_infracao, data_vencimento, valor, pontos, gravidade, descricao, status, responsavel, data_pagamento, data_criacao, updated_at) FROM stdin;
\.


--
-- Data for Name: parcela_seguro; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.parcela_seguro (id, seguro_id, veiculo_id, numero_parcela, valor, vencimento, data_pagamento, status) FROM stdin;
\.


--
-- Data for Name: prorrogacao_contrato; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.prorrogacao_contrato (id, contrato_id, data_anterior, data_nova, motivo, diarias_adicionais, valor_adicional, data_criacao) FROM stdin;
\.


--
-- Data for Name: quilometragem; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.quilometragem (id, contrato_id, discriminacao, quantidade, preco_unitario, preco_total, data_registro) FROM stdin;
\.


--
-- Data for Name: relatorio_nf; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.relatorio_nf (id, veiculo_id, empresa_id, uso_id, periodo_inicio, periodo_fim, km_percorrida, km_excedente, valor_total_extra, caminho_pdf, data_criacao) FROM stdin;
\.


--
-- Data for Name: reservas; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.reservas (id, cliente_id, veiculo_id, data_inicio, data_fim, status, valor_estimado, data_criacao, updated_at) FROM stdin;
\.


--
-- Data for Name: seguros; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.seguros (id, veiculo_id, seguradora, numero_apolice, tipo_seguro, data_inicio, data_fim, valor, valor_franquia, status, qtd_parcelas, data_criacao, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.users (id, email, hashed_password, nome, perfil, ativo, permitted_pages, data_cadastro, password_reset_token_hash, password_reset_expires_at, password_reset_requested_at) FROM stdin;
1	admin@mpcars.com	$2b$12$VgPwpB3oawzHoXsqKJ9PI.lfg1/oHWkSwI07dyVMvTaEIgkR9vwqS	Administrador	admin	t	["dashboard", "clientes", "veiculos", "contratos", "empresas", "financeiro", "seguros", "ipva", "multas", "manutencoes", "reservas", "despesas-loja", "relatorios", "configuracoes", "usuarios", "governanca"]	2026-03-08 17:56:11.371508	\N	\N	\N
6	marcellopetterson@hotmail.com	$2b$12$T8qZaybHaika8kBNHPDqTuVsq2xNGw8yW.V9IWj6g86L/7x4T225C	Marcelo Petterson Alves Arnaud	owner	t	["dashboard", "clientes", "veiculos", "contratos", "empresas", "financeiro", "seguros", "ipva", "multas", "manutencoes", "reservas", "despesas-loja", "relatorios", "configuracoes", "usuarios", "governanca"]	2026-03-12 20:19:00.606297	\N	\N	\N
\.


--
-- Data for Name: uso_veiculo_empresa; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.uso_veiculo_empresa (id, veiculo_id, empresa_id, contrato_id, km_inicial, km_final, km_percorrido, data_inicio, data_fim, km_referencia, valor_km_extra, valor_diaria_empresa, status, data_criacao) FROM stdin;
\.


--
-- Data for Name: veiculos; Type: TABLE DATA; Schema: public; Owner: mpcars2
--

COPY public.veiculos (id, placa, marca, modelo, ano, cor, chassis, renavam, combustivel, capacidade_tanque, km_atual, data_aquisicao, valor_aquisicao, status, checklist_item_1, checklist_item_2, checklist_item_3, checklist_item_4, checklist_item_5, checklist_item_6, checklist_item_7, checklist_item_8, checklist_item_9, checklist_item_10, categoria, valor_diaria, foto_url, data_cadastro, ativo, updated_at, checklist) FROM stdin;
13	SHG3G73	FIAT	MOBI	2023	BRANCO	\N	\N	\N	\N	65465	2026-03-12	46.25	alugado	0	0	0	0	0	0	0	0	0	0	\N	\N	\N	2026-03-12 20:39:07.367472	t	2026-03-12 21:04:26.962937	{}
\.


--
-- Name: activity_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.activity_logs_id_seq', 81, true);


--
-- Name: alerta_historico_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.alerta_historico_id_seq', 1, false);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 1, false);


--
-- Name: checkin_checkout_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.checkin_checkout_id_seq', 1, true);


--
-- Name: clientes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.clientes_id_seq', 10, true);


--
-- Name: configuracoes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.configuracoes_id_seq', 33, true);


--
-- Name: contratos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.contratos_id_seq', 9, true);


--
-- Name: despesa_contrato_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.despesa_contrato_id_seq', 6, true);


--
-- Name: despesa_loja_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.despesa_loja_id_seq', 10, true);


--
-- Name: despesa_nf_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.despesa_nf_id_seq', 1, false);


--
-- Name: despesa_operacional_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.despesa_operacional_id_seq', 1, false);


--
-- Name: despesa_veiculo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.despesa_veiculo_id_seq', 6, true);


--
-- Name: documentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.documentos_id_seq', 1, false);


--
-- Name: empresas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.empresas_id_seq', 7, true);


--
-- Name: ipva_aliquota_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.ipva_aliquota_id_seq', 40, true);


--
-- Name: ipva_parcela_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.ipva_parcela_id_seq', 9, true);


--
-- Name: ipva_registro_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.ipva_registro_id_seq', 9, true);


--
-- Name: lancamentos_financeiros_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.lancamentos_financeiros_id_seq', 1, true);


--
-- Name: manutencoes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.manutencoes_id_seq', 7, true);


--
-- Name: motorista_empresa_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.motorista_empresa_id_seq', 1, false);


--
-- Name: multas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.multas_id_seq', 3, true);


--
-- Name: parcela_seguro_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.parcela_seguro_id_seq', 45, true);


--
-- Name: prorrogacao_contrato_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.prorrogacao_contrato_id_seq', 1, false);


--
-- Name: quilometragem_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.quilometragem_id_seq', 1, false);


--
-- Name: relatorio_nf_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.relatorio_nf_id_seq', 1, true);


--
-- Name: reservas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.reservas_id_seq', 4, true);


--
-- Name: seguros_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.seguros_id_seq', 6, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.users_id_seq', 6, true);


--
-- Name: uso_veiculo_empresa_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.uso_veiculo_empresa_id_seq', 1, true);


--
-- Name: veiculos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mpcars2
--

SELECT pg_catalog.setval('public.veiculos_id_seq', 13, true);


--
-- Name: activity_logs activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.activity_logs
    ADD CONSTRAINT activity_logs_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: alerta_historico alerta_historico_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.alerta_historico
    ADD CONSTRAINT alerta_historico_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: checkin_checkout checkin_checkout_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.checkin_checkout
    ADD CONSTRAINT checkin_checkout_pkey PRIMARY KEY (id);


--
-- Name: clientes clientes_cpf_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_cpf_key UNIQUE (cpf);


--
-- Name: clientes clientes_email_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_email_key UNIQUE (email);


--
-- Name: clientes clientes_numero_cnh_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_numero_cnh_key UNIQUE (numero_cnh);


--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);


--
-- Name: configuracoes configuracoes_chave_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.configuracoes
    ADD CONSTRAINT configuracoes_chave_key UNIQUE (chave);


--
-- Name: configuracoes configuracoes_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.configuracoes
    ADD CONSTRAINT configuracoes_pkey PRIMARY KEY (id);


--
-- Name: contratos contratos_numero_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.contratos
    ADD CONSTRAINT contratos_numero_key UNIQUE (numero);


--
-- Name: contratos contratos_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.contratos
    ADD CONSTRAINT contratos_pkey PRIMARY KEY (id);


--
-- Name: despesa_contrato despesa_contrato_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_contrato
    ADD CONSTRAINT despesa_contrato_pkey PRIMARY KEY (id);


--
-- Name: despesa_loja despesa_loja_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_loja
    ADD CONSTRAINT despesa_loja_pkey PRIMARY KEY (id);


--
-- Name: despesa_nf despesa_nf_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_nf
    ADD CONSTRAINT despesa_nf_pkey PRIMARY KEY (id);


--
-- Name: despesa_operacional despesa_operacional_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_operacional
    ADD CONSTRAINT despesa_operacional_pkey PRIMARY KEY (id);


--
-- Name: despesa_veiculo despesa_veiculo_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_veiculo
    ADD CONSTRAINT despesa_veiculo_pkey PRIMARY KEY (id);


--
-- Name: documentos documentos_nome_arquivo_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.documentos
    ADD CONSTRAINT documentos_nome_arquivo_key UNIQUE (nome_arquivo);


--
-- Name: documentos documentos_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.documentos
    ADD CONSTRAINT documentos_pkey PRIMARY KEY (id);


--
-- Name: empresas empresas_cnpj_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.empresas
    ADD CONSTRAINT empresas_cnpj_key UNIQUE (cnpj);


--
-- Name: empresas empresas_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.empresas
    ADD CONSTRAINT empresas_pkey PRIMARY KEY (id);


--
-- Name: ipva_aliquota ipva_aliquota_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_aliquota
    ADD CONSTRAINT ipva_aliquota_pkey PRIMARY KEY (id);


--
-- Name: ipva_parcela ipva_parcela_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_parcela
    ADD CONSTRAINT ipva_parcela_pkey PRIMARY KEY (id);


--
-- Name: ipva_registro ipva_registro_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_registro
    ADD CONSTRAINT ipva_registro_pkey PRIMARY KEY (id);


--
-- Name: lancamentos_financeiros lancamentos_financeiros_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.lancamentos_financeiros
    ADD CONSTRAINT lancamentos_financeiros_pkey PRIMARY KEY (id);


--
-- Name: manutencoes manutencoes_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.manutencoes
    ADD CONSTRAINT manutencoes_pkey PRIMARY KEY (id);


--
-- Name: motorista_empresa motorista_empresa_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.motorista_empresa
    ADD CONSTRAINT motorista_empresa_pkey PRIMARY KEY (id);


--
-- Name: multas multas_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.multas
    ADD CONSTRAINT multas_pkey PRIMARY KEY (id);


--
-- Name: parcela_seguro parcela_seguro_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.parcela_seguro
    ADD CONSTRAINT parcela_seguro_pkey PRIMARY KEY (id);


--
-- Name: prorrogacao_contrato prorrogacao_contrato_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.prorrogacao_contrato
    ADD CONSTRAINT prorrogacao_contrato_pkey PRIMARY KEY (id);


--
-- Name: quilometragem quilometragem_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.quilometragem
    ADD CONSTRAINT quilometragem_pkey PRIMARY KEY (id);


--
-- Name: relatorio_nf relatorio_nf_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.relatorio_nf
    ADD CONSTRAINT relatorio_nf_pkey PRIMARY KEY (id);


--
-- Name: reservas reservas_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.reservas
    ADD CONSTRAINT reservas_pkey PRIMARY KEY (id);


--
-- Name: seguros seguros_numero_apolice_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.seguros
    ADD CONSTRAINT seguros_numero_apolice_key UNIQUE (numero_apolice);


--
-- Name: seguros seguros_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.seguros
    ADD CONSTRAINT seguros_pkey PRIMARY KEY (id);


--
-- Name: ipva_aliquota uq_ipva_aliquota; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_aliquota
    ADD CONSTRAINT uq_ipva_aliquota UNIQUE (estado, tipo_veiculo);


--
-- Name: motorista_empresa uq_motorista_empresa; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.motorista_empresa
    ADD CONSTRAINT uq_motorista_empresa UNIQUE (empresa_id, cliente_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: uso_veiculo_empresa uso_veiculo_empresa_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.uso_veiculo_empresa
    ADD CONSTRAINT uso_veiculo_empresa_pkey PRIMARY KEY (id);


--
-- Name: veiculos veiculos_chassis_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.veiculos
    ADD CONSTRAINT veiculos_chassis_key UNIQUE (chassis);


--
-- Name: veiculos veiculos_pkey; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.veiculos
    ADD CONSTRAINT veiculos_pkey PRIMARY KEY (id);


--
-- Name: veiculos veiculos_placa_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.veiculos
    ADD CONSTRAINT veiculos_placa_key UNIQUE (placa);


--
-- Name: veiculos veiculos_renavam_key; Type: CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.veiculos
    ADD CONSTRAINT veiculos_renavam_key UNIQUE (renavam);


--
-- Name: ix_activity_logs_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_activity_logs_id ON public.activity_logs USING btree (id);


--
-- Name: ix_alerta_historico_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_alerta_historico_id ON public.alerta_historico USING btree (id);


--
-- Name: ix_audit_logs_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_audit_logs_id ON public.audit_logs USING btree (id);


--
-- Name: ix_checkin_checkout_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_checkin_checkout_id ON public.checkin_checkout USING btree (id);


--
-- Name: ix_clientes_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_clientes_id ON public.clientes USING btree (id);


--
-- Name: ix_configuracoes_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_configuracoes_id ON public.configuracoes USING btree (id);


--
-- Name: ix_contratos_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_contratos_id ON public.contratos USING btree (id);


--
-- Name: ix_despesa_contrato_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_despesa_contrato_id ON public.despesa_contrato USING btree (id);


--
-- Name: ix_despesa_loja_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_despesa_loja_id ON public.despesa_loja USING btree (id);


--
-- Name: ix_despesa_nf_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_despesa_nf_id ON public.despesa_nf USING btree (id);


--
-- Name: ix_despesa_operacional_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_despesa_operacional_id ON public.despesa_operacional USING btree (id);


--
-- Name: ix_despesa_veiculo_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_despesa_veiculo_id ON public.despesa_veiculo USING btree (id);


--
-- Name: ix_documentos_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_documentos_id ON public.documentos USING btree (id);


--
-- Name: ix_empresas_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_empresas_id ON public.empresas USING btree (id);


--
-- Name: ix_ipva_aliquota_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_ipva_aliquota_id ON public.ipva_aliquota USING btree (id);


--
-- Name: ix_ipva_parcela_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_ipva_parcela_id ON public.ipva_parcela USING btree (id);


--
-- Name: ix_ipva_registro_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_ipva_registro_id ON public.ipva_registro USING btree (id);


--
-- Name: ix_lancamentos_financeiros_data; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_lancamentos_financeiros_data ON public.lancamentos_financeiros USING btree (data);


--
-- Name: ix_lancamentos_financeiros_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_lancamentos_financeiros_id ON public.lancamentos_financeiros USING btree (id);


--
-- Name: ix_lancamentos_financeiros_status; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_lancamentos_financeiros_status ON public.lancamentos_financeiros USING btree (status);


--
-- Name: ix_lancamentos_financeiros_tipo; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_lancamentos_financeiros_tipo ON public.lancamentos_financeiros USING btree (tipo);


--
-- Name: ix_manutencoes_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_manutencoes_id ON public.manutencoes USING btree (id);


--
-- Name: ix_motorista_empresa_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_motorista_empresa_id ON public.motorista_empresa USING btree (id);


--
-- Name: ix_multas_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_multas_id ON public.multas USING btree (id);


--
-- Name: ix_parcela_seguro_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_parcela_seguro_id ON public.parcela_seguro USING btree (id);


--
-- Name: ix_prorrogacao_contrato_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_prorrogacao_contrato_id ON public.prorrogacao_contrato USING btree (id);


--
-- Name: ix_quilometragem_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_quilometragem_id ON public.quilometragem USING btree (id);


--
-- Name: ix_relatorio_nf_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_relatorio_nf_id ON public.relatorio_nf USING btree (id);


--
-- Name: ix_reservas_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_reservas_id ON public.reservas USING btree (id);


--
-- Name: ix_seguros_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_seguros_id ON public.seguros USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_uso_veiculo_empresa_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_uso_veiculo_empresa_id ON public.uso_veiculo_empresa USING btree (id);


--
-- Name: ix_veiculos_id; Type: INDEX; Schema: public; Owner: mpcars2
--

CREATE INDEX ix_veiculos_id ON public.veiculos USING btree (id);


--
-- Name: checkin_checkout checkin_checkout_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.checkin_checkout
    ADD CONSTRAINT checkin_checkout_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contratos(id);


--
-- Name: clientes clientes_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: contratos contratos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.contratos
    ADD CONSTRAINT contratos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: contratos contratos_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.contratos
    ADD CONSTRAINT contratos_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: despesa_contrato despesa_contrato_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_contrato
    ADD CONSTRAINT despesa_contrato_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contratos(id);


--
-- Name: despesa_nf despesa_nf_uso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_nf
    ADD CONSTRAINT despesa_nf_uso_id_fkey FOREIGN KEY (uso_id) REFERENCES public.uso_veiculo_empresa(id);


--
-- Name: despesa_nf despesa_nf_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_nf
    ADD CONSTRAINT despesa_nf_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: despesa_operacional despesa_operacional_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_operacional
    ADD CONSTRAINT despesa_operacional_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: despesa_operacional despesa_operacional_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_operacional
    ADD CONSTRAINT despesa_operacional_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: despesa_veiculo despesa_veiculo_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.despesa_veiculo
    ADD CONSTRAINT despesa_veiculo_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: ipva_parcela ipva_parcela_ipva_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_parcela
    ADD CONSTRAINT ipva_parcela_ipva_id_fkey FOREIGN KEY (ipva_id) REFERENCES public.ipva_registro(id);


--
-- Name: ipva_parcela ipva_parcela_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_parcela
    ADD CONSTRAINT ipva_parcela_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: ipva_registro ipva_registro_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.ipva_registro
    ADD CONSTRAINT ipva_registro_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: manutencoes manutencoes_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.manutencoes
    ADD CONSTRAINT manutencoes_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: motorista_empresa motorista_empresa_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.motorista_empresa
    ADD CONSTRAINT motorista_empresa_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: motorista_empresa motorista_empresa_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.motorista_empresa
    ADD CONSTRAINT motorista_empresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: multas multas_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.multas
    ADD CONSTRAINT multas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: multas multas_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.multas
    ADD CONSTRAINT multas_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contratos(id);


--
-- Name: multas multas_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.multas
    ADD CONSTRAINT multas_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: parcela_seguro parcela_seguro_seguro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.parcela_seguro
    ADD CONSTRAINT parcela_seguro_seguro_id_fkey FOREIGN KEY (seguro_id) REFERENCES public.seguros(id);


--
-- Name: parcela_seguro parcela_seguro_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.parcela_seguro
    ADD CONSTRAINT parcela_seguro_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: prorrogacao_contrato prorrogacao_contrato_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.prorrogacao_contrato
    ADD CONSTRAINT prorrogacao_contrato_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contratos(id);


--
-- Name: quilometragem quilometragem_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.quilometragem
    ADD CONSTRAINT quilometragem_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contratos(id);


--
-- Name: relatorio_nf relatorio_nf_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.relatorio_nf
    ADD CONSTRAINT relatorio_nf_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: relatorio_nf relatorio_nf_uso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.relatorio_nf
    ADD CONSTRAINT relatorio_nf_uso_id_fkey FOREIGN KEY (uso_id) REFERENCES public.uso_veiculo_empresa(id);


--
-- Name: relatorio_nf relatorio_nf_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.relatorio_nf
    ADD CONSTRAINT relatorio_nf_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: reservas reservas_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.reservas
    ADD CONSTRAINT reservas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: reservas reservas_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.reservas
    ADD CONSTRAINT reservas_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: seguros seguros_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.seguros
    ADD CONSTRAINT seguros_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- Name: uso_veiculo_empresa uso_veiculo_empresa_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.uso_veiculo_empresa
    ADD CONSTRAINT uso_veiculo_empresa_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contratos(id);


--
-- Name: uso_veiculo_empresa uso_veiculo_empresa_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.uso_veiculo_empresa
    ADD CONSTRAINT uso_veiculo_empresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: uso_veiculo_empresa uso_veiculo_empresa_veiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mpcars2
--

ALTER TABLE ONLY public.uso_veiculo_empresa
    ADD CONSTRAINT uso_veiculo_empresa_veiculo_id_fkey FOREIGN KEY (veiculo_id) REFERENCES public.veiculos(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 1DzNglDLSAwiMZDiJPgYdmoNnUpJbAXfF3zLEYplEXuDfBONd1bcre2CF6SqjUf

