import unittest
from types import SimpleNamespace
from unittest.mock import patch
from configuracao import TOOL_CALL_LIMIT
from agente import exigir_execucao_concluida, _agente
from agno.run.base import RunStatus
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.response import ModelResponse
from agno.exceptions import ModelProviderError
from ferramentas import consultar_cadastro_servidor, analisar_deterministico
from barreiras import validar_argumentos, RecusaSeguranca


class FalhasProvocadasTest(unittest.TestCase):
    def test_laco_sem_convergencia_tem_teto_no_agno(self):
        executions = []
        model_calls = []
        def lookup():
            executions.append(True)
            return {"status": "incompleto"}
        def invoke(model, *args, **kwargs):
            model_calls.append(True)
            if len(model_calls) > 2 * TOOL_CALL_LIMIT:
                return ModelResponse(role="assistant", content="limite alcancado")
            return ModelResponse(role="assistant", tool_calls=[{
                "id": str(len(model_calls)), "type": "function",
                "function": {"name": "lookup", "arguments": "{}"}
            }])
        with patch.object(OpenAIChat, "invoke", invoke):
            agent = Agent(model=OpenAIChat(id="gpt-5.6-luna"), tools=[lookup],
                          tool_call_limit=TOOL_CALL_LIMIT, telemetry=False)
            response = agent.run("continue consultando")
        self.assertEqual(response.status, RunStatus.completed)
        self.assertEqual(len(response.tools), TOOL_CALL_LIMIT)
        self.assertEqual(len(executions), TOOL_CALL_LIMIT)
        self.assertGreater(len(model_calls), TOOL_CALL_LIMIT)

    def test_erro_api_controlado_passando_pelo_agno(self):
        def invoke(model, *args, **kwargs):
            raise ModelProviderError(message="detalhe_tecnico_privado",
                                     model_name="OpenAI", model_id="gpt-5.6-luna")
        with patch.object(OpenAIChat, "invoke", invoke):
            agent = _agente()
            response = agent.run("consulta")
        self.assertEqual(response.status, RunStatus.error)
        self.assertNotIn("detalhe_tecnico_privado", response.content)
        with self.assertRaisesRegex(RuntimeError, "status não concluído") as error:
            exigir_execucao_concluida(response)
        self.assertNotIn("detalhe_tecnico_privado", str(error.exception))

    def test_erro_controlado_nao_e_resultado_valido(self):
        with self.assertRaises(LookupError):
            consultar_cadastro_servidor("999999")
        response = SimpleNamespace(status=RunStatus.error, content="mensagem técnica confidencial")
        with self.assertRaisesRegex(RuntimeError, "status não concluído") as error:
            exigir_execucao_concluida(response)
        self.assertNotIn("confidencial", str(error.exception))

    def test_argumento_de_data_inventado_recusado(self):
        pedido, fatos = analisar_deterministico("DIA-2026-0101")
        args = {"grupo": "B", "destino": "MT", "data_saida": "2026-12-01", "data_retorno": pedido["data_retorno"]}
        with self.assertRaises(RecusaSeguranca):
            validar_argumentos("calcular_diarias", args, pedido, fatos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
