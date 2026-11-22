import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from memoria import ocorrencias_sqlite
from memoria import eliminar_dados, criar_banco, expurgar_expiradas
from agno.db.schemas.memory import UserMemory
from agno.session.agent import AgentSession
from agno.run.agent import RunOutput
from ferramentas import carregar_pedido, carregar_complementacao
import re
from unittest.mock import patch
from experimento_memoria import _pair_row


class MemoriaTest(unittest.TestCase):
    def test_turno_0112_bloqueado_tem_metricas_zero_e_segundo_turno_medido(self):
        case = "DIA-2026-0112"
        first = SimpleNamespace(user_id="")
        second = SimpleNamespace(
            instrucao=SimpleNamespace(numero_pedido=case, recomendacao="apto_para_autorizacao"),
            fatos={"complementacao_aplicada": True, "dados_completos": True},
            user_id="MATRICULA_CORRIGIDA",
        )
        row = _pair_row(
            "historico_limitado", case, first, {"modelo_usado": False}, second,
            {"modelo_usado": True, "tokens_entrada": 12000, "tokens_saida": 500,
             "chamadas_modelo": 5, "custo_usd": 0.003},
            "complemento_com_identidade_corrigida", None, None,
        )
        self.assertEqual(row["primeiro_turno_status"], "bloqueado_antes_do_modelo")
        self.assertFalse(row["primeiro_turno_saida_validada"])
        self.assertEqual(row["primeiro_turno_chamadas_modelo"], 0)
        self.assertEqual(row["primeiro_turno_tokens_entrada"], 0)
        self.assertEqual(row["primeiro_turno_tokens_saida"], 0)
        self.assertEqual(row["primeiro_turno_custo_usd"], 0)
        self.assertEqual(row["custo_total_usd"], 0.003)
        self.assertEqual(row["recuperacao_historico_status"],
                         "nao_aplicavel_pedido_reenviado_com_identidade_corrigida")
        self.assertTrue(row["aplicou_complementacao"])

    def test_varredura_generica_sem_expor_conteudo(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"x.sqlite"
            c = sqlite3.connect(path)
            c.execute("CREATE TABLE agno_sessions (session_id TEXT, user_id TEXT)")
            c.execute("INSERT INTO agno_sessions VALUES (?, ?)", ("DIA-TESTE", "123456"))
            c.commit(); c.close()
            result = ocorrencias_sqlite(path, ["123456"])
            self.assertEqual(result["tabelas"], {"agno_sessions": 1})
            self.assertNotIn("123456", str(result))

    def test_eliminacao_agno_em_banco_sintetico(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"agno.sqlite"
            db = criar_banco(path)
            db._create_all_tables()
            db.upsert_session(AgentSession(session_id="DIA-2026-0101", user_id="TESTE-UID"))
            db.upsert_run(RunOutput(run_id="run-synthetic", session_id="DIA-2026-0101", user_id="TESTE-UID", content="evidência sintética"), session_id="DIA-2026-0101", user_id="TESTE-UID", run_index=0)
            db.upsert_user_memory(UserMemory(memory="Memória sintética do caso DIA-2026-0101", user_id="TESTE-UID", memory_id="mem-test"))
            before = ocorrencias_sqlite(path, ["DIA-2026-0101", "TESTE-UID"])
            self.assertGreaterEqual(before["total"], 2)
            self.assertIn("agno_runs", before["tabelas"])
            result = eliminar_dados("DIA-2026-0101", ["TESTE-UID"], path)
            after = ocorrencias_sqlite(path, ["DIA-2026-0101", "TESTE-UID"])
            self.assertTrue(result["sucesso"], result["tabelas_com_residuos"])
            self.assertEqual(after["total"], 0)
            self.assertEqual(result["contagens_depois"]["agno_sessions"], 0)
            self.assertEqual(result["contagens_depois"]["agno_runs"], 0)
            self.assertEqual(result["contagens_depois"]["agno_memories"], 0)
            db.db_engine.dispose()

    def test_eliminacao_sqlite_nao_altera_registro_jsonl_separado(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db_path = root / "agno.sqlite"
            conference_path = root / "conferencias.jsonl"
            db = criar_banco(db_path)
            db.upsert_session(AgentSession(session_id="DIA-2026-0101", user_id="SYNTHETIC-UID"))
            db.upsert_run(RunOutput(run_id="synthetic-run", session_id="DIA-2026-0101",
                user_id="SYNTHETIC-UID", content="synthetic"), session_id="DIA-2026-0101",
                user_id="SYNTHETIC-UID", run_index=0)
            db.upsert_user_memory(UserMemory(memory="synthetic memory", user_id="SYNTHETIC-UID",
                memory_id="synthetic-memory"))
            db.db_engine.dispose()
            conference_path.write_text('{"pedido":"SYNTHETIC-CASE","registro":"preservar"}\n',
                                       encoding="utf-8")
            before = conference_path.read_bytes()
            result = eliminar_dados("DIA-2026-0101", ["SYNTHETIC-UID"], db_path)
            self.assertTrue(result["sucesso"], result)
            self.assertEqual(conference_path.read_bytes(), before)

    def test_expurgo_configuravel_em_banco_sintetico(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"retencao.sqlite"
            db = criar_banco(path)
            db.upsert_session(AgentSession(session_id="DIA-OLD", user_id="OLD-UID", created_at=1, updated_at=1))
            db.upsert_user_memory(UserMemory(memory="memória sintética antiga", user_id="OLD-UID", memory_id="old-memory", created_at=1, updated_at=1))
            result = expurgar_expiradas(path, retencao_dias=30)
            self.assertTrue(result["sucesso"], result)
            self.assertGreaterEqual(result["expurgadas"], 1)
            self.assertEqual(ocorrencias_sqlite(path, ["DIA-OLD", "OLD-UID", "old-memory"])["total"], 0)
            db.db_engine.dispose()

    def test_isolamento_de_usuarios_e_limpeza_matricula_trocada(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"isolamento.sqlite"
            pedido = carregar_pedido("DIA-2026-0112")
            wrong_uid = pedido["matricula"]
            correct_uid = re.search(r"matrícula correta é\s*(\d+)", carregar_complementacao("DIA-2026-0112"), re.I).group(1)
            holder_name = pedido["nome"]
            db = criar_banco(path)
            db.upsert_user_memory(UserMemory(memory="memória do titular A", user_id="USER-A", memory_id="memory-a"))
            db.upsert_user_memory(UserMemory(memory="memória do titular B", user_id="USER-B", memory_id="memory-b"))
            self.assertEqual([m.memory_id for m in db.get_user_memories(user_id="USER-A")], ["memory-a"])
            self.assertEqual([m.memory_id for m in db.get_user_memories(user_id="USER-B")], ["memory-b"])
            db.upsert_session(AgentSession(session_id="DIA-2026-0112", user_id=wrong_uid))
            db.upsert_user_memory(UserMemory(memory=f"caso DIA-2026-0112; {holder_name}", user_id=wrong_uid, memory_id="case-memory"))
            db.upsert_user_memory(UserMemory(memory="outra memória sintética", user_id=wrong_uid, memory_id="unrelated-memory"))
            db.upsert_session(AgentSession(session_id="DIA-2026-0112", user_id=correct_uid))
            db.upsert_user_memory(UserMemory(memory=f"caso DIA-2026-0112; {holder_name}", user_id=correct_uid, memory_id="holder-case"))
            result = eliminar_dados("DIA-2026-0112", caminho=path)
            self.assertTrue(result["sucesso"], result)
            # A memória sem vínculo com o processo permanece; preserva os dados de terceiro.
            self.assertEqual([m.memory_id for m in db.get_user_memories(user_id=wrong_uid)], ["unrelated-memory"])
            self.assertEqual(db.get_user_memories(user_id=correct_uid), [])
            db.db_engine.dispose()

    def test_falha_ao_listar_sessoes_nao_confirma_eliminacao(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"erro_lista.sqlite"
            db = criar_banco(path)
            db._create_all_tables()
            with patch("memoria.criar_banco", return_value=db), patch("memoria.Agent"):
                with patch.object(db, "get_sessions", side_effect=RuntimeError("synthetic")):
                    result = eliminar_dados("DIA-2026-0101", caminho=path)
            self.assertFalse(result["sucesso"])
            self.assertIn("listar_sessoes", [e["etapa"] for e in result["erros"]])

    def test_falha_ao_excluir_sessao_deixa_residuo_visivel(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"erro_exclusao.sqlite"
            db = criar_banco(path)
            db.upsert_session(AgentSession(session_id="DIA-2026-0101", user_id=carregar_pedido("DIA-2026-0101")["matricula"]))
            with patch("memoria.criar_banco", return_value=db), patch("memoria.Agent") as fake_agent:
                fake_agent.return_value.delete_session.side_effect = RuntimeError("synthetic")
                result = eliminar_dados("DIA-2026-0101", caminho=path)
            self.assertFalse(result["sucesso"])
            self.assertTrue(result["tabelas_com_residuos"])
            self.assertIn("excluir_sessao", [e["etapa"] for e in result["erros"]])

    def test_falha_ao_listar_expiradas_nao_informa_sucesso(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"erro_expurgo.sqlite"
            db = criar_banco(path)
            db._create_all_tables()
            with patch("memoria.criar_banco", return_value=db):
                with patch.object(db, "get_sessions", side_effect=RuntimeError("synthetic")):
                    result = expurgar_expiradas(path, retencao_dias=30)
            self.assertFalse(result["sucesso"])
            self.assertIn("listar_sessoes", [e["etapa"] for e in result["erros"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
