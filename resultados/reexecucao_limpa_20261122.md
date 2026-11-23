# Reexecucao final limpa — 22/11/2026

## Ambiente e execucao

As dependencias foram instaladas em `.venv` conforme `LEIA-ME.md`. O `.env` local, criado pelo responsavel, foi usado sem expor a chave e continua ignorado pelo Git. A avaliacao com modelo iniciou sem banco SQLite de trabalho existente; os bancos do ensaio de memoria foram temporarios e removidos apos verificacao.

Comandos executados: `pip check`; `python -m unittest discover -s testes -v`; `python avaliacao.py --repeticoes 3`; `python avaliacao.py --live --repeticoes 3`; `python experimento_memoria.py --live`; smoke test do Streamlit em localhost.

## Resultados

- Dependencias: `pip check` sem problemas.
- Testes: 42 aprovados.
- Avaliacao offline: 42 execucoes, 42 correspondencias, sem erro.
- Avaliacao live: 84 execucoes em tres rodadas e dois modos; seis bloqueios preventivos de identidade; 78 propostas avaliadas, 78 acertos integrais e zero erros de execucao. Ambos os modos tiveram 39/39 acertos e zero divergencia nos argumentos das ferramentas.
- Medianas live sequenciais: cinco chamadas ao modelo, 15.581 tokens totais, custo estimado de US$ 0,0036072 e 6,69 s. Paralelas: quatro chamadas, 12.585 tokens, US$ 0,0030266 e 5,81 s. Custos seguem os precos de referencia do exercicio e nao sao valores de fatura.
- Memoria: seis turnos em tres configuracoes. Sem memoria, a complementacao isolada de 0111 nao foi recuperada; historico limitado recuperou e aplicou 0111; historico com memoria de usuario validou as duas complementacoes, sem recuperacao adicional e com custo maior. A correcao de identidade do 0112 foi aplicada sob a identidade confirmada nas tres configuracoes. Ver resultados/memoria.json.
- Eliminacao: bancos temporarios do ensaio de memoria inspecionados; nenhum residuo dos casos-alvo. Ver resultados/eliminacao_memoria_live.json.
- Interface: AppTest aprovado e servidor respondeu HTTP 200 em localhost; nao houve captura nem revisao visual em navegador.

## Avaliacao dos requisitos e pendencias

Ferramentas, saida estruturada, barreiras, limites, filtro de PII, testes de falha controlada, memoria, formulario e benchmark estao cobertos pelo codigo e evidencias atuais. O contrato trata chamada de ferramenta identica repetida como segura somente quando o wrapper confirma resultado em cache; repeticao sem cache permanece recusada.

A estimativa didatica inicial nao tem evidencia de ter sido registrada antes da implementacao; o projeto nao a apresenta como estimativa historica. **Atualização da auditoria documental (22/11/2026):** `resultados/conferencias.jsonl` está presente e contém 14 linhas válidas e completas para 12 pedidos, sem duplicatas integrais. As 14 recomendações estão alinhadas aos encaminhamentos e marcadas concordantes. Há duas linhas para cada um dos pedidos 0111 e 0112, com decisões de diligência e prosseguimento e complementações correspondentes no acervo; o JSONL, porém, não identifica etapa nem sessão. Também não há snapshot anterior para comprovar continuidade histórica. A política de acesso, retenção, descarte e backups continua pendente e bloqueia uso com dados reais. Veja `resultados/ACAO_HUMANA_PENDENTE.md` e `resultados/pendencia_politica_conferencias.md`.
