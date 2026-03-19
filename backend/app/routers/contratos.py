from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import distinct, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.pagination import escape_like, paginate
from app.models import (
    CheckinCheckout,
    Cliente,
    Contrato,
    DespesaContrato,
    Multa,
    ProrrogacaoContrato,
    Quilometragem,
    UsoVeiculoEmpresa,
    Veiculo,
)
from app.models.user import User
from app.schemas.contratos import (
    ContratoCreate,
    ContratoFinalizeRequest,
    ContratoPaymentUpdate,
    ContratoResponse,
    ContratoUpdate,
    DespesaContratoResponse,
)
from app.services.activity_logger import log_activity
from app.services.contratos import (
    apply_payment_details,
    append_observacao,
    calcular_qtd_diarias,
    calcular_valor_total,
    ensure_cliente_exists,
    ensure_veiculo_available,
    normalize_contrato_payload,
    normalize_finalizacao_payload,
    recalcular_status_veiculo,
    resolve_cliente_contrato,
    resolver_data_fim,
    sincronizar_uso_empresa,
    validar_datas,
)
from app.services.pdf_service import PDFService
from app.routers.dashboard import invalidate_dashboard_cache


router = APIRouter(
    prefix="/contratos",
    tags=["Contratos"],
    dependencies=[Depends(require_page_access("contratos"))],
)


@router.get("/")
def list_contratos(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all contracts with pagination."""
    del current_user

    # Subquery for frota_count (distinct vehicles for the client's company)
    frota_count_subquery = (
        db.query(func.count(distinct(UsoVeiculoEmpresa.veiculo_id)))
        .join(Cliente, Cliente.empresa_id == UsoVeiculoEmpresa.empresa_id)
        .filter(Cliente.id == Contrato.cliente_id)
        .correlate(Contrato)
        .as_scalar()
    )

    query = (
        db.query(Contrato)
        .options(joinedload(Contrato.cliente), joinedload(Contrato.veiculo))
        .join(Cliente, Cliente.id == Contrato.cliente_id)
        .join(Veiculo, Veiculo.id == Contrato.veiculo_id)
        .order_by(Contrato.data_criacao.desc())
    )

    if search:
        search_term = "%{}%".format(escape_like(search.strip()))
        query = query.filter(
            or_(
                Contrato.numero.ilike(search_term),
                Cliente.nome.ilike(search_term),
                Veiculo.placa.ilike(search_term),
                Veiculo.marca.ilike(search_term),
                Veiculo.modelo.ilike(search_term),
            )
        )

    if status_filter:
        if status_filter == "atraso":
            query = query.filter(
                Contrato.status == "ativo",
                Contrato.data_fim < datetime.now(),
            )
        else:
            query = query.filter(Contrato.status == status_filter)

    result = paginate(query=query, page=page, limit=limit)
    
    # Add frota_count to serialized items
    for item_dict in result["data"]:
        cliente_id = item_dict.get("cliente_id")
        if cliente_id:
            # Get the company_id for this client
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if cliente and cliente.empresa_id:
                count = db.query(func.count(distinct(UsoVeiculoEmpresa.veiculo_id)))\
                    .filter(UsoVeiculoEmpresa.empresa_id == cliente.empresa_id)\
                    .scalar()
                item_dict["frota_count"] = count or 0
            else:
                item_dict["frota_count"] = 0

        # For empresa contracts: override valor_total and valor_recebido with real NF data
        if str(item_dict.get("tipo") or "").lower() == "empresa":
            from app.models import RelatorioNF as _ListNF
            nf_records = db.query(_ListNF).filter(
                _ListNF.veiculo_id == item_dict.get("veiculo_id")
            ).all()
            nf_total = sum(float(nf.valor_total_periodo or 0) for nf in nf_records)
            nf_recebido = sum(float(nf.valor_total_periodo or 0) for nf in nf_records if nf.pago)
            if nf_total > 0:
                item_dict["valor_total"] = nf_total
                item_dict["valor_recebido"] = nf_recebido
                # Update status_pagamento based on NF payments
                if nf_recebido >= nf_total - 0.01:
                    item_dict["status_pagamento"] = "pago"
                elif nf_recebido > 0:
                    item_dict["status_pagamento"] = "parcial"
                else:
                    item_dict["status_pagamento"] = "pendente"
    
    return result


@router.get("/atrasados", response_model=List[ContratoResponse])
def get_atrasados(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overdue contracts."""
    del current_user
    agora = datetime.now()
    contratos = db.query(Contrato).filter(
        Contrato.data_fim < agora,
        Contrato.status == "ativo",
    ).all()
    return contratos


@router.get("/vencimentos", response_model=List[ContratoResponse])
def get_vencimentos(
    dias: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contracts expiring within specified days."""
    del current_user
    agora = datetime.now()
    fim = agora + timedelta(days=dias)
    contratos = db.query(Contrato).filter(
        Contrato.data_fim.between(agora, fim),
        Contrato.status == "ativo",
    ).all()
    return contratos


@router.post("/", response_model=ContratoResponse)
def create_contrato(
    contrato: ContratoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create a new contract."""
    raw_payload = contrato.model_dump(exclude_unset=True)
    vigencia_indeterminada = bool(raw_payload.pop("vigencia_indeterminada", False))
    empresa_uso_id = raw_payload.pop("empresa_uso_id", None)
    empresa_id = raw_payload.pop("empresa_id", None)
    contrato_data = normalize_contrato_payload(
        raw_payload,
        is_create=True,
    )
    contrato_data["data_fim"] = resolver_data_fim(
        contrato_data["data_inicio"],
        contrato_data.get("data_fim"),
        tipo=contrato_data.get("tipo"),
        vigencia_indeterminada=vigencia_indeterminada,
    )
    if contrato_data.get("data_fim"):
        validar_datas(contrato_data["data_inicio"], contrato_data["data_fim"])

    if float(contrato_data.get("valor_diaria") or 0) < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor da diaria nao pode ser negativo",
        )

    existing = db.query(Contrato).filter(Contrato.numero == contrato_data["numero"]).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numero de contrato ja existe",
        )

    cliente = resolve_cliente_contrato(
        db,
        tipo=contrato_data.get("tipo"),
        cliente_id=contrato_data.get("cliente_id"),
        empresa_id=empresa_id,
    )
    contrato_data["cliente_id"] = cliente.id
    veiculo = ensure_veiculo_available(db, contrato_data["veiculo_id"])

    if contrato_data.get("km_inicial") is None:
        contrato_data["km_inicial"] = float(veiculo.km_atual or 0)

    if not contrato_data.get("qtd_diarias"):
        contrato_data["qtd_diarias"] = (
            1
            if str(contrato_data.get("tipo") or "").lower() == "empresa"
            else calcular_qtd_diarias(
                contrato_data["data_inicio"],
                contrato_data["data_fim"],
            )
        )

    if not contrato_data.get("valor_total"):
        contrato_data["valor_total"] = calcular_valor_total(
            contrato_data["data_inicio"],
            contrato_data.get("data_fim") or contrato_data["data_inicio"],
            float(contrato_data["valor_diaria"]),
            tipo=contrato_data.get("tipo"),
            km_inicial=contrato_data.get("km_inicial"),
            km_final=contrato_data.get("km_final"),
            km_livres=contrato_data.get("km_livres"),
            valor_km_excedente=contrato_data.get("valor_km_excedente"),
            valor_avarias=contrato_data.get("valor_avarias"),
            taxa_combustivel=contrato_data.get("taxa_combustivel"),
            taxa_limpeza=contrato_data.get("taxa_limpeza"),
            taxa_higienizacao=contrato_data.get("taxa_higienizacao"),
            taxa_pneus=contrato_data.get("taxa_pneus"),
            taxa_acessorios=contrato_data.get("taxa_acessorios"),
            valor_franquia_seguro=contrato_data.get("valor_franquia_seguro"),
            taxa_administrativa=contrato_data.get("taxa_administrativa"),
            desconto=contrato_data.get("desconto"),
        )

    db_contrato = Contrato(**contrato_data)
    apply_payment_details(
        db_contrato,
        contrato_data,
        reference_date=contrato_data["data_fim"],
    )
    db.add(db_contrato)
    db.flush()

    db.add(
        CheckinCheckout(
            contrato_id=db_contrato.id,
            tipo="retirada",
            km=db_contrato.km_inicial,
            nivel_combustivel=db_contrato.combustivel_saida,
            itens_checklist=veiculo.checklist or {},
        )
    )
    veiculo.status = "alugado"
    sincronizar_uso_empresa(
        db,
        db_contrato,
        cliente,
        empresa_uso_id=empresa_uso_id,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Veiculo ja possui contrato ativo. Operacao cancelada.",
        )
    db.refresh(db_contrato)
    invalidate_dashboard_cache()
    log_activity(
        db,
        current_user,
        "CRIAR",
        "Contrato",
        "Contrato {} criado".format(db_contrato.numero),
        db_contrato.id,
        request,
    )
    return db_contrato


@router.get("/{contrato_id}")
def get_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific contract."""
    del current_user
    contrato = db.query(Contrato).options(
        joinedload(Contrato.cliente),
        joinedload(Contrato.veiculo)
    ).filter(Contrato.id == contrato_id).first()
    
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )
    
    # Include ALL empresa_usos for company contracts (not just the ones from this contract)
    empresa_usos = []
    if str(contrato.tipo or "").lower() == "empresa" and contrato.cliente and contrato.cliente.empresa_id:
        # Get ALL vehicle usages for this company, not just from this contract
        usos = db.query(UsoVeiculoEmpresa).options(
            joinedload(UsoVeiculoEmpresa.veiculo)
        ).filter(
            UsoVeiculoEmpresa.empresa_id == contrato.cliente.empresa_id
        ).order_by(UsoVeiculoEmpresa.data_criacao.desc()).all()
        
        for uso in usos:
            # Check if this usage is linked to this contract
            is_linked_to_contract = uso.contrato_id == contrato_id
            
            empresa_usos.append({
                "id": uso.id,
                "veiculo_id": uso.veiculo_id,
                "placa": uso.veiculo.placa if uso.veiculo else None,
                "marca": uso.veiculo.marca if uso.veiculo else None,
                "modelo": uso.veiculo.modelo if uso.veiculo else None,
                "ano": uso.veiculo.ano if uso.veiculo else None,
                "cor": uso.veiculo.cor if uso.veiculo else None,
                "km_inicial": uso.km_inicial,
                "km_final": uso.km_final,
                "km_percorrido": uso.km_percorrido,
                "km_referencia": uso.km_referencia,
                "valor_km_extra": float(uso.valor_km_extra or 0),
                "valor_diaria_empresa": float(uso.valor_diaria_empresa or 0),
                "data_inicio": uso.data_inicio.isoformat() if uso.data_inicio else None,
                "data_fim": uso.data_fim.isoformat() if uso.data_fim else None,
                "data_criacao": uso.data_criacao.isoformat() if uso.data_criacao else None,
                "status": uso.status,
                "contrato_id": uso.contrato_id,
                "is_linked": is_linked_to_contract,
                "grupo_faturamento": uso.veiculo.categoria if uso.veiculo else None,
            })
    
    # Include cliente and veiculo data
    cliente_data = None
    if contrato.cliente:
        cliente_data = {
            "id": contrato.cliente.id,
            "nome": contrato.cliente.nome,
            "empresa_id": contrato.cliente.empresa_id,
        }
    
    veiculo_data = None
    if contrato.veiculo:
        veiculo_data = {
            "id": contrato.veiculo.id,
            "placa": contrato.veiculo.placa,
            "marca": contrato.veiculo.marca,
            "modelo": contrato.veiculo.modelo,
            "km_atual": contrato.veiculo.km_atual,
        }
    
    # Convert to dict and add empresa_usos
    contrato_dict = {
        "id": contrato.id,
        "numero": contrato.numero,
        "cliente_id": contrato.cliente_id,
        "cliente": cliente_data,
        "veiculo_id": contrato.veiculo_id,
        "veiculo": veiculo_data,
        "data_inicio": contrato.data_inicio.isoformat() if contrato.data_inicio else None,
        "data_fim": contrato.data_fim.isoformat() if contrato.data_fim else None,
        "data_finalizacao": contrato.data_finalizacao.isoformat() if contrato.data_finalizacao else None,
        "km_inicial": contrato.km_inicial,
        "km_final": contrato.km_final,
        "valor_diaria": float(contrato.valor_diaria or 0),
        "valor_total": float(contrato.valor_total or 0),
        "status": contrato.status,
        "observacoes": contrato.observacoes,
        "hora_saida": contrato.hora_saida,
        "combustivel_saida": contrato.combustivel_saida,
        "combustivel_retorno": contrato.combustivel_retorno,
        "km_livres": contrato.km_livres,
        "valor_km_excedente": float(contrato.valor_km_excedente or 0),
        "valor_avarias": float(contrato.valor_avarias or 0),
        "taxa_combustivel": float(contrato.taxa_combustivel or 0),
        "taxa_limpeza": float(contrato.taxa_limpeza or 0),
        "taxa_higienizacao": float(contrato.taxa_higienizacao or 0),
        "taxa_pneus": float(contrato.taxa_pneus or 0),
        "taxa_acessorios": float(contrato.taxa_acessorios or 0),
        "valor_franquia_seguro": float(contrato.valor_franquia_seguro or 0),
        "taxa_administrativa": float(contrato.taxa_administrativa or 0),
        "desconto": float(contrato.desconto or 0),
        "status_pagamento": contrato.status_pagamento,
        "forma_pagamento": contrato.forma_pagamento,
        "data_vencimento_pagamento": contrato.data_vencimento_pagamento.isoformat() if contrato.data_vencimento_pagamento else None,
        "data_pagamento": contrato.data_pagamento.isoformat() if contrato.data_pagamento else None,
        "valor_recebido": float(contrato.valor_recebido or 0),
        "tipo": contrato.tipo,
        "qtd_diarias": contrato.qtd_diarias,
        "empresa_usos": empresa_usos,
    }
    
    return contrato_dict


@router.put("/{contrato_id}", response_model=ContratoResponse)
@router.patch("/{contrato_id}", response_model=ContratoResponse)
def update_contrato(
    contrato_id: int,
    contrato_data: ContratoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Update a contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    raw_payload = contrato_data.model_dump(exclude_unset=True)
    vigencia_indeterminada = raw_payload.pop("vigencia_indeterminada", None)
    empresa_uso_id = raw_payload.pop("empresa_uso_id", None)
    empresa_id = raw_payload.pop("empresa_id", None)
    update_data = normalize_contrato_payload(raw_payload)

    if "numero" in update_data and update_data["numero"]:
        existing = db.query(Contrato).filter(
            Contrato.numero == update_data["numero"],
            Contrato.id != contrato_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Numero de contrato ja existe",
            )

    novo_cliente_id = update_data.get("cliente_id", contrato.cliente_id)
    novo_veiculo_id = update_data.get("veiculo_id", contrato.veiculo_id)
    nova_data_inicio = update_data.get("data_inicio", contrato.data_inicio)
    nova_data_fim = update_data.get("data_fim", contrato.data_fim)
    novo_status = update_data.get("status", contrato.status)
    novo_valor_diaria = update_data.get("valor_diaria", contrato.valor_diaria)

    nova_data_fim = resolver_data_fim(
        nova_data_inicio,
        nova_data_fim,
        tipo=update_data.get("tipo", contrato.tipo),
        vigencia_indeterminada=bool(vigencia_indeterminada),
    )
    update_data["data_fim"] = nova_data_fim
    if nova_data_fim:
        validar_datas(nova_data_inicio, nova_data_fim)
    cliente = resolve_cliente_contrato(
        db,
        tipo=update_data.get("tipo", contrato.tipo),
        cliente_id=novo_cliente_id,
        empresa_id=empresa_id,
    )
    update_data["cliente_id"] = cliente.id

    veiculo_destino = None
    if novo_status == "ativo":
        veiculo_destino = ensure_veiculo_available(
            db,
            novo_veiculo_id,
            contrato_id=contrato_id,
        )

    if "veiculo_id" in update_data and "km_inicial" not in update_data and veiculo_destino:
        update_data["km_inicial"] = float(veiculo_destino.km_atual or 0)

    veiculo_antigo_id = contrato.veiculo_id

    for key, value in update_data.items():
        setattr(contrato, key, value)

    if not contrato.qtd_diarias or {"data_inicio", "data_fim", "tipo"} & set(update_data.keys()):
        contrato.qtd_diarias = (
            1
            if str(contrato.tipo or "").lower() == "empresa"
            else calcular_qtd_diarias(nova_data_inicio, nova_data_fim or nova_data_inicio)
        )

    if "valor_total" not in update_data and (
        {
            "data_inicio",
            "data_fim",
            "valor_diaria",
            "km_inicial",
            "km_final",
            "km_livres",
            "valor_km_excedente",
            "valor_avarias",
            "taxa_combustivel",
            "taxa_limpeza",
            "taxa_higienizacao",
            "taxa_pneus",
            "taxa_acessorios",
            "valor_franquia_seguro",
            "taxa_administrativa",
            "desconto",
        }
        & set(update_data.keys())
    ):
        contrato.valor_total = calcular_valor_total(
            nova_data_inicio,
            nova_data_fim or nova_data_inicio,
            float(novo_valor_diaria or 0),
            tipo=contrato.tipo,
            km_inicial=contrato.km_inicial,
            km_final=contrato.km_final,
            km_livres=contrato.km_livres,
            valor_km_excedente=contrato.valor_km_excedente,
            valor_avarias=contrato.valor_avarias,
            taxa_combustivel=contrato.taxa_combustivel,
            taxa_limpeza=contrato.taxa_limpeza,
            taxa_higienizacao=contrato.taxa_higienizacao,
            taxa_pneus=contrato.taxa_pneus,
            taxa_acessorios=contrato.taxa_acessorios,
            valor_franquia_seguro=contrato.valor_franquia_seguro,
            taxa_administrativa=contrato.taxa_administrativa,
            desconto=contrato.desconto,
        )

    apply_payment_details(
        contrato,
        update_data,
        reference_date=contrato.data_finalizacao or contrato.data_fim,
    )

    db.flush()
    sincronizar_uso_empresa(
        db,
        contrato,
        cliente,
        empresa_uso_id=empresa_uso_id,
        encerrar=contrato.status != "ativo",
    )
    recalcular_status_veiculo(db, veiculo_antigo_id)
    recalcular_status_veiculo(db, contrato.veiculo_id)

    db.commit()
    db.refresh(contrato)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Contrato {} editado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.post("/{contrato_id}/encerrar", response_model=ContratoResponse)
@router.post("/{contrato_id}/finalizar", response_model=ContratoResponse)
def finalizar_contrato(
    contrato_id: int,
    payload: Optional[ContratoFinalizeRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Finalize a contract and register the vehicle return."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    if contrato.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Somente contratos ativos podem ser encerrados",
        )

    veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veiculo nao encontrado",
        )

    finalize_data = normalize_finalizacao_payload(
        (payload or ContratoFinalizeRequest()).model_dump(exclude_unset=True)
    )
    data_finalizacao = finalize_data.get("data_finalizacao") or datetime.now()
    km_final = finalize_data.get("km_final")
    checklist_retorno = finalize_data.get("itens_checklist")

    if isinstance(checklist_retorno, dict):
        checklist_retorno = {
            str(chave): bool(valor)
            for chave, valor in checklist_retorno.items()
        }
    else:
        checklist_retorno = None

    if km_final is not None and contrato.km_inicial is not None and float(km_final) < float(contrato.km_inicial):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KM atual nao pode ser menor que o KM de retirada",
        )

    if km_final is not None:
        contrato.km_final = float(km_final)
        veiculo.km_atual = float(km_final)

    if "combustivel_retorno" in finalize_data:
        contrato.combustivel_retorno = finalize_data.get("combustivel_retorno")
    if "valor_avarias" in finalize_data:
        contrato.valor_avarias = finalize_data.get("valor_avarias")
    if "taxa_combustivel" in finalize_data:
        contrato.taxa_combustivel = finalize_data.get("taxa_combustivel")
    if "taxa_limpeza" in finalize_data:
        contrato.taxa_limpeza = finalize_data.get("taxa_limpeza")
    if "taxa_higienizacao" in finalize_data:
        contrato.taxa_higienizacao = finalize_data.get("taxa_higienizacao")
    if "taxa_pneus" in finalize_data:
        contrato.taxa_pneus = finalize_data.get("taxa_pneus")
    if "taxa_acessorios" in finalize_data:
        contrato.taxa_acessorios = finalize_data.get("taxa_acessorios")
    if "valor_franquia_seguro" in finalize_data:
        contrato.valor_franquia_seguro = finalize_data.get("valor_franquia_seguro")
    if "taxa_administrativa" in finalize_data:
        contrato.taxa_administrativa = finalize_data.get("taxa_administrativa")
    if "desconto" in finalize_data:
        contrato.desconto = finalize_data.get("desconto")
    if finalize_data.get("observacoes"):
        contrato.observacoes = append_observacao(
            contrato.observacoes,
            finalize_data.get("observacoes"),
            "Encerramento",
        )

    data_base_cobranca = max(contrato.data_fim, data_finalizacao)
    contrato.qtd_diarias = (
        1
        if str(contrato.tipo or "").lower() == "empresa"
        else calcular_qtd_diarias(contrato.data_inicio, data_base_cobranca)
    )
    # For empresa: valor_total = sum of all NF periods + extra fees
    if str(contrato.tipo or "").lower() == "empresa":
        from app.models import RelatorioNF as _FinalNF
        nf_total = sum(
            float(nf.valor_total_periodo or 0)
            for nf in db.query(_FinalNF).filter(_FinalNF.veiculo_id == contrato.veiculo_id).all()
        )
        taxas = sum(float(v or 0) for v in [
            finalize_data.get("valor_avarias"), finalize_data.get("taxa_combustivel"),
            finalize_data.get("taxa_limpeza"), finalize_data.get("taxa_higienizacao"),
            finalize_data.get("taxa_pneus"), finalize_data.get("taxa_acessorios"),
            finalize_data.get("valor_franquia_seguro"), finalize_data.get("taxa_administrativa"),
        ])
        desconto = float(finalize_data.get("desconto") or 0)
        contrato.valor_total = round(max(nf_total + taxas - desconto, 0), 2)
    else:
        contrato.valor_total = calcular_valor_total(
            contrato.data_inicio,
            data_base_cobranca,
            float(contrato.valor_diaria or 0),
            tipo=contrato.tipo,
            km_inicial=contrato.km_inicial,
            km_final=contrato.km_final,
            km_livres=contrato.km_livres,
            valor_km_excedente=contrato.valor_km_excedente,
            valor_avarias=contrato.valor_avarias,
            taxa_combustivel=contrato.taxa_combustivel,
            taxa_limpeza=contrato.taxa_limpeza,
            taxa_higienizacao=contrato.taxa_higienizacao,
            taxa_pneus=contrato.taxa_pneus,
            taxa_acessorios=contrato.taxa_acessorios,
            valor_franquia_seguro=contrato.valor_franquia_seguro,
        taxa_administrativa=contrato.taxa_administrativa,
        desconto=contrato.desconto,
    )
    contrato.status = "finalizado"
    contrato.data_finalizacao = data_finalizacao
    apply_payment_details(contrato, finalize_data, reference_date=data_finalizacao)

    db.flush()
    db.add(
        CheckinCheckout(
            contrato_id=contrato.id,
            tipo="devolucao",
            data_hora=data_finalizacao,
            km=contrato.km_final if contrato.km_final is not None else veiculo.km_atual,
            nivel_combustivel=contrato.combustivel_retorno,
            itens_checklist=checklist_retorno or veiculo.checklist or {},
            avarias=finalize_data.get("observacoes"),
        )
    )
    cliente = ensure_cliente_exists(db, contrato.cliente_id)
    sincronizar_uso_empresa(db, contrato, cliente, encerrar=True)
    recalcular_status_veiculo(db, contrato.veiculo_id)

    db.commit()
    db.refresh(contrato)
    invalidate_dashboard_cache()
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Contrato {} finalizado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.patch("/{contrato_id}/pagamento", response_model=ContratoResponse)
def atualizar_pagamento_contrato(
    contrato_id: int,
    pagamento_data: ContratoPaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    update_data = normalize_contrato_payload(
        pagamento_data.model_dump(exclude_unset=True)
    )
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum dado de pagamento informado",
        )

    apply_payment_details(
        contrato,
        update_data,
        reference_date=contrato.data_finalizacao or contrato.data_fim or datetime.now(),
    )

    db.commit()
    db.refresh(contrato)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Pagamento do contrato {} atualizado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.post("/{contrato_id}/prorrogar", response_model=ContratoResponse)
def prorrogar_contrato(
    contrato_id: int,
    data_nova: datetime,
    motivo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Extend a contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    if contrato.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Somente contratos ativos podem ser prorrogados",
        )

    if data_nova <= contrato.data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nova data deve ser posterior a data de fim atual",
        )

    prorrogacao = ProrrogacaoContrato(
        contrato_id=contrato_id,
        data_anterior=contrato.data_fim,
        data_nova=data_nova,
        motivo=motivo,
    )
    db.add(prorrogacao)

    contrato.data_fim = data_nova
    contrato.qtd_diarias = (
        1
        if str(contrato.tipo or "").lower() == "empresa"
        else calcular_qtd_diarias(contrato.data_inicio, data_nova)
    )
    if contrato.valor_diaria:
        contrato.valor_total = calcular_valor_total(
            contrato.data_inicio,
            data_nova,
            float(contrato.valor_diaria),
            tipo=contrato.tipo,
            km_inicial=contrato.km_inicial,
            km_final=contrato.km_final,
            km_livres=contrato.km_livres,
            valor_km_excedente=contrato.valor_km_excedente,
            valor_avarias=contrato.valor_avarias,
            taxa_combustivel=contrato.taxa_combustivel,
            taxa_limpeza=contrato.taxa_limpeza,
            taxa_higienizacao=contrato.taxa_higienizacao,
            taxa_pneus=contrato.taxa_pneus,
            taxa_acessorios=contrato.taxa_acessorios,
            valor_franquia_seguro=contrato.valor_franquia_seguro,
            taxa_administrativa=contrato.taxa_administrativa,
            desconto=contrato.desconto,
        )

    db.commit()
    db.refresh(contrato)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Contrato {} prorrogado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.get("/{contrato_id}/pdf")
def get_contrato_pdf(
    contrato_id: int,
    veiculo_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download contract PDF."""
    del current_user
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    # If veiculo_id is provided for a company contract, use that vehicle for the PDF
    target_veiculo_id = veiculo_id if veiculo_id else contrato.veiculo_id
    
    pdf_buffer = PDFService.generate_contrato_pdf(db, contrato_id, veiculo_id=target_veiculo_id)
    pdf_buffer.seek(0)
    
    # Include vehicle info in filename if different from contract's main vehicle
    filename_suffix = ""
    if veiculo_id and veiculo_id != contrato.veiculo_id:
        veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
        if veiculo:
            filename_suffix = f"_{veiculo.placa}"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="contrato_{}{}.pdf"'.format(
                contrato.numero, filename_suffix
            )
        },
    )


@router.get("/{contrato_id}/despesas", response_model=List[DespesaContratoResponse])
def get_contrato_despesas(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get expenses for a contract."""
    del current_user
    despesas = db.query(DespesaContrato).filter(
        DespesaContrato.contrato_id == contrato_id
    ).all()
    return despesas


@router.post("/{contrato_id}/despesas")
def add_contrato_despesa(
    contrato_id: int,
    tipo: str,
    descricao: str,
    valor: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Add expense to a contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    despesa = DespesaContrato(
        contrato_id=contrato_id,
        tipo=tipo,
        descricao=descricao,
        valor=valor,
        responsavel=current_user.email,
    )
    db.add(despesa)
    db.commit()
    db.refresh(despesa)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "DespesaContrato",
        "Despesa de contrato criada: {}".format(descricao),
        despesa.id,
        request,
    )
    return despesa


@router.delete("/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a contract without relying on DB cascades."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    numero = contrato.numero
    veiculo_id = contrato.veiculo_id

    db.query(Quilometragem).filter(
        Quilometragem.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(DespesaContrato).filter(
        DespesaContrato.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(ProrrogacaoContrato).filter(
        ProrrogacaoContrato.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(CheckinCheckout).filter(
        CheckinCheckout.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(UsoVeiculoEmpresa).filter(
        UsoVeiculoEmpresa.contrato_id == contrato_id
    ).update({UsoVeiculoEmpresa.contrato_id: None}, synchronize_session=False)
    db.query(Multa).filter(
        Multa.contrato_id == contrato_id
    ).delete(synchronize_session=False)

    db.delete(contrato)
    db.flush()
    recalcular_status_veiculo(db, veiculo_id)

    db.commit()
    invalidate_dashboard_cache()
    log_activity(
        db,
        current_user,
        "EXCLUIR",
        "Contrato",
        "Contrato {} excluido".format(numero),
        contrato_id,
        request,
    )
