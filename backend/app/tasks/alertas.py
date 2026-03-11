from datetime import datetime, timedelta
from sqlalchemy import text
from app.celery_app import celery
from app.core.database import SessionLocal


@celery.task(name="app.tasks.alertas.gerar_alertas_diarios")
def gerar_alertas_diarios():
    """Gera alertas diários verificando CNH, contratos, seguros, IPVA e manutenções.

    CORRIGIDO: nomes de tabelas/colunas agora correspondem ao model SQLAlchemy.
    - validade_cnh (não cnh_validade)
    - data_fim (não data_prevista_devolucao)
    - alerta_historico (não alertas_historico)
    - data_fim em seguros (não data_vencimento)
    - status 'concluida' em manutencoes (não 'Concluída')
    - Adicionado: alertas de multas vencendo e parcelas de seguro atrasadas
    - Adicionado: limpeza de alertas antigos para evitar duplicatas
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        future_30 = now + timedelta(days=30)
        future_7 = now + timedelta(days=7)
        alertas = []

        # CNH vencendo em 30 dias
        rows = db.execute(text(
            "SELECT id, nome, validade_cnh FROM clientes "
            "WHERE validade_cnh BETWEEN :now AND :future AND ativo = true"
        ), {"now": now.date(), "future": future_30.date()}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "CNH vencendo",
                "urgencia": "atencao",
                "entidade_tipo": "cliente",
                "entidade_id": r[0],
                "titulo": "CNH de {} vence em breve".format(r[1]),
                "descricao": "Validade: {}".format(r[2])
            })

        # CNH vencida
        rows = db.execute(text(
            "SELECT id, nome, validade_cnh FROM clientes "
            "WHERE validade_cnh < :now AND validade_cnh IS NOT NULL AND ativo = true"
        ), {"now": now.date()}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "CNH vencida",
                "urgencia": "critico",
                "entidade_tipo": "cliente",
                "entidade_id": r[0],
                "titulo": "CNH de {} VENCIDA".format(r[1]),
                "descricao": "Venceu em: {}".format(r[2])
            })

        # Contratos atrasados (data_fim passou e status ainda ativo)
        rows = db.execute(text(
            "SELECT c.id, cl.nome, c.data_fim FROM contratos c "
            "JOIN clientes cl ON cl.id = c.cliente_id "
            "WHERE c.status = 'ativo' AND c.data_fim < :now"
        ), {"now": now}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "Contrato atrasado",
                "urgencia": "critico",
                "entidade_tipo": "contrato",
                "entidade_id": r[0],
                "titulo": "Contrato #{} de {} atrasado".format(r[0], r[1]),
                "descricao": "Devolucao prevista: {}".format(r[2])
            })

        # Contratos vencendo em 7 dias
        rows = db.execute(text(
            "SELECT c.id, cl.nome, c.data_fim FROM contratos c "
            "JOIN clientes cl ON cl.id = c.cliente_id "
            "WHERE c.status = 'ativo' AND c.data_fim BETWEEN :now AND :future"
        ), {"now": now, "future": future_7}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "Contrato vencendo",
                "urgencia": "atencao",
                "entidade_tipo": "contrato",
                "entidade_id": r[0],
                "titulo": "Contrato #{} de {} vence em breve".format(r[0], r[1]),
                "descricao": "Vencimento: {}".format(r[2])
            })

        # Seguros vencendo em 30 dias (campo correto: data_fim)
        rows = db.execute(text(
            "SELECT id, seguradora, data_fim FROM seguros "
            "WHERE status = 'ativo' AND data_fim BETWEEN :now AND :future"
        ), {"now": now.date(), "future": future_30.date()}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "Seguro vencendo",
                "urgencia": "atencao",
                "entidade_tipo": "seguro",
                "entidade_id": r[0],
                "titulo": "Seguro {} vence em breve".format(r[1]),
                "descricao": "Vencimento: {}".format(r[2])
            })

        # IPVA vencendo em 30 dias
        rows = db.execute(text(
            "SELECT id, ano_referencia, data_vencimento FROM ipva_registro "
            "WHERE status = 'pendente' AND data_vencimento BETWEEN :now AND :future"
        ), {"now": now.date(), "future": future_30.date()}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "IPVA vencendo",
                "urgencia": "atencao",
                "entidade_tipo": "ipva",
                "entidade_id": r[0],
                "titulo": "IPVA {} vence em breve".format(r[1]),
                "descricao": "Vencimento: {}".format(r[2])
            })

        # Manutenção atrasada (por data)
        rows = db.execute(text(
            "SELECT id, descricao, data_proxima FROM manutencoes "
            "WHERE status IN ('pendente', 'agendada') AND data_proxima < :now"
        ), {"now": now.date()}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "Manutencao atrasada",
                "urgencia": "critico",
                "entidade_tipo": "manutencao",
                "entidade_id": r[0],
                "titulo": "Manutencao atrasada: {}".format(r[1]),
                "descricao": "Data prevista: {}".format(r[2])
            })

        # Manutenção por KM atingido
        rows = db.execute(text(
            "SELECT m.id, m.descricao, v.km_atual, m.km_proxima FROM manutencoes m "
            "JOIN veiculos v ON v.id = m.veiculo_id "
            "WHERE m.status NOT IN ('concluida') AND m.km_proxima IS NOT NULL "
            "AND v.km_atual >= m.km_proxima"
        )).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "Manutencao por KM",
                "urgencia": "atencao",
                "entidade_tipo": "manutencao",
                "entidade_id": r[0],
                "titulo": "KM atingido para: {}".format(r[1]),
                "descricao": "KM atual: {}, KM previsto: {}".format(r[2], r[3])
            })

        # Multas pendentes vencendo (NOVO)
        rows = db.execute(text(
            "SELECT id, descricao, data_vencimento, valor FROM multas "
            "WHERE status = 'pendente' AND data_vencimento BETWEEN :now AND :future"
        ), {"now": now.date(), "future": future_30.date()}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "Multa vencendo",
                "urgencia": "atencao",
                "entidade_tipo": "multa",
                "entidade_id": r[0],
                "titulo": "Multa vence em breve: {}".format(r[1] or "Sem descricao"),
                "descricao": "Vencimento: {} - Valor: R$ {}".format(r[2], r[3])
            })

        # Parcelas de seguro atrasadas (NOVO)
        rows = db.execute(text(
            "SELECT ps.id, s.seguradora, ps.vencimento, ps.valor FROM parcela_seguro ps "
            "JOIN seguros s ON s.id = ps.seguro_id "
            "WHERE ps.status = 'pendente' AND ps.vencimento < :now"
        ), {"now": now.date()}).fetchall()
        for r in rows:
            alertas.append({
                "tipo_alerta": "Parcela seguro atrasada",
                "urgencia": "critico",
                "entidade_tipo": "seguro",
                "entidade_id": r[0],
                "titulo": "Parcela de seguro {} atrasada".format(r[1]),
                "descricao": "Vencimento: {} - Valor: R$ {}".format(r[2], r[3])
            })

        # Limpar alertas antigos não resolvidos (evitar duplicatas)
        db.execute(text(
            "DELETE FROM alerta_historico WHERE resolvido = false AND data_criacao < :hoje"
        ), {"hoje": now.replace(hour=0, minute=0, second=0)})

        # Inserir novos alertas (tabela correta: alerta_historico)
        for a in alertas:
            db.execute(text(
                "INSERT INTO alerta_historico (tipo_alerta, urgencia, entidade_tipo, entidade_id, "
                "titulo, descricao, data_criacao, resolvido) "
                "VALUES (:tipo_alerta, :urgencia, :entidade_tipo, :entidade_id, "
                ":titulo, :descricao, :now, false)"
            ), {**a, "now": now})

        db.commit()
        return "Gerados {} alertas".format(len(alertas))
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
