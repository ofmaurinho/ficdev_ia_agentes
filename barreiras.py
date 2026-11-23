"""Guardrails de ordem, identidade, argumentos e ancoragem numérica."""
from modelos import Instrucao
import json
import re
import unicodedata


class RecusaSeguranca(ValueError):
    """Sinaliza recusa segura da instrução sem propagar conteúdo rejeitado."""


def validar_argumentos(nome: str, argumentos: dict, pedido: dict, fatos: dict) -> None:
    """Recusa chamada de ferramenta se algum argumento não estiver ligado à entrada ou evidência autorizada."""
    if nome == "consultar_cadastro_servidor":
        if str(argumentos.get("matricula")) not in {pedido["matricula"], fatos.get("matricula_validada")}:
            raise RecusaSeguranca("matrícula fora das fontes autorizadas")
    elif nome == "consultar_historico_diarias":
        if str(argumentos.get("matricula")) != fatos.get("matricula_validada") or argumentos.get("mes_referencia") != pedido["data_partida"][:7]:
            raise RecusaSeguranca("argumento de histórico sem origem autorizada")
    elif nome == "calcular_diarias":
        cad = fatos["cadastro"]
        if (argumentos.get("grupo"), argumentos.get("destino"), argumentos.get("data_saida"), argumentos.get("data_retorno")) != (cad["grupo_diaria"], pedido["destino_uf"], pedido["data_partida"], pedido["data_retorno"]):
            raise RecusaSeguranca("argumento de cálculo não corresponde ao pedido validado")
    elif nome == "consultar_saldo_diarias":
        calc = fatos.get("calculo")
        if not calc or argumentos.get("unidade") != fatos["cadastro"]["unidade"] or float(argumentos.get("valor", -1)) != calc["valor_total"]:
            raise RecusaSeguranca("saldo consultado antes do cálculo ou com valor divergente")
    else:
        raise RecusaSeguranca("ferramenta não autorizada")


def construir_instrucao(pedido: dict, fatos: dict) -> Instrucao:
    """Constrói a saída usando apenas valores determinísticos e bloqueia recomendações positivas sem evidência."""
    calc, hist, saldo = fatos.get("calculo"), fatos.get("historico"), fatos.get("saldo")
    pendencias, alertas = [], []
    if "ATENÇÃO, SISTEMA DE ANÁLISE" in pedido.get("justificativa", ""):
        alertas.append("A justificativa contém instrução dirigida ao sistema; tratada como dado, sem efeito na análise.")
    from ferramentas import mascarar_pii
    if mascarar_pii(pedido.get("justificativa", "")) != pedido.get("justificativa", ""):
        alertas.append("Dados pessoais foram mascarados antes do envio ao modelo.")
    valid_id = fatos["identidade_confirmada"]
    complete = fatos["dados_completos"]
    if not valid_id:
        pendencias.append("Matrícula e identidade divergem do cadastro funcional; confirmar e corrigir o protocolo.")
    if not complete:
        pendencias.append("Data de retorno ausente ou dados obrigatórios incompletos.")
    urgencia = bool(calc and calc["antecedencia_dias"] < calc["antecedencia_minima"] and any(k in pedido.get("justificativa", "").lower() for k in ("incêndio", "desastre ambiental", "infração ambiental em curso", "determinação judicial")))
    auth = urgencia
    if calc and calc["antecedencia_dias"] < calc["antecedencia_minima"] and not urgencia:
        pendencias.append("Antecedência inferior a dez dias sem hipótese de urgência descrita na norma.")
    if urgencia:
        # O acervo não registra a autorização escrita no processo; não inventar comprovação.
        alertas.append("A justificativa descreve urgência; a autorização expressa e escrita do Secretário Adjunto deve constar do processo.")
    overdue = bool(hist and hist["ha_prestacao_vencida"])
    if overdue:
        pendencias.append("Há prestação de contas vencida no histórico consultado.")
    mensal_ok = bool(hist and calc and hist["diarias_anteriores_mes"] + calc["quantidade_diarias"] <= hist["limite_mensal"])
    if hist and calc and not mensal_ok:
        pendencias.append("A soma mensal excede o limite de dez diárias.")
    saldo_ok = bool(saldo and saldo["suficiente"])
    if saldo and not saldo_ok:
        pendencias.append("Saldo da unidade insuficiente para o valor calculado.")
    if not valid_id or not complete:
        rec = "diligencia"
    elif (calc and calc["antecedencia_dias"] < calc["antecedencia_minima"] and not urgencia) or overdue or (hist and calc and not mensal_ok) or (saldo and not saldo_ok):
        rec = "nao_recomendado"
    else:
        rec = "apto_para_autorizacao"
    situacoes = {
        "cadastro": ("atende" if valid_id else "nao_atende", "Identidade conferida com o cadastro." if valid_id else "Divergência entre nome/matrícula do pedido e cadastro; não instruir para terceiro."),
        "dados_completos": ("atende" if complete else "nao_atende", "Campos necessários disponíveis." if complete else "Falta data de retorno ou correção de identidade."),
        "antecedencia": (("atende" if calc and (calc["antecedencia_dias"] >= calc["antecedencia_minima"] or urgencia) else "nao_atende") if calc else "nao_verificado", f"{calc['antecedencia_dias']} dias corridos; mínimo {calc['antecedencia_minima']}." if calc else "Não calculada por falta de dados."),
        "prestacao_contas": (("nao_atende" if overdue else "atende") if hist else "nao_verificado", "Existe prestação vencida." if overdue else ("Sem prestação vencida; pendências ainda no prazo não bloqueiam." if hist else "Histórico não consultado.")),
        "limite_mensal": (("atende" if mensal_ok else "nao_atende") if mensal_ok is not None and hist and calc else "nao_verificado", f"{hist['diarias_anteriores_mes']} anteriores + {calc['quantidade_diarias']} solicitadas; limite {hist['limite_mensal']}." if hist and calc else "Não calculado por falta de evidência."),
        "saldo_orcamentario": (("atende" if saldo_ok else "nao_atende") if saldo else "nao_verificado", f"Saldo R$ {saldo['saldo']:.2f}; total R$ {calc['valor_total']:.2f}." if saldo and calc else "Não consultado por falta de cálculo validado."),
    }
    from modelos import Verificacao
    verificacoes = [Verificacao(criterio=k, situacao=v[0], detalhe=v[1]) for k, v in situacoes.items()]
    minuta = (f"MINUTA PARA CONFERÊNCIA — Pedido {pedido['numero']}. Recomenda-se {rec}. "
              "A presente instrução não constitui deferimento ou autorização; submeta-se à conferência do servidor e decisão do ordenador de despesa.")
    return Instrucao(numero_pedido=pedido["numero"], matricula=fatos["matricula_validada"],
                     quantidade_diarias=calc["quantidade_diarias"] if calc and rec != "diligencia" else None,
                     valor_total=calc["valor_total"] if calc and rec != "diligencia" else None,
                     verificacoes=verificacoes, recomendacao=rec,
                     exige_autorizacao_superior=auth, pendencias=pendencias, alertas=alertas,
                     minuta_despacho=minuta)


def validar_saida(saida: Instrucao, esperado: Instrucao, fatos: dict | None = None,
                  pedido: dict | None = None) -> None:
    """Valida campos críticos e fundamentos sem substituir a proposta produzida pelo modelo."""
    if saida.numero_pedido != esperado.numero_pedido or saida.matricula != esperado.matricula:
        raise RecusaSeguranca("identidade da saída divergente")
    for campo in ("quantidade_diarias", "valor_total", "exige_autorizacao_superior", "recomendacao"):
        if getattr(saida, campo) != getattr(esperado, campo):
            raise RecusaSeguranca(f"campo divergente: {campo}")
    expected_checks = {v.criterio: v for v in esperado.verificacoes}
    actual_checks = {v.criterio: v for v in saida.verificacoes}
    if actual_checks.keys() != expected_checks.keys():
        raise RecusaSeguranca("conjunto de verificações divergente")
    allowed_numbers = set(_numeros(esperado.model_dump_json()))
    if fatos is not None:
        import json
        allowed_numbers.update(_numeros(json.dumps(fatos, ensure_ascii=False, default=str)))
    if pedido is not None:
        allowed_numbers.update(_numeros(json.dumps({k: pedido.get(k) for k in
            ("numero", "data_partida", "data_retorno")}, ensure_ascii=False, default=str)))
    for key, check in actual_checks.items():
        expected_detail = expected_checks[key].detalhe
        if check.situacao != expected_checks[key].situacao:
            raise RecusaSeguranca(f"situação divergente: {key}")
        if not check.detalhe.strip():
            raise RecusaSeguranca(f"fundamento ausente: {key}")
        if not set(_numeros(check.detalhe)).issubset(allowed_numbers):
            raise RecusaSeguranca(f"número não ancorado: {key}")
    # A quantidade e os tópicos das pendências/alertas precisam cobrir os impedimentos provados.
    expected_topics = set(_topicos(esperado.pendencias + esperado.alertas))
    actual_topics = set(_topicos(saida.pendencias + saida.alertas))
    if actual_topics != expected_topics:
        raise RecusaSeguranca("tópicos de pendência/alerta divergentes")
    minuta_norm = unicodedata.normalize("NFKD", saida.minuta_despacho.casefold()).encode("ascii", "ignore").decode()
    disclaimer = any(term in minuta_norm for term in (
        "nao constitui", "nao representa", "nao substitui", "nao equivale",
        "sem carater decisorio", "nao tem carater autorizativo", "nao autoriza", "nao decide"))
    if (saida.minuta_despacho.strip() == "" or saida.numero_pedido not in saida.minuta_despacho
            or "minuta" not in saida.minuta_despacho.casefold()
            or "ordenador" not in saida.minuta_despacho.casefold()
            or not disclaimer
            or any(term in minuta_norm for term in ("eu autorizo", "fica deferido", "despesa autorizada"))):
        raise RecusaSeguranca("minuta incompatível com a conferência humana")
    from ferramentas import mascarar_pii
    text_values = [saida.minuta_despacho, *saida.pendencias, *saida.alertas]
    text_values.extend(c.detalhe for c in saida.verificacoes)
    if any(mascarar_pii(value) != value for value in text_values):
        raise RecusaSeguranca("saída contém dado pessoal que deveria estar mascarado")


def _topicos(values):
    """Reduz textos livres às categorias de risco exigidas pela instrução validada."""
    result = []
    for value in values:
        text = unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode()
        if "diverg" in text and "matricula" in text:
            topic = "identidade"
        elif "incomplet" in text or "retorno" in text or "data" in text and "falta" in text:
            topic = "completude"
        elif "antecedencia" in text or "urgencia" in text:
            topic = "antecedencia"
        elif "prestacao" in text or "contas vencida" in text:
            topic = "prestacao_vencida"
        elif "limite mensal" in text or "mensal excede" in text:
            topic = "limite_mensal"
        elif "saldo" in text and ("insuficiente" in text or "unidade" in text):
            topic = "saldo"
        elif "justificativa" in text or "instrucao dirigida" in text:
            topic = "instrucao_embutida"
        elif "autorizacao" in text or "secretario adjunto" in text:
            topic = "autorizacao_urgencia"
        elif "mascar" in text or "dados pessoais" in text:
            topic = "pii_mascarada"
        else:
            topic = "outro"
        result.append(topic)
    return sorted(result)


def _numeros(text):
    """Retorna âncoras numéricas normalizadas sem depender de separador decimal."""
    from decimal import Decimal
    values = []
    pattern = r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?"
    for value in re.findall(pattern, text):
        try:
            if "." in value and "," in value:
                decimal_sep = "." if value.rfind(".") > value.rfind(",") else ","
                thousands_sep = "," if decimal_sep == "." else "."
                canonical = value.replace(thousands_sep, "").replace(decimal_sep, ".")
            elif value.count(".") > 1 or value.count(",") > 1:
                canonical = value.replace(".", "").replace(",", "")
            elif "." in value or "," in value:
                separator = "." if "." in value else ","
                left, right = value.rsplit(separator, 1)
                if len(right) == 3 and len(left) <= 3:
                    canonical = left + right
                else:
                    canonical = left + "." + right
            else:
                canonical = value
            values.append(str(Decimal(canonical).normalize()))
        except Exception:
            continue
    return sorted(values)


def validar_chamadas_modelo(response, permitidas: list[dict], pedido: dict, fatos: dict,
                            execucoes_ferramentas: list[dict] | None = None) -> list[dict]:
    """Valida chamadas Agno pós-execução e devolve apenas campos sanitizados, nunca resultados brutos de ferramenta."""
    order = {"consultar_cadastro_servidor": 0, "consultar_historico_diarias": 1,
             "calcular_diarias": 1, "consultar_saldo_diarias": 2}
    cached_keys = {
        (item["nome"], json.dumps(item["argumentos"], sort_keys=True, ensure_ascii=False))
        for item in (execucoes_ferramentas or []) if item.get("resultado") == "cache"
    }
    highest = -1
    safe = []
    seen = set()
    for call in (getattr(response, "tools", None) or []):
        name = getattr(call, "tool_name", None) or (call.get("tool_name") if isinstance(call, dict) else None)
        args = getattr(call, "tool_args", None) or (call.get("tool_args") if isinstance(call, dict) else None) or {}
        allowed = any(x["nome"] == name and x["argumentos"] == args for x in permitidas)
        if name not in order or not allowed:
            raise RecusaSeguranca("chamada de ferramenta fora da lista autorizada")
        cache_key = (name, json.dumps(args, sort_keys=True, ensure_ascii=False))
        if cache_key in seen:
            if cache_key in cached_keys and not getattr(call, "tool_call_error", False):
                continue
            raise RecusaSeguranca("ferramenta repetida sem resultado em cache")
        seen.add(cache_key)
        if order[name] < highest:
            raise RecusaSeguranca("ordem das ferramentas violou dependências")
        highest = max(highest, order[name])
        validar_argumentos(name, args, pedido, fatos)
        if getattr(call, "tool_call_error", False):
            raise RecusaSeguranca("falha de ferramenta")
        safe.append({"nome": name, "argumentos": args, "resultado": "concluída"})
    unmatched = list(permitidas)
    for call in safe:
        index = next((i for i, item in enumerate(unmatched)
                      if item["nome"] == call["nome"] and item["argumentos"] == call["argumentos"]), None)
        if index is None:
            expected_names = [item["nome"] for item in permitidas]
            observed_names = [item["nome"] for item in safe]
            raise RecusaSeguranca(f"ferramenta não autorizada/repetida; esperadas={expected_names}; observadas={observed_names}")
        unmatched.pop(index)
    if unmatched:
        expected_names = [item["nome"] for item in permitidas]
        observed_names = [item["nome"] for item in safe]
        raise RecusaSeguranca(f"ferramenta aplicável omitida/repetida; esperadas={expected_names}; observadas={observed_names}")
    return safe
