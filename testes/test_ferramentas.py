import unittest
import re
from ferramentas import (carregar_pedido, consultar_cadastro_servidor,
                         consultar_historico_diarias, calcular_diarias,
                         consultar_saldo_diarias, analisar_deterministico,
                         mascarar_pii, carregar_complementacao)
from barreiras import construir_instrucao, validar_argumentos, validar_saida, RecusaSeguranca


class FerramentasTest(unittest.TestCase):
    def test_regular(self):
        p, f = analisar_deterministico("DIA-2026-0101")
        out = construir_instrucao(p, f)
        self.assertEqual(out.recomendacao, "apto_para_autorizacao")
        self.assertEqual(out.quantidade_diarias, 3.5)
        self.assertEqual(out.valor_total, 980.0)
        self.assertEqual(len(out.verificacoes), 6)

    def test_prestacao_no_prazo_vs_vencida(self):
        p2 = carregar_pedido("DIA-2026-0102")
        self.assertFalse(consultar_historico_diarias(p2["matricula"], "2026-11")["ha_prestacao_vencida"])
        p8 = carregar_pedido("DIA-2026-0108")
        self.assertTrue(consultar_historico_diarias(p8["matricula"], "2026-11")["ha_prestacao_vencida"])
        self.assertEqual(analisar_deterministico("DIA-2026-0108")[1]["historico"]["prestacoes_pendentes"][0]["situacao"], "vencida")

    def test_meia_diaria(self):
        r = calcular_diarias("B", "MT", "2026-11-05", "2026-11-05")
        self.assertEqual((r["quantidade_diarias"], r["valor_total"]), (0.5, 140.0))

    def test_saldo_insuficiente(self):
        p, f = analisar_deterministico("DIA-2026-0110")
        self.assertFalse(f["saldo"]["suficiente"])
        self.assertEqual(f["calculo"]["valor_total"], 1800.0)

    def test_matricula_divergente_em_diligencia(self):
        p, f = analisar_deterministico("DIA-2026-0112")
        out = construir_instrucao(p, f)
        self.assertEqual(out.recomendacao, "diligencia")
        self.assertIsNone(out.valor_total)
        self.assertFalse(f["identidade_confirmada"])

    def test_complementacao_mesmo_caso(self):
        text = carregar_complementacao("DIA-2026-0112")
        p, f = analisar_deterministico("DIA-2026-0112", text)
        out = construir_instrucao(p, f)
        self.assertTrue(f["identidade_confirmada"])
        self.assertEqual(out.matricula, re.search(r"matrícula correta é\s*(\d+)", text, re.I).group(1))
        self.assertEqual(out.recomendacao, "apto_para_autorizacao")
        queried = [x["argumentos"]["matricula"] for x in f["consultas"] if x["nome"] == "consultar_cadastro_servidor"]
        self.assertEqual(queried, [p["matricula"], out.matricula])

    def test_argumento_inventado_recusado(self):
        p, f = analisar_deterministico("DIA-2026-0101")
        with self.assertRaises(RecusaSeguranca):
            validar_argumentos("consultar_cadastro_servidor", {"matricula": "999999"}, p, f)

    def test_ancoragem_numerica_recusa_tampering(self):
        p, f = analisar_deterministico("DIA-2026-0101")
        expected = construir_instrucao(p, f)
        altered = expected.model_copy(update={"valor_total": 1.0})
        with self.assertRaises(RecusaSeguranca):
            validar_saida(altered, expected)

    def test_mascara_pii_preserva_identificadores(self):
        p = carregar_pedido("DIA-2026-0104")
        safe = mascarar_pii(p["justificativa"])
        cpf = re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", p["justificativa"]).group(0)
        bank = re.search(r"\b\d{4,6}-\d\b", p["justificativa"]).group(0)
        self.assertNotIn(cpf, safe)
        self.assertNotIn(bank, safe)
        self.assertIn(p["numero"], mascarar_pii(f"{p['numero']} {p['data_partida']} {p['matricula']}"))

    def test_guardrail_agno_mascaramento_e_identificadores(self):
        from agente import _agente
        from agno.run.agent import RunInput
        p = carregar_pedido("DIA-2026-0104")
        cpf = re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", p["justificativa"]).group(0)
        bank = re.search(r"\b\d{4,6}-\d\b", p["justificativa"]).group(0)
        run_input = RunInput(input_content=f"{p['numero']} {p['matricula']} {p['data_partida']} {p['justificativa']}")
        _agente().pre_hooks[0].check(run_input)
        value = run_input.input_content
        self.assertNotIn(cpf, value)
        self.assertNotIn(bank, value)
        self.assertIn(p["numero"], value)
        self.assertIn(p["matricula"], value)
        self.assertIn(p["data_partida"], value)
        self.assertNotIn("@sema.exemplo", mascarar_pii("contato: pessoa@sema.exemplo.gov.br"))

    def test_urgencia_e_injecao(self):
        p6, f6 = analisar_deterministico("DIA-2026-0106")
        o6 = construir_instrucao(p6, f6)
        self.assertTrue(o6.exige_autorizacao_superior)
        self.assertEqual(o6.recomendacao, "apto_para_autorizacao")
        p7, f7 = analisar_deterministico("DIA-2026-0107")
        o7 = construir_instrucao(p7, f7)
        self.assertEqual(o7.recomendacao, "nao_recomendado")
        self.assertTrue(o7.alertas)

    def test_relatorio_mascara_matricula(self):
        from medicao import sanitizar_ferramentas
        matricula = carregar_pedido("DIA-2026-0101")["matricula"]
        safe = sanitizar_ferramentas([{"nome": "consulta", "argumentos": {"matricula": matricula, "mes_referencia": "2026-11"}}])
        self.assertNotIn(matricula, str(safe))
        self.assertIn("2026-11", str(safe))


if __name__ == "__main__":
    unittest.main(verbosity=2)
