"""Ferramentas determinísticas e somente leitura sobre o acervo fornecido."""
import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path
from configuracao import (NORMAS_PATH, SERVIDORES_PATH, HISTORICO_DIARIAS_PATH,
                          TABELA_DIARIAS_PATH, UNIDADES_PATH, PEDIDOS_PATH,
                          COMPLEMENTACOES_PATH)


def _json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _pedidos():
    return _json(PEDIDOS_PATH)


def carregar_pedido(numero: str) -> dict:
    """Retorna uma cópia do pedido protocolado pelo identificador exato; lança erro se ausente."""
    found = next((dict(p) for p in _pedidos() if p["numero"] == numero), None)
    if not found:
        raise LookupError("Pedido não localizado no acervo")
    return found


def carregar_complementacao(numero: str) -> str | None:
    """Retorna somente o texto da complementação vinculada ao número informado, se houver."""
    return next((c["texto"] for c in _json(COMPLEMENTACOES_PATH) if c["numero"] == numero), None)


def mascarar_pii(texto: str) -> str:
    """Mascara CPF e par de agência/conta bancária em texto antes de qualquer envio ao modelo."""
    texto = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[CPF MASCARADO]", texto)
    texto = re.sub(r"\b(?:conta corrente\s+)?\d{4,6}-\d\s+da agência\s+\d{4}-\d\b", "[DADOS BANCÁRIOS MASCARADOS]", texto, flags=re.I)
    texto = re.sub(r"\b\d{4,6}-\d\b", "[DADO BANCÁRIO MASCARADO]", texto)
    texto = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL MASCARADO]", texto, flags=re.I)
    return texto


def consultar_cadastro_servidor(matricula: str) -> dict:
    """Confere a identidade e obtém dados funcionais antes das demais consultas.

    Args:
        matricula: matrícula como string de algarismos, exatamente como consta do
            pedido ou da complementação. Não informe nome, CPF ou número do pedido.

    Returns:
        Dicionário com ``matricula`` (str), ``nome`` (str), ``cargo`` (str),
        ``grupo_diaria`` (str), ``unidade`` (str) e ``municipio_sede`` (str).
        CPF e e-mail não fazem parte do retorno.

    Raises:
        LookupError: se a matrícula não existir no cadastro local.
    """
    rows = _csv(SERVIDORES_PATH)
    row = next((r for r in rows if r["matricula"] == str(matricula)), None)
    if row is None:
        raise LookupError("Matrícula não encontrada no cadastro")
    return {k: row[k] for k in ("matricula", "nome", "cargo", "grupo_diaria", "unidade", "municipio_sede")}


def consultar_historico_diarias(matricula: str, mes_referencia: str) -> dict:
    """Consulta diárias e prestações do mês, depois de confirmar o cadastro.

    Chame após ``consultar_cadastro_servidor`` e use a matrícula confirmada. O
    mês deve ser o mês da partida do pedido; esta consulta pode ocorrer antes
    do cálculo das diárias solicitadas.

    Args:
        matricula: matrícula confirmada, como string de algarismos.
        mes_referencia: mês no formato ISO ``AAAA-MM``, por exemplo ``2026-11``.

    Returns:
        Dicionário com ``registros_mes`` (int), ``diarias_anteriores_mes``
        (float), ``limite_mensal`` (float), ``diarias_restantes`` (float),
        ``prestacoes_pendentes`` (list de dicionários com ``pedido`` (str) e
        ``situacao`` (``"no_prazo"`` ou ``"vencida"``)) e
        ``ha_prestacao_vencida`` (bool). As quantidades são diárias, não valores
        monetários.

    Raises:
        ValueError: se ``mes_referencia`` não representar um mês válido.
    """
    date.fromisoformat(mes_referencia + "-01")
    norma = _json(TABELA_DIARIAS_PATH)
    analise = date.fromisoformat(norma["data_da_analise"])
    todos = [r for r in _csv(HISTORICO_DIARIAS_PATH) if r["matricula"] == str(matricula)]
    registros = [r for r in todos if r["data_partida"].startswith(mes_referencia)]
    pendencias = []
    total = 0.0
    for r in todos:
        if r["data_partida"].startswith(mes_referencia):
            total += float(r["quantidade"])
        if r["prestacao_contas"] == "pendente" and r["data_retorno"]:
            retorno = date.fromisoformat(r["data_retorno"])
            due, dias = retorno, 0
            while dias < norma["prazo_prestacao_dias_uteis"]:
                due += timedelta(days=1)
                if due.weekday() < 5:
                    dias += 1
            if analise > due:
                pendencias.append({"pedido": r["pedido"], "situacao": "vencida"})
            else:
                pendencias.append({"pedido": r["pedido"], "situacao": "no_prazo"})
    limite = float(norma["limite_mensal_diarias"])
    return {"registros_mes": len(registros), "diarias_anteriores_mes": total,
            "limite_mensal": limite, "diarias_restantes": limite-total,
            "prestacoes_pendentes": pendencias,
            "ha_prestacao_vencida": any(p["situacao"] == "vencida" for p in pendencias)}


def calcular_diarias(grupo: str, destino: str, data_saida: str, data_retorno: str) -> dict:
    """Calcula antecedência, quantidade e valor após validar cadastro e pedido.

    Chame somente após confirmar a identidade e a completude das datas. O grupo
    deve vir do cadastro funcional; destino e datas devem vir do pedido ou da
    complementação validada. Não estime valores nem substitua dados ausentes.

    Args:
        grupo: grupo funcional em ``"A"``, ``"B"`` ou ``"C"``, obtido do
            cadastro.
        destino: sigla da UF com duas letras, incluindo ``"DF"`` ou ``"MT"``,
            conforme o destino do pedido.
        data_saida: data de partida no formato ISO ``AAAA-MM-DD``.
        data_retorno: data de retorno no formato ISO ``AAAA-MM-DD``.

    Returns:
        Dicionário com ``antecedencia_dias`` (int), ``quantidade_diarias``
        (float), ``valor_unitario`` (float em reais), ``valor_total`` (float
        em reais, arredondado a centavos), ``classe_destino`` (str: ``"DF"``
        mapeado a ``"distrito_federal"``, ``"MT"`` a ``"interior_mt"`` e
        demais UFs a ``"outra_uf"``), ``pernoites`` (int) e
        ``antecedencia_minima`` (int, em dias). Viagem sem pernoite retorna
        meia diária; nos demais casos retorna uma por pernoite e meia no
        retorno.

    Raises:
        ValueError: se uma data for inválida, o retorno anteceder a partida ou
        o grupo não estiver previsto na tabela local.
    """
    partida, retorno = date.fromisoformat(data_saida), date.fromisoformat(data_retorno)
    if retorno < partida:
        raise ValueError("Data de retorno anterior à partida")
    if grupo not in {"A", "B", "C"}:
        raise ValueError("Grupo sem correspondência na tabela")
    tabela = _json(TABELA_DIARIAS_PATH)
    destino = destino.upper()
    classe = "distrito_federal" if destino == "DF" else ("interior_mt" if destino == "MT" else "outra_uf")
    noites = (retorno-partida).days
    quantidade = 0.5 if noites == 0 else noites + 0.5
    valor_unitario = float(tabela["valores"][grupo][classe])
    antecedencia = (partida-date.fromisoformat(tabela["data_da_analise"])).days
    return {"antecedencia_dias": antecedencia, "quantidade_diarias": quantidade,
            "valor_unitario": valor_unitario, "valor_total": round(quantidade*valor_unitario, 2),
            "classe_destino": classe, "pernoites": noites,
            "antecedencia_minima": int(tabela["antecedencia_minima_dias"])}


def consultar_saldo_diarias(unidade: str, valor: float) -> dict:
    """Compara o saldo da unidade com o valor exato calculado para o pedido.

    Chame somente após obter o cálculo e use a unidade do cadastro e o valor
    produzido por ``calcular_diarias``. Esta consulta é somente leitura e não
    reserva nem debita saldo.

    Args:
        unidade: sigla da unidade funcional exatamente como retornada pelo
            cadastro (string, por exemplo ``"CFF"``).
        valor: valor total em reais retornado pelo cálculo, como número Python
            ``float`` (por exemplo ``980.0``); não envie valor estimado.

    Returns:
        Dicionário com ``unidade`` (str), ``saldo`` (float em reais),
        ``valor_consultado`` (float em reais), ``suficiente`` (bool) e
        ``saldo_apos_compromisso`` (float em reais, projeção aritmética que
        não representa débito ou reserva).

    Raises:
        LookupError: se a sigla da unidade não existir no acervo local.
    """
    row = _json(UNIDADES_PATH).get(unidade)
    if row is None:
        raise LookupError("Unidade não localizada")
    saldo = float(row["saldo_diarias"])
    return {"unidade": unidade, "saldo": saldo, "valor_consultado": float(valor),
            "suficiente": saldo >= float(valor), "saldo_apos_compromisso": round(saldo-float(valor), 2)}


def analisar_deterministico(numero: str, texto_complementar: str | None = "", on_stage=None) -> tuple[dict, dict]:
    """Executa as quatro consultas em ordem, bloqueia identidade divergente e devolve fatos rastreáveis sem chamar modelo."""
    pedido = carregar_pedido(numero)
    complemento = texto_complementar or None
    matricula = pedido["matricula"]
    consultas = []
    cadastro = _consultar_com_progresso(consultar_cadastro_servidor, on_stage, matricula=matricula)
    consultas.append({"nome": "consultar_cadastro_servidor", "argumentos": {"matricula": matricula}})
    identidade = cadastro["nome"].casefold() == pedido["nome"].casefold()
    if complemento and "matrícula correta é" in complemento:
        corrigida = re.search(r"matrícula correta é\s*(\d+)", complemento, re.I)
        if corrigida:
            matricula = corrigida.group(1)
            cadastro = _consultar_com_progresso(consultar_cadastro_servidor, on_stage, matricula=matricula)
            consultas.append({"nome": "consultar_cadastro_servidor", "argumentos": {"matricula": matricula}})
            identidade = cadastro["nome"].casefold() == pedido["nome"].casefold()
    dados_completos = bool(pedido.get("data_partida") and pedido.get("data_retorno") and pedido.get("destino_uf"))
    if not pedido.get("data_retorno") and complemento:
        m = re.search(r"\b\d{4}-\d{2}-\d{2}\b", complemento)
        if m:
            pedido["data_retorno"] = m.group()
            dados_completos = True
    hist = calc = saldo = None
    if identidade:
        hist = _consultar_com_progresso(consultar_historico_diarias, on_stage,
                                        matricula=matricula, mes_referencia=pedido["data_partida"][:7])
        consultas.append({"nome": "consultar_historico_diarias", "argumentos": {"matricula": matricula, "mes_referencia": pedido["data_partida"][:7]}})
        if dados_completos:
            calc = _consultar_com_progresso(calcular_diarias, on_stage, grupo=cadastro["grupo_diaria"],
                destino=pedido["destino_uf"], data_saida=pedido["data_partida"], data_retorno=pedido["data_retorno"])
            consultas.append({"nome": "calcular_diarias", "argumentos": {"grupo": cadastro["grupo_diaria"], "destino": pedido["destino_uf"], "data_saida": pedido["data_partida"], "data_retorno": pedido["data_retorno"]}})
            saldo = _consultar_com_progresso(consultar_saldo_diarias, on_stage,
                                             unidade=cadastro["unidade"], valor=calc["valor_total"])
            consultas.append({"nome": "consultar_saldo_diarias", "argumentos": {"unidade": cadastro["unidade"], "valor": calc["valor_total"]}})
    return pedido, {"cadastro": cadastro, "identidade_confirmada": identidade, "historico": hist, "calculo": calc, "saldo": saldo, "dados_completos": dados_completos, "matricula_inicial": pedido["matricula"], "matricula_validada": matricula, "complementacao_aplicada": bool(complemento), "consultas": consultas}


def _consultar_com_progresso(function, callback, **kwargs):
    if callback:
        callback("in_progress", function.__name__)
    result = function(**kwargs)
    if callback:
        callback("complete", function.__name__)
    return result
