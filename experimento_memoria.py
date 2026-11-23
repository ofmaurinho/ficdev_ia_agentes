"""Mede se a sessão Agno recupera diligências sem reenviar o pedido após o primeiro turno."""
import argparse
from pathlib import Path

from configuracao import OPENAI_API_KEY, PROJECT_ROOT
from agente import _agente, analisar_pedido
from ferramentas import carregar_complementacao
from memoria import criar_banco, eliminar_dados
from medicao import salvar_json, mascarar_identificador
from barreiras import RecusaSeguranca

RESULTS = PROJECT_ROOT / "resultados"
CASES = ("DIA-2026-0111", "DIA-2026-0112")
CONFIGS = (("sem_memoria", False, False),
           ("historico_limitado", True, False),
           ("historico_e_memoria_usuario", True, True))


def executar():
    """Executa pares de turnos em três modos; só o caso sem contexto corrigido recebe pedido+complemento."""
    if not OPENAI_API_KEY:
        raise RuntimeError("Medição live não executada: OPENAI_API_KEY não está definida.")
    rows = []
    cleanup = []
    for name, use_db, user_memory in CONFIGS:
        path = RESULTS / f"memoria_{name}.sqlite"
        db = criar_banco(path) if use_db else None
        agent = _agente(db=db, paralelo=False, memoria_usuario=user_memory)
        try:
            for case in CASES:
                complement = carregar_complementacao(case) or ""
                first = second = None
                first_metrics = second_metrics = {}
                first_error = second_error = None
                try:
                    first = analisar_pedido(case, usar_modelo=True, agent=agent)
                    first_metrics = first.metricas
                except Exception as exc:
                    first_error = exc
                    first_metrics = getattr(exc, "metricas", {})
                if first_error and not getattr(first_error, "resposta_agente", None):
                    rows.append(_pair_row(name, case, first, first_metrics, None, {},
                                          "primeiro_turno_sem_resposta", first_error, None))
                    continue
                if first is not None and not first.metricas.get("modelo_usado"):
                    # Em 0112, a identidade inicial divergente bloqueia o modelo; a correção
                    # envia o pedido junto e não é contabilizada como recuperação de histórico.
                    stage = "complemento_com_identidade_corrigida"
                    only_complement = False
                else:
                    # O segundo turno omite o pedido: a recuperação contextual é medida
                    # separadamente da aceitação da síntese e da barreira.
                    stage = "recuperacao_so_complemento"
                    only_complement = True
                try:
                    second = analisar_pedido(case, complement, usar_modelo=True, agent=agent,
                        prompt_complementacao_apenas=only_complement)
                    second_metrics = second.metricas
                except Exception as exc:
                    second_error = exc
                    second_metrics = getattr(exc, "metricas", {})
                rows.append(_pair_row(name, case, first, first_metrics, second, second_metrics,
                                      stage, first_error, second_error))
        finally:
            if db is not None:
                try:
                    db.db_engine.dispose()
                except Exception:
                    pass
        if use_db:
            # Limpeza verificável antes de remover os bancos temporários do ensaio.
            outcomes = [eliminar_dados(case, caminho=path) for case in CASES]
            cleanup.append({"banco": name, "sucesso": all(x["sucesso"] for x in outcomes),
                            "residuos": any(bool(x["tabelas_com_residuos"]) for x in outcomes),
                            "erros": sum(len(x["erros"]) for x in outcomes),
                            "tabelas_inspecionadas": sorted({table for x in outcomes for table in
                                set(x["contagens_antes"]) | set(x["contagens_depois"]) | set(x["tabelas_com_residuos"])}),
                            "linhas_antes": {table: sum(x["contagens_antes"].get(table, 0) for x in outcomes)
                                for table in sorted({table for x in outcomes for table in x["contagens_antes"]})},
                            "linhas_depois": {table: sum(x["contagens_depois"].get(table, 0) for x in outcomes)
                                for table in sorted({table for x in outcomes for table in x["contagens_depois"]})}})
            if path.exists() and all(x["sucesso"] for x in outcomes):
                path.unlink()
    salvar_json(RESULTS / "memoria.json", {"status": "executado_live_contexto_separado_da_validacao",
        "configs": rows, "limpeza_bancos": cleanup})
    return rows


def _pair_row(name, case, first, m1, second, m2, stage, first_error, second_error):
    second_result = second is not None
    first_model_used = bool(m1.get("modelo_usado"))
    first_blocked_pre_model = first is not None and not first_model_used
    first_status = ("bloqueado_antes_do_modelo" if first_blocked_pre_model else
                    "saida_validada" if first is not None and first_model_used else
                    "falha_sem_saida")
    first_zero_if_blocked = lambda key: (0 if first_blocked_pre_model else m1.get(key))
    first_cost = first_zero_if_blocked("custo_usd")
    history_status = ("nao_aplicavel_pedido_reenviado_com_identidade_corrigida"
                      if stage == "complemento_com_identidade_corrigida" else
                      "recuperado" if m2.get("historico_sessao_recuperou_id_caso") else
                      "nao_recuperado")
    observed_tools = []
    response = getattr(second_error, "resposta_agente", None) if second_error else None
    for call in (getattr(response, "tools", None) or []):
        observed_tools.append({
            "nome": getattr(call, "tool_name", None),
            "erro": bool(getattr(call, "tool_call_error", False)),
        })
    rejected_tools = [item.get("nome") for item in getattr(second_error, "ferramentas", [])
                      if item.get("resultado") in {"recusada", "falha"}] if second_error else []
    return {"caso": mascarar_identificador(case), "configuracao": name,
        "etapa_complementacao": stage,
        "primeiro_turno_status": first_status,
        "primeiro_turno_motivo": ("identidade divergente bloqueada antes do modelo"
            if first_blocked_pre_model else None),
        "primeiro_turno_modelo_usado": first_model_used,
        "primeiro_turno_saida_validada": first is not None and first_model_used,
        "primeiro_turno_erro": type(first_error).__name__ if first_error else None,
        "primeiro_turno_barreira": str(first_error) if isinstance(first_error, RecusaSeguranca) else None,
        "primeiro_turno_tokens_entrada": first_zero_if_blocked("tokens_entrada"),
        "primeiro_turno_tokens_saida": first_zero_if_blocked("tokens_saida"),
        "primeiro_turno_chamadas_modelo": first_zero_if_blocked("chamadas_modelo"),
        "primeiro_turno_custo_usd": first_cost,
        "complementacao_saida_validada": second_result,
        "complementacao_erro": type(second_error).__name__ if second_error else None,
        "complementacao_barreira": str(second_error) if isinstance(second_error, RecusaSeguranca) else None,
        "complementacao_ferramentas_observadas": observed_tools,
        "complementacao_ferramentas_recusadas": rejected_tools,
        "complementacao_tokens_entrada": m2.get("tokens_entrada"),
        "complementacao_tokens_saida": m2.get("tokens_saida"),
        "complementacao_chamadas_modelo": m2.get("chamadas_modelo"),
        "complementacao_custo_usd": m2.get("custo_usd"),
        "custo_total_usd": _sum_cost(first_cost, m2.get("custo_usd")),
        "id_caso_recuperado_de_historico": (m2.get("historico_sessao_recuperou_id_caso")
            if stage == "recuperacao_so_complemento" else None),
        "recuperacao_historico_status": history_status,
        "recuperou_caso": bool(second_result and second.instrucao.numero_pedido == case),
        "aplicou_complementacao": bool(second_result and second.fatos.get("complementacao_aplicada") and
                                        second.fatos.get("dados_completos") and
                                        second.instrucao.recomendacao != "diligencia"),
        "modelo_usado_no_segundo_turno": bool(m2.get("modelo_usado")),
        "session_id_mascarado": mascarar_identificador(case),
        "user_id_mascarado": mascarar_identificador(second.user_id if second else (first.user_id if first else None)),
        "status": "medido"}


def _sum_cost(a, b):
    return a+b if isinstance(a, (float, int)) and isinstance(b, (float, int)) else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", required=True)
    parser.parse_args()
    try:
        result = executar()
        print(f"Medições registradas: {len(result)}")
    except Exception as exc:
        print(f"Medição não concluída: {type(exc).__name__}. Verifique chave e configuração local.")
