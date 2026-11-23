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

## Medicao final comparada com a estimativa didatica

A reexecucao final de 22/11/2026 usou a versao atual do agente: 84 casos (tres rodadas dos 12 pedidos e duas complementacoes em cada modo). Seis identidades divergentes foram bloqueadas antes do modelo; as outras 78 propostas passaram pelas barreiras e acertaram integralmente o gabarito, sem erros de execucao (39/39 por modo).

| Medida por execucao do modelo | Sequencial | Paralelo |
|---|---:|---:|
| Casos avaliados / acertos exatos | 39 / 39 | 39 / 39 |
| Chamadas ao modelo, mediana / maximo | 5 / 5 | 4 / 5 |
| Invocacoes de ferramenta | 150 (4 por caso completo) | 150 (4 por caso completo) |
| Tokens de entrada, mediana | 15.088 | 12.076 |
| Tokens de saida, mediana | 490 | 507 |
| Tokens totais, mediana / maximo | 15.581 / 15.833 | 12.585 / 15.554 |
| Custo estimado, mediana / maximo | US$ 0,0036072 / US$ 0,0036836 | US$ 0,0030266 / US$ 0,0035978 |
| Latencia, mediana / maximo | 6,69 / 9,85 s | 5,81 / 7,01 s |

A referencia didatica inicial estimava 2.420-2.660 tokens de entrada em cinco chamadas e 2.330-2.510 em quatro chamadas. Na reexecucao final, as medianas de entrada foram 15.088 e 12.076 tokens: a referencia ficou muito abaixo do fluxo medido. A calibracao posterior com seis casos para ajuste e seis distintos para validacao esta separada acima; nao deve ser confundida com esta rodada final.

Pela taxa de entrada de US$ 0,20 por milhao de tokens, as medianas de entrada custaram US$ 0,0030176 no sequencial e US$ 0,0024152 no paralelo. O custo total mediano, que inclui saida a US$ 1,20 por milhao, foi US$ 0,0036072 e US$ 0,0030266. O custo mediano geral das 78 propostas foi US$ 0,0030942; maximo US$ 0,0036836. Custos sao estimativas pelos precos de referencia, nao valores de fatura.

O modo paralelo teve medianas menores de tokens, custo e latencia nesta amostra, mas isso nao demonstra causalidade. O modo sequencial permanece padrao devido as dependencias de negocio. Para hipotese de 300 execucoes mensais, o custo estimado pela mediana e US$ 1,08216 no sequencial e US$ 0,90798 no paralelo; nao e dado operacional. As linhas e argumentos sanitizados estao em resultados/benchmark_live.json; a comparacao esta em resultados/paralelismo.json.

## Reversibilidade, tempo de detecção e autonomia

| Reversibilidade do efeito | Erro detectado logo | Erro detectado tarde |
|---|---|---|
| Reversível | Agente pode agir dentro de limites | Agente pode agir com auditoria por amostra |
| Irreversível ou de alto custo para desfazer | Agente age mediante aprovação | **Agente apenas aconselha** |

O processo de diárias fica no **quadrante inferior direito: efeito de baixa reversibilidade prática (ou alto custo para desfazer) × erro detectado tarde — agente apenas aconselha**. O pagamento pode ser revertido por devolução, mas uma despesa indevida também deixa efeitos administrativos e pode ser percebida somente em auditoria; a devolução não apaga o histórico nem o custo da correção. Consideramos o efeito processual parcialmente irreversível e, portanto, de alto custo para desfazer. Esse quadrante exige conferência humana: o agente prepara a minuta, a pessoa confere e o ordenador decide; o agente não deve decidir nem autorizar sozinho. A classificação é conservadora para o exercício e não afirma que todo valor pago seja literalmente irrecuperável.

## Experimento de memoria e falhas

O ensaio live mediu seis turnos em tres configuracoes. No caso 0111, o turno de complemento sem reenviar o pedido nao recuperou o contexto sem memoria; com historico limitado, recuperou o pedido e aplicou a complementacao. Historico acrescido de memoria de usuario tambem validou os dois casos, sem recuperacao adicional e com mais chamadas/custo.

| Configuracao | Complementacoes validadas | Chamadas | Tokens | Custo observado |
|---|---:|---:|---:|---:|
| Sem memoria | 1/2 | 9 | 25.879 | US$ 0,0064038 |
| Historico limitado | 2/2 | 16 | 41.842 | US$ 0,0097234 |
| Historico + memoria do usuario | 2/2 | 19 | 46.110 | US$ 0,0106180 |

No 0112, identidade divergente foi bloqueada antes do modelo; pedido corrigido e complementacao seguiram juntos sob identidade confirmada. Bancos temporarios foram verificados e os registros-alvo eliminados. Ver resultados/memoria.json e resultados/eliminacao_memoria_live.json. O JSONL de conferencia esta presente: auditoria encontrou 14 linhas validas e completas para 12 pedidos, sem duplicatas integrais. As 14 marcacoes de concordancia estao alinhadas as recomendacoes e encaminhamentos. Para 0111 e 0112, ha uma decisao de diligencia e outra de prosseguimento, alem das complementacoes correspondentes no acervo. O arquivo nao registra etapa/sessao nem ha snapshot anterior para verificar continuidade historica. A politica institucional segue pendente em resultados/pendencia_politica_conferencias.md.

O limite de ferramentas, argumentos inventados, erro controlado do provedor, injecao e urgencia nao validada foram exercitados em testes locais. Nao foi provocada falha HTTP em endpoint externo. A rotina SQLite foi testada sem apagar um JSONL sintetico; nao existe comprovacao de retencao ou descarte para o registro de conferencia. Ver resultados/falhas.json.

## Referências do exercício e limites

As regras vêm do enunciado e de `exemplos/dados/normas.md`; os valores e casos vêm do acervo fornecido. A estimativa e a matriz de autonomia seguem a Aula 01 e as instruções do desafio. O volume de 300 pedidos/mês é hipótese substituível, não dado operacional. O conjunto é pequeno e hipotético; não prova desempenho em produção. A retenção padrão de 30 dias é decisão provisória do exercício, sujeita à aprovação institucional. A suíte local atual possui 42 testes aprovados.
