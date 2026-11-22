"""Contrato validado da instrução apresentada ao conferente."""
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class Verificacao(BaseModel):
    criterio: Literal["cadastro", "dados_completos", "antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario"] = Field(description="Critério administrativo conferido")
    situacao: Literal["atende", "nao_atende", "nao_verificado"] = Field(description="Resultado comprovado da conferência")
    detalhe: str = Field(description="Fundamento objetivo, sem dado pessoal desnecessário")


class Instrucao(BaseModel):
    numero_pedido: str = Field(description="Identificador do pedido protocolado")
    matricula: str = Field(description="Matrícula confirmada ou informada no protocolo em diligência")
    quantidade_diarias: Optional[float] = Field(description="Quantidade calculada; nula em diligência")
    valor_total: Optional[float] = Field(description="Valor em reais calculado; nulo em diligência")
    verificacoes: list[Verificacao] = Field(description="As seis verificações administrativas")
    recomendacao: Literal["apto_para_autorizacao", "diligencia", "nao_recomendado"] = Field(description="Recomendação limitada ao contrato; não substitui decisão do ordenador")
    exige_autorizacao_superior: bool = Field(description="Exigência de autorização escrita superior")
    pendencias: list[str] = Field(description="Itens que requerem correção, análise ou providência")
    alertas: list[str] = Field(description="Alertas relevantes sem dados pessoais desnecessários")
    minuta_despacho: str = Field(description="Minuta editável, sujeita a conferência humana")

    @field_validator("verificacoes")
    @classmethod
    def seis_criterios_unicos(cls, value):
        esperados = {"cadastro", "dados_completos", "antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario"}
        if len(value) != 6 or {item.criterio for item in value} != esperados:
            raise ValueError("A instrução requer exatamente as seis verificações únicas")
        return value
