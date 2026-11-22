# Desenho do processo — instrução de pedidos de diárias

## Processo atual de instrução

Etapas do processo de referência do desafio, não observadas em uma unidade real:

1. Recebe o pedido protocolado e confere se os campos e documentos necessários estão presentes.
2. Consulta o cadastro funcional e compara a identidade e a unidade com o protocolo.
3. Consulta as diárias do mês e a situação dos comprovantes de prestação de contas.
4. Consulta a norma e a tabela para conferir antecedência, quantidade, valor e limite mensal.
5. Consulta o saldo da unidade e compara-o com o valor calculado.
6. Registra pendências ou impedimentos e encaminha o processo instruído ao ordenador, que decide.

O acervo fornecido é a fonte das regras e dos valores. Esta sequência descreve somente o processo de referência do desafio; não é observação independente do procedimento da SEMA-MT.

## Processo proposto com o agente

```text
Pedido/complementação
  -> validação e minimização de dados pessoais
  -> agente chama cadastro
  -> identidade confirmada: agente chama histórico e cálculo
  -> cálculo concluído: agente chama saldo
  -> modelo prepara Instrucao estruturada
  -> barreiras verificam argumentos, fatos, números e recomendação
  -> servidor confere a instrução e registra seu encaminhamento
  -> ordenador decide
```

As quatro funções são ferramentas do ciclo Agno. Os wrappers validam argumentos e a ordem das dependências. Uma saída recusada não é exibida nem substituída por uma resposta determinística. O agente não recebe o gabarito.

## Quadro PEAS

| Elemento | Especificação |
|---|---|
| Performance (desempenho) | Acerto contra o gabarito; seis verificações corretas; argumentos rastreáveis; ausência de dados pessoais desnecessários; tokens, custo, tempo e falhas medidos. |
| Environment (ambiente) | Acervo local com norma, cadastro funcional, histórico, tabela, unidades, pedidos e complementações. |
| Actuators (atuadores) | Quatro consultas somente leitura; produção de instrução estruturada e minuta editável; registro da conferência humana. |
| Sensors (sensores) | Pedido e complementação; identidade confirmada; fatos devolvidos pelo cadastro, histórico, cálculo e saldo. |

## Premissas de planejamento e referencia didatica (sem registro previo)

### Confiabilidade composta

Limitacao temporal: nao foi localizado registro datado que comprove uma estimativa de custo elaborada antes da implementacao. Os valores de referencia didatica abaixo nao sao apresentados como previsao historica do projeto. A calibracao com dados live foi feita posteriormente e e reportada separadamente.

A Aula 01 define confiabilidade composta como `p^n`, em que `p` é a confiabilidade suposta de cada chamada ao modelo e `n` é o número de chamadas. O planejamento inicial usa cinco chamadas ao modelo: quatro chamadas sequenciais para as ferramentas e uma chamada para a síntese final. O cenário de quatro chamadas considera a consolidação de ferramentas em chamadas paralelas:

| Chamadas planejadas | Conta a 95% por chamada | Resultado | Conta a 99% por chamada | Resultado |
|---:|---:|---:|---:|---:|
| 5 | `0,95^5` | 77,38% | `0,99^5` | 95,10% |
| 4 | `0,95^4` | 81,45% | `0,99^4` | 96,06% |

Esses números são projeções pedagógicas, não taxas de acerto medidas. O benchmark mede o resultado do fluxo real separadamente.

### Referencia didatica do enunciado: sem evidencia temporal do projeto

Estimativa de referência didática do enunciado (não há registro histórico de uma estimativa feita antes do código): a primeira chamada reúne instruções, esquemas das ferramentas, esquema da saída e pedido, com cerca de 2.060 tokens de entrada; cada chamada subsequente acrescenta aproximadamente 90 a 150 tokens de entrada. Cada chamada ao modelo conta como um passo. O cenário sequencial estima cinco passos — pedidos de ferramenta ao longo do ciclo e síntese final — e o cenário paralelo estima quatro passos:

```text
total_estimado = tokens_primeira_chamada + (passos - 1) × incremento_por_passo
estimativa inferior = 2.060 + 4 × 90  = 2.420 tokens
estimativa superior = 2.060 + 4 × 150 = 2.660 tokens
custo estimado de entrada = tokens × US$ 0,20 / 1.000.000
intervalo = US$ 0,000484 a US$ 0,000532 por caso
```

A estimativa de referência não separa tokens de saída e, por isso, o custo acima considera apenas tokens de entrada. Para quatro chamadas, o mesmo cálculo é `2.060 + 3 × (90 a 150) = 2.330 a 2.510 tokens`, ou US$ 0,000466 a US$ 0,000502 de entrada.

### Estimativa recalibrada com validação independente

A faixa didatica anterior nao e previsao observada e ficou distante do primeiro benchmark. Foi feita uma rodada live adicional de uma repeticao, salva separadamente em `resultados/benchmark_live_calibracao.json`. Seis pedidos foram usados para calibracao e seis pedidos distintos para validacao, em cada modo. So entraram execucoes completas com cinco chamadas no sequencial ou quatro no paralelo.

Para cada posicao da chamada, tomou-se a mediana de `input_tokens` das seis execucoes de calibracao. O total estimado e a soma dessas medianas. Cada chamada subsequente acrescenta seu input efetivamente cobrado, incluindo instrucoes, esquemas, historico e resultados de ferramentas reenviados; nao se calcula delta entre contagens de chamadas. As metricas por mensagem retornadas pelo Agno somaram o mesmo total que `RunOutput.metrics` em todas as execucoes elegiveis.

| Modo | Tokens de entrada medianos por chamada na calibracao | Estimativa | Mediana medida nos seis pedidos de validacao | Erro absoluto | Custo total estimado | Custo total medido mediano |
|---|---|---:|---:|---:|---:|---:|
| Sequencial, 5 chamadas | 2.613; 2.707,5; 2.825; 2.952,5; 3.046,5 | 14.144,5 tokens | 14.161 tokens | 0,12% | US$ 0,0034409 | US$ 0,0034469 |
| Paralelo, 4 chamadas | 2.613; 2.707,5; 2.952,5; 3.046,5 | 11.319,5 tokens | 11.334,5 tokens | 0,13% | US$ 0,0028831 | US$ 0,0029011 |

O erro e `abs(estimativa - mediana medida) / mediana medida x 100`; os dois modos ficam abaixo do limite de 3% na amostra de validacao. A memoria de calculo, os pedidos de cada grupo, tokens de saida e custos estao em `resultados/estimativa_tokens_calibracao.json`. Com a mediana de custo total da validacao, 300 execucoes mensais projetam US$ 1,03407 no sequencial e US$ 0,87033 no paralelo. O volume e os precos sao hipotese do exercicio, nao custo de fatura.

## Medição final comparada com a estimativa

O benchmark final (22/11/2026) executou 84 casos: três rodadas de 14 casos em cada modo. Seis divergências de identidade foram bloqueadas antes do modelo. As 78 saídas elegíveis passaram pelas barreiras e acertaram integralmente o gabarito.

| Métrica das saídas de modelo | Sequencial | Paralelo |
|---|---:|---:|
| Casos avaliados / acertos | 39 / 39 | 39 / 39 |
| Chamadas de modelo, mediana / máximo | 5 / 5 | 4 / 4 |
| Invocações de ferramentas pelo agente | 150 (4 por caso completo) | 150 (4 por caso completo) |
| Tokens de entrada acumulados na execução, mediana | 11.906 | 9.530 |
| Custo mediano da entrada, calculado na mesma base | US$ 0,0023812 | US$ 0,001906 |
| Tokens de saída, mediana | 508 | 525 |
| Tokens totais, mediana / máximo | 12.419 / 12.672 | 10.055 / 10.256 |
| Custo, mediana / máximo | US$ 0,002992 / US$ 0,0030724 | US$ 0,0025352 / US$ 0,0026056 |
| Latência, mediana / máximo | 7,00 / 10,64 s | 5,96 / 7,26 s |

Para esta comparacao do benchmark original, `tokens_entrada` e o total de entrada acumulado nas chamadas ao modelo de **uma execucao** (`RunOutput.metrics.input_tokens` registrado em cada linha); nao e o total de uma rodada inteira nem a soma das 84 execucoes. Essa comparacao retrospectiva usa somente a referencia didatica: no modo sequencial, 11.906 tokens medidos ficaram 347,6%-392,0% acima dos 2.420-2.660 estimados; no paralelo, 9.530 ficaram 279,7%-309,0% acima dos 2.330-2.510. Portanto, a referencia didatica nao atingiu a proximidade de 3%. A calibracao posterior, com pedidos distintos para validacao, e apresentada em secao separada abaixo. O percentual usa `(tokens medidos - tokens estimados) / tokens estimados x 100`, comparando os extremos do intervalo. `tokens_total` inclui entrada e saida e nao e comparado a referencia de entrada.

O custo pré-estimado considera somente entrada: US$ 0,000484–0,000532 em cinco passos e US$ 0,000466–0,000502 em quatro. Para comparar a mesma base, o custo mediano medido da entrada é `tokens_entrada × US$ 0,20 / 1.000.000`: US$ 0,0023812 no modo sequencial e US$ 0,001906 no paralelo. O custo total medido também inclui saída, à taxa de US$ 1,20 por milhão, e está discriminado na tabela. Assim, estimativa de entrada é comparada a entrada medida; o custo total é apresentado à parte. A estimativa inicial é um baseline didático, não uma previsão precisa para o ciclo real.

O modo paralelo teve menor mediana de chamadas, tokens, custo e latência nesta amostra; ambos tiveram 39/39 acertos. Não se atribui causalidade a essa diferença. O padrão operacional segue sequencial porque as ferramentas têm dependências de negócio: cadastro precede histórico/cálculo e cálculo precede saldo. Custos não são valores de fatura. As linhas e argumentos sanitizados estão em `resultados/benchmark_live.json`; a agregação está em `resultados/paralelismo.json`.

O custo mediano geral foi US$ 0,002591, o máximo US$ 0,0030724 e a razão máximo/mediana 1,19. A mediana geral foi 10.204,5 tokens, com máximo 12.672. Para hipótese de dimensionamento de 300 pedidos por mês, a projeção pela mediana é `300 × US$ 0,002591 = US$ 0,7773`; pela execução mais cara, `300 × US$ 0,0030724 = US$ 0,92172`.

## Reversibilidade, tempo de detecção e autonomia

| Reversibilidade do efeito | Erro detectado logo | Erro detectado tarde |
|---|---|---|
| Reversível | Agente pode agir dentro de limites | Agente pode agir com auditoria por amostra |
| Irreversível ou de alto custo para desfazer | Agente age mediante aprovação | **Agente apenas aconselha** |

O processo de diárias fica no **quadrante inferior direito: efeito de baixa reversibilidade prática (ou alto custo para desfazer) × erro detectado tarde — agente apenas aconselha**. O pagamento pode ser revertido por devolução, mas uma despesa indevida também deixa efeitos administrativos e pode ser percebida somente em auditoria; a devolução não apaga o histórico nem o custo da correção. Consideramos o efeito processual parcialmente irreversível e, portanto, de alto custo para desfazer. Esse quadrante exige conferência humana: o agente prepara a minuta, a pessoa confere e o ordenador decide; o agente não deve decidir nem autorizar sozinho. A classificação é conservadora para o exercício e não afirma que todo valor pago seja literalmente irrecuperável.

## Experimento de memória e falhas

O ensaio mediu seis linhas (dois casos em três configurações). O histórico limitado recuperou a diligência 0111 na complementação isolada e validou sua aplicação. Sem memória, o segundo turno não recuperou o caso. Memória de usuário não trouxe recuperação adicional e elevou chamadas e custo. No 0112, a matrícula divergente foi bloqueada e a correção foi enviada junto ao pedido sob identidade confirmada. Os bancos temporários foram inspecionados e removidos sem resíduos dos registros-alvo. Ver `resultados/memoria.json` e `resultados/eliminacao_memoria_live.json`.

O limite de ferramentas e o erro controlado do provedor foram testados pelo `Agent.run` Agno com o modelo stubado localmente. Não foi provocada falha HTTP em endpoint externo. A rotina de exclusão do SQLite foi testada sem alterar um arquivo JSONL sintético separado; para o arquivo real de conferências, prazo e exclusão continuam pendentes de decisão institucional. Ver `resultados/falhas.json` e `resultados/eliminacao_memoria_live.json`.

## Referências do exercício e limites

As regras vêm do enunciado e de `exemplos/dados/normas.md`; os valores e casos vêm do acervo fornecido. A estimativa e a matriz de autonomia seguem a Aula 01 e as instruções do desafio. O volume de 300 pedidos/mês é hipótese substituível, não dado operacional. O conjunto é pequeno e hipotético; não prova desempenho em produção. A retenção padrão de 30 dias é decisão provisória do exercício, sujeita à aprovação institucional. A suíte local atual possui 40 testes aprovados.
