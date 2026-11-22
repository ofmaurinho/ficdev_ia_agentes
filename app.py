"""Interface de conferência humana para instruções de diárias."""
import json
from datetime import datetime, timezone
import streamlit as st
from configuracao import PEDIDOS_PATH, DB_PATH
from ferramentas import _json, mascarar_pii
from agente import analisar_pedido, _agente, AGNO_IMPORT_ERROR
from memoria import criar_banco, eliminar_dados, expurgar_expiradas
from medicao import sanitizar_ferramentas

PADRAO_ERRO = "Não foi possível concluir a instrução automatizada com segurança. Encaminhe este pedido para análise manual."


@st.cache_resource
def recursos():
    """Cria o banco uma vez por processo e expurga registros vencidos antes do uso."""
    db = criar_banco()
    result = expurgar_expiradas()
    if not result["sucesso"]:
        db.db_engine.dispose()
        raise RuntimeError("A verificação de retenção não foi concluída")
    return db


def registrar_conferencia(registro, caminho=None):
    """Persiste decisão humana, justificativa e minuta editada após mascarar dados pessoais conhecidos."""
    path = __import__("pathlib").Path(caminho) if caminho else (__import__("pathlib").Path(__file__).resolve().parent / "resultados" / "conferencias.jsonl")
    path.parent.mkdir(exist_ok=True)
    registro["justificativa_divergencia"] = mascarar_pii(registro.get("justificativa_divergencia", ""))
    registro["minuta_final"] = mascarar_pii(registro.get("minuta_final", ""))
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def main():
    st.set_page_config(page_title="Instrução de diárias", layout="wide")
    st.title("Instrução de pedidos de diárias")
    st.warning("O agente apenas prepara uma instrução. Não defere, indefere ou autoriza despesa. A decisão final é do ordenador de despesa.")
    st.warning("O registro local será salvo em resultados/conferencias.jsonl. O prazo de guarda e a rotina autorizada de exclusão ainda dependem de política institucional; use somente o acervo hipotético até essa definição. A aba Eliminar memória remove somente dados do SQLite do agente.")
    try:
        recursos()
    except Exception:
        st.error(PADRAO_ERRO)
        st.stop()
    tabs = st.tabs(["Analisar pedido", "Complementar diligência", "Eliminar memória"])
    pedidos = _json(PEDIDOS_PATH)
    labels = {p["numero"]: p for p in pedidos}
    with tabs[0]:
        numero = st.selectbox("Número do pedido", list(labels))
        p = labels[numero]
        display = {k: v for k, v in p.items() if k not in {"nome", "justificativa"}}
        display["justificativa"] = mascarar_pii(p["justificativa"])
        st.json(display)
        st.text_area("Justificativa protocolada (dados pessoais mascarados)", display["justificativa"], disabled=True, height=100)
        if st.button("Analisar", type="primary"):
            st.session_state.pop("resultado", None)
            st.session_state.pop("minuta_" + numero, None)
            try:
                with st.status("Preparando a análise…", expanded=True) as status:
                    result = analisar_pedido(numero, usar_modelo=True, agent=_agente(db=recursos()),
                                             on_stage=lambda state, step: _atualizar_progresso(status, state, step))
                    status.update(label="Instrução validada", state="complete")
                st.session_state.resultado = result
                if result.metricas.get("modelo_usado"):
                    sessions = set(st.session_state.get("casos_com_sessao_de_modelo", []))
                    sessions.add(numero)
                    st.session_state["casos_com_sessao_de_modelo"] = sorted(sessions)
            except Exception:
                st.session_state.pop("resultado", None)
                st.error(PADRAO_ERRO)
        if st.session_state.get("resultado") and st.session_state.resultado.instrucao.numero_pedido == numero:
            _mostrar(st.session_state.resultado)
    with tabs[1]:
        numero_c = st.selectbox("Pedido em diligência", ["DIA-2026-0111", "DIA-2026-0112"])
        comp = st.text_area("Complementação recebida")
        if st.button("Processar na mesma sessão"):
            st.session_state.pop("resultado_comp", None)
            st.session_state.pop("minuta_" + numero_c, None)
            try:
                with st.status("Preparando a diligência…", expanded=True) as status:
                    previous_model_session = numero_c in st.session_state.get("casos_com_sessao_de_modelo", [])
                    result = analisar_pedido(numero_c, comp, usar_modelo=True, agent=_agente(db=recursos()),
                                             on_stage=lambda state, step: _atualizar_progresso(status, state, step),
                                             prompt_complementacao_apenas=previous_model_session)
                    status.update(label="Complementação validada", state="complete")
                st.session_state.resultado_comp = result
                if result.metricas.get("modelo_usado"):
                    sessions = set(st.session_state.get("casos_com_sessao_de_modelo", []))
                    sessions.add(numero_c)
                    st.session_state["casos_com_sessao_de_modelo"] = sorted(sessions)
            except Exception:
                st.session_state.pop("resultado_comp", None)
                st.error(PADRAO_ERRO)
        if (st.session_state.get("resultado_comp") and
                st.session_state.resultado_comp.instrucao.numero_pedido == numero_c):
            _mostrar(st.session_state.resultado_comp)
    with tabs[2]:
        caso = st.text_input("Identificador do pedido para eliminação")
        if st.button("Eliminar dados de trabalho", type="secondary"):
            try:
                result = eliminar_dados(caso)
                if result["sucesso"]:
                    st.success("Verificação concluída: não restaram registros identificáveis nas tabelas inspecionadas.")
                else:
                    st.error("Não foi possível confirmar a eliminação completa. Encaminhe para análise manual.")
                st.json({k: result.get(k) for k in ("contagens_antes", "contagens_depois", "tabelas_com_residuos", "sucesso")})
            except Exception:
                st.error(PADRAO_ERRO)


def _mostrar(result):
    obj = result.instrucao
    if result.origem_saida == "barreira_pre_modelo":
        st.info("A análise do agente não foi executada: a divergência de identidade foi barrada antes da chamada ao modelo. Esta diligência é uma proteção determinística.")
    st.subheader(f"Recomendação: {obj.recomendacao}")
    st.caption(f"Pedido {obj.numero_pedido} · matrícula {obj.matricula}")
    if result.fatos.get("complementacao_aplicada"):
        st.info("Complementação aplicada ao pedido selecionado; identidade e dados atuais foram revalidados nas ferramentas.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Diárias", obj.quantidade_diarias if obj.quantidade_diarias is not None else "—")
    c2.metric("Valor total", f"R$ {obj.valor_total:.2f}" if obj.valor_total is not None else "—")
    c3.metric("Autorização superior", "Exigida" if obj.exige_autorizacao_superior else "Não indicada")
    st.markdown("#### Verificações")
    for check in obj.verificacoes:
        st.write(f"**{check.criterio} · {check.situacao}** — {check.detalhe}")
    if obj.pendencias:
        st.markdown("#### Pendências")
        for item in obj.pendencias: st.write(f"- {item}")
    if obj.alertas:
        st.markdown("#### Alertas")
        for item in obj.alertas: st.write(f"- {item}")
    st.markdown("#### Ferramentas e argumentos")
    tool_evidence = result.ferramentas or (result.fatos["consultas"] if result.origem_saida == "barreira_pre_modelo" else [])
    st.json(sanitizar_ferramentas(tool_evidence))
    st.caption("A minuta editada será incluída no registro local de conferência após o envio.")
    minuta = st.text_area("Minuta editável para conferência", obj.minuta_despacho, key="minuta_"+obj.numero_pedido)
    st.caption("Métricas reais disponíveis: " + json.dumps(result.metricas, ensure_ascii=False))
    st.markdown("#### Registro da conferência humana")
    choices = ["prosseguir_ao_ordenador", "devolver_em_diligencia", "nao_recomendar"]
    encaminhamento = st.selectbox("Encaminhamento decidido pelo servidor", choices, key="dec_"+obj.numero_pedido)
    corresponde = {"apto_para_autorizacao": "prosseguir_ao_ordenador",
                   "diligencia": "devolver_em_diligencia",
                   "nao_recomendado": "nao_recomendar"}[obj.recomendacao]
    diverge = encaminhamento != corresponde
    justificativa = st.text_area("Justificativa obrigatória da divergência", key="just_"+obj.numero_pedido)
    if st.button("Registrar conferência", key="reg_"+obj.numero_pedido):
        if diverge and not justificativa.strip():
            st.error("Informe a justificativa para a divergência.")
        else:
            try:
                registrar_conferencia({"pedido": obj.numero_pedido, "recomendacao_agente": obj.recomendacao,
                    "encaminhamento_servidor": encaminhamento, "concordancia": not diverge,
                    "justificativa_divergencia": justificativa if diverge else "",
                    "minuta_final": minuta,
                    "horario_utc": datetime.now(timezone.utc).isoformat()})
                st.success("Conferência humana registrada.")
            except Exception:
                st.error("Não foi possível registrar a conferência. Encaminhe o pedido para análise manual.")


def _atualizar_progresso(status, state, step):
    labels = {
        "consultar_cadastro_servidor": "Consultando o cadastro funcional…",
        "consultar_historico_diarias": "Consultando o histórico e prestações de contas…",
        "calcular_diarias": "Calculando antecedência, quantidade e valor…",
        "consultar_saldo_diarias": "Conferindo o saldo da unidade…",
        "modelo": "Validando e redigindo a instrução estruturada…",
    }
    if state == "in_progress":
        status.update(label=labels.get(step, "Executando etapa autorizada…"), state="running")
    elif state == "complete":
        status.update(label=labels.get(step, "Etapa concluída"), state="running")


if __name__ == "__main__":
    main()
