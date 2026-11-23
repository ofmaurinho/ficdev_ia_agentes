import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from app import PADRAO_ERRO, registrar_conferencia
from barreiras import construir_instrucao
from ferramentas import analisar_deterministico, carregar_complementacao

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"

class InterfaceTest(unittest.TestCase):
    def test_tela_inicial_renderiza_e_erro_limpa_resultado_anterior(self):
        pedido, fatos = analisar_deterministico("DIA-2026-0101")
        result = SimpleNamespace(instrucao=construir_instrucao(pedido, fatos), fatos=fatos,
                                 ferramentas=fatos["consultas"], metricas={}, origem_saida="modelo_validado")
        fake_db = SimpleNamespace(db_engine=SimpleNamespace(dispose=lambda: None))
        at = AppTest.from_file(str(APP_PATH))
        with patch("memoria.criar_banco", return_value=fake_db), \
             patch("memoria.expurgar_expiradas", return_value={"sucesso": True}), \
             patch("agente._agente", return_value=object()), \
             patch("agente.analisar_pedido", side_effect=[result, RuntimeError("synthetic")]):
            at.run(timeout=20)
            self.assertEqual(len(at.exception), 0)
            self.assertEqual([t.label for t in at.tabs], ["Analisar pedido", "Complementar diligência", "Eliminar memória"])
            at.button[0].click().run(timeout=20)
            self.assertTrue(any("Recomendação:" in item.value for item in at.subheader))
            self.assertTrue(any("conferencias.jsonl" in item.value and
                                "política institucional" in item.value for item in at.warning))
            at.selectbox[0].select("DIA-2026-0102").run(timeout=20)
            self.assertFalse(any("Recomendação:" in item.value for item in at.subheader))
            at.button[0].click().run(timeout=20)
            self.assertTrue(any(item.value == PADRAO_ERRO for item in at.error))
            self.assertFalse(any("Recomendação:" in item.value for item in at.subheader))
        st.cache_resource.clear()

    def test_analise_e_complementacao_do_mesmo_pedido_tem_minutas_independentes(self):
        case = "DIA-2026-0112"
        original_pedido, original_fatos = analisar_deterministico(case)
        complemento = carregar_complementacao(case)
        complemento_pedido, complemento_fatos = analisar_deterministico(case, complemento)
        original = SimpleNamespace(
            instrucao=construir_instrucao(original_pedido, original_fatos).model_copy(
                update={"minuta_despacho": "MINUTA ORIGINAL INDEPENDENTE"}),
            fatos=original_fatos, ferramentas=original_fatos["consultas"],
            metricas={"modelo_usado": True}, origem_saida="modelo_validado")
        atualizado = SimpleNamespace(
            instrucao=construir_instrucao(complemento_pedido, complemento_fatos).model_copy(
                update={"minuta_despacho": "MINUTA DA COMPLEMENTACAO INDEPENDENTE"}),
            fatos=complemento_fatos, ferramentas=complemento_fatos["consultas"],
            metricas={"modelo_usado": True}, origem_saida="modelo_validado")
        fake_db = SimpleNamespace(db_engine=SimpleNamespace(dispose=lambda: None))
        at = AppTest.from_file(str(APP_PATH))
        st.cache_resource.clear()
        with patch("memoria.criar_banco", return_value=fake_db), \
             patch("memoria.expurgar_expiradas", return_value={"sucesso": True}), \
             patch("agente._agente", return_value=object()), \
             patch("agente.analisar_pedido", side_effect=[original, atualizado]):
            at.run(timeout=20)
            next(b for b in at.button if b.label == "Analisar").click().run(timeout=20)
            self.assertEqual(len(at.exception), 0)

            next(s for s in at.selectbox if s.label == "Pedido em diligência").select(case).run(timeout=20)
            next(t for t in at.text_area if t.label == "Complementação recebida").set_value(complemento)
            next(b for b in at.button if b.label == "Processar na mesma sessão").click().run(timeout=20)
            self.assertEqual(len(at.exception), 0)

            minuta_complemento = next(t for t in at.text_area if t.key == "minuta_complementacao_" + case)
            self.assertEqual(minuta_complemento.value, "MINUTA DA COMPLEMENTACAO INDEPENDENTE")
            self.assertEqual(at.session_state.resultado.instrucao.minuta_despacho,
                             "MINUTA ORIGINAL INDEPENDENTE")
            self.assertEqual(at.session_state.resultado_comp.instrucao.minuta_despacho,
                             "MINUTA DA COMPLEMENTACAO INDEPENDENTE")
        st.cache_resource.clear()

    def test_mostrar_duas_analises_do_mesmo_pedido_mantem_widgets_independentes(self):
        case = "DIA-2026-0112"
        pedido, fatos = analisar_deterministico(case)
        from app import _mostrar
        original = SimpleNamespace(
            instrucao=construir_instrucao(pedido, fatos).model_copy(
                update={"minuta_despacho": "MINUTA ORIGINAL INDEPENDENTE"}),
            fatos=fatos, ferramentas=fatos["consultas"], metricas={}, origem_saida="modelo_validado")
        complemento = SimpleNamespace(
            instrucao=construir_instrucao(pedido, fatos).model_copy(
                update={"minuta_despacho": "MINUTA DA COMPLEMENTACAO INDEPENDENTE"}),
            fatos={**fatos, "complementacao_aplicada": True}, ferramentas=fatos["consultas"],
            metricas={}, origem_saida="modelo_validado")
        at = AppTest.from_string(
            "import streamlit as st\n"
            "from app import _mostrar\n"
            "_mostrar(st.session_state.original, contexto='principal')\n"
            "_mostrar(st.session_state.complemento, contexto='complementacao')\n")
        at.session_state["original"] = original
        at.session_state["complemento"] = complemento
        at.run()
        self.assertEqual(len(at.exception), 0)
        original_widget = next(t for t in at.text_area if t.key == f"minuta_principal_{case}")
        complemento_widget = next(t for t in at.text_area if t.key == f"minuta_complementacao_{case}")
        self.assertEqual(original_widget.value, "MINUTA ORIGINAL INDEPENDENTE")
        self.assertEqual(complemento_widget.value, "MINUTA DA COMPLEMENTACAO INDEPENDENTE")
        original_widget.set_value("EDICAO SOMENTE ORIGINAL")
        complemento_widget.set_value("EDICAO SOMENTE COMPLEMENTACAO")
        at.run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.session_state["minuta_principal_" + case], "EDICAO SOMENTE ORIGINAL")
        self.assertEqual(at.session_state["minuta_complementacao_" + case], "EDICAO SOMENTE COMPLEMENTACAO")

    def test_registro_persiste_minuta_editada_com_pii_mascarada(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "conferencias.jsonl"
            registrar_conferencia({"pedido": "DIA-TESTE", "concordancia": False,
                "justificativa_divergencia": "Conferido por pessoa@example.invalid, CPF 123.456.789-00",
                "minuta_final": "Valor e conta 12345-6 da agência 1234-5; pessoa@example.invalid"}, path)
            saved = path.read_text(encoding="utf-8")
            row = json.loads(saved)
            self.assertIn("minuta_final", row)
            self.assertIn("[CPF MASCARADO]", saved)
            self.assertIn("[DADOS BANCÁRIOS MASCARADOS]", saved)
            self.assertIn("[EMAIL MASCARADO]", saved)
            self.assertNotIn("123.456.789-00", saved)
            self.assertNotIn("12345-6", saved)
            self.assertNotIn("pessoa@example.invalid", saved)


if __name__ == "__main__":
    unittest.main(verbosity=2)
