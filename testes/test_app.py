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
from ferramentas import analisar_deterministico

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
