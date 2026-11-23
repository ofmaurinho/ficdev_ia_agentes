# Relatório final — Desafio 01: instrução de pedidos de diárias

## Arquitetura e segurança

O agente Agno usa as quatro ferramentas no próprio ciclo: cadastro, histórico mensal, cálculo de diárias e saldo da unidade. Os argumentos são validados contra pedido e fatos determinísticos; as dependências impõem cadastro antes de histórico/cálculo e cálculo antes de saldo. A saída estruturada do modelo é comparada com os fatos e só aparece na interface após passar pelas barreiras. Não há fallback para uma resposta determinística quando a proposta do modelo diverge.

O modelo não recebe gabarito. Identidade divergente bloqueia a chamada e a memória; PII é minimizada antes do envio. A aplicação prepara instrução para conferência humana, não decide nem autoriza despesa. O padrão operacional mantém `parallel_tool_calls=False`.

## Benchmark live final

Em 22/11/2026 foram executadas tres rodadas dos 12 pedidos e duas complementacoes, em cada modo de paralelismo: 84 execucoes. Seis identidades divergentes foram bloqueadas antes do modelo. As outras 78 propostas passaram pelas barreiras e acertaram integralmente o gabarito (39/39 em cada modo), sem divergencias de argumentos ou erros de execucao.

| Medida por execucao do modelo | Paralelismo desligado | Paralelismo ligado |
|---|---:|---:|
| Casos avaliados / acertos exatos | 39 / 39 | 39 / 39 |
| Invocacoes de ferramenta pelo agente | 150 (4 por caso completo) | 150 (4 por caso completo) |
| Chamadas de modelo, mediana / maximo | 5 / 5 | 4 / 5 |
| Tokens de entrada, mediana | 15.088 | 12.076 |
| Tokens de saida, mediana | 490 | 507 |
| Tokens totais, mediana / maximo | 15.581 / 15.833 | 12.585 / 15.554 |
| Custo estimado, mediana / maximo | US$ 0,0036072 / US$ 0,0036836 | US$ 0,0030266 / US$ 0,0035978 |
| Latencia, mediana / maximo | 6,69 / 9,85 s | 5,81 / 7,01 s |

O modo paralelo teve menores medianas de tokens, custo e latencia nesta amostra; ambos acertaram 39/39. Isso nao prova que o paralelismo causou a diferenca. O padrao operacional continua sequencial porque as consultas tem dependencias de negocio. A aplicacao aceita chamada identica repetida somente quando o wrapper confirma que o resultado veio do cache; chamadas repetidas sem cache continuam recusadas.

Os custos usam os precos de referencia do exercicio: entrada US$ 0,20 e saida US$ 1,20 por milhao de tokens; nao sao valores de fatura. Sobre as 78 propostas avaliadas, o custo mediano foi US$ 0,0030942 e o maximo US$ 0,0036836. A mediana de tokens totais foi 12.793,5, com maximo 15.833. Metricas por execucao e chamadas sanitizadas estao em resultados/benchmark_live.json e .csv; a comparacao agregada esta em resultados/paralelismo.json.

## Memoria e complementacao

O ensaio live avaliou os casos 0111 e 0112 em tres configuracoes. No 0111, somente a complementacao foi enviada no segundo turno para medir recuperacao; sem memoria, ela nao foi aplicada. Com historico limitado, o modelo recuperou o pedido e aplicou a complementacao. O modo com memoria de usuario tambem aplicou os dois casos, mas nao acrescentou recuperacao em relacao ao historico limitado e aumentou chamadas e custo.

| Configuracao | Complementacoes validadas | Chamadas de modelo | Tokens agregados | Custo observado agregado |
|---|---:|---:|---:|---:|
| Sem memoria | 1/2 | 9 | 25.879 | US$ 0,0064038 |
| Historico limitado | 2/2 | 16 | 41.842 | US$ 0,0097234 |
| Historico + memoria do usuario | 2/2 | 19 | 46.110 | US$ 0,0106180 |

No 0112, o primeiro turno foi bloqueado antes do modelo; a correcao foi enviada junto ao pedido sob identidade confirmada e validada nas tres configuracoes. Esse caso avalia correcao segura, nao recuperacao de historico. Os bancos temporarios do experimento foram inspecionados e os registros de casos-alvo removidos sem residuos. A evidencia por turno e a limpeza estao em resultados/memoria.json e resultados/eliminacao_memoria_live.json.

O arquivo `resultados/conferencias.jsonl` está presente. Auditoria somente de leitura em 22/11/2026 encontrou **14 linhas JSON válidas para 12 pedidos**, sem duplicatas integrais ou registros incompletos nos campos auditados. Os **14 registros estão completos e alinhados** entre recomendação e encaminhamento: 14 concordantes, zero divergentes; são 7 `apto_para_autorizacao` / `prosseguir_ao_ordenador`, 5 `nao_recomendado` / `nao_recomendar` e 2 `diligencia` / `devolver_em_diligencia`. Os pedidos 0111 e 0112 têm duas entradas cada, uma de diligência e outra de prosseguimento, e uma complementação correspondente para cada no acervo. O JSONL não identifica explicitamente etapa ou sessão, nem há snapshot anterior para comprovar continuidade histórica. No caso 0112, a matrícula corrigida na complementação corresponde ao acervo de servidores, mas a matrícula não consta do JSONL. A auditoria documental está concluída; a governança institucional de retenção, acesso, descarte e backups continua pendente antes do uso de dados reais. Detalhes estão em `resultados/pendencia_politica_conferencias.md` e `resultados/ACAO_HUMANA_PENDENTE.md`.

## Falhas provocadas, interface e testes

Os testes de falha agora passam pelo `Agent.run` real do Agno, com modelo controlado localmente: solicitação repetida de ferramenta até o limite configurado e erro `ModelProviderError` no caminho do modelo. O primeiro confirmou que a execução de ferramentas é limitada; o segundo retornou status de erro e foi recusado sem propagar detalhe técnico pela exceção da aplicação. Isso não é uma falha HTTP provocada em endpoint externo. O benchmark live final não registrou recusa de síntese nem erro de execução; seis bloqueios de identidade eram esperados. Veja `resultados/falhas.json`.

Na reexecução documentada, os 42 testes passaram, incluindo AppTest da interface, barreiras, memória, bloqueio pré-modelo do caso 0112, isolamento do JSONL e integração controlada com o loop Agno. `pip check` não encontrou dependências quebradas. O benchmark offline obteve 42/42 correspondências. Na revisão documental atual, os 44 testes da suíte passaram. A interface passou AppTest e o servidor Streamlit respondeu HTTP 200; não houve captura automatizada de navegador. O acervo é pequeno e controlado; a evidência não substitui aprovação institucional.

## Arquivos de evidência

- `resultados/benchmark_live.json` e `.csv`: 84 execuções finais, métricas e chamadas sanitizadas.
- `resultados/paralelismo.json`: comparação entre os dois modos.
- `resultados/memoria.json` e `resultados/eliminacao_memoria_live.json`: recuperação e limpeza.
- `resultados/falhas.json`: testes controlados e distinção de falha externa não provocada.
- `resultados/benchmark_offline.json`: referência determinística, sem chamada ao modelo.


## Recalibracao de tokens e situacao da conferencia

A estimativa didatica inicial de 2.420-2.660 tokens foi identificada como inadequada para o fluxo medido. Foi instrumentada a coleta de `input_tokens` e `output_tokens` por mensagem do assistente. Uma nova rodada live isolada (28 casos, uma repeticao) preservou os arquivos principais e registrou detalhes em `resultados/benchmark_live_calibracao.json`. Seis pedidos calibraram e seis distintos validaram. Erro absoluto de entrada: 0,12% sequencial (14.144,5 estimados; 14.161 medidos) e 0,13% paralelo (11.319,5; 11.334,5). A conta, custos e projecao hipotetica de 300 execucoes estao em `resultados/estimativa_tokens_calibracao.json`. A soma das metricas por chamada confere com o total de cada execucao elegivel.

A politica do JSONL de conferencia continua pendente de decisao institucional. Nao ha prazo nem procedimento aprovados; o uso com dados reais permanece condicionado. O bloqueio e os campos de aprovacao estao formalizados em `resultados/pendencia_politica_conferencias.md`. A interface alerta essa limitacao e a eliminacao SQLite nao e apresentada como eliminacao total. A decisao depende da unidade responsavel definir finalidade, classificacao, custodiante, perfis de acesso, prazo, backups e procedimento de descarte.


## Conferencia final dos criterios de entrega

- Ponta a ponta: `resultados/benchmark_live.json` registra 84 execucoes (tres rodadas, dois modos), 78 saidas de modelo avaliadas e aceitas, sem erros, e seis bloqueios de identidade antes do modelo.
- Agente e ferramentas: argumentos, ordem, limites, PII e status concluido estao cobertos por `testes/test_barreiras.py`, `testes/test_ferramentas.py` e `testes/test_falhas.py`; as ferramentas documentam argumentos e retornos em docstrings.
- Memoria: `resultados/memoria.json` documenta identificadores, turnos, tokens e custos; `resultados/eliminacao_memoria_live.json` verifica os bancos SQLite temporarios. A conferência JSONL é um repositório distinto; a auditoria dos registros atuais e as limitações de contexto e histórico estão descritas em `resultados/pendencia_politica_conferencias.md`. A política institucional ainda bloqueia o uso com dados reais.
- Falhas: `resultados/falhas.json` e testes provam teto de ferramentas e erro controlado dentro do Agno; nao foi provocada falha HTTP externa real.
- Interface: `app.py` apresenta progresso, minuta editavel, encaminhamento humano, justificativa obrigatoria para divergencia e mensagens padrao de erro; `testes/test_app.py` verifica renderizacao, erro e persistencia sanitizada.
- Pacote e segredos: fontes, testes, acervo hipotetico, `.env.example`, resultados, `desenho.md`, `relatorio.md` e `LEIA-ME.md` estao presentes. `.gitignore` cobre `.env`, JSONL de conferencia, SQLite e sidecars; `.env.example` nao e ignorado.
- Verificacao local daquela reexecucao: 42 testes aprovados e `pip check` sem dependencias quebradas. `git status` ainda lista os arquivos do projeto como nao rastreados naquele checkout, mas mantem `.env` local ignorado pelo Git; SQLite e caches de execucao nao fazem parte das evidencias finais. O JSONL contém evidências de conferência, com as limitações registradas nesta revisão.
