import unittest
import json
from types import SimpleNamespace
from agente import analisar_pedido, autorizar_ferramentas, _PROTECTED_TOOLS
import agente as agente_module
from barreiras import construir_instrucao, validar_saida, RecusaSeguranca, _topicos
from ferramentas import analisar_deterministico
from modelos import Instrucao
from ferramentas import carregar_pedido


class BarreiraTest(unittest.TestCase):
    def test_recomendacao_positiva_bloqueada_por_prestacao_vencida(self):
        p, f = analisar_deterministico("DIA-2026-0108")
        e = construir_instrucao(p, f)
        bad = e.model_copy(update={"recomendacao": "apto_para_autorizacao"})
        with self.assertRaises(RecusaSeguranca):
            validar_saida(bad, e)

    def test_numero_inventado_no_fundamento_e_recusado(self):
        p, f = analisar_deterministico("DIA-2026-0101")
        expected = construir_instrucao(p, f)
        checks = [v.model_copy() for v in expected.verificacoes]
        checks[2].detalhe += " O modelo inventou 999 dias."
        proposal = expected.model_copy(update={"verificacoes": checks})
        with self.assertRaises(RecusaSeguranca):
            validar_saida(proposal, expected, f, p)

    def test_topico_duplicado_nao_altera_cobertura_de_pendencias(self):
        p, f = analisar_deterministico("DIA-2026-0105")
        expected = construir_instrucao(p, f)
        self.assertTrue(expected.pendencias)
        proposal = expected.model_copy(update={
            "pendencias": expected.pendencias + [expected.pendencias[0]]
        })
        validar_saida(proposal, expected, f, p)

    def test_topicos_normalizam_variacoes_de_acentos(self):
        self.assertEqual(_topicos(["Pendência de prestação de contas vencida"]),
                         _topicos(["Pendencia de prestacao de contas vencida"]))
        self.assertEqual(_topicos(["Divergência de matrícula"]),
                         _topicos(["Divergencia de matricula"]))

    def test_falha_de_acervo_nao_vira_aprovacao(self):
        with self.assertRaises(LookupError):
            analisar_deterministico("DIA-9999-9999")

    def test_caso_regular_nao_precisa_modelo(self):
        r = analisar_pedido("DIA-2026-0101", usar_modelo=False)
        self.assertEqual(r.metricas["status"], "deterministico")
        self.assertEqual(r.instrucao.recomendacao, "apto_para_autorizacao")

    def test_matricula_divergente_nao_cria_memoria_para_terceiro(self):
        # Mesmo solicitado como execução live, a identidade divergente evita qualquer chamada ao modelo.
        r = analisar_pedido("DIA-2026-0112", usar_modelo=True)
        self.assertEqual(r.metricas["status"], "diligencia_identidade_sem_modelo")
        self.assertFalse(r.metricas["modelo_usado"])
        self.assertEqual(r.user_id, "")

    def test_complementacao_reutiliza_session_e_user_id(self):
        class FakeAgent:
            def __init__(self, proposals, permitted): self.calls = []; self.proposals = iter(proposals); self.permitted = iter(permitted)
            def run(self, prompt, user_id, session_id):
                self.calls.append((user_id, session_id, prompt))
                self.assert_no_expected_answer(prompt)
                allowed = next(self.permitted)
                wrappers = {tool.__name__: tool for tool in agente_module._PROTECTED_TOOLS}
                calls = []
                for item in allowed:
                    wrappers[item["nome"]](**item["argumentos"])
                    calls.append(SimpleNamespace(tool_name=item["nome"], tool_args=item["argumentos"], tool_call_error=False))
                return SimpleNamespace(status=agente_module.RunStatus.completed,
                    content=next(self.proposals), tools=calls, metrics={})
            @staticmethod
            def assert_no_expected_answer(prompt):
                assert "resultado_esperado" not in prompt and "gabarito" not in prompt
                assert "resumo_factual" in prompt
        original_key = agente_module.OPENAI_API_KEY
        agente_module.OPENAI_API_KEY = "synthetic-test-key"
        try:
            first_case = analisar_deterministico("DIA-2026-0111")
            second_case = analisar_deterministico("DIA-2026-0111", "Retorno 2026-11-20")
            proposals = [construir_instrucao(*first_case), construir_instrucao(*second_case)]
            fake = FakeAgent(proposals, [first_case[1]["consultas"], second_case[1]["consultas"]])
            first = analisar_pedido("DIA-2026-0111", usar_modelo=True, agent=fake)
            second = analisar_pedido("DIA-2026-0111", "Retorno 2026-11-20", usar_modelo=True, agent=fake)
        finally:
            agente_module.OPENAI_API_KEY = original_key
        uid = carregar_pedido("DIA-2026-0111")["matricula"]
        self.assertEqual([c[:2] for c in fake.calls], [(uid, "DIA-2026-0111")]*2)
        self.assertEqual(first.instrucao.recomendacao, "diligencia")
        self.assertEqual(second.instrucao.recomendacao, "apto_para_autorizacao")
        self.assertIn("2026-11-20", fake.calls[1][2])
        self.assertEqual(first.origem_saida, "modelo_validado")
        self.assertEqual(second.origem_saida, "modelo_validado")
        self.assertNotIn("resultado_esperado", fake.calls[0][2])
        self.assertIn("resumo_factual", fake.calls[0][2])

    def test_resposta_valida_exibida_e_a_propria_proposta_do_modelo(self):
        class FakeAgent:
            def __init__(self, proposal, permitted): self.proposal, self.permitted = proposal, permitted
            def run(self, prompt, user_id, session_id):
                tools = {tool.__name__: tool for tool in agente_module._PROTECTED_TOOLS}
                calls = []
                for item in self.permitted:
                    tools[item["nome"]](**item["argumentos"])
                    calls.append(SimpleNamespace(tool_name=item["nome"], tool_args=item["argumentos"], tool_call_error=False))
                return SimpleNamespace(status=agente_module.RunStatus.completed,
                    content=self.proposal, tools=calls, metrics={})
        p, f = analisar_deterministico("DIA-2026-0101")
        proposal = construir_instrucao(p, f)
        original_key = agente_module.OPENAI_API_KEY
        agente_module.OPENAI_API_KEY = "synthetic-test-key"
        progress = []
        try:
            result = analisar_pedido("DIA-2026-0101", usar_modelo=True,
                                     agent=FakeAgent(proposal, f["consultas"]), on_stage=lambda *x: progress.append(x))
        finally:
            agente_module.OPENAI_API_KEY = original_key
        self.assertIs(result.instrucao, proposal)
        self.assertEqual([{k: call[k] for k in ("nome", "argumentos")} for call in result.ferramentas], f["consultas"])
        self.assertEqual(progress[0], ("in_progress", "consultar_cadastro_servidor"))
        self.assertEqual([step for state, step in progress if state == "in_progress" and step != "modelo"],
                         [c["nome"] for c in f["consultas"]] * 2)
        self.assertEqual(progress[-1], ("complete", "modelo"))

    def test_resposta_divergente_do_modelo_e_recusada_sem_fallback(self):
        class FakeAgent:
            def __init__(self, proposal, permitted): self.proposal, self.permitted = proposal, permitted
            def run(self, prompt, user_id, session_id):
                tools = {tool.__name__: tool for tool in agente_module._PROTECTED_TOOLS}
                calls = []
                for item in self.permitted:
                    tools[item["nome"]](**item["argumentos"])
                    calls.append(SimpleNamespace(tool_name=item["nome"], tool_args=item["argumentos"], tool_call_error=False))
                return SimpleNamespace(status=agente_module.RunStatus.completed,
                    content=self.proposal, tools=calls, metrics={})
        p, f = analisar_deterministico("DIA-2026-0101")
        proposal = construir_instrucao(p, f).model_copy(update={"recomendacao": "nao_recomendado"})
        original_key = agente_module.OPENAI_API_KEY
        agente_module.OPENAI_API_KEY = "synthetic-test-key"
        try:
            with self.assertRaises(RecusaSeguranca):
                analisar_pedido("DIA-2026-0101", usar_modelo=True,
                                agent=FakeAgent(proposal, f["consultas"]))
        finally:
            agente_module.OPENAI_API_KEY = original_key

    def test_modelo_nao_pode_omitir_ferramentas_obrigatorias(self):
        class FakeAgent:
            def __init__(self, proposal): self.proposal = proposal
            def run(self, prompt, user_id, session_id):
                assert "resultado_esperado" not in prompt and "resumo_factual" in prompt
                return SimpleNamespace(status=agente_module.RunStatus.completed,
                                        content=self.proposal, tools=[], metrics={})
        p, f = analisar_deterministico("DIA-2026-0101")
        proposal = construir_instrucao(p, f)
        original_key = agente_module.OPENAI_API_KEY
        agente_module.OPENAI_API_KEY = "synthetic-test-key"
        try:
            with self.assertRaises(RecusaSeguranca):
                analisar_pedido("DIA-2026-0101", usar_modelo=True, agent=FakeAgent(proposal))
        finally:
            agente_module.OPENAI_API_KEY = original_key

    def test_argumentos_sao_barrados_antes_da_chamada_da_ferramenta(self):
        p, f = analisar_deterministico("DIA-2026-0101")
        guarded = _PROTECTED_TOOLS[0]
        with self.assertRaises(RecusaSeguranca):
            guarded(matricula="999999")
        with autorizar_ferramentas(p, f, f["consultas"]):
            result = guarded(matricula=p["matricula"])
        self.assertEqual(result["matricula"], p["matricula"])
        self.assertNotIn("cpf", result)

    def test_metricas_agno_dataclass_sao_lidas(self):
        from agno.metrics import RunMetrics, ModelMetrics
        from types import SimpleNamespace
        from agente import _metricas
        metrics = RunMetrics(input_tokens=100, output_tokens=20, total_tokens=120,
                             details={"model": [ModelMetrics(id="synthetic-model")]})
        message_metrics = SimpleNamespace(input_tokens=100, output_tokens=20,
                                          total_tokens=120, cost=None, duration=None)
        parsed = _metricas(SimpleNamespace(metrics=metrics, status=agente_module.RunStatus.completed,
                                           messages=[SimpleNamespace(role="assistant", metrics=message_metrics)]), 1.25)
        self.assertEqual(parsed["tokens_entrada"], 100)
        self.assertEqual(parsed["tokens_saida"], 20)
        self.assertEqual(parsed["tokens_total"], 120)
        self.assertEqual(parsed["chamadas_modelo"], 1)
        self.assertEqual(parsed["custo_usd"], 0.000044)
        self.assertEqual(parsed["metricas_por_chamada"], [{"numero": 1, "tokens_entrada": 100,
                                                          "tokens_saida": 20, "tokens_total": 120}])
        self.assertEqual(parsed["soma_tokens_entrada_por_chamada"], 100)
        self.assertEqual(parsed["soma_tokens_saida_por_chamada"], 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
