"""Memória SQLite, inspeção e rotina de eliminação em dois estágios."""
import sqlite3
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from configuracao import DB_PATH, RETENCAO_DIAS
from agente import AGNO_IMPORT_ERROR, SqliteDb, Agent
from ferramentas import carregar_pedido, carregar_complementacao


def criar_banco(caminho: Path = DB_PATH):
    """Cria/retorna o adaptador SQLite do Agno em caminho local, sem fixar IDs de usuário/sessão."""
    if AGNO_IMPORT_ERROR or SqliteDb is None:
        raise RuntimeError("Agno não está instalado")
    return SqliteDb(db_file=str(caminho))


def ocorrencias_sqlite(caminho: Path, termos: list[str]) -> dict:
    """Inspeciona todas as tabelas SQLite sem imprimir conteúdo e conta linhas que contêm termos indicados."""
    if not caminho.exists():
        return {"tabelas": {}, "total": 0}
    con = sqlite3.connect(caminho)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        found = {}
        for table in tables:
            columns = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
            if not columns:
                continue
            rows = con.execute(f'SELECT * FROM "{table}"').fetchall()
            count = sum(any(term.casefold() in str(value).casefold() for value in row if value is not None for term in termos) for row in rows)
            if count:
                found[table] = count
        return {"tabelas": found, "total": sum(found.values())}
    finally:
        con.close()


def contagens_tabelas_sqlite(caminho: Path) -> dict:
    """Retorna somente nome e contagem das tabelas SQLite, sem valores de registros."""
    if not caminho.exists():
        return {}
    con = sqlite3.connect(caminho)
    try:
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in names}
    finally:
        con.close()


def _residuos_alvo(caminho: Path, caso: str, nomes: list[str], ids_titular: set[str], ids_iniciais_divergentes: set[str]) -> dict:
    """Conta somente linhas ligadas ao caso/titular, evitando apagar ou sinalizar dados alheios de matrícula digitada errada."""
    con = sqlite3.connect(caminho)
    try:
        result = {}
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            rows = con.execute(f'SELECT * FROM "{table}"').fetchall()
            count = 0
            for row in rows:
                text = " ".join(str(x) for x in row if x is not None).casefold()
                linked = caso.casefold() in text or any(n.casefold() in text for n in nomes) or any(uid.casefold() in text for uid in ids_titular)
                wrong_linked = any(uid.casefold() in text for uid in ids_iniciais_divergentes) and (caso.casefold() in text or any(n.casefold() in text for n in nomes))
                if linked or wrong_linked:
                    count += 1
            if count:
                result[table] = count
        return result
    finally:
        con.close()


def eliminar_dados(caso: str, user_ids: list[str] | None = None, caminho: Path = DB_PATH) -> dict:
    """Exclui sessões e memórias do titular e remove apenas os dados do caso do ID inicialmente divergente."""
    pedido = carregar_pedido(caso)
    names = [pedido["nome"]]
    uids = {pedido["matricula"]}
    complemento = carregar_complementacao(caso) or ""
    corrected = re.search(r"matrícula correta é\s*(\d+)", complemento, re.I)
    if corrected:
        uids.add(corrected.group(1))
    if user_ids:
        uids.update(x.strip() for x in user_ids if x.strip())
    db = criar_banco(caminho)
    agente = Agent(db=db, telemetry=False, debug_mode=False)
    before_tables = contagens_tabelas_sqlite(caminho)
    removidas_sessao = 0
    erros = []
    for uid in sorted(uids):
        try:
            sessions = db.get_sessions(user_id=uid, include_runs=True) or []
        except Exception as exc:
            sessions = []
            erros.append({"etapa": "listar_sessoes", "erro": type(exc).__name__})
        for session in sessions:
            sid = getattr(session, "session_id", None)
            if not sid:
                continue
            # A matrícula inicial divergente pertence a terceiro: apagar somente a sessão deste caso.
            if corrected and uid == pedido["matricula"] and sid != caso:
                continue
            # A ação solicitada é por titular. Para o titular validado, remover todas as sessões;
            # para qualquer ID extra, limitar estritamente à sessão deste caso.
            if uid not in {corrected.group(1) if corrected else pedido["matricula"]} and sid != caso:
                continue
            try:
                agente.delete_session(session_id=sid, user_id=uid)
                removidas_sessao += 1
            except Exception as exc:
                erros.append({"etapa": "excluir_sessao", "erro": type(exc).__name__})
        try:
            memories = db.get_user_memories(user_id=uid)
        except Exception as exc:
            memories = []
            erros.append({"etapa": "listar_memorias", "erro": type(exc).__name__})
        # Não apagar memórias não relacionadas de um possível terceiro que digitou a matrícula errada.
        if corrected and uid == pedido["matricula"]:
            memories = [m for m in memories if caso in str(getattr(m, "memory", "")) or any(n.casefold() in str(getattr(m, "memory", "")).casefold() for n in names)]
        ids = [getattr(m, "memory_id", None) or getattr(m, "id", None) for m in memories]
        ids = [str(i) for i in ids if i]
        if ids:
            try:
                db.delete_user_memories(memory_ids=ids, user_id=uid)
            except Exception as exc:
                erros.append({"etapa": "excluir_memorias", "erro": type(exc).__name__})
    wrong_ids = {pedido["matricula"]} if corrected else set()
    try:
        remaining_tables = _residuos_alvo(caminho, caso, names, uids-wrong_ids, wrong_ids)
        after_tables = contagens_tabelas_sqlite(caminho)
    except Exception as exc:
        remaining_tables, after_tables = {"inspecao": 1}, {}
        erros.append({"etapa": "verificar_residuos", "erro": type(exc).__name__})
    try:
        db.db_engine.dispose()
    except Exception as exc:
        erros.append({"etapa": "fechar_banco", "erro": type(exc).__name__})
    return {"caso": caso, "sessoes_tentadas": removidas_sessao,
            "contagens_antes": before_tables, "contagens_depois": after_tables,
            "tabelas_com_residuos": remaining_tables, "erros": erros,
            "sucesso": not remaining_tables and not erros}


def expurgar_expiradas(caminho: Path = DB_PATH, retencao_dias: int = RETENCAO_DIAS) -> dict:
    """Expurga sessões anteriores ao prazo configurado e suas memórias, sem tocar em registros oficiais."""
    if not caminho.exists():
        return {"expurgadas": 0, "sucesso": True}
    db = criar_banco(caminho)
    agent = Agent(db=db, telemetry=False, debug_mode=False)
    cutoff_epoch = int((datetime.now(timezone.utc)-timedelta(days=retencao_dias)).timestamp())
    errors = []
    try:
        sessions = db.get_sessions(limit=10001, include_runs=True) or []
        if len(sessions) > 10000:
            errors.append({"etapa": "listar_sessoes", "erro": "limite_de_varredura_excedido"})
            sessions = sessions[:10000]
    except Exception as exc:
        sessions = []
        errors.append({"etapa": "listar_sessoes", "erro": type(exc).__name__})
    expired = []
    for session in sessions:
        timestamp = getattr(session, "updated_at", None) or getattr(session, "created_at", None)
        if timestamp is not None and int(timestamp) < cutoff_epoch:
            expired.append(session)
    deleted = 0
    affected_users = set()
    for session in expired:
        sid, uid = getattr(session, "session_id", None), getattr(session, "user_id", None)
        if sid:
            try:
                agent.delete_session(session_id=sid, user_id=uid)
                deleted += 1
            except Exception as exc:
                errors.append({"etapa": "excluir_sessao", "erro": type(exc).__name__})
        if uid:
            affected_users.add(uid)
    memories_deleted = 0
    for uid in affected_users:
        try:
            memories = db.get_user_memories(user_id=uid) or []
        except Exception as exc:
            memories = []
            errors.append({"etapa": "listar_memorias", "erro": type(exc).__name__})
        stale = [m for m in memories if getattr(m, "created_at", None) is not None and int(m.created_at) < cutoff_epoch]
        ids = [getattr(m, "memory_id", None) or getattr(m, "id", None) for m in stale]
        ids = [str(x) for x in ids if x]
        if ids:
            try:
                db.delete_user_memories(memory_ids=ids, user_id=uid)
                memories_deleted += len(ids)
            except Exception as exc:
                errors.append({"etapa": "excluir_memorias", "erro": type(exc).__name__})
    try:
        db.db_engine.dispose()
    except Exception as exc:
        errors.append({"etapa": "fechar_banco", "erro": type(exc).__name__})
    # A checagem direta garante que sessões antigas e memórias vencidas não permaneceram.
    con = sqlite3.connect(caminho)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        leftovers = 0
        expired_ids = [getattr(s, "session_id", None) for s in expired]
        expired_ids = [x for x in expired_ids if x]
        for table in tables:
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
            if "session_id" in cols and expired_ids:
                marks = ",".join("?" for _ in expired_ids)
                leftovers += con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE session_id IN ({marks})', expired_ids).fetchone()[0]
            if "user_id" in cols and "created_at" in cols and affected_users:
                marks = ",".join("?" for _ in affected_users)
                leftovers += con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE user_id IN ({marks}) AND created_at < ?', (*affected_users, cutoff_epoch)).fetchone()[0]
            if table == "agno_sessions" and "created_at" in cols:
                leftovers += con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE created_at < ?', (cutoff_epoch,)).fetchone()[0]
        success = leftovers == 0 and not errors
        return {"expurgadas": deleted, "memorias_excluidas": memories_deleted,
                "retencao_dias": retencao_dias, "tabelas_inspecionadas": tables,
                "residuos_vencidos": leftovers, "erros": errors, "sucesso": success}
    except Exception as exc:
        return {"expurgadas": deleted, "memorias_excluidas": memories_deleted,
                "retencao_dias": retencao_dias, "residuos_vencidos": None,
                "erros": errors + [{"etapa": "verificar_residuos", "erro": type(exc).__name__}],
                "sucesso": False}
    finally:
        con.close()
