# Relatório final — Desafio 01: instrução de pedidos de diárias

## Arquitetura e segurança

O agente Agno usa as quatro ferramentas no próprio ciclo: cadastro, histórico mensal, cálculo de diárias e saldo da unidade. Os argumentos são validados contra pedido e fatos determinísticos; as dependências impõem cadastro antes de histórico/cálculo e cálculo antes de saldo. A saída estruturada do modelo é comparada com os fatos e só aparece na interface após passar pelas barreiras. Não há fallback para uma resposta determinística quando a proposta do modelo diverge.

O modelo não recebe gabarito. Identidade divergente bloqueia a chamada e a memória; PII é minimizada antes do envio. A aplicação prepara instrução para conferência humana, não decide nem autoriza despesa. O padrão operacional mantém `parallel_tool_calls=False`.

## Benchmark live final

Em 22/11/2026 foram executadas três rodadas dos 12 pedidos e duas complementações, em cada modo de paralelismo: 84 execuções. Seis pedidos com divergência de identidade foram bloqueados antes do modelo (três por modo). Nos 78 casos restantes, todas as propostas passaram pelas barreiras e coincidiram integralmente com o gabarito (39/39 por modo). Não houve recusa de saída nem erro de execução no ciclo final.

| Medida por execução do modelo | Paralelismo desligado | Paralelismo ligado |
|---|---:|---:|
| Casos avaliados / acertos exatos | 39 / 39 (100%) | 39 / 39 (100%) |
| Invocações reais de ferramenta pelo agente | 150 | 150 |
| Invocações de ferramenta por caso completo | 4 | 4 |
| Chamadas de modelo, mediana / máximo | 5 / 5 | 4 / 4 |
| Tokens totais, mediana / máximo | 12.419 / 12.672 | 10.055 / 10.256 |
| Custo estimado, mediana / máximo | US$ 0,002992 / US$ 0,0030724 | US$ 0,0025352 / US$ 0,0026056 |
| Latência, mediana / máximo | 7,00 / 10,64 s | 5,96 / 7,26 s |

O modo ligado teve menor mediana de chamadas, tokens, custo e latência nesta amostra. Os dois modos tiveram a mesma acurácia; isso não prova que o paralelismo causou a diferença de custo ou tempo. O modo desligado permanece padrão porque as ferramentas têm dependências de negócio ordenadas. A distribuição por caso, argumentos sanitizados e métricas completas estão em `resultados/benchmark_live.json`; a comparação agregada está em `resultados/paralelismo.json`.

Os custos usam os preços de referência do exercício: entrada US$ 0,20 e saída US$ 1,20 por milhão de tokens. O custo mediano sobre as 78 execuções foi US$ 0,002591 e o máximo US$ 0,0030724; os tokens totais tiveram mediana 10.204,5 e máximo 12.672. São estimativas, não valores de fatura. O fluxo completo invocou quatro ferramentas pelo agente em cada pedido elegível. Três casos incompletos por modo usaram duas; os bloqueios de identidade não chamaram o modelo.

## Memória e complementação

O ensaio live final avaliou DIA-2026-0111 e DIA-2026-0112 em três configurações: sem memória, histórico de sessão limitado e histórico com memória de usuário. O segundo turno de 0111 enviou somente a complementação; assim, recuperação do contexto foi medida separadamente da qualidade da resposta. A sessão com histórico recuperou o identificador e aplicou a complementação. Memória de usuário não acrescentou recuperação em relação ao histórico limitado.

| Configuração | Recuperou 0111 pelo histórico | Complementações validadas | Chamadas de modelo | Tokens agregados | Custo observado agregado |
|---|---:|---:|---:|---:|---:|
| Sem memória | 0/1 | 1/2 | 13 | 30.333 | US$ 0,0074466 |
| Histórico limitado | 1/1 | 2/2 | 16 | 34.914 | US$ 0,0084078 |
| Histórico + memória do usuário | 1/1 | 2/2 | 19 | 38.982 | US$ 0,0091924 |

Em 0112, a matrícula inicialmente divergente bloqueia o primeiro envio ao modelo. O primeiro turno está marcado `bloqueado_antes_do_modelo`, com zero chamadas, tokens e custo de modelo; nenhuma execução ocorreu sob a matrícula divergente. O pedido corrigido e a complementação são enviados juntos sob a identidade confirmada; esse caso verifica correção segura, não recuperação de histórico. Para esse fluxo, a recuperação por histórico está marcada como não aplicável, com justificativa no JSON. As sessões/run-alvo foram apagadas nos bancos temporários, sem resíduos; os arquivos temporários foram removidos. Evidências por turno e contagens de limpeza estão em `resultados/memoria.json` e `resultados/eliminacao_memoria_live.json`.

O registro humano em `resultados/conferencias.jsonl` é separado do SQLite e não é removido pela aba de eliminação. O prazo e o procedimento autorizado de exclusão ainda aguardam decisão institucional; por isso, a verificação de eliminação total do sistema permanece pendente para esse arquivo. O app exibe esse aviso e o uso com dados reais fica condicionado à definição da política.

## Falhas provocadas, interface e testes

Os testes de falha agora passam pelo `Agent.run` real do Agno, com modelo controlado localmente: solicitação repetida de ferramenta até o limite configurado e erro `ModelProviderError` no caminho do modelo. O primeiro confirmou que a execução de ferramentas é limitada; o segundo retornou status de erro e foi recusado sem propagar detalhe técnico pela exceção da aplicação. Isso não é uma falha HTTP provocada em endpoint externo. O benchmark live final não registrou recusa de síntese nem erro de execução; seis bloqueios de identidade eram esperados. Veja `resultados/falhas.json`.

Os 40 testes passaram, incluindo AppTest da interface, barreiras, memória, bloqueio pré-modelo do caso 0112, isolamento do JSONL e integração controlada com o loop Agno. `pip check` não encontrou dependências quebradas. O benchmark offline obteve 42/42 correspondências. A interface foi verificada por AppTest, sem captura automatizada de navegador. O acervo é pequeno e controlado; a evidência não substitui avaliação institucional ou conferência humana.

## Arquivos de evidência

- `resultados/benchmark_live.json` e `.csv`: 84 execuções finais, métricas e chamadas sanitizadas.
- `resultados/paralelismo.json`: comparação entre os dois modos.
- `resultados/memoria.json` e `resultados/eliminacao_memoria_live.json`: recuperação e limpeza.
- `resultados/falhas.json`: testes controlados e distinção de falha externa não provocada.
- `resultados/benchmark_offline.json`: referência determinística, sem chamada ao modelo.
- `resultados/arquivo_pilotos/avaliacao_correcao_relatorio/`: piloto e ciclo de prompt anterior, preservados fora do resultado final.


## Recalibracao de tokens e situacao da conferencia

A estimativa didatica inicial de 2.420-2.660 tokens foi identificada como inadequada para o fluxo medido. Foi instrumentada a coleta de `input_tokens` e `output_tokens` por mensagem do assistente. Uma nova rodada live isolada (28 casos, uma repeticao) preservou os arquivos principais e registrou detalhes em `resultados/benchmark_live_calibracao.json`. Seis pedidos calibraram e seis distintos validaram. Erro absoluto de entrada: 0,12% sequencial (14.144,5 estimados; 14.161 medidos) e 0,13% paralelo (11.319,5; 11.334,5). A conta, custos e projecao hipotetica de 300 execucoes estao em `resultados/estimativa_tokens_calibracao.json`. A soma das metricas por chamada confere com o total de cada execucao elegivel.

A politica do JSONL de conferencia continua pendente de decisao institucional. Nao ha prazo nem procedimento aprovados; o uso com dados reais permanece condicionado. O bloqueio e os campos de aprovacao estao formalizados em `resultados/pendencia_politica_conferencias.md`. A interface alerta essa limitacao e a eliminacao SQLite nao e apresentada como eliminacao total. A decisao depende da unidade responsavel definir finalidade, classificacao, custodiante, perfis de acesso, prazo, backups e procedimento de descarte.


## Conferencia final dos criterios de entrega

- Ponta a ponta: `resultados/benchmark_live.json` registra 84 execucoes (tres rodadas, dois modos), 78 saidas de modelo avaliadas e aceitas e seis bloqueios de identidade antes do modelo.
- Agente e ferramentas: argumentos, ordem, limites, PII e status concluido estao cobertos por `testes/test_barreiras.py`, `testes/test_ferramentas.py` e `testes/test_falhas.py`; as ferramentas documentam argumentos e retornos em docstrings.
- Memoria: `resultados/memoria.json` documenta identificadores, turnos, tokens e custos; `resultados/eliminacao_memoria_live.json` verifica os bancos SQLite temporarios. A conferencia JSONL e repositorio distinto, permanece pendente e bloqueada para dados reais em `resultados/pendencia_politica_conferencias.md`.
- Falhas: `resultados/falhas.json` e testes provam teto de ferramentas e erro controlado dentro do Agno; nao foi provocada falha HTTP externa real.
- Interface: `app.py` apresenta progresso, minuta editavel, encaminhamento humano, justificativa obrigatoria para divergencia e mensagens padrao de erro; `testes/test_app.py` verifica renderizacao, erro e persistencia sanitizada.
- Pacote e segredos: fontes, testes, acervo hipotetico, `.env.example`, resultados, `desenho.md`, `relatorio.md` e `LEIA-ME.md` estao presentes. `.gitignore` cobre `.env`, JSONL de conferencia, SQLite e sidecars; `.env.example` nao e ignorado.
- Verificacao local desta revisao: 40 testes aprovados e `pip check` sem dependencias quebradas. `git status` ainda lista os arquivos do projeto como nao rastreados neste checkout, mas nao lista `.env`, JSONL, SQLite, sidecars, `.venv` ou caches.
