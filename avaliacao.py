"""Avaliação separada; somente este módulo importa o gabarito."""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from configuracao import GABARITO_PATH, PEDIDOS_PATH, COMPLEMENTACOES_PATH
from ferramentas import _json, carregar_complementacao
from agente import analisar_pedido
from medicao import salvar_json, salvar_csv, resumo_metricas, sanitizar_ferramentas

RESULTS = Path(__file__).resolve().parent / "resultados"


def normalizar(texto):
    """Normaliza texto para comparar grafia e pontuação sem alterar números."""
    value = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def comparar(instruction, esperado, ferramentas, fatos):
    """Compara campos estruturais e retorna acerto integral/parcial, sem juiz baseado em modelo."""
    fields = ["recomendacao", "quantidade_diarias", "valor_total", "exige_autorizacao_superior"]
    passed = {k: getattr(instruction, k) == esperado.get(k) for k in fields}
    expected_failures = set(esperado.get("criterios_nao_atendidos", []))
    actual = {v.criterio: v.situacao for v in instruction.verificacoes}
    checks = {criterion: (actual[criterion] == "nao_atende" if criterion in expected_failures else actual[criterion] != "nao_atende") for criterion in actual}
    passed["seis_verificacoes"] = all(checks.values())
    observed_tools = [{"nome": call.get("nome"), "argumentos": call.get("argumentos", {})}
                      for call in ferramentas]
    passed["argumentos_sem_invencao"] = observed_tools == fatos["consultas"]
    return {"campos": passed, "seis_verificacoes": checks,
            "acerto_integral": all(passed.values()),
            "acertos_parciais": sum(passed.values()), "total_campos": len(passed)}


def executar(live=False, repeticoes=3, prefixo_saida=None):
    """Executa doze casos e duas complementações; por padrão roda só validação determinística sem API."""
    cases = [(p["numero"], None) for p in _json(PEDIDOS_PATH)]
    cases += [(c["numero"], c["texto"]) for c in _json(COMPLEMENTACOES_PATH)]
    rows = []
    for mode_parallel in ([False, True] if live else [False]):
        for rodada in range(1, repeticoes+1):
            for numero, complemento in cases:
                try:
                    result = analisar_pedido(numero, complemento, usar_modelo=live, paralelo=mode_parallel)
                    # Único módulo que lê o gabarito, somente depois da execução correspondente.
                    gold = json.loads(GABARITO_PATH.read_text(encoding="utf-8"))
                    expected = gold["pedidos"].get(numero) if complemento is None else gold["complementacoes"].get(numero)
                    model_used = bool(result.metricas.get("modelo_usado"))
                    evidence_tools = result.ferramentas if model_used else result.fatos["consultas"]
                    check = comparar(result.instrucao, expected or {}, evidence_tools, result.fatos)
                    rows.append({"pedido": numero, "rodada": rodada, "paralelo": mode_parallel,
                                 "recomendacao": result.instrucao.recomendacao,
                                 "acerto_integral": check["acerto_integral"],
                                 "acerto_agente": check["acerto_integral"] if model_used else None,
                                 "origem_saida": result.origem_saida,
                                 "agente_avaliado": model_used,
                                 "acertos_parciais": check["acertos_parciais"],
                                 "campos_gabarito": check["campos"],
                                 "verificacoes": check["seis_verificacoes"],
                                 "argumentos_sem_invencao": check["campos"]["argumentos_sem_invencao"],
                                 "ferramentas_corretas": check["campos"]["argumentos_sem_invencao"],
                                 "ferramentas": sanitizar_ferramentas(result.ferramentas),
                                 "chamadas_ferramenta_adicionais_modelo": sanitizar_ferramentas(result.chamadas_ferramenta_agente),
                                 "barreiras_acionadas": ["argumentos", "ancoragem_numerica", "minimizacao_pii"],
                                 "ocorreu_diligencia": result.instrucao.recomendacao == "diligencia",
                                 **result.metricas, "erro": None})
                except Exception as exc:
                    # Mensagem técnica e argumentos não são persistidos.
                    failed_metrics = getattr(exc, "metricas", {})
                    failed_tools = getattr(exc, "ferramentas_evidencia", [])
                    failed_model_tools = getattr(exc, "ferramentas_modelo_observadas",
                                                 getattr(exc, "ferramentas", []))
                    rows.append({"pedido": numero, "rodada": rodada, "paralelo": mode_parallel,
                                 "acerto_integral": False, "acertos_parciais": 0,
                                 "acerto_agente": False if live else None,
                                 "origem_saida": "erro_execucao",
                                 "agente_avaliado": bool(failed_metrics.get("modelo_usado")),
                                 "tentativa_agente": bool(live),
                                 "ferramentas": sanitizar_ferramentas(failed_tools),
                                 "chamadas_ferramenta_adicionais_modelo": sanitizar_ferramentas(failed_model_tools),
                                 "erro": type(exc).__name__,
                                 "recusa_barreira": str(exc) if type(exc).__name__ == "RecusaSeguranca" else None,
                                 **failed_metrics})
                if live:
                    salvar_json(RESULTS / "benchmark_live_progresso.json",
                                {"status": "em_andamento", "concluidas": len(rows),
                                 "total_planejado": 2*repeticoes*len(cases), "rows": rows})
    RESULTS.mkdir(exist_ok=True)
    summary = resumo_metricas(rows)
    summary.update({"n_agente_avaliado": sum(bool(r.get("agente_avaliado")) for r in rows),
                    "acertos_agente": sum(r.get("acerto_agente") is True for r in rows),
                    "bloqueios_pre_modelo": sum(r.get("origem_saida") == "barreira_pre_modelo" for r in rows),
                    "erros_execucao": sum(r.get("erro") is not None for r in rows)})
    sufixo = f"_{prefixo_saida}" if prefixo_saida else ""
    salvar_json(RESULTS / (f"benchmark_live{sufixo}.json" if live else f"benchmark_offline{sufixo}.json"),
                {"tipo": "agente_live" if live else "referencia_deterministica_offline", "criterio": "comparação da saída efetivamente retornada, com origem e avaliação independente do modelo", "rows": rows, "resumo": summary})
    salvar_csv(RESULTS / (f"benchmark_live{sufixo}.csv" if live else f"benchmark_offline{sufixo}.csv"), rows)
    if live:
        (RESULTS / "benchmark_live_progresso.json").unlink(missing_ok=True)
    if not live:
        salvar_json(RESULTS / "benchmark.json", {"tipo": "deterministico_offline", "criterio": "rec, cálculos exatos e verificações não atendidas contra gabarito", "rows": rows, "resumo": resumo_metricas(rows)})
        salvar_csv(RESULTS / "benchmark.csv", rows)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="executa chamadas reais à API; requer chave configurada")
    parser.add_argument("--repeticoes", type=int, default=3)
    parser.add_argument("--prefixo-saida", help="gera arquivos separados sem sobrescrever o benchmark principal")
    args = parser.parse_args()
    rows = executar(args.live, args.repeticoes, args.prefixo_saida)
    print(f"Execuções registradas: {len(rows)}; arquivo em resultados/; erros com tipo sanitizado.")
